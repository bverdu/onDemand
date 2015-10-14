'''
Created on 17 mai 2015

@author: Bertrand Verdu
'''

from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.model.binary import ByteArray


class Volume(ServiceBase):
    '''
    Volume OpenHome service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = 'urn:av-openhome-org:service:Volume:1'

    @rpc(_returns=(Integer, Integer, Integer, Integer, Integer, Integer),
         _out_variable_names=(
        'VolumeMax', 'VolumeUnity', 'VolumeSteps', 'VolumeMilliDbPerStep',
        'BalanceMax', 'FadeMax'))
    def Characteristics(ctx):  # @NoSelf
        pass

    @rpc(Integer)
    def SetVolume(ctx, Value):  # @NoSelf
        pass

    @rpc()
    def VolumeInc(ctx):  # @NoSelf
        pass

    @rpc()
    def VolumeDec(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name='Value')
    def Volume(ctx):  # @NoSelf
        pass

    @rpc(Integer)
    def SetBalance(ctx, Value):  # @NoSelf
        pass

    @rpc()
    def BalanceInc(ctx):  # @NoSelf
        pass

    @rpc()
    def BalanceDec(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name='Value')
    def Balance(ctx):  # @NoSelf
        pass

    @rpc(Integer)
    def SetFade(ctx, Value):  # @NoSelf
        pass

    @rpc()
    def FadeInc(ctx):  # @NoSelf
        pass

    @rpc()
    def FadeDec(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name='Value')
    def Fade(ctx):  # @NoSelf
        pass

    @rpc(Boolean)
    def SetMute(ctx, Value):  # @NoSelf
        pass

    @rpc(_returns=Boolean, _out_variable_name='Value')
    def Mute(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name="Value")
    def VolumeLimit(ctx):  # @NoSelf
        pass

