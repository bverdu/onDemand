'''
Created on 27 déc. 2014

@author: babe
'''

from upnpy.event import EventProperty
from upnpy.services import Service, ServiceActionArgument,\
    register_action, ServiceStateVariable
from upnpy.utils import soapConfig


class SwitchPower(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:SwitchPower:1"
    serviceId = "urn:upnp-org:serviceId:SwitchPower"
    serviceUrl = "SP"

    subscription_timeout_range = (None, None)

    actions = {
        'SetTarget': [
            ServiceActionArgument('newTargetValue', 'in', 'Target')],
        'GetTarget': [
            ServiceActionArgument('RetTargetValue', 'out', 'Target')],
        'GetStatus': [
            ServiceActionArgument('ResultStatus', 'out', 'Status')]
    }
    stateVariables = [
        ServiceStateVariable('Target', 'boolean'),
        ServiceStateVariable('Status', 'boolean')
        ]

    status = EventProperty('Status')
    soap_conf = soapConfig(actions)

    @register_action('SetTarget')
    def setTarget(self, new_value):
        raise NotImplementedError()

    @register_action('GetTarget')
    def getTarget(self):
        raise NotImplementedError()

    @register_action('GetStatus')
    def getStatus(self):
        raise NotImplementedError()
