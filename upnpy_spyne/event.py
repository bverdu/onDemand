# PyUPnP - Simple Python UPnP device library built in Twisted
# Copyright (C) 2013  Dean Gardiner <gardiner91@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
# import requests
from cStringIO import StringIO
# from urllib import quote_plus
from lxml import etree as et
# from upnpy.lict import Lict
# from collections import OrderedDict
from twisted.logger import Logger
from twisted.internet import reactor
from twisted.web.client import Agent, FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.words.protocols.jabber.client import IQ
from twisted.words.xish import domish


# from upnpy.utils import make_element


class EventProperty(object):
    __slots__ = ['name',
                 'value',
                 'namespace',
                 'instance',
                 'state_variable',
                 'initialized',
                 '__dict__']

    def __init__(self, name, initial=None, ns=None):
        self.log = Logger
        self.name = name
        self.value = initial
        self.namespace = ns
#         log.err(name)
        self.instance = None
        self.state_variable = None
        self.initialized = False

    def _instance_initialize(self, instance):
        #  log.err(instance.stateVariables)
        if not hasattr(instance, 'stateVariables'):
            raise TypeError()

        if self.name not in instance.stateVariables:
            raise KeyError()

        if not instance.stateVariables[self.name].sendEvents:
            raise ValueError()

        self.instance = instance
        self.state_variable = instance.stateVariables[self.name]

        if self.instance.event_properties is None:
            # self.instance.event_properties = Lict(searchNames='name')
            self.instance.event_properties = {}
            # self.instance.event_properties.append(self)
        self.instance.event_properties.update({self.name: self})

        self.initialized = True
        if self.value is None:
            self.value = self._default()

    def _default(self):
        if not self.initialized:
            raise Exception()
        if self.state_variable.dataType == 'string':
            return str()
        if self.state_variable.dataType == 'boolean':
            return False
        if self.state_variable.dataType == 'ui4':
            return 0
        if self.state_variable.dataType == 'i4':
            return 0
        if self.state_variable.dataType == 'bin.base64':
            return ''
        self.log.error(
            '******************%s ------------------%s'
            % (self.state_variable.name, self.state_variable.dataType))
        self.log.debug(self.state_variable.dataType + "not implemented")
#         raise NotImplementedError()

    def __get__(self, instance, owner):
        if not self.initialized:
            self._instance_initialize(instance)
        if self.value is None:
            return self._default()
        return self.value

    def __set__(self, instance, value, ns=None):
        # log.msg('set!')
        # if hasattr(instance, 'parent'):
        # log.err('SET %s ----> %s' % (instance.parent.friendlyName, value))
        if not self.initialized:
            self._instance_initialize(instance)
        if value is not None:
            if isinstance(value, dict):
                try:
                    self.value.update(value)
                except:
                    self.value = value
                instance.notify(self)
                return
            if self.state_variable.dataType == 'string':
                value = str(value)
            elif self.state_variable.dataType in ['ui4', 'i4']:
                value = int(value)
            elif self.state_variable.dataType == 'boolean':
                value = bool(value)
            elif self.state_variable.dataType == 'bin.base64':
                value = str(value)
            else:
                raise NotImplementedError()
            self.value = value
#             log.msg("eventing : %s from %s" % (value, self.instance))
            instance.notify(self)


class EventSubscription(object):
    __slots__ = ['sid',
                 'callback',
                 'timeout',
                 'last_subscribe',
                 'next_notify_key',
                 'expired',
                 '__dict__']

    def __init__(self, sid, callback, timeout):
        self.log = Logger()
        self.sid = sid
        self.callback_addr = callback
        self.timeout = timeout
        self.last_subscribe = time.time()
        self.next_notify_key = 0
        self.expired = False  # subscription has been flagged for deletion
        self.agent = Agent(reactor)
        self.pending_events = {}
        self.pending = False

    def _increment_notify_key(self):
        if self.next_notify_key >= 4294967295:
            self.next_notify_key = 0
        else:
            self.next_notify_key += 1

    def check_expiration(self):
        if self.expired is True:
            return True

        if time.time() > self.last_subscribe + self.timeout:
            self.expired = True
            return True

        return False

    def send_notify(self):

        self.pending = False
        if len(self.pending_events) == 0:
            return
        PREFIX = "{urn:schemas-upnp-org:event-1-0}"
        _propertyset = et.Element(
            'propertyset',
            nsmap={'e': 'urn:schemas-upnp-org:event-1-0'})
