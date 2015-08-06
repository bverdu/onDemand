'''
Created on 18 fev. 2015

@author: babe
'''
import sys
import socket
import uuid
import time
from urlparse import urlparse
from lxml import etree as et
from twisted.application import service, internet
from twisted.python import log
from twisted.internet import reactor, task, endpoints, defer
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.web import server, error as werror
from twisted.web.resource import Resource
# from twisted.names.srvconnect import SRVConnector

from twisted.words.xish import domish
from twisted.words.protocols.jabber import xmlstream, client
from twisted.words.protocols.jabber.client import IQ
from twisted.words.protocols.jabber.jid import JID, parse
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.client import Service, RemoteProcedureBase, ClientBase
from spyne.client.twisted import _Producer, _Protocol
from upnpy_spyne import ssdp
from upnpy_spyne.utils import get_default_v4_address, XmlDictConfig
import logging


logger = logging.getLogger(__name__)

SSDP_ADDR_V4 = "239.255.255.250"
SSDP_ADDR_V6 = "[FF05::C]"
SSDP_PORT = 1900


class Controller(service.MultiService):
    targets = {}
    services = []
    binary_light_list = []
    hvac_list = []
    media_player_list = []
    server_list = []
    shutter_list = []
    camera_list = []
    multiscreen_list = []
    dimmable_light_list = []
    ambi_light_list = []
    searchables = {'upnp:rootdevice': log.msg}
    event_catcher = None
    cloud_event_catcher = None
    subscriptions = {}
    subscriptions_cloud = {}
    ready_to_close = False
    current_device = None
    cloud = False
    lan = False
    agent = None

    def __init__(
            self, parent=None, searchables=None, xmldir=None,
            network='lan', cloud_user=None, cloud_servers=[]):
        print('controller start')
        self.xmldir = xmldir
        self.devices = []
        self._services = {}
        self.parent = parent
        self.uuid = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                socket.gethostname()+'onDemand_Controller'))
        if searchables:
            for typ in searchables:
                self.searchables.update({typ[0]: typ[1]})
#                 print(self.searchables)
        if network in ('lan', 'both'):
            self.lan = True
            self.listener = ssdp.SSDP_Listener(self)
            self.mcast = internet.MulticastServer(  # @UndefinedVariable
                SSDP_PORT,
                self.listener,
                listenMultiple=True,
                interface=SSDP_ADDR_V4)
            self.mcast.setServiceParent(self)
            self.ssdp_cli = ssdp.SSDP_Client(
                self, get_default_v4_address(), device=False)
            self.ucast = internet.UDPServer(  # @UndefinedVariable
                0, self.ssdp_cli, self.ssdp_cli.interface)
            self.ucast.setServiceParent(self)
