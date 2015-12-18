# encoding: utf-8
'''
Created on 30 août 2015

@author: Bertrand Verdu
'''

import hashlib

from lxml.etree import tostring, fromstring, dump
from twisted.logger import Logger
from twisted.internet import reactor, defer
from twisted.application.service import Service
from twisted.names.srvconnect import SRVConnector
from twisted.words.xish import domish
from twisted.words.protocols.jabber import xmlstream, client
from twisted.words.protocols.jabber.client import IQ
from twisted.words.protocols.jabber.jid import JID, parse
from twisted.web import static
from spyne.application import Application
from spyne.service import ServiceBase
from spyne.protocol.soap import Soap11
from upnpy_spyne.event import XmppEvent
from upnpy_spyne.services import UserDefinedContext
from upnpy_spyne.utils import get_default_v4_address
from spyne_plus.server.twisted.xmpp import TwistedXMPPApp


class XmppService(Service):

    timeout = True
    active_controllers = []

    def __init__(self, device, user='test@xmpp.example.com',
                 secret='password', userlist=[], web_server=None):
        self.log = Logger()
        self.description = None
        self.reactor = reactor
        self.user = user
        self.services = {}
        self.nodes = []
        self.registrations = []
        self.active_controllers = []
        self.webserver = web_server
        self.resource = web_server.resource
        device.location = user

        def _map_context(ctx):
            ctx.udc = UserDefinedContext(device.player)

        self._jid = _jid = ''.join(
            (user, '/', device.deviceType, ':uuid:', device.uuid))
        self.device = device
        device.parent = self
        for service in device.services:
            #             if appreg.get_application(service.tns, service.name):
            #                 name = service.name + '_'
            #             else:
            #                 name = service.name
            #             soap_service = type(
            #                 service.name, (ServiceBase,), service.soap_functions)
            #             soap_service.tns = service.tns
            #             app = Application(
            #                 [soap_service],
            #                 tns=soap_service.tns,
            #                 in_protocol=Soap11(xml_declaration=False),
            #                 out_protocol=Soap11(xml_declaration=False),
            #                 name=name)
            #             app.event_manager.add_listener('method_call', _map_context)
            self.services.update(
                {str(service.serviceId):
                    {'app': TwistedXMPPApp(service.app), 'svc': service}})
#             print('name: %s, methods: %s' %
#                   (device.name, service.app.interface.service_method_map))
            for var in service.stateVariables.values():
                if var.sendEvents:
                    self.nodes.append(
                        (var, service.serviceType, service))
        self.users = {user: False}
        for user in userlist:
            self.users.update({user: False})
        self.jid = jid = JID(_jid)
        self.factory = f = client.XMPPClientFactory(jid, secret)
        f.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        f.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        f.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        f.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failed)
#         self.get_device_info(device)
        self.finished = defer.Deferred()

#     def get_device_info(self, device):
#         if len(device.icons) > 0:
#             icon = device.icons[0]
#             buf = read(open())

    def startService(self):
        self.connector = SRVConnector(
            self.reactor, 'xmpp-client', self.jid.host,
            self.factory, defaultPort=5222)
        self.connector.connect()

    def stopService(self):
        for node in self.registrations:
            self.delete_ps_node(node)
        self.xmlstream.sendFooter()
        Service.stopService(self)

    def connected(self, xs):
        #  print 'Connected.'
        #  log.debug('!!!!!!!!!!!!!!!!!!!{app}', app=appreg._applications)
        self.xmlstream = xs

        # Log all traffic
#         xs.rawDataInFn = self.rawDataIn
#         xs.rawDataOutFn = self.rawDataOut

    def disconnected(self, xs):

        self.log.debug('%s disconnected.' % self._jid)

