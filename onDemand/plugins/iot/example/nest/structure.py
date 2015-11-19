# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''

from twisted.internet import defer
from twisted.logger import Logger
from onDemand.plugins.iot.device import Device
from onDemand.plugins.iot.sensor import Sensor

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
    urn_template = 'urn:upnp.org:smgt-surn:' +\
        '%s:onDemand.org:nest.com-away:nest.org:%s'
    sensor_urns = [
        urn_template % ('85S3', 'status')]  # Thermostat
    sensors = {urn_template % ('85S3', 'status'): []}
    _sensors = {}
    parameters = {}
    parameters = {'CollectionFriendlyName': 'name'}

    def __init__(self, structure_id, data={}, nestapi=None):
        self.structure_id = structure_id
        self.device_id = ''
        self.where_id = ''
        super(Structure, self).__init__(data, nestapi)
        self.generate_sensors()

    def generate_sensors(self):
        s = Sensor('away',
                   '[' + self.structure_id + ']away',
                   'uda:string',
                   '-'.join((self.structure_id, 'away')),
                   '',
                   access='rw',
                   desc=self.name + 'Away Status',
                   urn=self.urn_template % ('85S3', 'status'))
        self.sensors[self.urn_template % ('85S3', 'status')].append(s)
        self._sensors.update({'away': s})

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
