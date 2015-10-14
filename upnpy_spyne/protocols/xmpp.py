'''
Created on 8 juin 2015

@author: Bertrand Verdu
'''
import sys

from twisted.internet import defer
from twisted.internet.defer import Deferred
from twisted.internet.task import react
from twisted.names.srvconnect import SRVConnector
from twisted.words.xish import domish, utility
from twisted.words.protocols.jabber import xmlstream, client
from twisted.words.protocols.jabber.client import IQ
from twisted.words.protocols.jabber.jid import JID, parse


class Client(object):
    '''
    classdocs
    '''

    def __init__(self, reactor, jid, secret):
        self.reactor = reactor
        self.jid = jid = JID(jid)
        f = client.XMPPClientFactory(jid, secret)
        f.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        f.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        f.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        f.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failed)
        connector = SRVConnector(
            reactor, 'xmpp-client', jid.host, f, defaultPort=5222)
        connector.connect()
        self.finished = Deferred()

    def rawDataIn(self, buf):
        print "RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')

    def rawDataOut(self, buf):
        print "SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')

    def connected(self, xs):
        raise NotImplementedError()

    def disconnected(self, xs):
        raise NotImplementedError()

    def authenticated(self, xs):
        raise NotImplementedError()

    def init_failed(self, failure):
        print "Initialization failed."
        print failure

        self.xmlstream.sendFooter()


class Controller(Client):
    '''
    Handle upnp controller operations over xmpp (UCA)
    '''
    def __init__(self, reactor, jid, secret, controller=None, users=[]):
        self._jid = jid
        self.users = {'onDemand@xmpp.bertrandverdu.me': {'state': False}}
        for user in users:
            self.users.update({user: {'state': False}})
        self.hosts = {}
        if controller:
            self.resource = ''.join((
                'urn:schemas-upnp-org:cloud-1-0:ControlPoint:1:uuid:',
                controller.uuid))
        else:
            self.resource = 'urn:schemas-upnp-org:cloud-1-0:ControlPoint:1:'\
                + 'uuid:e70e8d0e-d9eb-4748-b163-636a323e7950'
        self.full_jid = ''.join((self._jid, '/', self.resource))
        super(Controller, self).__init__(
            reactor,
            self.full_jid,
            secret)

    def connected(self, xs):
        print 'Connected.'

        self.xmlstream = xs

        # Log all traffic
#         xs.rawDataInFn = self.rawDataIn
#         xs.rawDataOutFn = self.rawDataOut

    def disconnected(self, xs):
        print 'Disconnected.'

        self.finished.callback(None)

    def authenticated(self, xs):
        print "Authenticated."
#         bind = IQ(xs, 'set')
# #         res = domish.Element((None, 'resource'), content=self.resource)
#         res = domish.Element(('urn:ietf:params:xml:ns:xmpp-bind', 'bind'))
#         res.addElement('resource', content=self.resource)
#         bind.addChild(res)
# #         bind['from'] = self._jid
# #         bind['to'] = self.jid.host
#         xs.send(bind)
        presence = domish.Element((None, 'presence'))
        xs.send(presence)
        xs.addObserver('/presence', self.on_presence)
        xs.addObserver('/iq', self.on_iq)
        disco = IQ(xs, 'get')