#             self.agent = Agent(reactor)
        if network in ('cloud', 'both'):
            if cloud_user:
                print('cloud !')
                self.cloud = True
                self._jid, secret = cloud_user
                self.users = {self._jid: {'state': True}}
                for user in cloud_servers:
                    self.users.update({user: {'state': False}})
                self.hosts = {}
                self.resourcepart = ''.join((
                    'urn:schemas-upnp-org:cloud-1-0:ControlPoint:1:uuid:',
                    self.uuid))
                full_jid = ''.join(
                    (self._jid, '/', self.resourcepart))
                self.jid = jid = JID(full_jid)
                self.reactor = reactor
                f = client.XMPPClientFactory(jid, secret)
                f.addBootstrap(
                    xmlstream.STREAM_CONNECTED_EVENT, self.cloud_connected)
                f.addBootstrap(
                    xmlstream.STREAM_END_EVENT, self.cloud_disconnected)
                f.addBootstrap(
                    xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
                f.addBootstrap(
                    xmlstream.INIT_FAILED_EVENT, self.cloud_failed)
                self.connector = endpoints.HostnameEndpoint(
                    reactor, jid.host, 5222)
                self.factory = f
#                 self.connector = SRVConnector(
#                     reactor, 'xmpp-client', jid.host, f, defaultPort=5222)
        log.startLogging(sys.stdout)

    def startService(self):
        '''
        '''
        service.MultiService.startService(self)
        if self.cloud:
            log.msg('cloud Service starting')
            self.connector.connect(self.factory)
        if self.lan:
            t = task.LoopingCall(self.search_devices)
            t.start(15)
            log.msg('SSDP Service started')

    def stopService(self):
        print('stopping...')
        self.clean()
        time.sleep(5)
        service.MultiService.stopService(self)
#         reactor.callLater(10, reactor.stop)  # @UndefinedVariable

    def cloud_disconnected(self, reason):
        log.msg('cloud disconnected')

    def cloud_failed(self, failure):
        print('Initialization failed.')
        print(failure)

        self.xmlstream.sendFooter()

    @inlineCallbacks
    def clean(self):
        def cleaned(res):
            print('cleaned')
            self.ready_to_close = True
        dl = []
        if self.lan:
            for name in self.subscriptions:
                dl.append(self.unsubscribe(name))
        if self.cloud:
            self.xmlstream.sendFooter()
            for name in self.subscriptions_cloud:
                dl.append(self.unsubscribe(name))
        d = defer.DeferredList(dl)
        d.addCallback(cleaned)
        r = yield d
        print(r)

    def cloud_connected(self, xs):
        print 'Connected.'
        self._services = {}
        self.subscriptions = {}
        self.xmlstream = xs
#         xs.rawDataInFn = self.rawDataIn

    def authenticated(self, xs):

        print "Authenticated."
        presence = domish.Element((None, 'presence'))
        xs.send(presence)
        xs.addObserver('/presence', self.on_presence)
        xs.addObserver('/iq', self.on_iq)
        xs.addObserver('/message', self.on_event)
        disco = IQ(xs, 'get')
        disco.addElement(('http://jabber.org/protocol/disco#items', 'query'))
        disco.addCallback(self.cloud_discovered)
        disco.send()
#         self.reactor.callLater(120, xs.sendFooter)
        self.reactor.callLater(5, self.check_users)

    def check_users(self):
        for user, value in self.users.items():
            if value['state'] is False:
                iq = IQ(self.xmlstream, 'set')
                query = domish.Element(('jabber:iq:roster', 'query'))
                item = domish.Element((None, 'item'))
                item['name'] = user
                item['jid'] = user
                item.addElement('group', content='hosts')
                query.addChild(item)
                iq.addChild(query)
                iq.addCallback(self.cloud_subscribe, user)
#                 print('send IQ: %s' % (iq.toXml().encode('utf-8')))
                iq.send()

    def cloud_subscribe(self, jid, result):
        print('Subscribe callback from %s' % jid)
        presence = domish.Element((None, 'presence'))
        presence['type'] = 'subscribe'
        presence['to'] = jid
        self.xmlstream.send(presence)

    def on_event(self, message):
        if not self.cloud_event_catcher:
            reactor.callLater(1, self.on_event, message)  # @UndefinedVariable
            return
        if message.name == 'iq':
            if message['type'] == 'result':
                try:
                    last = ''
                    for child in message.children[0].children[0].children:
                        last = child.children[0]
                except KeyError:
                    return
                print(message.toXml())
                print(last.toXml())
                self.cloud_event_catcher.receive(last.toXml().encode('utf-8'))
        elif message.children[0].name == 'event':
            evt = message.children[0]
            items = evt.children[0]
            node_name = str(items['node'])
            if node_name in self.subscriptions_cloud:
                for item in items.children:
                    propertyset = item.children[0]
                    self.cloud_event_catcher.receive(
                        (node_name, propertyset.toXml().encode('utf-8'),))

    def rawDataIn(self, buf):
        print(
            "Device RECV: %s"
            % unicode(buf, 'utf-8').encode('ascii', 'replace'))

    def on_presence(self, resp):
        print('got presence: %s' % resp.toXml().encode('utf-8'))
#         print('from :%s' % resp['from'])
        user, host, res = parse(resp['from'])
        jid = '@'.join((user, host))
        if resp.hasAttribute('type'):
            if resp['type'] == 'subscribed':
                if jid in self.users:
                    self.users[jid].update({'state': True})
                    if 'services' in self.users[jid]:
                        self.users[jid]['services'].append(res)
                    else:
                        self.users[jid].update({'services': [res]})
                    presence = domish.Element((None, 'presence'))
                    presence['type'] = 'subscribe'
                    presence['to'] = resp['from']
                    self.xmlstream.send(presence)
                else:
                    presence = domish.Element((None, 'presence'))
                    presence['type'] = 'denying'
                    presence['to'] = resp['from']
                    self.xmlstream.send(presence)
            elif resp['type'] == 'unsubscribed':
                if jid in self.users:
                    print('subscription failed: %s' % resp['from'])
                return
        for child in resp.elements():
            if child.name == 'ConfigIdCloud':
                print('Found UPnP Cloud device : %s type is: %s' % (
                    jid,
                    res))
                info = IQ(self.xmlstream, 'get')
#                 info['to'] = resp['from']
                query = domish.Element(
                    ('urn:schemas-upnp-org:cloud-1-0', 'query'))
                query['type'] = 'description'
                query['name'] = ':'.join(res.split(':')[-2:])
                info.addChild(query)
                info.addCallback(self.on_description, res)
#                 info.send()
                info.send(to=resp['from'])

    def on_description(self, resource, iq):
        location = iq['from']
        clbk = self.searchables[
            self.searchables.keys()[0]]
        if iq['type'] == 'result':
            if iq.children[0].name == 'query'\
                    and iq.children[0]['type'] == 'described':
                self.update_devices(
                    resource,
                    location,
                    clbk,
                    xml=iq.children[0].children[0].toXml())

    def cloud_discovered(self, iq):
        print('Discovered item: %s' % iq.toXml().encode('utf-8'))
        if iq['type'] == 'result':
            for child in iq.children:
                if child.name == 'query':
                    for grandchild in child.children:
                        if grandchild['jid'].encode('utf-8') == self.full_jid:
                            continue
                        if grandchild['name'].encode('utf-8')\
                                in self.hosts:
                            self.hosts[
                                grandchild['name'].encode('utf-8')].append(
                                    grandchild['jid'].encode('utf-8'))
                        else:
                            self.hosts.update(
                                {grandchild['name'].encode('utf-8'):
                                    [grandchild['jid'].encode('utf-8')]})
#         print(self.hosts)

    def on_iq(self, iq):
        pass
#         print('got iq: %s' % iq.toXml())
#         try:
#             print('from :%s' % iq['from'])
#         except KeyError:
#             print('From I don\'t know: %s' % iq.toXml())
#         print('type: %s' % iq['type'])

    def search_devices(self):
        for search in self.searchables:
            self.ssdp_cli.send_MSEARCH(search, uuid=self.uuid)

    def update_hosts(self, host, unicast=False):

        if 'location' in host:
            if 'usn' in host:
                if host['usn'] in self.devices:
                    return
                device = host['usn'].split('::')
                if len(device) > 1:
                    uid = device[0].split(':')[1]
                    if uid in self.devices:
                        return
                    typ = device[1]
                    if typ in self.searchables:
                        self.update_devices(
                            uid, host['location'], self.searchables[typ])
                        self.devices.append(uid)

    def update_devices(self, uid, location, callback_fct, xml=None):
        log.msg('new device %s: %s' % (uid, location))
        if '@' in location:
            print('cloud!')
            if xml:
                callback_fct(self.parse_host(xml, location, uid))
                return
        else:
            if not self.agent:
                self.agent = Agent(reactor)
            d = self.agent.request('GET', location)
            d.addCallback(readBody)
        d.addCallback(self.parse_host, *(location, uid))
        d.addCallback(callback_fct)

    def parse_host(self, xml, location, uid):
        typ = 'upnp'
        if '@' in location:
            url_prefix = ''.join(('xmpp://', location))
            net = 'cloud'
        else:
            url_prefix = urlparse(location).netloc
            net = 'lan'
        try:
            root = et.fromstring(xml)
        except:
            log.err('bad xml: %s' % xml)
            return {}
        host = {}
        icon = None
        for children in root:
            if children.tag.split('}')[-1] == 'device':
                for att in children:
                    if att.tag.split('}')[-1] == 'friendlyName':
                        fname = att.text
                    if att.tag.split('}')[-1] == 'deviceType':
                        devtype = att.text
                        if 'Source' in att.text:
                            typ = 'oh'
                    if att.tag.split('}')[-1] == 'iconList':
                        for ico in att:
                            #  log.msg(ico)
                            for info in ico:
                                if info.tag.split('}')[-1] == 'width':
                                    if int(info.text) <= 96:
                                        if ico[4].text.startswith('/'):
                                            icon = 'http://'\
                                                + url_prefix\
                                                + ico[4].text
                                        else:
                                            icon = ico[4].text
                    if att.tag.split('}')[-1] == 'serviceList':
                        svc = {}
                        for serv in att:
                            d = {}
                            for info in serv:
                                if 'URL' in info.tag.split('}')[-1]:
                                    if net == 'lan':
                                        d.update({info.tag.split('}')[-1]:
                                                  'http://' +
                                                  url_prefix + info.text})
                                    else:
                                        d.update(
                                            {info.tag.split('}')[-1]:
                                             url_prefix + info.text})
                                else:
                                    d.update(
                                        {info.tag.split('}')[-1]: info.text})
                            svc.update({d['serviceType']: d})
        host.update(
            {uid: {
                'name': fname,
                'devtype': devtype,
                'icon': icon,
                'services': svc,
                'type': typ,
                'network': net,
                'location': location}})
#         log.msg(host)
        return host

    def subscribe(self, *args, **kwargs):
        if args[0][args[0].keys()[0]]['network'] == 'lan':
            return self.subscribe_classic(*args, **kwargs)
        else:
            return self.subscribe_cloud(*args, **kwargs)

    def subscribe_classic(
            self, device, svc, var, callback_fct=log.msg, callback_args=()):
        name = device.keys()[0]
        dev = device[name]

        def subscribe_failed(err, name):
            self.parent.remove_device(name.split('_')[0])

        def subscribed(req, raddr, host, name):
            try:
                uuid = req.headers.getRawHeaders('sid')[0]
                print('subscription uuid = %s' % uuid)
                if name in self.subscriptions:
                    if host in self.subscriptions[name]:
                        self.subscriptions[name][host].update({uuid: raddr})
                    else:
                        self.subscriptions[name].update({host: {uuid: raddr}})
                else:
                    self.subscriptions.update({name: {host: {uuid: raddr}}})
                reactor.callLater(  # @UndefinedVariable
                    20, self.renew_subscription, uuid)
                return name
            except TypeError:
                return subscribe_failed(None, name)

        if self.event_catcher is None:
            self.event_catcher = EventServer()
            self.event_catcher.setServiceParent(self)
        subscription_id = '_'.join((name, svc.split(':')[-2]))
        childpath = '_'.join((subscription_id, 'event',))
#         log.err(childpath)
        if childpath in self.event_catcher.catcher.childs:
            self.event_catcher.catcher.childs[childpath].update(
                {var: (callback_fct, callback_args,)})
        else:
            self.event_catcher.catcher.childs.update(
                {childpath: {var: (callback_fct, callback_args,)}})
#         log.err(self.event_catcher.catcher.childs)
        if subscription_id in self.subscriptions:
            for k, value in self.event_catcher.catcher.unfiltered.items():
                if k == var:
                    if value == 'False':
                        value = False
                    elif value == 'True':
                        value = True
                    if isinstance(callback_args, str)\
                            or isinstance(callback_args, bool):
                        callback_fct(value, callback_args)
                    else:
                        callback_fct(value, *callback_args)
                    del self.event_catcher.catcher.unfiltered[k]
            return defer.succeed(None)
        else:
            self.subscriptions.update({subscription_id: {}})
        clbk = '<'+'http://' + get_default_v4_address() + ':' +\
            str(self.event_catcher.getPort()) + '/' + childpath + '>'
#             print(clbk)
        headers = {'HOST': [get_default_v4_address() + ':' +
                            str(self.event_catcher.getPort())],
                   'CALLBACK': [clbk],
                   'NT': ['upnp:event'],
                   'TIMEOUT': ['Second-25']}
        if svc in dev['services']:
            log.err(svc)
            addr = dev['services'][svc]['eventSubURL']
            log.err(addr)
            d = self.agent.request(
                'SUBSCRIBE',
                addr,
                Headers(headers))
            d.addCallbacks(
                subscribed,
                subscribe_failed,
                callbackArgs=(addr, headers['HOST'][0], subscription_id),
                errbackArgs=(subscription_id,))
            return d
#         log.err(dev['services'])
        return defer.fail(Exception('Service unknow'))

    def renew_subscription(self, sid):

        def renewed(res):
            print('subscription %s successfully renewed' % sid)
            reactor.callLater(  # @UndefinedVariable
                20, self.renew_subscription, sid)

        def failed(res):
            for name in self.subscriptions:
                for host in self.subscriptions[name]:
                    if sid in self.subscriptions[name][host]:
                        del self.subscriptions[name][host][sid]
                        self.parent.remove_device(name.split('_')[0])
        for name in self.subscriptions:
            for host in self.subscriptions[name]:
                if sid in self.subscriptions[name][host]:
                    headers = {'HOST': [host], 'SID': [sid],
                               'TIMEOUT': ['Second-25']}
                    d = self.agent.request(
                        'SUBSCRIBE',
                        self.subscriptions[name][host][sid],
                        Headers(headers))
                    d.addCallbacks(renewed, failed)
                    return d

    def unsubscribe(self, name):
        #         print('unsuscribe: %s' % name)
        deferreds = []
        if name in self.subscriptions:
            for host in self.subscriptions[name]:
                for sid in self.subscriptions[name][host]:
                    deferreds.append(self.unsubscribe_host(
                        sid,
                        host,
                        self.subscriptions[name][host][sid], name))
        if name in self.subscriptions_cloud:
            return self.unsubscribe_cloud(name)
        if len(deferreds) > 0:
            print(deferreds)
            d = defer.DeferredList(deferreds)
        else:
            d = defer.succeed('nothing to do')
        return d

    def unsubscribe_cloud(self, name):

        def unsubscribed(name, d, res):
            if res['type'] == 'result':
                print('unsubscribed: %s' % name)
                del self.subscriptions_cloud[name]
                d.callback(None)
            else:
                d.errback(Exception(res.toXml()))

        d = defer.Deferred()
        iq = IQ(self.xmlstream, 'set')
        ps = domish.Element(('http://jabber.org/protocol/pubsub', 'pubsub'))
        unsubscribe = domish.Element((None, 'unsubscribe'))
        unsubscribe['node'] = name
        unsubscribe['jid'] = self.jid.full()
        ps.addChild(unsubscribe)
        iq.addChild(ps)
        iq.addCallback(unsubscribed, name, d)
        iq.send(to='pubsub.'+self.jid.host)
        return d

    def unsubscribe_host(self, sid, host, addr, name=None):
        #  log.msg(
        #     'unsubscribe uuid host addr: %s %s %s' % (sid, host, addr))

        def unsubscribed(res):
            print('subscription %s successfully cancelled' % sid)
            if name:
                if len(self.subscriptions[name][host]) == 1:
                    del self.subscriptions[name]
                else:
                    del self.subscriptions[name][host][sid]
            return res

        headers = {'HOST': [host], 'SID': [sid]}
        d = self.agent.request(
            'UNSUBSCRIBE',
            addr,
            Headers(headers))
        d.addCallback(unsubscribed)
        return d

    def subscribe_cloud(
            self, device, svc, var, callback_fct=log.msg, callback_args=()):
        print('suscribe to %s' % var)
        name = device.keys()[0]
        dev = device[name]
        d = defer.Deferred()

        def subscribe_failed(err, name):
            self.parent.remove_device(name.split('_')[0])

        def subscribed(node_name, deferred, iq):
            if iq['type'] == 'result':
                self.subscriptions_cloud[str(node_name)] = True
                print('%s suscribed !' % str(node_name))
#                 iq = IQ(self.xmlstream, 'get')
#                 ps = domish.Element(
#                     ('http://jabber.org/protocol/pubsub', 'pubsub'))
#                 items = domish.Element((None, 'items'))
#                 items['node'] = node_name
#                 items['max_items'] = '1'
#                 ps.addChild(items)
#                 iq.addChild(ps)
#                 iq.addCallback(self.on_event)
#                 iq.send(to='pubsub.' + self.jid.host)
#                 print(iq.toXml())
                deferred.callback(str(node_name))
            else:
                deferred.errback(Exception('subscription to %s failed: %s'
                                           % (node_name, iq.toXml())))

        if svc in dev['services']:
            print('service %s ok' % svc)
            print('subscriptions :%s' % self.subscriptions_cloud)
            if not self.cloud_event_catcher:
                self.cloud_event_catcher = CloudEventCatcher({}, {})
            subscription_name = '/'.join((dev['location'], svc, var))
            #  subscription_service = svc
            if subscription_name in self.cloud_event_catcher.callbacks:
                self.cloud_event_catcher.callbacks[subscription_name].update(
                    {var: (callback_fct, callback_args,)})
            else:
                self.cloud_event_catcher.callbacks.update(
                    {subscription_name: {var: (callback_fct, callback_args,)}})
#             if var in self.cloud_event_catcher.callbacks:
#                 self.cloud_event_catcher.callbacks[var].update(
#                     {var: (callback_fct, callback_args,)})
#             else:
#                 self.cloud_event_catcher.callbacks.update(
#                     {var: {var: (callback_fct, callback_args,)}})
    #         log.err(self.event_catcher.catcher.childs)
            if subscription_name in self.subscriptions_cloud:
                if self.subscriptions_cloud[subscription_name]:
                    print('already subscribed: %s' % subscription_name)
                    for k, value in\
                            self.cloud_event_catcher.unfiltered_dict.items():
                        print('is %s == %s ?' % (k, var))
                        if k == var:
                            if value == 'False':
                                value = False
                            elif value == 'True':
                                value = True
                            if isinstance(callback_args, str)\
                                    or isinstance(callback_args, bool):
                                callback_fct(value, callback_args)
                            else:
                                callback_fct(value, *callback_args)
                            del self.cloud_event_catcher.unfiltered_dict[k]
                    return defer.succeed(None)
            self.subscriptions_cloud.update({str(subscription_name): False})
#             print(subscription_name)
#             print(subscription_service)
            iq = IQ(self.xmlstream, 'set')
            ps = domish.Element(
                ('http://jabber.org/protocol/pubsub', 'pubsub'))
            subscribe = domish.Element((None, 'subscribe'))
            subscribe['node'] = subscription_name
            subscribe['jid'] = self.jid.full()
            ps.addChild(subscribe)
            iq.addChild(ps)
            iq.addCallback(subscribed, subscription_name, d)
            iq.send(to='pubsub.'+self.jid.host)
            return d
        return defer.fail(Exception('Service unknow'))

    def get_client(self, device, service):
        if self.xmldir is not None:
                client = None
        else:
            import importlib
            module_name = service.split(':')[-2]
            app = getattr(importlib.import_module(
                'upnpy_spyne.services.templates.'+module_name.lower()),
                module_name)
            if device['network'] == 'lan':
                client = Client(
                    device['services'][service]['controlURL'],
                    Application([app], app.tns,
                                in_protocol=Soap11(), out_protocol=Soap11()))
                client.set_options(
                    out_header={'Content-Type': ['text/xml;charset="utf-8"'],
                                'Soapaction': [app.tns]})
            else:
                url = (self.xmlstream, device['location'],)
                client = Client(
                    url,
                    Application([app], app.tns,
                                in_protocol=Soap11(xml_declaration=False),
                                out_protocol=Soap11(xml_declaration=False)),
                    cloud=True)
                print('**********%s' % service)
                print(device['services'][service])
        return client

    def call(self, device, service, func, params=()):
        devname = device.keys()[0]
        dev = device[devname]
        if devname not in self._services:
            client = self.get_client(dev, service)
            self._services.update({devname: {service: client.service}})
        elif service not in self._services[devname]:
            client = self.get_client(dev, service)
            self._services[devname].update({service: client.service})
        try:
            f = getattr(
                self._services[devname][service], func)
        except AttributeError:
            log.err('function %s not found for service %s' % (func, service))
            return defer.fail(Exception(
                'function %s not found for service %s' % (func, service)))
        try:
            if len(params) > 0:
                if isinstance(params, str):
                    d = f(params)
                else:
                    d = f(*params)
            else:
                d = f()
        except TypeError:
            #  boolean has no len
            d = f(params)
        d.addErrback(
            lambda failure, fname: log.err(
                '%s call failed : %s' % (fname, failure.getErrorMessage())),
            func)
        return d


class EventServer(internet.StreamServerEndpointService):

    def __init__(self):
        '''
        Initialization of Event Server
         '''
        self.catcher = EventCatcher()
        self.site = server.Site(self.catcher)
        edp = endpoints.serverFromString(reactor, "tcp:0")
        super(EventServer, self).__init__(edp, self.site)
        self._choosenPort = None

    def privilegedStartService(self):
        r = super(EventServer, self).privilegedStartService()
        self._waitingForPort.addCallback(self.portCatcher)
        return r

    def portCatcher(self, port):
        self._choosenPort = port.getHost().port
#         print(self._choosenPort)
        return port

    def getPort(self):
        return self._choosenPort


class EventCatcher(Resource):
    isLeaf = False
    childs = {}
    unfiltered = {}

    def getChild(self, path, request):
        if path == '':
            return Resource()
        else:
            if path in self.childs:
                return EventResource(self.childs[path], self.unfiltered)
            else:
                return Resource()


class EventResource(Resource):
    isLeaf = True

    def __init__(self, callbacks, unfiltered_dict):
        self.callbacks = callbacks
        self.unfiltered_dict = unfiltered_dict
        Resource.__init__(self)

    def render(self, request):
        data = request.content.getvalue()
#         print(data)
        root = et.XML(data)
        dic = filter_event(XmlDictConfig(root), self.callbacks.keys())
#         d.update({'openHome': self.oh})
        if '_unfiltered' in dic:
            for k, v in dic['_unfiltered'].items():
                self.unfiltered_dict.update({k: v})
            del dic['_unfiltered']
        for name, value in dic.items():
            if value == 'False':
                value = False
            elif value == 'True':
                value = True
            if isinstance(self.callbacks[name][1], str)\
                    or isinstance(self.callbacks[name][1], bool):
                self.callbacks[name][0](value, self.callbacks[name][1])
            else:
                self.callbacks[name][0](value, *self.callbacks[name][1])
#         print(self.target)
        return ''


class CloudEventCatcher(object):

    def __init__(self, callbacks, unfiltered_dict):
        self.callbacks = callbacks
        self.unfiltered_dict = unfiltered_dict

    def receive(self, evt):

        #         print('receive %s %s' % evt)
        node, data = evt
        root = et.XML(data)
        #         print(self.callbacks)
        dic = filter_event(XmlDictConfig(root), self.callbacks[node].keys())
        if '_unfiltered' in dic:
            for k, v in dic['_unfiltered'].items():
                # print('unfiltered: %s  %s' % (k, v))
                self.unfiltered_dict.update({k: v})
            del dic['_unfiltered']
        for name, value in dic.items():
            if value == 'False':
                value = False
            elif value == 'True':
                value = True
            if isinstance(self.callbacks[node][name][1], str)\
                    or isinstance(self.callbacks[node][name][1], bool)\
                    or isinstance(self.callbacks[node][name][1], unicode):
                self.callbacks[node][name][0](
                    value, self.callbacks[node][name][1])
            else:
                self.callbacks[node][name][0](
                    value, *self.callbacks[node][name][1])


class Cloud_RemoteProcedure(RemoteProcedureBase):

    def __call__(self, *args, **kwargs):
        d = defer.Deferred()
        self.ctx, = self.contexts
        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)
        self.ctx.in_string = []
        action = IQ(self.url[0], 'set')
        for item in self.ctx.out_string:
            action.addRawXml(item)
        if action.callbacks:
            action.addCallback(self.on_response, d)
        else:
            print('wtf?')
        action.send(to=self.url[1])
        return d

    def on_response(self, deferred, result):
        if result['type'] == 'result':
            for child in result.children:
                if child.name == 'Envelope':
                    self.ctx.in_string.append(child.toXml().encode('utf-8'))
                    break
            if len(result.children) == 0:
                deferred.callback(None)
                return
            self.get_in_object(self.ctx)
            deferred.callback(self.ctx.in_object)
        else:
            deferred.errback(Exception(result.toXml().encode('utf-8')))


