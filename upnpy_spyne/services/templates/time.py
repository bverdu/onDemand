'''
Created on 16 juil. 2015

@author: Bertrand Verdu
'''

from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer
# from spyne.model.binary import ByteArray


class Time(ServiceBase):
    '''
    Time OpenHome service template
    Do not instantiate this class, it is an abstract class,
    use it as is for client application or subclass it for server application
    '''
    tns = 'urn:av-openhome-org:service:Time:1'

    @rpc(_returns=(Integer, Integer, Integer),
         _out_variable_names=('TrackCount', 'Duration', 'Seconds'))
    def Time(ctx):  # @NoSelf
        pass
