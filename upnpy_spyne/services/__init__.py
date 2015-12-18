'''
Created on 26 janv. 2015

@author: Bertrand Verdu
'''
from collections import OrderedDict
import uuid
import re

import logging
#  logger = logging.getLogger(__name__)

from twisted.python import log

from upnpy_spyne.event import EventSubscription, EventProperty
from upnpy_spyne.upnp import ServiceResource, ServiceEventResource
from upnpy_spyne.utils import make_element
from lxml import etree as et
from spyne.service import ServiceBase
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.decorator import rpc
from spyne.model import Unicode, Integer32, UnsignedInteger32, Boolean, Null
from spyne.model.complex import ComplexModel
from spyne.util import appreg


class Service(object):

    #     __slots__ = ['version',
    #                  'client',
    #                  'serviceId',
    #                  'actions',
    #                  'stateVariables',
    #                  'event_properties',
    #                  'subscription_timeout_range',
    #                  '_description',
    #                  'actionFunctions',
    #                  '__dict__']
    version = (1, 0)
    serviceUrl = None
    serviceId = None
    event_properties = None
    subscription_timeout_range = (1800, None)
    _description = None
    client = None
    upnp_type = 'upnp'

    def __init__(
            self, svcname, tns, client=None, xml=None, appname='Application'):
        #         log.msg(self.__class__.stateVariables)
        self.name = svcname
        self.client = client

        def _map_context(ctx):
            ctx.udc = UserDefinedContext(self.client)
        self.actions = {}
        self.soap_functions = {}
        self.stateVariables = {}
        self.app = None
        self.tns = self.serviceType = tns
        self.serviceUrl = tns.split(':')[-2].lower()
        if xml is not None:
            buildServiceFromXml(self.__class__, xml)
        tmp = OrderedDict()
        for v in self.__class__.stateVariables:
            tmp.update({v.name: v})
        self.stateVariables = tmp
#         print(self.__class__.stateVariables)
#         print(self.__class__.stateVariables['SearchCapabilities'])
#         print(self.__class__.actions.items())
#         print(self.actions.items())
        for name, arguments in self.__class__.actions.items():
            self.actions.update({name: arguments})
            args_in = []
            args_out = []
            for arg in arguments:
                #                 print(arg)
                try:
                    typ = self.stateVariables[
                        arg.stateVariable.strip()].dataType
#                     print(typ)
                except KeyError:
                    raise Exception(
                        '%s : State Variable not defined: %s'
                        % (name, arg.stateVariable))
                realtype = self._get_type(typ)
                if arg.direction == 'in':
                    args_in.append((realtype, arg.name))
                elif arg.direction == 'out':
                    args_out.append((realtype, arg.name))
                else:
                    raise Exception(
                        '%s : Bad direction %s for variable %s'
                        % (name, arg.direction, arg.stateVariable))
            action_in_type = Null
            action_out_type = Null
            action_out_varnames = ()
            args = ()
            action_out_varname = ''
            n = '_'.join(('r', cc_to_us(name)))
            f = make_func(n)
            if len(args_in) > 0:
                if len(args_in) > 1:
                    args = [arg[1] for arg in args_in]
                    action_in_type = [arg[0] for arg in args_in]
                else:
                    action_in_type = args_in[0][0]
                    args = [args_in[0][1]]
            if len(args_out) > 0:
                if len(args_out) > 1:
                    action_out_type = [arg[0] for arg in args_out]
                    action_out_varnames = [arg[1] for arg in args_out]
                else:
                    action_out_type = args_out[0][0]
                    action_out_varname = args_out[0][1]
            if len(args_in) > 0:
                print(args)
                if len(args_in) > 1:
                    if len(args_out) > 0:
                        if len(args_out) > 1:
                            func = rpc(
                                *action_in_type,
                                _returns=action_out_type,
                                _out_variable_names=action_out_varnames,
                                _operation_name=name,
                                _args=args)(f)
                        else:
                            func = rpc(
                                *action_in_type,
                                _returns=action_out_type,
                                _out_variable_name=action_out_varname,
                                _operation_name=name,
                                _args=args)(f)
                    else:
                        func = rpc(
                            *action_in_type,
                            _operation_name=name,
                            _args=args)(f)
                else:
                    if len(args_out) > 0:
                        if len(args_out) > 1:
                            func = rpc(
                                action_in_type,
                                _returns=action_out_type,
                                _out_variable_names=action_out_varnames,
                                _operation_name=name,
                                _args=args)(f)
                        else:
                            func = rpc(
                                action_in_type,
                                _returns=action_out_type,
                                _out_variable_name=action_out_varname,
                                _operation_name=name,
                                _args=args)(f)
                    else:
                        func = rpc(
                            action_in_type,
                            _operation_name=name,
                            _args=args)(f)
            else:
                if len(args_out) > 0:
                    if len(args_out) > 1:
                        #  print(
                        #      'name: %s -- varnames: %s -- types: %s'
                        #      % (name, action_out_varnames, action_out_type))
                        func = rpc(
                            _returns=action_out_type,
                            _out_variable_names=action_out_varnames,
                            _operation_name=name)(f)
                    else:
                        func = rpc(
                            _returns=action_out_type,
                            _out_variable_name=action_out_varname,
                            _operation_name=name)(f)
                else:
                    func = rpc(_operation_name=name)(f)
