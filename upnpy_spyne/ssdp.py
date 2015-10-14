'''
Created on 6 sept. 2014

@author: Bertrand Verdu
'''
import time
import logging
import socket
from random import Random
from twisted.internet import task, reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.python import log
from twisted.application import service, internet
from upnpy_spyne.utils import http_parse_raw, get_default_v4_address,\
    headers_join, build_notification_type


SSDP_ADDR_V4 = "239.255.255.250"
SSDP_ADDR_V6 = "[FF05::C]"
SSDP_PORT = 1900


class SSDPServer(service.MultiService):  # @UndefinedVariable
    '''
    Main class to manage SSDP
    '''
#     __slots__ = ['name',
#                  'services',
#                  'device',
#                  'targets',
#                  'listener',
#                  'ssdp',
#                  'client',
#                  'ssdp_client',
#                  '__dict__']
    name = "SSDPServer"
    targets = ['ssdp:all', 'upnp:rootdevice', ]
    listener = None

    def __init__(self, device):
        self.services = []
        '''
        Initialization of SSDP server
        '''
        self.device = device
        if self.device.uuid is None:
            raise ValueError()
        self.targets.append('uuid:' + self.device.uuid)
        self.targets.append(self.device.deviceType)
        for service in self.device.services:
            self.targets.append(service.serviceType)
        if not self.listener:
            self.listener = SSDP_Listener(self)
            self.ssdp = internet.MulticastServer(  # @UndefinedVariable
                SSDP_PORT,
                self.listener,
                listenMultiple=True,
                interface=SSDP_ADDR_V4)
            self.ssdp.setServiceParent(self)
            self.client = SSDP_Client(self, get_default_v4_address())
            self.ssdp_client = internet.UDPServer(  # @UndefinedVariable
                0, self.client, self.client.interface)
            self.ssdp_client.setServiceParent(self)

    def startService(self):
        '''
        '''
#         self.signal("started")
        log.msg('SSDP Service started', loglevel=logging.INFO)

    def stopService(self):
        self.client.sendall_NOTIFY(None, 'ssdp:byebye', True)


class SSDP_Client(DatagramProtocol):
    __slots__ = ['ssdp',
                 'interface',
                 'notifySequenceInterval',
                 'notifySequenceLoop',
                 'running',
                 'device',
                 '__dict__']
    device = False

    def __init__(self, ssdp, interface, device=True, notifyInterval=1800):
        self.ssdp = ssdp
        self.interface = interface
        if device:
            self.device = device
            self.notifySequenceInterval = notifyInterval
            self.notifySequenceLoop = task.LoopingCall(
                self._notifySequenceCall)
        self.running = False

    def startProtocol(self):
        if self.device:
            reactor.callLater(  # @UndefinedVariable
                0, self._notifySequenceCall, True)
            self.notifySequenceLoop.start(self.notifySequenceInterval)

    def datagramReceived(self, data, (address, port)):
        #  log.msg("Unicast datagramReceived() from %s:%s" % (address, port))
        if not self.device:
            try:
                self.ssdp.update_hosts(http_parse_raw(data)[3], unicast=True)
            except AttributeError:
                pass

    def respond(self, headers, (address, port)):
        log.msg("respond() %s %d" % (address, port))
        msg = 'HTTP/1.1 200 OK\r\n'
        msg += headers_join(headers)
        msg += '\r\n'

        try:
            self.transport.write(msg, (address, port))
        except socket.error, e:
            log.err("socket.error: %s" % e)

    def send(self, method, headers, (address, port)):
        #  log.msg("send() %s:%s" % (address, port))
        msg = '%s * HTTP/1.1\r\n' % method
        msg += headers_join(headers)
        msg += '\r\n'

        try:
            self.transport.write(msg, (address, port))
        except socket.error, e:
            log.err("socket.error: %s" % e)

    def send_MSEARCH(self, st, uuid=None, man='"ssdp:discover"'):
        #  log.msg('send MSEARCH')
        headers = {
            'HOST': '239.255.255.250:1900',
            'ST': st,
            'MX': 1,
            'MAN': man}
        self.send('M-SEARCH', headers, (SSDP_ADDR_V4, SSDP_PORT))

    def send_NOTIFY(self, nt, uuid=None, nts='ssdp:alive'):
        if self.ssdp.device.bootID is None:
            self.ssdp.device.bootID = int(time.time())

        location = self.ssdp.device.getLocation(get_default_v4_address())

        if uuid is None:
            uuid = self.ssdp.device.uuid

        usn, nt = build_notification_type(uuid, nt)

        log.msg("send_NOTIFY %s:%s" % (nts, usn))

        headers = {
            # max-age is notifySequenceInterval + 10 minutes
            'CACHE-CONTROL': 'max-age = %d' % (
                self.notifySequenceInterval + (10 * 60)),
            'LOCATION': location,
            'SERVER': self.ssdp.device.server,
            'NT': nt,
            'NTS': nts,
            'USN': usn,
            'BOOTID.UPNP.ORG': self.ssdp.device.bootID,
            'CONFIGID.UPNP.ORG': self.ssdp.device.configID
        }

        self.send('NOTIFY', headers, (SSDP_ADDR_V4, SSDP_PORT))

    def sendall_NOTIFY(self, delay=1, nts='ssdp:alive', blocking=False):
        if delay is None:
            delay = 0

        notifications = [
            # rootdevice
            'upnp:rootdevice',
            '',
            self.ssdp.device.deviceType,
        ]

        # Add service notifications
        for service in self.ssdp.device.services:
            notifications.append(service.serviceType)

        # Queue notify calls
        cur_delay = delay
        for nt in notifications:
            uuid = None
            if type(nt) is tuple:
                if len(nt) == 1:
                    nt = nt[0]
                elif len(nt) == 2:
                    nt, uuid = nt
                else:
                    raise ValueError()
                # Execute the call
            if blocking:
                self.send_NOTIFY(nt, uuid, nts)
            else:
                reactor.callLater(  # @UndefinedVariable
                    cur_delay, self.send_NOTIFY, nt, uuid, nts)
                cur_delay += delay

    def _notifySequenceCall(self, initial=False):
        log.msg("_notifySequenceCall initial=%s" % initial)

        # 3 + 2d + k
        #  - 3  rootdevice
        #  - 2d embedded devices
        #  - k  distinct services
        # TODO: Embedded device calls
        call_count = 3 + len(self.ssdp.device.services)

        call_delay = self.notifySequenceInterval / call_count
        if initial:
            call_delay = 1

        self.sendall_NOTIFY(call_delay)


