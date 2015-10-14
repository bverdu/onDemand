# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''
from onDemand.plugins.nest.device import Device


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

    def __init__(self, _id, data={}, nestapi=None):
        self._sensors = {}
        self.parameters = {}
        self.structure_id = ''
        self.where_id = ''
        self.device_id = _id
        super(SmokeAlarm, self).__init__(data, nestapi.event)

    def event(self, evt, var):
        print('Smoke_co_alarm event: %s: %s' % (var, evt))
