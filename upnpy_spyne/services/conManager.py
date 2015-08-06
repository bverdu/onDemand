'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from upnpy.services import register_action
from templates.connection_manager import ConnectionManagerService


class ConnectionManager(ConnectionManagerService):
    def __init__(self, player):
        ConnectionManagerService.__init__(self)
        self.event_schema = 'urn:schemas-upnp-org:metadata-1-0/RCS/'
        self.source_protocol_info_value = ''
        self.sink_protocol_info_value = ''
        self.current_connection_ids = '0'
        player.upnp_eventCM = self.upnp_event

    @register_action('GetProtocolInfo')
    def getProtocolInfo(self):
        log.err('GetProtocolInfo from ConnectionManager', loglevel='debug')
        log.err(self.parent.player.mtlist)
        return {
            'Source': self.source_protocol_info_value,
            'Sink': self.parent.player.mtlist}

    def upnp_event(self, var, evt):
        log.msg(evt)
        setattr(self, var, evt)
