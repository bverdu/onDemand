# encoding: utf-8
'''
Created on 18 mars 2015

@author: Bertrand Verdu
'''
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, Unicode


class ContentDirectory(ServiceBase):
    '''
    Content Directory upnp service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = 'urn:schemas-upnp-org:service:ContentDirectory:1'

    @rpc(_returns=Unicode)
    def GetSearchCapabilities(ctx):  # @NoSelf
        pass

    @rpc(_returns=Unicode)
    def GetSortCapabilities(ctx):  # @NoSelf
        pass

    @rpc(_returns=Unicode)
    def GetSystemUpdateID(ctx):  # @NoSelf
        pass

    @rpc(
        Unicode, Unicode, Unicode, Integer, Integer, Unicode,
        _returns=(Unicode, Integer, Integer, Integer),
        _out_variable_names=(
            'Result', 'NumberReturned', 'TotalMatches', 'UpdateID'))
    def Browse(ctx, ObjectID, BrowseFlag, Filter,  # @NoSelf
               StartingIndex, RequestedCount, SortCriteria):
        pass

    @rpc(
        Unicode, Unicode, Unicode, Integer, Integer, Unicode,
        _returns=(Unicode, Integer, Integer, Integer),
        _out_variable_names=(
            'Result', 'NumberReturned', 'TotalMatches', 'UpdateID'))
    def Search(  # @NoSelf
            ctx, containerID, searchCriteria, searchFilter, startingIndex,
            requestedCount, sortCriteria):
        pass

    @rpc(Unicode, Unicode, _returns=(Unicode, Unicode),
         _out_variable_names=('ObjectID', 'Result'))
    def CreateObject(ctx, containerID, elements):   # @NoSelf
        pass

    @rpc(Unicode)
    def DestroyObject(ctx, objectID):  # @NoSelf
        pass

    @rpc(Unicode, Unicode, Unicode)
    def UpdateObject(ctx, objectID, currentTagValue, newTagValue):  # @NoSelf
        pass

    @rpc(Unicode, Unicode, _returns=Unicode,  _out_variable_name='TransferID')
    def ImportResource(ctx, sourceUri, destUri):  # @NoSelf
        pass

    @rpc(Unicode, Unicode, _returns=Unicode, _out_variable_name='TransferID')
    def ExportResource(ctx, sourceUri, destUri):  # @NoSelf
        pass

    @rpc(Unicode)
    def StopTransferResource(ctx, transferID):  # @NoSelf
        pass

    @rpc(Unicode, _returns=(Unicode, Integer, Integer),
         _out_variable_names=(
        'TransferStatus', 'TransferLength', 'TransferTotal'))
    def GetTransferProgress(ctx, transferID):  # @NoSelf
        pass

    @rpc(Unicode)
    def DeleteResource(ctx, ResourceUri):  # @NoSelf
        pass

    @rpc(Unicode, Unicode, _returns=Unicode,  _out_variable_name='NewID')
    def CreateReference(ctx, containerID, objectID):  # @NoSelf
        pass