#             print(name)
#             print(f.fname)
            self.soap_functions.update({name: func})
        self.subscriptions = {}
        if appreg.get_application(self.tns, appname):
            print('**/*/')
            appname = appname + '_'
        soap_service = type(self.name, (ServiceBase,), self.soap_functions)
        soap_service.tns = self.tns
        app = Application([soap_service], tns=self.tns,
                          in_protocol=Soap11(),
                          out_protocol=Soap11(),
                          name=appname)
        app.event_manager.add_listener('method_call', _map_context)
        self.app = app
#         print(self.soap_functions)
#         print('name: %s, methods: %s' %
#               (appname, app.interface.service_method_map))
        if self.event_properties is None:
            self.event_properties = {}

    def _get_type(self, typ):
        if typ in ('string', 'bin.base64', 'uri'):
            return Unicode
        elif typ == 'ui4':
            return UnsignedInteger32
        elif typ == 'i4':
            return Integer32
        elif typ == 'boolean':
            return Boolean
        else:
            raise Exception('Unknown type: %s' % typ)

    def _generate_subscription_sid(self):
        result = None
        retries = 0
        while result is None and retries < 10:
            generated_uuid = str(uuid.uuid4())
            if generated_uuid not in self.subscriptions:
                result = generated_uuid
            else:
                retries += 1
        if result is None:
            raise Exception()
        return result

    def subscribe(self, callback, timeout, renew=False):
        sid = 'uuid:' + self._generate_subscription_sid()
