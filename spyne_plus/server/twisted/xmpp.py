# encoding: utf-8
from __future__ import absolute_import
'''
Created on 17 juin 2015

@author: babe
'''

import logging
logger = logging.getLogger(__name__)
from lxml.etree import tostring, fromstring, dump

from twisted.logger import Logger
from twisted.internet import defer
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.names.srvconnect import SRVConnector
from twisted.words.xish import domish
from twisted.words.protocols.jabber import xmlstream, client
from twisted.words.protocols.jabber.client import IQ
from twisted.words.protocols.jabber.jid import JID, parse

from spyne import MethodContext
from spyne.model import ComplexModelBase
from spyne.server import ServerBase
from spyne.application import Application
from spyne.service import ServiceBase
from spyne.protocol.soap import Soap11
from upnpy_spyne.services import UserDefinedContext

UPNP_ERROR = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '\
    + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" >'\
    + '<s:Header mustUnderstand="1">'\
    + '<uc xmlns="urn:schemas-upnp-org:cloud-1-0" serviceId="%s"/>'\
    + '</s:Header><s:Body><s:Fault><faultcode>%s</faultcode>'\
    + '<faultstring>UpnPError</faultstring><detail>'\
    + '<UPnPError xmlns="urn:schemas-upnp-org:control-1-0">'\
    + '<errorCode>500</errorCode>'\
    + '<errorDescription>%s</errorDescription>'\
    + '</UPnPError></detail>'\
    + '</s:Fault></s:Body></s:Envelope>'
log = Logger()


class XmppService(Service):

    timeout = True
    active_controllers = []

    def __init__(self, device, user='test@xmpp.example.com',
                 secret='password', userlist=[]):
        self.description = None
        self.reactor = reactor
        self.user = user
        self.services = {}
        self.nodes = []
        self.registrations = []
        self.active_controllers = []
        device.location = user

        def _map_context(ctx):
            ctx.udc = UserDefinedContext(device.player)

        self._jid = _jid = ''.join(
            (user, '/', device.deviceType, ':uuid:', device.uuid))
        self.device = device
        for service in device.services:
            soap_service = type(
                service.name, (ServiceBase,), service.soap_functions)
            soap_service.tns = service.tns
            app = Application(
                [soap_service],
                tns=soap_service.tns,
                in_protocol=Soap11(xml_declaration=False),
                out_protocol=Soap11(xml_declaration=False),
                name=service.name)
            app.event_manager.add_listener('method_call', _map_context)
            self.services.update(
                {str(service.serviceId):
                    {'app': TwistedXMPPApp(app), 'svc': service}})
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
        self.finished = Deferred()

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
        print 'Connected.'

        self.xmlstream = xs

        # Log all traffic
#         xs.rawDataInFn = self.rawDataIn
#         xs.rawDataOutFn = self.rawDataOut

    def disconnected(self, xs):
        print 'Disconnected.'

#         self.finished.callback(None)

    def authenticated(self, xs):
        print "Authenticated."

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
        disco.send(to='pubsub.xmpp.bertrandverdu.me')
        self.check_ps_nodes()
        self.reactor.callLater(30, self.ping)

    def ping(self):

        def pong(res):
            if res['type'] == 'result':
                log.debug('pong !')
                self.timeout = False
                self.reactor.callLater(30, self.ping)
            else:
                log.error('ping error: %s' % res.toXml())
                self.timeout = False
#                 self.startService()

        def check_timeout():
            if self.timeout:
                log.error('ping timeout !')
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
            e = fromstring(res.toXml())
            dump(e)
        log.debug("server checked")
        display_info(result)
#         e = fromstring(result.toXml())
#         dump(e)
        iq = IQ(self.xmlstream, 'get')
        ps = domish.Element(
            ('http://jabber.org/protocol/pubsub#owner', 'pubsub'))
        ps.addElement('default')
        iq.addChild(ps)
        iq.addCallback(display_info)
        iq.send(to='pubsub.' + self.jid.host)
#         print(result.toXml())

    def dump_description(self, dest):

        def sent(res):
            log.debug('description sent')
            pass

        log.debug('send description')