class Custom_RemoteProcedure(RemoteProcedureBase):

    def __call__(self, *args, **kwargs):
        # there's no point in having a client making the same request more than
        # once, so if there's more than just one context, it's rather a bug.
        # The comma-in-assignment trick is a pedantic way of getting the first
        # and the only variable from an iterable. so if there's more than one
        # element in the iterable, it'll fail miserably.
        self.ctx, = self.contexts
        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)
        self.ctx.in_string = []
        header = {'User-Agent': ['onDemand Controller']}
        if self.ctx.out_header is not None\
                and 'Soapaction' in self.ctx.out_header:
            if '#' in self.ctx.out_header['Soapaction'][0]:
                self.ctx.out_header.update({'Soapaction': [
                    self.ctx.out_header['Soapaction'][0].split('#')[0] +
                    '#' + self.ctx.method_request_string + '"']})
            else:
                self.ctx.out_header.update(
                    {'Soapaction': [
                        '"' + self.ctx.out_header['Soapaction'][0] +
                        '#' + self.ctx.method_request_string + '"']})
            header.update(self.ctx.out_header)
        agent = Agent(reactor)
        d = agent.request(
            'POST', self.url,
            Headers(header),
            _Producer(self.ctx.out_string)
        )

        def _process_response(_, response):
            # this sets ctx.in_error if there's an error, and ctx.in_object if
            # there's none.
            self.get_in_object(self.ctx)

            if self.ctx.in_error is not None:
                raise self.ctx.in_error
            elif response.code >= 400:
                raise werror.Error(response.code)