#         self.finished.callback(None)

    def authenticated(self, xs):
        #  print "Authenticated."

        xs.addObserver('/presence', self.on_presence)
        xs.addObserver('/iq', self.on_iq)

        presence = domish.Element((None, 'presence'))
        uc = domish.Element(
            ('urn:schemas-upnp-org:cloud-1-0', 'ConfigIdCloud'))
        uc['hash'] = 'uda'
        uc.addContent('1.0')
        #  print(uc.toXml())
        presence.addChild(uc)
        #  print(presence.toXml())
        xs.send(presence)
        disco = IQ(xs, 'get')
        disco.addElement(('http://jabber.org/protocol/disco#info', 'query'))
        disco.addCallback(self.check_server)
        disco.send(to='pubsub.' + self.jid.host)
        self.check_ps_nodes()
        self.reactor.callLater(120, self.ping)

    def ping(self):

        def pong(res):
            if res['type'] == 'result':
                #                 log.debug('pong !')
                self.timeout = False
                self.reactor.callLater(120, self.ping)
            else:
                self.log.error('ping error: %s' % res.toXml())
                self.timeout = False
#                 self.startService()

        def check_timeout():
            if self.timeout:
                self.log.error('ping timeout !')
#                 self.connector.connect()
        iq = IQ(self.xmlstream, 'get')
        iq.addElement('ping', 'urn:xmpp:ping')
        self.reactor.callLater(10, check_timeout)
        iq.addCallback(pong)
        self.timeout = True
        iq.send(to=self.jid.host)

    def rawDataIn(self, buf):
        print(
            "Device RECV: %s"
            % unicode(buf, 'utf-8').encode('ascii', 'replace'))

    def rawDataOut(self, buf):
        print(
            "Device SEND: %s"
            % unicode(buf, 'utf-8').encode('ascii', 'replace'))

    def check_server(self, result):

        def display_info(res):
            return
            e = fromstring(res.toXml())
            dump(e)
        self.log.debug("server checked")
        display_info(result)
#         e = fromstring(result.toXml())
#         dump(e)
#         iq = IQ(self.xmlstream, 'get')
#         ps = domish.Element(
#             ('http://jabber.org/protocol/pubsub#owner', 'pubsub'))
#         ps.addElement('default')
#         iq.addChild(ps)
#         iq.addCallback(display_info)
#         iq.send(to='pubsub.' + self.jid.host)
#         print(result.toXml())

    def dump_description(self, dest):

        def sent(res):
            self.log.debug('description sent')
            pass

        self.log.debug('send description')
#         print(dest['id'])
        if self.description:
            self.log.debug('cached description')
            iq = IQ(self.xmlstream, 'result')
            iq.addRawXml(self.description)
            iq['id'] = dest['id']
        else:
            self.log.debug('generate description')
            iq = IQ(self.xmlstream, 'result')
            query = domish.Element(
                ('urn:schemas-upnp-org:cloud-1-0', 'query'))
            query['type'] = 'described'
            query['name'] = self.device.uuid
            d = tostring(self.device.dump(), encoding='unicode')
            query.addRawXml(d)
    #         print(query.toXml())
            for service in self.device.services:
                s = tostring(service.dump(), encoding='unicode')
    #             print(s)
                query.addRawXml(s)
    #         print(query.toXml())
            self.description = query.toXml()
            iq.addChild(query)
            iq['id'] = dest['id']