#         print(dest['id'])
        if self.description:
            log.debug('cached description')
            iq = IQ(self.xmlstream, 'result')
            iq.addRawXml(self.description)
            iq['id'] = dest['id']
        else:
            log.debug('generate description')
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
            if response['type'] == 'error':
                self.create_ps_node(node)
            elif response['type'] == 'result':
                node_name = '/'.join((self._jid, node[1]))
                if node_name in self.registrations:
                    return
                self.registrations.append(node_name)
                log.debug('node %s registered' % node_name)
                event = XmppEvent(
                    node_name,
                    self,
                    'pubsub.' + self.jid.host)
                node[2].subscribe(event, 100)
                self.reactor.callLater(
                    95, self.renew_subscription, *(node_name, node))
            else:
                log.error(response.toXml())
        log.debug('check nodes: %s' % self.nodes)
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
                log.debug('node %s registered' % node_name)
            else:
                log.error(iq.toXml())

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
        configure.addChild(x)
        ps.addChild(configure)
        iq.addChild(ps)
        iq.addCallback(registered, node)
        iq.send(to='pubsub.' + self.jid.host)

    def delete_ps_node(self, node):

        def deleted(res):
            if res['type'] == 'error':
                log.error('node deletion failed: %s' % res.toXml())

        iq = IQ(self.xmlstream, 'set')
        ps = domish.Element(
            ('http://jabber.org/protocol/pubsub#owner', 'pubsub'))
        delete = domish.Element((None, 'delete'))
        delete['node'] = node
        ps.addChild(delete)
        iq.addChild(ps)
        iq.send(to='pubsub.' + self.jid.host)

    def renew_subscription(self, name, node):
        log.debug('renew %s : %s' % (name, (name in self.registrations)))
        if name in self.registrations:
            log.debug('renew: %s' % name)
            event = XmppEvent(
                name,
                self,
                'pubsub.' + self.jid.host)
            node[2].subscribe(event, 100)
            self.reactor.callLater(
                95, self.renew_subscription, *(name, node))

    def on_iq(self, iq):
#         print('received iq: %s' % iq.toXml().encode('utf-8'))
        user, host, res = parse(iq['from'])
        del(res)
        if not user:
            return
        jid = '@'.join((user, host))
        log.debug('received request of type %s from %s' % (iq['type'], jid))
        if jid not in self.users and jid != self.user:
            log.info('rejected User: %s' % jid)
            return
        if iq['type'] == 'get':
            for child in iq.children:
                if child.name == 'query':
                    if child['type'] == 'description':
                        log.debug('description requested')
                        self.dump_description(iq)
        elif iq['type'] == 'set':
            if iq.children[0].name == 'Envelope':
                log.debug('received rpc')
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
                             decomposed[2]+'Id',
                             decomposed[3]))
                        res = self.services[
                            str(guessed_id)]['app'].handle_rpc(
                                root.toXml(), str(guessed_id))
                    res.addCallback(self.respond_rpc, iq['from'], iq['id'])

    def respond_rpc(self, resp, to, queryID):
        #         print('send: %s' % resp)
        log.debug('respond rpc')
        res = IQ(self.xmlstream, 'result')
        res['id'] = queryID
        if resp:
            for item in resp:
                res.addRawXml(item.decode('utf-8'))
        res.send(to=to)

    def on_presence(self, presence):
        log.debug(
            'received presence: %s'
            % presence.toXml().encode('utf-8'))
        if presence.hasAttribute('from'):
            user, host, res = parse(presence['from'])
            if presence['from'] in self.active_controllers:
                if presence.hasAttribute('type'):
                    if presence['type'] == 'unavailable':
                        self.active_controllers.remove(presence['from'])
                        log.info('User %s disconnected' % presence['from'])
                        return
            elif 'ControlPoint' in res:
                if presence.hasAttribute('type'):
                    if presence['type'] == 'unavailable':
                        return
                log.info('control point %s added' % presence['from'])
                if len(self.active_controllers) == 0:
                    self.check_ps_nodes()
                self.active_controllers.append(presence['from'])
            del(res)
            jid = '@'.join((user, host))
            if presence.hasAttribute('type'):
                if presence['type'] == 'subscribe':
                    if jid in self.users:
                        log.info('received subscription from %s' % jid)
                        if self.users[jid] is False:
                            iq = IQ(self.xmlstream, 'set')
                            query = domish.Element(('jabber:iq:roster', 'query'))
                            item = domish.Element((None, 'item'))
                            item['jid'] = jid
                            item['name'] = jid
                            item.addElement('group', content='UPnPCloud')
                            query.addChild(item)
                            iq.addChild(query)
                            iq.addCallback(self.subscribed, jid)
                            iq.send()
                    else:
                        log.error('subscription for user %s failed: %s'
                                % (jid, 'Not in user list'))
                        pres = domish.Element((None, 'presence'))
                        pres['type'] = 'unsubscribed'
                        pres['to'] = presence['from']
                        self.xmlstream.send(pres)

    def subscribed(self, jid, result):
        if result['type'] == 'result':
            log.info('user %s successfully suscribed' % jid)
            self.users.update({jid: True})
            pres = domish.Element((None, 'presence'))
            pres['type'] = 'subscribed'
            pres['to'] = jid
            self.xmlstream.send(pres)
        else:
            log.error('subscription for user %s failed: %s'
                    % (jid, result.toXml()))
            pres = domish.Element((None, 'presence'))
            pres['type'] = 'unsubscribed'
            pres['to'] = jid
            self.xmlstream.send(pres)

    def init_failed(self, failure):
        print "Initialization failed."
        print failure


