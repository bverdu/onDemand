# encoding: utf-8
'''
Created on 20 mars 2015

@author: babe
'''


from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.model.binary import ByteArray


class Playlist(ServiceBase):
    '''
    Playlist OpenHome service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = 'urn:av-openhome-org:service:Playlist:1'

    @rpc()
    def Play(ctx):  # @NoSelf
        pass

    @rpc()
    def Pause(ctx):  # @NoSelf
        pass

    @rpc()
    def Stop(ctx):  # @NoSelf
        pass

    @rpc()
    def Next(ctx):  # @NoSelf
        pass

    @rpc()
    def Previous(ctx):  # @NoSelf
        pass

    @rpc(Boolean)
    def SetRepeat(ctx, Value):  # @NoSelf
        pass

    @rpc(_returns=Boolean, _out_variable_name='Value')
    def Repeat(ctx):  # @NoSelf
        pass

    @rpc(Boolean)
    def SetShuffle(ctx, Value):  # @NoSelf
        pass

    @rpc(_returns=Boolean, _out_variable_name='Value')
    def Shuffle(ctx):  # @NoSelf
        pass

    @rpc(Integer)
    def SeekSecondAbsolute(ctx, Value):  # @NoSelf
        pass

    @rpc(Integer)
    def SeekSecondRelative(ctx, Value):  # @NoSelf
        pass

    @rpc(Unicode)
    def SeekId(ctx, Value):  # @NoSelf
        pass

    @rpc(Unicode)
    def SeekIndex(ctx, Value):  # @NoSelf
        pass

    @rpc(_returns=Unicode, _out_variable_name='Value')
    def TransportState(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name='Value')
    def Id(ctx):  # @NoSelf
        pass

    @rpc(Unicode,  _returns=(Unicode, Unicode),
         _out_variable_names=('Uri', 'Metadata'))
    def Read(ctx, Id):  # @NoSelf
        pass

    @rpc(Unicode,  _returns=Unicode,
         _out_variable_name='TrackList')
    def ReadList(ctx, IdList):  # @NoSelf
        pass

    @rpc(Integer, Unicode, Unicode, _returns=Integer,
         _out_variable_name='NewId')
    def Insert(ctx, AfterId, Uri, Metadata):  # @NoSelf
        pass

    @rpc(Unicode)
    def DeleteId(ctx, Value):  # @NoSelf
        pass

    @rpc()
    def DeleteAll(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer,  _out_variable_name='Value')
    def TracksMax(ctx):  # @NoSelf
        pass

    @rpc(_returns=(Unicode, Unicode), _out_variable_names=('Token', 'Array'))
    def IdArray(ctx):  # @NoSelf
        pass

    @rpc(Unicode, _return=Unicode, _out_variable_name='Value')
    def IdArrayChanged(ctx, Token):  # @NoSelf
        pass

    @rpc(_returns=Unicode, _out_variable_name='Value')
    def ProtocolInfo(ctx):  # @NoSelf
        pass