#             self.description = iq
#         print(iq.toXml())
        iq.addCallback(sent)
        iq.send(to=dest['from'])

    def check_ps_nodes(self):

        def got_response(node, response):
            if response['type'] in ('error', 'cancel'):
                self.create_ps_node(node)
            elif response['type'] == 'result':
                node_name = '/'.join((self._jid, node[1]))
                if node_name in self.registrations:
                    return
                self.registrations.append(node_name)
                self.log.debug('node {name} registered', name=node_name)
                event = XmppEvent(
                    node_name,
                    self,
                    'pubsub.' + self.jid.host)
                node[2].subscribe(event, 100)
                self.reactor.callLater(
                    99, self.renew_subscription, *(node_name, node))
            else:
                self.log.error('unknown response from server: %s' %
                               response.toXml())
        self.log.debug('check nodes: {nodes}', nodes=str(self.nodes))
        IQ_ = IQ  # Basic optimisation...
        element = domish.Element
        for node in self.nodes:
            iq = IQ_(self.xmlstream, 'get')
            query = element((
                'http://jabber.org/protocol/disco#info', 'query'))
            query['node'] = '/'.join((self._jid, node[1], node[0].name))
            iq.addChild(query)
            iq.addCallback(got_response, node)
            iq.send(to='pubsub.' + self.jid.host)

    def create_ps_node(self, node):

        def registered(node, iq):
            if iq['type'] == 'result':
                node_name = '/'.join((self._jid, node[1]))
                if node_name in self.registrations:
                    return
                event = XmppEvent(
                    node_name,
                    self,
                    'pubsub.' + self.jid.host)
                node[2].subscribe(event, 100)
                self.reactor.callLater(
                    95, self.renew_subscription, *(node_name, node))
                self.registrations.append(node_name)
                self.log.debug('node {node} registered', node=node_name)
            else:
                self.log.error(
                    'node creation {name} failed:{iq}',
                    name=node,
                    iq=iq.toXml())

        iq = IQ(self.xmlstream, 'set')
        ps = domish.Element(
            ('http://jabber.org/protocol/pubsub', 'pubsub'))
        create = domish.Element((None, 'create'))
        create['node'] = '/'.join((self._jid, node[1], node[0].name))
        ps.addChild(create)
        configure = domish.Element((None, 'configure'))
        x = domish.Element(('jabber:x:data', 'x'))
        x['type'] = 'submit'
        field = domish.Element((None, 'field'))
        field['var'] = 'FORM_TYPE'
        field['type'] = 'hidden'
        field.addElement(
            'value',
            content='http://jabber.org/protocol/pubsub#node_config')
        x.addChild(field)
        access = domish.Element((None, 'field'))
        access['var'] = 'pubsub#access_model'
        access.addElement('value', content='roster')
        x.addChild(access)
#         expire = domish.Element((None, 'field'))
#         expire['var'] = 'pubsub#item_expire'
#         expire.addElement('value', content='60')
#         x.addChild(expire)
        last = domish.Element((None, 'field'))
        last['var'] = 'pubsub#send_last_published_item'
        last.addElement('value', content='on_sub_and_presence')
        x.addChild(last)
        numitems = domish.Element((None, 'field'))
        numitems['var'] = 'pubsub#max_items'
        numitems.addElement('value', content='1')
        x.addChild(numitems)
        configure.addChild(x)
        ps.addChild(configure)
        iq.addChild(ps)
        iq.addCallback(registered, node)
        iq.send(to='pubsub.' + self.jid.host)

    def delete_ps_node(self, node):

        def deleted(res):
            if res['type'] == 'error':
                self.log.error('node deletion failed: %s' % res.toXml())

        iq = IQ(self.xmlstream, 'set')
        ps = domish.Element(
            ('http://jabber.org/protocol/pubsub#owner', 'pubsub'))
        delete = domish.Element((None, 'delete'))
        delete['node'] = node
        ps.addChild(delete)
        iq.addChild(ps)
        iq.send(to='pubsub.' + self.jid.host)

    def renew_subscription(self, name, node):
#         self.log.debug('renew %s : %s' % (name, (name in self.registrations)))
        if name in self.registrations:
            self.log.debug('renew: %s' % name)
            event = XmppEvent(
                name,
                self,
                'pubsub.' + self.jid.host)
            node[2].subscribe(event, 100, True)
            self.reactor.callLater(
                99, self.renew_subscription, *(name, node))

    def on_iq(self, iq):
        #         print('received iq: %s' % iq.toXml().encode('utf-8'))
        user, host, res = parse(iq['from'])
        del(res)
        if not user:
            return
        jid = '@'.join((user, host))
        self.log.debug('received request of type {typ} from {user}',
                       typ=iq['type'], user=jid)
        if jid not in self.users and jid != self.user:
            self.log.info('rejected User: %s' % jid)
            return
        if iq['type'] == 'get':
            for child in iq.children:
                if child.name == 'query':
                    if child['type'] == 'description':
                        self.log.debug('description requested')
                        self.dump_description(iq)
        elif iq['type'] == 'set':
            if iq.children[0].name == 'Envelope':
                self.log.debug('received rpc')
                root = iq.children[0]