#         disco['to'] = 'ondemand@xmpp.bertrandverdu.me/urn:schemas-upnp-org:device:MediaRenderer:1:uuid:e70e9d0e-d9eb-4748-b163-636a323e7950'
#         search = domish.Element(('http://jabber.org/protocol/disco#items', 'query'))
        disco.addElement(('http://jabber.org/protocol/disco#items', 'query'))
        disco.addCallback(self.discovered)
        disco.send()
        self.reactor.callLater(120, xs.sendFooter)
        self.reactor.callLater(5, self.check_users)
    
    def rawDataIn(self, buf):
        print "Controller RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')

    def rawDataOut(self, buf):
        print "Controller SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')
        
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
                iq.addCallback(self.subscribe, user)
                print('send IQ: %s' % (iq.toXml().encode('utf-8')))
                iq.send()

    def subscribe(self, jid, result):
        print('Subscribe callback from %s' % jid)
        presence = domish.Element((None, 'presence'))
        presence['type'] = 'subscribe'
        presence['to'] = jid
        self.xmlstream.send(presence)

    def on_presence(self, resp):
        print('got presence: %s' % resp.toXml().encode('utf-8'))
        print('from :%s' % resp['from'])
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
#                 if jid == self._jid:
#                     return
                info = IQ(self.xmlstream, 'get')
                info['to'] = resp ['from']
                query = domish.Element(
                    ('urn:schemas-upnp-org:cloud-1-0', 'query'))
                query['type'] = 'description'
                query['name'] = ':'.join(res.split(':')[-2:])
                info.addChild(query)
                info.addCallback(self.on_description)
                info.send()

    def on_description(self, iq):
#         print(
#             'Received description from %s: %s'
#             % (iq['from'], iq.toXml().encode('utf-8')))
        pause = IQ(self.xmlstream, 'set')
        pause['to'] = iq['from']
#         enveloppe = domish.Element(
#             ('http://schemas.xmlsoap.org/soap/envelope/', 'Envelope'))
        enveloppe = domish.Element(
            ('http://schemas.xmlsoap.org/soap/envelope/', 'Envelope'), localPrefixes={'s': 'http://schemas.xmlsoap.org/soap/envelope/'})
        enveloppe['s:encodingStyle'] = "http://schemas.xmlsoap.org/soap/encoding/"
        header = domish.Element((None, 's:Header'))
#         header = domish.Element(('http://schemas.xmlsoap.org/soap/envelope/', 'Header'))
        header['mustUnderstand'] = "1"
        uc = domish.Element(('urn:schemas-upnp-org:cloud-1-0', 'uc'))
        uc['serviceId'] = 'urn:av-openhome-org:serviceId:Playlist'
        header.addChild(uc)
        enveloppe.addChild(header)
        body = domish.Element((None, 's:Body'))
#         body = domish.Element(('http://schemas.xmlsoap.org/soap/envelope/', 'Body'))
        action = domish.Element(
            ('urn:av-openhome-org:service:Playlist:1', 'Read'), localPrefixes={'u': 'urn:av-openhome-org:service:Playlist:1'})
#         action = domish.Element(
#             ('urn:av-openhome-org:service:Playlist:1', 'Pause'))
        body.addChild(action)
        enveloppe.addChild(body)
        pause.addChild(enveloppe)
        pause.addCallback(self.paused)
        print('send pause')
        print(pause.toXml())
        pause.send()
    
    def paused(self, res):
        print('paused ?: %s' % res.toXml())

    def discovered(self, iq):
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
        print(self.hosts)

    def on_iq(self, iq):
        print('got iq')
        try:
            print('from :%s' % iq['from'])
        except KeyError:
            print('From I don\'t know: %s' % iq.toXml())
        print('type: %s' % iq['type'])


class Device(Client):
    '''
    Provide additional services for xmpp server (UCS)
    '''
    def __init__(self, reactor, jid, secret, device=None, users=[]):
        self.users = {'test@xmpp.bertrandverdu.me': False}
        for user in users:
            self.users.update({user: False})
        if device:
            jid = ''.join((jid, '/', device.deviceType, ':uuid:', device.uuid))
        else:
            jid += ''.join(('/urn:schemas-upnp-org:device:MediaRenderer:1:',
                            'uuid:e70e9d0e-d9eb-4748-b163-636a323e7950'))
        super(Device, self).__init__(reactor, jid, secret)

    def connected(self, xs):
        print 'Connected.'

        self.xmlstream = xs

        # Log all traffic
