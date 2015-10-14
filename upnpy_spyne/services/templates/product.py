'''
Created on 8 janv. 2015

@author: Bertrand Verdu
'''

from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.model.binary import ByteArray


class Product(ServiceBase):
    '''
    Playlist OpenHome service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = 'urn:av-openhome-org:service:Product:1'

    @rpc(_returns=(Unicode, Unicode, Unicode, Unicode),
         _out_variable_names=('Name', 'Info', 'Url', 'ImageUri'))
    def Manufacturer(ctx):  # @NoSelf
        pass

    @rpc(_returns=(Unicode, Unicode, Unicode, Unicode),
         _out_variable_names=('Name', 'Info', 'Url', 'ImageUri'))
    def Model(ctx):  # @NoSelf
        pass

    @rpc(_returns=(Unicode, Unicode, Unicode, Unicode, Unicode),
         _out_variable_names=('Room', 'Name', 'Info', 'Url', 'ImageUri'))
    def Product(ctx):  # @NoSelf
        pass

    @rpc(_returns=Boolean, _out_variable_name="Value")
    def Standby(ctx):  # @NoSelf
        pass

    @rpc(Boolean)
    def SetStandby(ctx, Value):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name='Value')
    def SourceCount(ctx):  # @NoSelf
        pass

    @rpc(_returns=Unicode, _out_variable_name="Value")
    def SourceXml(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name="Value")
    def SourceIndex(ctx):  # @NoSelf
        pass

    @rpc(Integer)
    def SetSourceIndex(ctx, Value):  # @NoSelf
        pass

    @rpc(Unicode)
    def SetSourceIndexByName(ctx, Value):  # @NoSelf
        pass

    @rpc(Integer, _returns=(Unicode, Unicode, Unicode, Boolean),
         _out_variable_names=('SystemName', 'Type', 'Name', 'Visible'))
    def Source(ctx, Index):  # @NoSelf
        pass

    @rpc(_returns=Unicode, _out_variable_name="Value")
    def Attributes(ctx):  # @NoSelf
        pass

    @rpc(_returns=Integer, _out_variable_name="Value")
    def SourceXmlChangeCount(ctx):  # @NoSelf
        pass