#         if isinstance(callback, str):
#             sid = 'uuid:' + self._generate_subscription_sid()
#         else:
#             sid = callback
#             callback = None
#         log.err(
#             '%s subscription for callback %s' % (
#                                     self.parent.friendlyName, callback))
        if (self.subscription_timeout_range[0] is not None and
                timeout < self.subscription_timeout_range[0]):
            timeout = self.subscription_timeout_range[0]

        if (self.subscription_timeout_range[1] is not None and
                timeout > self.subscription_timeout_range[1]):
            timeout = self.subscription_timeout_range[1]

        subscription = EventSubscription(sid, callback, timeout)

        if not renew:
            for prop in self.event_properties.values():
                subscription.notify(prop)
        if callback:
            if sid in self.subscriptions:
                self.subscriptions[sid].append(subscription)
            else:
                self.subscriptions.update({sid: [subscription]})
            return {
                'SID': sid,
                'TIMEOUT': 'Second-' + str(timeout)}
        else:
            return timeout

    def notify(self, prop):

        #  if hasattr(self, 'parent'):
        #      log.err('%s notify: %s' % (
        #                       self.parent.friendlyName, self.subscriptions))
        #  log.msg('svc notify')
        #  log.msg(self.subscriptions)
        for sid, subscription_list in self.subscriptions.items():
            for i, subscription in enumerate(subscription_list):
                if subscription.expired:
                    log.msg('pop!')
                    subscription_list.pop(i)
                else:
                    subscription.notify(prop)
            self.subscriptions[sid] = subscription_list

    def dump(self):
        scpd = et.Element('scpd',
                          {'xmlns': 'urn:schemas-upnp-org:service-1-0'})

        # specVersion
        specVersion = et.Element('specVersion')
        specVersion.append(make_element('major', str(self.version[0])))
        specVersion.append(make_element('minor', str(self.version[1])))
        scpd.append(specVersion)

        # actionList
        actionList = et.Element('actionList')
        for action_name, action_args in self.actions.items():
            action = et.Element('action')
            action.append(make_element('name', action_name))

            argumentList = et.Element('argumentList')
            for arg in action_args:
                argumentList.append(arg.dump())
            action.append(argumentList)

            actionList.append(action)
        scpd.append(actionList)

        # serviceStateTable
        serviceStateTable = et.Element('serviceStateTable')
        for stateVariable in self.stateVariables.values():
            serviceStateTable.append(stateVariable.dump())
        scpd.append(serviceStateTable)
#         log.msg("xml tree dumped")

        return scpd

    def dumps(self, force=False):
        if self.__class__._description is None or force:
            self.__class__._description =\
                '<?xml version="1.0" encoding="utf-8"?>' +\
                et.tostring(self.dump())
        return self.__class__._description


def notify(cls, prop):

    #  if hasattr(cls, 'parent'):
    #      log.err('%s notify: %s' % (
    #                           cls.parent.friendlyName, cls.subscriptions))
    log.msg('svc notify')
    for sid, subscription_list in cls.subscriptions.items():
        for i, subscription in enumerate(subscription_list):
            if subscription.expired:
                subscription_list.pop(i)
            else:
                subscription.notify(prop)
        cls.subscriptions[sid] = subscription_list


class ServiceActionArgument(object):
    __slots__ = ['name', 'direction', 'stateVariable',
                 'parameterName', '__dict__']

    def __init__(self, name='', direction='out', relatedStateVariable=''):
        self.name = name
        self.direction = direction
        self.stateVariable = relatedStateVariable
        self.parameterName = None

    def dump(self):
        argument = et.Element('argument')
        argument.append(make_element('name', self.name))
        argument.append(make_element('direction', self.direction))
        argument.append(make_element(
            'relatedStateVariable', self.stateVariable))
        return argument


class ServiceStateVariable(object):
    __slots__ = ['name',
                 'dataType',
                 'allowedValues',
                 'sendEvents',
                 'allowedRange',
                 '__dict__']

    def __init__(
            self, name, dataType,
            allowedValues=None, sendEvents=False, allowedRange=None):
        self.name = name
        self.dataType = dataType
        self.allowedValues = allowedValues
        self.sendEvents = sendEvents
        self.allowedRange = allowedRange

    def dump(self):
        sendEventsStr = "no"
        if self.sendEvents:
            sendEventsStr = "yes"

        stateVariable = et.Element('stateVariable', sendEvents=sendEventsStr)

        stateVariable.append(make_element('name', self.name))
        stateVariable.append(make_element('dataType', self.dataType))

        if self.allowedValues:
            allowedValues = et.Element('allowedValueList')
            for value in self.allowedValues:
                allowedValues.append(make_element('allowedValue', value))
            stateVariable.append(allowedValues)

        if self.allowedRange:
            allowedRange = et.Element('allowedValueRange')
#             minimum = et.Element('minimum', text=str(self.allowedRange[0]))
            allowedRange.append(make_element('minimum', self.allowedRange[0]))
#             maximum = et.Element('maximum', text=str(self.allowedRange[1]))
            allowedRange.append(make_element('maximum', self.allowedRange[1]))
