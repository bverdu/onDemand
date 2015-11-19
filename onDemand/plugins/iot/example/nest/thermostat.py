# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''
from onDemand.plugins.iot.device import Device
from onDemand.plugins.iot.sensor import Sensor


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
    urn_template = 'urn:upnp.org:smgt-surn:%s:onDemand.org:' + \
        'nest.com-thermostat-meet-nest-thermostat:nest.org:%s'
    sensor_urns = [
        urn_template % ('10S3', 'setting')]  # Thermostat
    sensors = {urn_template % ('10S3', 'setting'): []}
    _sensors = {}
    parameters = {}

    def __init__(self, _id, data={}, nestapi=None):
        self._sensors = {}
        self.parameters = {}
        self.structure_id = ''
        self.where_id = ''
        self.device_id = _id
        super(Thermostat, self).__init__(data, nestapi)
        self.generate_sensors()

    def generate_sensors(self):
        prefix = '[' + self.where_id + ']'
        urn = self.urn_template % ('10S3', 'setting')
        for var in self.events:
            _id = '-'.join((self.device_id, var))
            tm = ''
            name = prefix + var
            if var == 'humidity':
                paramtype = 'uda:float'
                access = 'ro'
                desc = 'Humidity'
            elif 'temperature' in var:
                if 'scale' in var:
                    paramtype = 'uda:string'
                    access = 'ro'
                    desc = 'Unity'
                elif 'ambient' in var:
                    paramtype = 'uda:float'
                    access = 'ro'
                    desc = 'Temperature'
                else:
                    paramtype = 'uda:float'
                    access = 'rw'
                    desc = 'Set ' + var.split('_')[0] + ' temperature'
            elif 'hvac' in var:
                paramtype = 'uda:string'
                desc = 'Hvac ' + ''.join(var.split('_')[1:])
                access = 'ro'
            elif var == 'has_leaf':
                paramtype = 'uda:bool'
                access = 'ro'
                desc = 'Eco'
            elif var == 'fan_timer_active':
                paramtype = 'uda:bool'
                desc = 'Fan'
                access = 'rw'
            elif var == 'is_using_emergency_heat':
                paramtype = 'uda:bool'
                access = 'rw'
                desc = 'Emergency Heat'
            s = Sensor(var, name, paramtype, _id, tm, access=access,
                       desc=desc, urn=urn)
            self.sensors[urn].append(s)
            self._sensors.update({var: s})

    def event(self, evt, var):
        print('Thermostat event: %s: %s' % (var, evt))

if __name__ == '__main__':
    test = Thermostat('toto')
    print(test.sensors.keys())