#             print(self.ctx.in_string)
#             print(self.ctx.in_body_doc)
            return self.ctx.in_object

        def _cb_request(response):
            p = _Protocol(self.ctx)
            response.deliverBody(p)
            return p.deferred.addCallback(_process_response, response)

        d.addCallback(_cb_request)
        return d


class Client(ClientBase):
    def __init__(self, url, app, cloud=False):
        super(Client, self).__init__(url, app)
        if cloud:
            self.service = Service(
                Cloud_RemoteProcedure, url, app)
        else:
            self.service = Service(Custom_RemoteProcedure, url, app)


def filter_event(dic, varnames):
    filtered_dic = {}
#     print('filtering: %s' % dic)
    for k, v in dic.items():
        if isinstance(v, list):
            u = {}
            for i in v:
                for k, v in filter_event(i, varnames).items():
                    if k == '_unfiltered':
                        for key, value in v.items():
                            u.update({key: value})
                    else:
                        filtered_dic.update({k: v})
            if len(u) > 0:
                filtered_dic.update({'_unfiltered': u})
        elif 'property' in k:
            d = filter_event(v, varnames)
            if '_unfiltered' in d:
                if '_unfiltered' in filtered_dic:
                    filtered_dic['_unfiltered'].update(d['_unfiltered'])
                else:
                    filtered_dic.update(d)
            else:
                filtered_dic.update(d)
        else:
            if k in varnames:
                filtered_dic.update({k: v})
            else:
                if '_unfiltered' in filtered_dic:
                    filtered_dic['_unfiltered'].update({k: v})
                else:
                    filtered_dic.update({'_unfiltered': {k: v}})