#         xs.rawDataInFn = self.rawDataIn
#         xs.rawDataOutFn = self.rawDataOut

    def disconnected(self, xs):
        print 'Disconnected.'

        self.finished.callback(None)

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
#         disco['to'] = 'pubsub.xmpp.bertrandverdu.me'
#         search = domish.Element(('http://jabber.org/protocol/disco#items', 'query'))
        disco.addElement(('http://jabber.org/protocol/disco#info', 'query'))
        disco.addCallback(self.check_server)
        disco.send(to='pubsub.xmpp.bertrandverdu.me')

        self.reactor.callLater(120, xs.sendFooter)

    def rawDataIn(self, buf):
        print "Device RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')

    def rawDataOut(self, buf):
        print "Device SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')
        
    def check_server(self, result):
        print("server checked")

    def on_iq(self, iq):
        print('received iq: %s' % iq.toXml().encode('utf-8'))

    def on_presence(self, presence):
        print('received presence: %s' % presence.toXml().encode('utf-8'))
        user, host, res = parse(presence['from'])
        jid = '@'.join((user, host))
        if presence.hasAttribute('type'):
            if presence['type'] == 'subscribe':
                if jid in self.users:
                    print('received subscription')
                    if self.users[jid] is False:
                        iq = IQ(self.xmlstream, 'set')
                        query = domish.Element(('jabber:iq:roster', 'query'))
                        item = domish.Element((None, 'item'))
                        item['jid'] = jid
                        item['name'] = jid
                        item.addElement('group', content='controllers')
                        query.addChild(item)
                        iq.addChild(query)
                        iq.addCallback(self.subscribed, jid)
                        self.xmlstream.send(iq)
                        pres = domish.Element((None, 'presence'))
                        pres['type'] = 'subscribed'
                        pres['to'] = jid
                        self.xmlstream.send(pres)
                        
                else:
                    presence = domish.Element((None, 'presence'))
                    presence['type'] = 'unsubscribed'
                    presence['to'] = presence['from']
                    self.xmlstream.send(presence)
                    
    def subscribed(self, jid, result):
        print(result)
        self.users.update({jid: True})


class SoapIQ(domish.Element):
    """
    Wrapper for a Info/Query packet.

    This provides the necessary functionality to send IQs and get notified when
    a result comes back. It's a subclass from L{domish.Element}, so you can use
    the standard DOM manipulation calls to add data to the outbound request.

    @type callbacks: L{utility.CallbackList}
    @cvar callbacks: Callback list to be notified when response comes back

    """
    def __init__(self, xmlstream, type = "set"):
        """
        @type xmlstream: L{xmlstream.XmlStream}
        @param xmlstream: XmlStream to use for transmission of this IQ

        @type type: C{str}
        @param type: IQ type identifier ('get' or 'set')
        """

        domish.Element.__init__(self, (None, "iq"))
        self.addUniqueId()
        self["type"] = type
        self._xmlstream = xmlstream
        self.callbacks = utility.CallbackList()

    def addCallback(self, fn, *args, **kwargs):
        """
        Register a callback for notification when the IQ result is available.
        """

        self.callbacks.addCallback(True, fn, *args, **kwargs)

    def send(self, to = None):
        """
        Call this method to send this IQ request via the associated XmlStream.

        @param to: Jabber ID of the entity to send the request to
        @type to: C{str}

        @returns: Callback list for this IQ. Any callbacks added to this list
                  will be fired when the result comes back.
        """
        if to != None:
            self["to"] = to
        self._xmlstream.addOnetimeObserver("/iq[@id='%s']" % self["id"], \
                                                             self._resultEvent)
        self._xmlstream.send(self)

    def _resultEvent(self, iq):
        self.callbacks.callback(iq)
        self.callbacks = None


def main(reactor, type, jid, secret):
    if type == 'device':
        return Device(reactor, jid, secret).finished
    else:
        return Controller(reactor, jid, secret).finished

if __name__ == '__main__':
    react(main, sys.argv[1:])