class TwistedXMPPApp(ServerBase):
    """A server transport that exposes the application
        as a twisted words jabber soap transport.
    """
    transport = 'http://jabber.org/protocol/soap'

    def __init__(self, app):

        super(TwistedXMPPApp, self).__init__(app)
        self._wsdl = None

    def handle_rpc(self, element, serviceId):

        log.debug('call handle_rpc')

        def _cb_deferred(ret, ctx):
            #             print('deferred: %s' % str(ret))
            log.debug('deferred result')
            om = ctx.descriptor.out_message
            if ((not issubclass(om, ComplexModelBase)) or len(om._type_info) <= 1):
                    ctx.out_object = [ret.encode('utf-8')]
            else:
                ctx.out_object = (r.decode('utf-8') for r in ret)
            self.get_out_string(ctx)
#             print(ctx.out_string[0])
            return ctx.out_string[0]

        def _eb_deferred(error, ctx):
            ctx.out_error = error.value
            if isinstance(ctx.out_string, list):
                logging.error(''.join(ctx.out_string))
            else:
                logging.error(ctx.out_string)
            return ctx.out_string

        initial_ctx = MethodContext(self)
        initial_ctx.in_string = element
#         print(initial_ctx.in_string)
        for ctx in self.generate_contexts(initial_ctx, 'utf8'):
            # This is standard boilerplate for invoking services.
#             print(ctx)
            try:
                self.get_in_object(ctx)
            except AttributeError:
                logging.error(ctx.out_string)
                return defer.succeed(UPNP_ERROR %(serviceId, ctx.in_error.faultcode, ctx.in_error.faultstring))
            if ctx.in_error:
                self.get_out_string(ctx)
                logging.error(''.join(ctx.out_string))
                continue

            self.get_out_object(ctx)
            if ctx.out_error:
                self.get_out_string(ctx)
                logging.error(''.join(ctx.out_string))
                continue
            ret = ctx.out_object[0]
#             print(ret)
            if isinstance(ret, Deferred):
                if ret.called:
                    return defer.succeed(_cb_deferred(ret.result, ctx))
                ret.addCallback(_cb_deferred, ctx)
                ret.addErrback(_eb_deferred, ctx)
                return ret
            else:
                self.get_out_string(ctx)
#                 print('no deferred: %s' % ctx.out_string)
                log.debug('result type no deferred')
                return defer.succeed(ctx.out_string)


class XmppEvent(object):

    def __init__(self, nodeId, parent, pubsub_addr):
        self.nodeId = nodeId
        self.parent = parent
        self.addr = pubsub_addr

    def publish(self, event):

        if len(self.parent.active_controllers) == 0:
            log.debug('event cancelled')
            self.parent.registrations = []
            return

        def success(res):
            print('event sent')
            if res['type'] == 'error':
                log.error('Publish Event failed :%s' % res.toXml())
            else:
                if 'Id' in res.children[0].children[0]['node']:
                    log.debug('Event Published: %s' % res.toXml())
        name, data = event
        if name == 'Seconds':
            return
        iq = IQ(self.parent.xmlstream, 'set')
        ps = domish.Element(('http://jabber.org/protocol/pubsub', 'pubsub'))
        publish = domish.Element((None, 'publish'))
        publish['node'] = '/'.join((self.nodeId, name))
        item = domish.Element((None, 'item'))
        propertyset = domish.Element(
            ('urn:schemas-upnp-org:event-1-0', 'propertyset'),
            localPrefixes={'e': 'urn:schemas-upnp-org:event-1-0'})
        prop = domish.Element((None, 'e:property'))
        evt = domish.Element((None, name))
        if isinstance(data.value, dict):
            ev = domish.Element((data.namespace, 'Event'))
            inst = domish.Element((None, 'InstanceID'))
            inst['val'] = '0'
            for k, v in data.value.items:
                if 'namespace' in v:
                    var = domish.Element((v['namespace'], k))
                else:
                    var = domish.Element((None, k))
                if 'attrib' in v:
                    attr = v['attrib']
                else:
                    attr = {}
                value = v['value']
                if isinstance(value, bool):
                    value = int(value)
                attr.update(
                    {'val': str(value)
                     .decode('utf-8')})
                for attname, attval in attr:
                    var[attname] = attval
                inst.addChild(var)
            ev.addChild(inst)
            evt.addChild(ev)
        else:
#             print(str(data.value).decode('utf-8'))
            if isinstance(data.value, bool):
                data.value = int(data.value)
            evt.addContent(str(data.value).decode('utf-8'))
        prop.addChild(evt)
        propertyset.addChild(prop)
        item.addChild(propertyset)
        publish.addChild(item)
        ps.addChild(publish)
        iq.addChild(ps)
        iq.addCallback(success)
        iq.send(to=self.addr)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne_plus.protocol.xml').setLevel(logging.DEBUG)
    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)
    from upnpy_spyne.devices.ohSource import Source
    from onDemand.protocols.mpd_new import get_Mpd
    from twisted.internet.task import react
    def main(reactor):
        s = XmppService(reactor, device)
        s.startService()
        return s.finished
        
    n, f = get_Mpd(addr='192.168.0.9')
    device = Source(
        'test xmpp renderer',
        f,
        '/home/babe/Projets/eclipse/onDemand/data/')
    react(main)
