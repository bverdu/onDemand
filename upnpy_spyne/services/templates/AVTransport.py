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

from upnpy.event import EventProperty
from upnpy.services import Service, ServiceActionArgument, \
    ServiceStateVariable
from upnpy.utils import soapConfig


class AVTransportService(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:AVTransport:1"
    serviceId = "urn:upnp-org:serviceId:AVTransport"
    serviceUrl = "AVTransport"
    subscription_timeout_range = (None, None)
    type = 'UpnpAv'
    actions = {
        'SetAVTransportURI': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('CurrentURI', 'in', 'AVTransportURI'),
            ServiceActionArgument(
                'CurrentURIMetaData',
                'in',
                'AVTransportURIMetaData')],
        'SetNextTranportURI': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('NextURI', 'in', 'AVTransportURI'),
            ServiceActionArgument(
                'CurrentURIMetaData', 'in', 'AVTransportURIMetaData')],
        'GetMediaInfo': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('NrTracks', 'out', 'NumberOfTracks'),
            ServiceActionArgument(
                'MediaDuration', 'out', 'CurrentMediaDuration'),
            ServiceActionArgument('CurrentURI', 'out', 'AVTransportURI'),
            ServiceActionArgument(
                'CurrentURIMetaData', 'out', 'AVTransportURIMetaData'),
            ServiceActionArgument('NextURI', 'out', 'AVTransportURI'),
            ServiceActionArgument(
                'NextURIMetaData', 'out', 'AVTransportURIMetaData'),
            ServiceActionArgument(
                'PlayMedium', 'out', 'PlaybackStorageMedium'),
            ServiceActionArgument(
                'RecordMedium', 'out', 'RecordStorageMedium'),
            ServiceActionArgument(
                'WriteStatus', 'out', 'RecordMediumWriteStatus')],
        'GetMediaInfo_Ext': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument(
                'CurrentType', 'out', 'CurrentMediaCategory'),
            ServiceActionArgument('NrTracks', 'out', 'NumberOfTracks'),
            ServiceActionArgument(
                'MediaDuration', 'out', 'CurrentMediaDuration'),
            ServiceActionArgument('CurrentURI', 'out', 'AVTransportURI'),
            ServiceActionArgument(
                'CurrentURIMetaData', 'out', 'AVTransportURIMetaData'),
            ServiceActionArgument('NextURI', 'out', 'AVTransportURI'),
            ServiceActionArgument(
                'NextURIMetaData', 'out', 'AVTransportURIMetaData'),
            ServiceActionArgument(
                'PlayMedium', 'out', 'PlaybackStorageMedium'),
            ServiceActionArgument(
                'RecordMedium', 'out', 'RecordStorageMedium'),
            ServiceActionArgument(
                'WriteStatus', 'out', 'RecordMediumWriteStatus')],
        'GetTransportInfo': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument(
                'CurrentTransportState', 'out', 'TransportState'),
            ServiceActionArgument(
                'CurrentTransportStatus', 'out', 'TransportStatus'),
            ServiceActionArgument(
                'CurrentSpeed', 'out', 'TransportPlaySpeed')],
        'GetPositionInfo': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Track', 'out', 'CurrentTrack'),
            ServiceActionArgument(
                'TrackDuration', 'out', 'CurrentTrackDuration'),
            ServiceActionArgument(
                'TrackMetaData', 'out', 'CurrentTrackMetaData'),
            ServiceActionArgument('TrackURI', 'out', 'CurrentTrackURI'),
            ServiceActionArgument('RelTime', 'out', 'RelativeTimePosition'),
            ServiceActionArgument('AbsTime', 'out', 'AbsoluteTimePosition'),
            ServiceActionArgument(
                'RelCount', 'out', 'RelativeCounterPosition'),
            ServiceActionArgument(
                'AbsCount', 'out', 'AbsoluteCounterPosition')],
        'GetDeviceCapabilities': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument(
                'PlayMedia', 'out', 'PossiblePlaybackStorageMedia'),
            ServiceActionArgument(
                'RecMedia', 'out', 'PossibleRecordStorageMedia'),
            ServiceActionArgument(
                'RecQualityModes', 'out', 'PossibleRecordQualityModes')],
        'GetTransportSettings': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('PlayMode', 'out', 'CurrentPlayMode'),
            ServiceActionArgument(
                'RecQualityMode', 'out', 'CurrentRecordQualityMode')],
        'Stop': [
            ServiceActionArgument(
                'InstanceID', 'in', 'A_ARG_TYPE_InstanceID')],
        'Play': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Speed', 'in', 'TransportPlaySpeed')],
        'Pause': [
            ServiceActionArgument(
                'InstanceID', 'in', 'A_ARG_TYPE_InstanceID')],
        'Record': [
            ServiceActionArgument(
                'InstanceID', 'in', 'A_ARG_TYPE_InstanceID')],
        'Seek': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Unit', 'in', 'A_ARG_TYPE_SeekMode'),
            ServiceActionArgument('Target', 'in', 'A_ARG_TYPE_SeekTarget')],
        'Next': [
            ServiceActionArgument(
                'InstanceID', 'in', 'A_ARG_TYPE_InstanceID')],
        'Previous': [
            ServiceActionArgument(
                'InstanceID', 'in', 'A_ARG_TYPE_InstanceID')],
        'SetPlayMode': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('NewPlayMode', 'in', 'CurrentPlayMode')],
        'SetRecordQualityMode': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument(
                'NewRecordQualityMode', 'in', 'CurrentRecordQualityMode')],
        'GetCurrentTransportActions': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Actions', 'out', 'CurrentTransportActions')]
    }
    stateVariables = [
        ServiceStateVariable('TransportState', 'string', [
            'STOPPED', 'PLAYING', 'TRANSITIONING', 'PAUSED_PLAYBACK',
            'PAUSED_RECORDING', 'RECORDING', 'NO_MEDIA_PRESENT']),
        ServiceStateVariable('TransportStatus', 'string', [
            'OK', 'ERROR_OCCURED']),
        ServiceStateVariable('CurrentMediaCategory', 'string', [
            'NO_MEDIA', 'TRACK_AWARE', 'TRACK_UNAWARE']),
        ServiceStateVariable('PlaybackStorageMedium', 'string', [
            'UNKNOWN', 'DV', 'MINI-DV', 'VHS', 'W-VHS', 'S-VHS', 'D-VHS',
            'VHSC', 'VIDEO8', 'HI8', 'CD-ROM', 'CD-DA', 'CD-R', 'CD-RW',
            'VIDEO-CD', 'SACD',  'MD-AUDIO', 'MD-PICTURE', 'DVD-ROM',
            'DVD-VIDEO', 'DVD+R', 'DVD-R', 'DVD+RW', 'DVD-RW', 'DVD-RAM',
            'DVD-AUDIO', 'DAT', 'LD', 'HDD', 'MICRO-MV', 'NETWORK', 'NONE',
            'NOT_IMPLEMENTED', 'SD', 'PC-CARD', 'MMC', 'CF', 'BD', 'MS',
            'HD-DVD']),
        ServiceStateVariable('RecordStorageMedium', 'string', [
            'UNKNOWN', 'DV', 'MINI-DV', 'VHS', 'W-VHS', 'S-VHS', 'D-VHS',
            'VHSC', 'VIDEO8', 'HI8', 'CD-ROM', 'CD-DA', 'CD-R', 'CD-RW',
            'VIDEO-CD', 'SACD',  'MD-AUDIO', 'MD-PICTURE', 'DVD-ROM',
            'DVD-VIDEO', 'DVD+R', 'DVD-R', 'DVD+RW', 'DVD-RW', 'DVD-RAM',
            'DVD-AUDIO', 'DAT', 'LD', 'HDD', 'MICRO-MV', 'NETWORK', 'NONE',
            'NOT_IMPLEMENTED', 'SD', 'PC-CARD', 'MMC', 'CF', 'BD', 'MS',
            'HD-DVD']),
        ServiceStateVariable('PossiblePlaybackStorageMedia', 'string', [
            'UNKNOWN', 'DV', 'MINI-DV', 'VHS', 'W-VHS', 'S-VHS', 'D-VHS',
            'VHSC', 'VIDEO8', 'HI8', 'CD-ROM', 'CD-DA', 'CD-R', 'CD-RW',
            'VIDEO-CD', 'SACD',  'MD-AUDIO', 'MD-PICTURE', 'DVD-ROM',
            'DVD-VIDEO', 'DVD+R', 'DVD-R', 'DVD+RW', 'DVD-RW', 'DVD-RAM',
            'DVD-AUDIO', 'DAT', 'LD', 'HDD', 'MICRO-MV', 'NETWORK', 'NONE',
            'NOT_IMPLEMENTED', 'SD', 'PC-CARD', 'MMC', 'CF', 'BD', 'MS',
            'HD-DVD']),
        ServiceStateVariable('PossibleRecordStorageMedia', 'string', [
            'UNKNOWN', 'DV', 'MINI-DV', 'VHS', 'W-VHS', 'S-VHS', 'D-VHS',
            'VHSC', 'VIDEO8', 'HI8', 'CD-ROM', 'CD-DA', 'CD-R', 'CD-RW',
            'VIDEO-CD', 'SACD',  'MD-AUDIO', 'MD-PICTURE', 'DVD-ROM',
            'DVD-VIDEO', 'DVD+R', 'DVD-R', 'DVD+RW', 'DVD-RW', 'DVD-RAM',
            'DVD-AUDIO', 'DAT', 'LD', 'HDD', 'MICRO-MV', 'NETWORK', 'NONE',
            'NOT_IMPLEMENTED', 'SD', 'PC-CARD', 'MMC', 'CF', 'BD', 'MS',
            'HD-DVD']),
        ServiceStateVariable('CurrentPlayMode', 'string', [
            'NORMAL', 'SHUFFLE', 'REPEAT_ONE', 'REPEAT_ALL',
            'RANDOM', 'DIRECT_1', 'INTRO']),
        ServiceStateVariable('TransportPlaySpeed', 'string'),
        ServiceStateVariable('RecordMediumWriteStatus', 'string', [
            'WRITABLE', 'PROTECTED', 'NOT_WRITABLE',
            'UNKNOWN', 'NOT_IMPLEMENTED']),
        ServiceStateVariable('CurrentRecordQualityMode', 'string', [
            '0:EP', '1:LP', '2:SP', '0:BASIC',
            '1:MEDIUM', '2:HIGH', 'NOT_IMPLEMENTED']),
        ServiceStateVariable('PossibleRecordQualityModes', 'string'),
        ServiceStateVariable('NumberOfTracks', 'ui4'),
        ServiceStateVariable('CurrentTrack', 'ui4'),
        ServiceStateVariable('CurrentTrackDuration', 'string'),
        ServiceStateVariable('CurrentMediaDuration', 'string'),
        ServiceStateVariable('CurrentTrackMetaData', 'string'),
        ServiceStateVariable('CurrentTrackURI', 'string'),
        ServiceStateVariable('AVTransportURI', 'string'),
        ServiceStateVariable('AVTransportURIMetaData', 'string'),
        ServiceStateVariable('NextAVTransportURI', 'string'),
        ServiceStateVariable('NextAVTransportURIMetaData', 'string'),
        ServiceStateVariable('RelativeTimePosition', 'string'),
        ServiceStateVariable('AbsoluteTimePosition', 'string'),
        ServiceStateVariable('RelativeCounterPosition', 'i4'),
        ServiceStateVariable('AbsoluteCounterPosition', 'ui4'),
        ServiceStateVariable(
            'CurrentTransportActions', 'string', [
                'PLAY', 'STOP', 'PAUSE', 'SEEK', 'NEXT', 'PREVIOUS', 'RECORD']
            ),
        ServiceStateVariable('LastChange', 'string', sendEvents=True),
        ServiceStateVariable('DRMState', 'string'),
        ServiceStateVariable('SyncOffset', 'string'),
        ServiceStateVariable('A_ARG_TYPE_SeekMode', 'string'),
        ServiceStateVariable('A_ARG_TYPE_SeekTarget', 'string'),
        ServiceStateVariable('A_ARG_TYPE_InstanceID', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_DeviceUDN', 'string'),
        ServiceStateVariable('A_ARG_TYPE_ServiceType', 'string'),
        ServiceStateVariable('A_ARG_TYPE_ServiceID', 'string'),
        ServiceStateVariable('A_ARG_TYPE_StateVariableValuePairs', 'string'),
        ServiceStateVariable('A_ARG_TYPE_StateVariableList', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistData', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistDataLength', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistOffset', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistTotalLength', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistMIMEType', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistExtendedType', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistStep', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistType', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistInfo', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistStartObjID', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PlaylistStartGroupID', 'string'),
        ServiceStateVariable('A_ARG_TYPE_SyncOffsetAdj', 'string'),
        ServiceStateVariable('A_ARG_TYPE_PresentationTime', 'string'),
        ServiceStateVariable('A_ARG_TYPE_ClockId', 'string'), ]

    last_change = EventProperty(
        'LastChange',
        initial={'TransportState': {'value': "STOPPED"}},
        ns='urn:schemas-upnp-org:metadata-1-0/AVT/')
    # container_update_ids = EventProperty('ContainerUpdateIDs')
    # remote_sharing_enabled = EventProperty('X_RemoteSharingEnabled', 1)
    soap_conf = soapConfig(actions)
    code = '''
from upnpy.services import register_action
@register_action('%s')
def %s(self, %s):
    raise NotImplementedError()
'''
    for action in actions:
        exec code % (
            action,
            'fct_' + action,
            ', '.join((arg.name for arg in actions[action]
                      if arg.direction == 'in')))

#     @register_action('SetAVTransportURI')
#     def set_AVTransportURI(self, instanceID, uri, uri_metadata):
#         raise NotImplementedError()
#
#     @register_action('SetNextTranportURI')
#     def set_NextTransportURI(self, instanceID, uri, uri_metadata):
#         raise NotImplementedError()
#
#     @register_action('GetMediaInfo')
#     def get_MediaInfo(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('GetMediaInfo_Ext')
#     def get_MediaInfoExt(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('GetTransportInfo')
#     def get_TransportInfo(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('GetPositionInfo')
#     def get_PositionInfo(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('GetDeviceCapabilities')
#     def get_DeviceCapabilities(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('GetTransportSettings')
#     def get_TransportSettings(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('Stop')
#     def stop(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('Play')
#     def play(self, instanceID, speed):
#         raise NotImplementedError()
#
#     @register_action('Pause')
#     def pause(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('Record')
#     def record(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('Seek')
#     def seek(self, instanceID, unit, pos):
#         raise NotImplementedError()
#
#     @register_action('Next')
#     def next(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('Previous')
#     def previous(self, instanceID):
#         raise NotImplementedError()
#
#     @register_action('SetPlayMode')
#     def set_PlayMode(self, instanceID, play_mode):
#         raise NotImplementedError()
#
#     @register_action('SetRecordQualityMode')
#     def set_RecordQualityMode(self, instanceID, record_quality_mode):
#         raise NotImplementedError()
#
#     @register_action('GetCurrentTransportActions')
#     def get_CurrentTransportActions(self, instanceID):
#         raise NotImplementedError()