#                 print(root.toXml())
                for child in root.children:
                    if child.name == 'Header':
                        res = self.services[
                            child.children[0]['serviceId']]['app'].handle_rpc(
                                root.toXml(), child.children[0]['serviceId'])
                    elif child.name == 'Body':
                        decomposed = child.children[0].uri.split(':')
                        guessed_id = ':'.join(
                            (decomposed[0],
                             decomposed[1],
                             decomposed[2] + 'Id',
                             decomposed[3]))
                        res = self.services[
                            str(guessed_id)]['app'].handle_rpc(
                                root.toXml(), str(guessed_id))
                    else:
                        self.log.warn('bad iq request: %s' % child.name)
                        continue

                    res.addCallback(self.respond_rpc, iq['from'], iq['id'])

    def respond_rpc(self, resp, to, queryID):
        #         print('send: %s' % resp)
        #         self.log.debug('respond rpc: %s' % resp[0][39:])
        res = IQ(self.xmlstream, 'result')
        res['id'] = queryID
        if resp:
            for item in resp:
                res.addRawXml(item[39:].decode('utf-8'))  # Skip the xml header
        res.send(to=to)

    def on_presence(self, presence):
        self.log.debug(
            'received presence: %s'
            % presence.toXml().encode('utf-8'))
        if presence.hasAttribute('from'):
            user, host, res = parse(presence['from'])
            if presence['from'] in self.active_controllers:
                if presence.hasAttribute('type'):
                    if presence['type'] == 'unavailable':
                        self.active_controllers.remove(presence['from'])
                        self.log.info('User {_from} disconnected',
                                      _from=presence['from'])
                        return
            elif 'ControlPoint' in res:
                if presence.hasAttribute('type'):
                    if presence['type'] == 'unavailable':
                        return
                self.log.info('control point %s added' % presence['from'])
                if len(self.active_controllers) == 0:
                    self.check_ps_nodes()
                self.active_controllers.append(presence['from'])
            del(res)
            jid = '@'.join((user, host))
            if presence.hasAttribute('type'):
                if presence['type'] == 'subscribe':
                    if jid in self.users:
                        self.log.info('received subscription from %s' % jid)
                        if self.users[jid] is False:
                            iq = IQ(self.xmlstream, 'set')
                            query = domish.Element(
                                ('jabber:iq:roster', 'query'))
                            item = domish.Element((None, 'item'))
                            item['jid'] = jid
                            item['name'] = jid
                            item.addElement('group', content='UPnPCloud')
                            query.addChild(item)
                            iq.addChild(query)
                            iq.addCallback(self.subscribed, jid)
                            iq.send()
                    else:
                        self.log.error('subscription for user %s failed: %s'
                                       % (jid, 'Not in user list'))
                        pres = domish.Element((None, 'presence'))
                        pres['type'] = 'unsubscribed'
                        pres['to'] = presence['from']
                        self.xmlstream.send(pres)

    def subscribed(self, jid, result):
        if result['type'] == 'result':
            self.log.info('user %s successfully suscribed' % jid)
            self.users.update({jid: True})
            pres = domish.Element((None, 'presence'))
            pres['type'] = 'subscribed'
            pres['to'] = jid
            self.xmlstream.send(pres)
        else:
            self.log.error('subscription for user %s failed: %s'
                           % (jid, result.toXml()))
            pres = domish.Element((None, 'presence'))
            pres['type'] = 'unsubscribed'
            pres['to'] = jid
            self.xmlstream.send(pres)

    def init_failed(self, failure):
        print "Initialization failed."
        print failure

    def register_art_url(self, url, cloud=False):
        if cloud:
            return None
        newurl = hashlib.md5(url).hexdigest() + url[-4:]
        self.resource.putChild(
            newurl,
            static.File(url))
        return self.webserver.weburl % get_default_v4_address() + '/' + newurl
