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
from upnpy.services import Service, ServiceActionArgument,\
    register_action, ServiceStateVariable
from upnpy.utils import soapConfig, make_event


class RenderingControlService(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:RenderingControl:1"
    serviceId = "urn:upnp-org:serviceId:RenderingControl"
    serviceUrl = "RDS"
    volume = 0

    subscription_timeout_range = (None, None)

    actions = {
        'ListPresets': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('CurrentPresetNameList',
                                  'out',
                                  'PresetNameList')],
        'SelectPreset': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('PresetName', 'in', 'A_ARG_TYPE_PresetName')
            ],
        'GetMute': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('CurrentMute', 'out', 'Mute')],
        'SetMute': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('DesiredMute', 'in', 'Mute')],
        'GetVolume': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('CurrentVolume', 'out', 'Volume')],
        'SetVolume': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('DesiredVolume', 'in', 'Volume')],
        'GetVolumeDB': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('CurrentVolume', 'out', 'VolumeDB')],
        'GetVolumeDBRange': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel',  'in',  'A_ARG_TYPE_Channel'),
            ServiceActionArgument('MinValue', 'out', 'VolumeDB'),
            ServiceActionArgument('MaxValue', 'out', 'VolumeDB')],
        'SetVolumeDB': [
            ServiceActionArgument('InstanceID', 'in', 'A_ARG_TYPE_InstanceID'),
            ServiceActionArgument('Channel', 'in', 'A_ARG_TYPE_Channel'),
            ServiceActionArgument('DesiredVolume', 'in',  'VolumeDB')]
    }
    stateVariables = [
        ServiceStateVariable('LastChange', 'string', sendEvents=True),
        ServiceStateVariable('PresetNameList', 'string'),
        ServiceStateVariable('Mute', 'boolean'),
        ServiceStateVariable('Volume', 'ui4', allowedRange=['0', '100', '1']),
        ServiceStateVariable('VolumeDB', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_Channel', 'string', [
            'Master', 'LF', 'RF', 'CF', 'LFE', 'LS', 'RS', 'LFC', 'RFC', 'SD',
            'SL', 'SR', 'T', 'B', 'BC', 'BL', 'BR']),
        ServiceStateVariable('A_ARG_TYPE_InstanceID', 'ui4'),
        ServiceStateVariable('A_ARG_TYPE_PresetName', 'string', [
            'FactoryDefaults', 'InstallationDefaults'])]

    last_change = EventProperty('LastChange',
                                initial={'Volume':
                                         {'attrib': {'channel': 'Master'},
                                          'value': 100},
                                         'Mute':
                                         {'attrib': {'channel': 'Master'},
                                          'value': 0}},
                                ns='urn:schemas-upnp-org:metadata-1-0/RCS/')
    # container_update_ids = EventProperty('ContainerUpdateIDs')
    # remote_sharing_enabled = EventProperty('X_RemoteSharingEnabled', 1)
    soap_conf = soapConfig(actions)

    @register_action('ListPresets')
    def list_presets(self, instanceID):
        raise NotImplementedError()

    @register_action('SelectPreset')
    def select_preset(self, instanceID, preset_name):
        raise NotImplementedError()

    @register_action('GetMute')
    def get_mute(self, instanceID, channel):
        return {self.volume == 0}

    @register_action('SetMute')
    def set_mute(self, instanceID, channel, mute):
        self.set_volume(instanceID, channel)

    @register_action('GetVolume')
    def get_volume(self, instanceID, channel):
        raise NotImplementedError()

    @register_action('SetVolume')
    def set_volume(self, instanceID, channel, volume=0):
        raise NotImplementedError()

    @register_action('GetVolumeDB')
    def get_volumeDB(self, instanceID, channel):
        raise NotImplementedError()

    @register_action('GetVolumeDBRange')
    def get_volumeDB_range(self, instanceID, channel):
        raise NotImplementedError()

    @register_action('SetVolumeDB')
    def set_volumeDB(self, instanceID, channel, volume=53):
        raise NotImplementedError()