class SSDP_Listener(DatagramProtocol):
    __slots__ = ['ssdp',
                 'responseExpire',
                 'running',
                 'rand',
                 '__dict__']

    def __init__(self, ssdp, cache=None, responseExpire=900):
        self.ssdp = ssdp
        self.responseExpire = responseExpire
        self.cache = cache
        self.running = False
        self.rand = Random()

    def startProtocol(self):
        self.transport.setTTL(2)
        self.transport.joinGroup(SSDP_ADDR_V4)
#         log.msg("joined on ANY")

    def datagramReceived(self, data, (address, port)):
        #  log.msg("datagramReceived() from %s:%s" % (address, port))

        #         method, path, version, headers = http_parse_raw(data)
        remote_call = http_parse_raw(data)
        method = remote_call[0]
        headers = remote_call[3]
        del remote_call
        if method == 'M-SEARCH':
            self.received_MSEARCH(headers, (address, port))
        elif method == 'NOTIFY':
            self.received_NOTIFY(headers, (address, port))
        else:
            log.msg("Unhandled Method '%s'" % method, loglevel=logging.DEBUG)

    def received_MSEARCH(self, headers, (address, port)):
        #  log.msg("received_MSEARCH: %s" % headers)
        try:
            #             host = headers['host']
            man = str(headers['man']).strip('"')
            mx = int(headers['mx'])
            st = headers['st']
#             log.msg('man = %s, mx = %s, st= %s \n' % (man, mx, st))
        except KeyError:
            log.msg("Received message with missing headers",
                    loglevel=logging.DEBUG)
            return
        except ValueError:
            log.msg("Received message with invalid values",
                    loglevel=logging.DEBUG)
            return

        if man != 'ssdp:discover':
            log.msg(
                "Received message where MAN != 'ssdp:discover'",
                loglevel=logging.DEBUG)
            return
        if st == 'ssdp:all':
            for target in self.ssdp.targets:
                reactor.callLater(  # @UndefinedVariable
                    self.rand.randint(1, mx),
                    self.respond_MSEARCH, target, (address, port))
        elif st in self.ssdp.targets:
            reactor.callLater(  # @UndefinedVariable
                self.rand.randint(1, mx),
                self.respond_MSEARCH, st, (address, port))
#         else:
#             log.msg("ignoring %s"% st)

    def respond(self, headers, (address, port)):
        log.msg("respond to %s:%s, header=%s" % (address, port, headers))
        msg = 'HTTP/1.1 200 OK\r\n'
        msg += headers_join(headers)
        msg += '\r\n'

        try:
            self.transport.write(msg, (address, port))
        except socket.error, e:
            log.err("socket.error: %s" % e)

    def respond_MSEARCH(self, st, (address, port)):
        log.msg("respond_MSEARCH to %s:%s, headers=%s" % (address, port, st))

        if self.ssdp.device.bootID is None:
            self.ssdp.device.bootID = int(time.time())

        if address == '127.0.0.1':
            location = self.ssdp.device.getLocation('127.0.0.1')
        else:
            location = self.ssdp.device.getLocation(get_default_v4_address())

        usn, st = build_notification_type(self.ssdp.device.uuid, st)

        headers = {
            'CACHE-CONTROL': 'max-age = %d' % self.responseExpire,
            'EXT': '',
            'LOCATION': location,
            'SERVER': self.ssdp.device.server,
            'ST': st,
            'USN': usn,
            'OPT': '"http://schemas.upnp.org/upnp/1/0/"; ns=01',
            '01-NLS': self.ssdp.device.bootID,
            'BOOTID.UPNP.ORG': self.ssdp.device.bootID,
            'CONFIGID.UPNP.ORG': self.ssdp.device.configID,
        }

        self.respond(headers, (address, port))

    def received_NOTIFY(self, headers, (address, port)):
        #         log.msg("received_NOTIFY: %s" % headers)
        try:
            if headers['nt'] == 'upnp:rootdevice':
                self.ssdp.update_hosts(headers)
        except AttributeError:
            pass