#         _propertyset = et.Element(
#             'e:propertyset',
#             attrib={'xmlns:e': 'urn:schemas-upnp-org:event-1-0'})
        for prop in self.pending_events.values():
            if prop.namespace is not None:
                et.register_namespace('e', prop.namespace)
            _property = et.SubElement(_propertyset, PREFIX + 'property')
#             log.msg('Child xml = %s' % prop.value)
#             _property.append(make_element(prop.name, str(prop.value)))
            try:
                evt = et.Element(prop.name)
                if prop.name == 'LastChange':
                    if prop.namespace is None:
                        ev = et.Element('Event')
                    else:
                        ev = et.Element('Event',
                                        attrib={'xmlns': prop.namespace})
                    inst = et.Element('InstanceID', attrib={'val': "0"})
                    prefix = ''
                    for n in prop.value:
                        if 'namespace' in prop.value[n]:
                            prefix = '%s:' % n[0]
                            et.register_namespace(prefix,
                                                  prop.value[n]['namespace'])
                        if 'attrib' in prop.value[n]:
                            attr = prop.value[n]['attrib']
                        else:
                            attr = {}
                        attr.update(
                            {'val': str(prop.value[n]['value'])
                             .decode('utf-8')})
                        var = et.Element(prefix + n, attrib=attr)
#                         var.text = str(prop.value[n]['value'])
                        inst.append(var)
                    ev.append(inst)
#                     evt.append(ev)
                    evt.text = et.tostring(ev)
                else:
                    #  log.err('%s - %s' % (prop.name, prop.value))
                    evt.text = str(prop.value).decode('utf-8')
                _property.append(evt)
            except:
                self.log.debug(
                    'Malformed XML Event: %s' % dir(prop))
                return
            _propertyset.append(_property)
        headers = {
            'NT': ['upnp:event'],
            'NTS': ['upnp:propchange'],
            'SID': [self.sid],
            'SEQ': [str(self.next_notify_key)],
            'Content-Type': ['text/xml']
        }
        data = StringIO(''.join(('<?xml version="1.0" ',
                                 'encoding="utf-8" ',
                                 'standalone="yes"?>',
                                 et.tostring(_propertyset))))
#         log.err("Event TCP Frame Data: %s" % data)
        body = FileBodyProducer(data)

        def notify_failed(err):
            self.log.debug(
                'Notify failed: %s --- %s'
                % (err.type, err.getErrorMessage()))
            self.expired = True
#         log.err(self.callback_addr)
        d = self.agent.request(
            'NOTIFY',
            self.callback_addr,
            Headers(headers),
            body)
        d.addCallbacks(lambda ignored: data.close(), notify_failed)
#         d.addErrback(notify_failed)
        self._increment_notify_key()
        self.pending_events = {}
        return d

    def notify(self, prop):
        """

        :type props: EventProperty or list of EventProperty
        """
        #         log.msg('notify')
        if self.expired:
            return
        if self.check_expiration():
            self.log.debug("(%s) subscription expired" % self.sid)
            return
        if isinstance(self.callback_addr, str):
            if prop.name == 'LastChange':
                if prop.name in self.pending_events:
                    self.pending_events[prop.name].value.update(prop.value)
                else:
                    self.pending_events.update({prop.name: prop})
            else:
                self.pending_events.update({prop.name: prop})
            if not self.pending:
                self.pending = True
                reactor.callLater(0.5,  # @UndefinedVariable
                                  self.send_notify)
        else:
            self.callback_addr.publish((prop.name, prop,))


class XmppEvent(object):

    def __init__(self, nodeId, parent, pubsub_addr=None):
        self.log = Logger()
        self.nodeId = nodeId
        self.parent = parent
        self.addr = pubsub_addr

    def publish(self, event):

        if len(self.parent.active_controllers) == 0:
            #             self.log.debug('event cancelled')
            # self.parent.registrations = []
            return

        def success(res):
            #             print('event sent')
            if res['type'] == 'error':
                self.log.error('Publish Event failed :%s' % res.toXml())
            else:
                # if 'Id' in res.children[0].children[0]['node']:
                self.log.debug('Event Published: %s' % res.toXml())
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
        if self.addr:
            iq.send(to=self.addr)
        else:
            self.log.debug('yo!')
            self.log.debug(iq.toXml())
            iq.send()