#             step = et.Element('step', text=str(self.allowedRange[2]))
            allowedRange.append(make_element('step', self.allowedRange[2]))
            stateVariable.append(allowedRange)

#         if self.name == 'Volume':
#             log.msg(stateVariable)
        return stateVariable


class UserDefinedContext(object):

    def __init__(self, client):
        self.client = client


def cc_to_us(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(
        '([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace('__', '_')


def make_func(name):
    def func(ctx, *args, **kwargs):
        return getattr(ctx.udc.client, name)(*args, **kwargs)
    return func


def get_event_catcher(obj):
    def event_catcher(evt, var):
        log.msg('%s event: %s ==> %s' % (obj.type, var, evt))
        setattr(obj, var, evt)
    return event_catcher


def buildServiceFromXml(cls, filename):
    tree = et.parse(filename)
    root = tree.getroot()
    if not root.tag.endswith('scpd'):
        raise Exception('Bad xml service File')
        return
    for child in root:
        if child.tag.endswith('actionList'):
            cls.actions = OrderedDict()
            for actions in child:
                for action in actions:
                    if action.tag.endswith('name'):
                        args = []
                        name = action.text
#                         log.err(name)
                    elif action.tag.endswith('argumentList'):
                        for triple in action:
                            tri = {}
                            for arg in triple:
                                tri.update({arg.tag.split('}')[-1]: arg.text})
                            args.append(ServiceActionArgument(**tri))
                cls.actions.update({name: args})
        elif child.tag.endswith('serviceStateTable'):
            cls.stateVariables = []
            for statevariable in child:
                sendevents = False
                args = []
                values = []
                if "sendEvents" in statevariable.attrib:
                    if statevariable.attrib['sendEvents'] == 'yes':
                        sendevents = True
                for arg in statevariable:
                    if arg.tag.endswith('sendEventsAttribute'):
                        if arg.text == 'yes':
                            sendevents = True
                    else:
                        if arg.tag.endswith('allowedValueList'):
                            for value in arg:
                                values.append(value.text)
                        elif arg.tag.endswith('Optional'):
                            continue
                        else:
                            args.append(arg.text)
                if len(values) > 0:
                    args.append(values)
#                 print(args)
                if sendevents:
                    cls.stateVariables.append(
                        ServiceStateVariable(*args, sendEvents=True))
                    setattr(cls, args[0].lower(), EventProperty(args[0]))
                else:
                    cls.stateVariables.append(ServiceStateVariable(*args))


if __name__ == '__main__':
    from twisted.internet import reactor
    from twisted.web.server import Site
#     from upnpy_spyne.services.templates.playlist import Playlist

    class obj(object):
        pass

    class test2(Service):
        pass
    test = test2(
        'playlist', 'urn:av-openhome-org:service:Playlist:1', None,
        '/home/babe/Projets/eclipse/onDemand/data/xml/playlist.xml')
#     test = test2(
#         'pttroduct', 'urn:av-openhome-org:service:Product:1', None,
#         '/home/babe/Projets/eclipse/onDemand/data/xml/product.xml')
#     print(dir(test))
#     buildServiceFromXml(
#         test,
#         '/home/babe/Projets/eclipse/onDemand/data/xml/playlist.xml')
#     print(test.actions)
#     print(test.stateVariables)
#     for var in test.stateVariables:
#         print(var.name)
#         print(var.sendEvents)
#     print("%s, %s, %s" % (
#         test.stateVariables[0].name,
#         test.stateVariables[0].dataType,
#         test.stateVariables[0].allowedValues))
#     print(dir(test.soap_service))
    for k, v in test.soap_functions.items():
        print('%s --> %s' % (k, v))
#     print(test.soap_functions)
    print(test.resource)

    reactor.listenTCP(  # @UndefinedVariable
        8000,
        Site(test.control_resource),
        interface='0.0.0.0')
    reactor.run()  # @UndefinedVariable