#     print('event :%s' % d)
    return filtered_dic


if __name__ == '__main__':

    def test_2():
        from upnpy_spyne.services.templates.switchpower import SwitchPower
        log.startLogging(sys.stdout)
        client = Client(
            'http://192.168.0.60:8000',
            Application([SwitchPower], SwitchPower.tns,
                        in_protocol=Soap11(), out_protocol=Soap11()))
        client.set_options(
            out_header={'Content-Type': ['text/xml;charset="utf-8"'],
                        'Soapaction': [SwitchPower.tns]})
        d = client.service.GetStatus()
        d.addCallback(log.msg)
        onoff = False
        for i in range(6):
            reactor.callLater(  # @UndefinedVariable
                i,
                client.service.SetTarget,
                not onoff)
            onoff = not onoff

    def show(*args):
        log.err('Event %s ' % str(args))

    def show_product(res):
        log.err(
            '==== Product found: %s - %s ====='
            % (res.Name, res.Room,))

    def search(res):
        for name, device in res.items():
            log.msg(name)
            for service in device['services']:
                log.msg(service)
                if service == u'urn:av-openhome-org:service:Product:1':
                    d = controller.call(res, service, 'Product')
                    d.addCallback(show_product)
                if service == u'urn:av-openhome-org:service:Playlist:1':
                    d = controller.subscribe(
                        res, service, 'Id', show, name)
#                     d.addCallback(show)
                elif service == u'urn:schemas-upnp-org:service:SwitchPower:1':
                    d = controller.subscribe(
                        res, service, 'Status', show, name)

    def test(controller):
        controller.startService()
        reactor.callLater(  # @UndefinedVariable
            50, lambda: log.msg(controller.devices))
        reactor.callLater(  # @UndefinedVariable
            100, controller.stopService)  # @UndefinedVariable
    log.startLogging(sys.stdout)
    controller = Controller(
        searchables=[('upnp:rootdevice', search)],
        network='cloud',
        cloud_user=('test@xmpp.bertrandverdu.me', 'test'))
    reactor.callWhenRunning(  # @UndefinedVariable
        test, controller)
    reactor.run()  # @UndefinedVariable
