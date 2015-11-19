# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''
from onDemand.plugins.iot.device import Device
from onDemand.plugins.iot.sensor import Sensor


class SmokeAlarm(Device):
    dev_type = 'smoke_co_alarm'
    actions = ()
    events = ('battery_health',
              'co_alarm_state',
              'smoke_alarm_state',
              'ui_color_state',
              'is_manual_test_active',
              'last_manual_test_time')
    name = ''
    locale = 'fr-CA'
    software_version = "1.0.2rc2"
    name_long = ''
    is_online = True
    battery_health = 'ok'
    co_alarm_state = 'ok'
    smoke_alarm_state = 'ok'
    ui_color_state = 'ok'
    is_manual_test_active = False
    last_manual_test_time = "2015-08-11T14:00:43.000Z"
    urn_template = 'urn:upnp.org:smgt-surn:%s:onDemand.org:' + \
        'nest.com-smoke-co-alarm-meet-nest-protect:nest.org:%s'
    sensor_urns = [
        urn_template % ('85S6', 'alarm'),  # Co alam
        urn_template % ('85S8', 'alarm'),  # Smoke Alarm
        urn_template % ('51', 'status'),  # Battery
        urn_template % ('85', 'status'),  # Test
        urn_template % ('47', 'status')]  # ui color
    sensors = {urn_template % ('85S6', 'alarm'): [],
               urn_template % ('85S8', 'alarm'): [],
               urn_template % ('51', 'status'): [],
               urn_template % ('85', 'status'): [],
               urn_template % ('47', 'status'): []}
    parameters = {}

    def __init__(self, _id, data={}, nestapi=None):
        self._sensors = {}
        self.parameters = {}
        self.structure_id = ''
        self.where_id = ''
        self.device_id = _id
        super(SmokeAlarm, self).__init__(data, nestapi)
        self.generate_sensors()

    def generate_sensors(self):
        prefix = '[' + self.where_id + ']'
        for var in self.events:
            _id = '-'.join((self.device_id, var))
            tm = ''
            name = prefix + var
            if var == 'battery_health':
                paramtype = 'uda:string'
                access = 'ro'
                desc = 'Battery Health'
                urn = self.urn_template % ('51', 'status')
            elif var in ('is_manual_test_active', 'last_manual_test_time'):
                urn = self.urn_template % ('85', 'status')
                if var == 'is_manual_test_active':
                    paramtype = 'uda:bool'
                    access = 'ro'
                    desc = 'Test in progress'
                if var == 'last_manual_test_time':
                    paramtype = 'xsd:dateTime'
                    access = 'ro'
                    desc = 'Last test'
            elif var == 'co_alarm_state':
                urn = self.urn_template % ('85S6', 'alarm')
                paramtype = 'uda:string'
                access = 'ro'
                desc = 'Co Alarm'
            elif var == 'smoke_alarm_state':
                urn = self.urn_template % ('85S8', 'alarm')
                paramtype = 'uda:string'
                access = 'ro'
                desc = 'Smoke Alarm'
            elif var == 'ui_color_state':
                urn = self.urn_template % ('47', 'status')
                paramtype = 'uda:string'
                access = 'ro'
                desc = 'Ui color'
            s = Sensor(var, name, paramtype, _id, tm, access=access,
                       desc=desc, urn=urn)
            self.sensors[urn].append(s)
            self._sensors.update({var: s})

    def event(self, evt, var):
        print('Smoke_co_alarm event: %s: %s' % (var, evt))

#     def __getattribute__(self, attr):
#         if attr in self.upnp_attr:
#             return self.upnp_attr[attr]
#         else:
#             return super(SmokeAlarm, self).__getattribute__(attr)

if __name__ == '__main__':
    test = SmokeAlarm('toto')
    print(test.sensors.keys())
    print(test._sensors)
