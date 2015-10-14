# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''

from twisted.internet import defer
from twisted.logger import Logger
from onDemand.plugins.nest.device import Device

log = Logger()


class Structure(Device):

    dev_type = 'structure'
    actions = ('set_away', 'set_eta')
    events = ('away',)
    away = 'unknown'
    name = 'Home'
    structure_id = ''
    thermostats = []
    smoke_co_alarms = []
    eta = {}
    peak_start_time = ''
    peak_end_time = ''
    wheres = []
    country_code = 'US'
    postal_code = '94304'
    time_zone = 'America/Los_Angeles'

    def __init__(self, structure_id, data={}, nestapi=None):
        self.structure_id = structure_id
        self.device_id = ''
        self.where_id = ''
        super(Structure, self).__init__(data, nestapi.event)

    def set_away(self, value):
        if value not in ('home', 'away', 'auto-away', 'unknown'):
            return defer.fail(ValueError)
        return self.structure_id, {'away': value}

    def set_eta(self, value):
        if isinstance(value, dict):
            if len(dict) == 3:
                if 'trip_id' in dict:
                    if 'estimated_arrival_window_begin' in dict:
                        if 'estimated_arrival_window_end' in dict:
                            return self.structure_id, {'eta': dict}
        raise ValueError

    def event(self, evt, var):
        print('Structure event: %s: %s' % (var, evt))
