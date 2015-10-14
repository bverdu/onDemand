# encoding: utf-8
'''
Created on 10 avr. 2015

@author: Bertrand Verdu
'''
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Boolean
import logging


class SwitchPower(ServiceBase):
    '''
    switch power upnp service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = "urn:schemas-upnp-org:service:SwitchPower:1"

    @rpc(Boolean)
    def SetTarget(ctx, newTargetValue):  # @NoSelf
        try:
            return ctx.udc.client.set_target(newTargetValue)
        except NameError:
            raise Exception('not found : %s' % ctx.udc)
            return

    @rpc(_returns=Boolean, _out_variable_name='RetTargetValue')
    def GetTarget(ctx):  # @NoSelf
        try:
            return ctx.udc.client.status
        except NameError:
            raise Exception('not found : %s' % ctx.udc)
            return False

    @rpc(_returns=Boolean, _out_variable_name='ResultStatus')
    def GetStatus(ctx):  # @NoSelf
        try:
            return ctx.udc.client.status
        except NameError:
            show('not found : %s' % ctx.udc)
            return False
        
def show(self, msg):
    logging.info(msg)
