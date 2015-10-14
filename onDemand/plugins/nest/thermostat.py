# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''
from onDemand.plugins.nest import Device
from onDemand.plugins.nest.util import nest_conv, upnp_conv


class Thermostat(Device):
    dev_type = 'thermostat'
    actions = ('fan_timer_active',
               'hvac_mode',
               'target_temperature_c',
               'target_temperature_f')
    events = ('humidity',
              'hvac_mode',
              'target_temperature_c',
              'target_temperature_f',
              'ambient_temperature_c',
              'ambient_temperature_f',
              'hvac_state',
              'has_leaf',
              'is_using_emergency_heat',
              'fan_timer_active',
              'temperature_scale')
    humidity = 0
    locale = "fr-CA"
    temperature_scale = "C"
    is_using_emergency_heat = False
    has_fan = False
    software_version = "1.0"
    has_leaf = True,
    name = ''
    can_heat = False
    can_cool = False
    hvac_mode = 'heat'
    target_temperature_c = .0
    target_temperature_f = .0
    target_temperature_high_c = .0
    target_temperature_high_f = .0
    target_temperature_low_c = .0
    target_temperature_low_f = .0
    ambient_temperature_c = .0
    ambient_temperature_f = .0
    away_temperature_high_c = .0
    away_temperature_high_f = .0
    away_temperature_low_c = .0
    away_temperature_low_f = .0
    fan_timer_active = False
    name_long = ''
    is_online = True
    hvac_state = 'cooling'

    def __init__(self, _id, data={}, nestapi=None):
        self._sensors = {}
        self.parameters = {}
        self.structure_id = ''
        self.where_id = ''
        self.device_id = _id
        self.api = nestapi
        super(Thermostat, self).__init__(data, nestapi.event)

    def event(self, evt, var):
        print('Thermostat event: %s: %s' % (var, evt))

    '''
    Remote UPNP Actions
    '''
    #  HVAC_UserOperatingMode

    def r_set_mode_target(self, mode):
        if mode in ('Off', 'HeatOn', 'CoolOn', 'AutoChangeOver'):
            self.api.devices('thermostats/' + bytes(self.device_id),
                             hvac_mode=nest_conv(mode))
        else:
            return 700

    def r_get_mode_target(self):
        return upnp_conv(self.hvac_mode)

    def r_get_mode_status(self):
        return upnp_conv(self.hvac_state)

    def r_get_name(self):
        struct = self.api._structures[self.structure_id]
        return self.name +\
            '[' + struct.name + '/' +\
            struct.wheres[self.where_id]['name'] + ']'
