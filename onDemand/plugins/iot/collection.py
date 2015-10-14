# encoding: utf-8
'''
Created on 2 sept. 2015

@author: Bertrand Verdu
'''
from time import gmtime, strftime
from twisted.internet import defer, reactor
from onDemand.plugins.iot.sensor import Sensor


class Device(object):
    '''
    classdocs
    '''
    events = ()

    def __init__(self, data={}, event=None):
        #         #         self._sensors = {}
        #         self.parameters = {}
        #         self.device_id = ''
        #         self.structure_id = ''
        #         self.where_id = ''
        for evt in self.events:
            self._sensors.update(
                {evt: Sensor(
                    evt,
                    evt,
                    'uda:string',
                    '-'.join((self.device_id, evt)),
                    strftime('%Y-%m-%dT%H%M%SZ', gmtime()))})
        if event:
            self.event = event
        self.update(data)

    def get_value(self, attr, surn=None, param=None):
        if surn:
            urnid = self.sensors.keys()[int(surn)]
            if param:
                return self.sensors[urnid][int(param)].get_value(attr)
            elif attr == 'SensorURN':
                return urnid
            else:
                print('unknown parameter')
        try:
            return getattr(self, self.parameters[attr])
        except KeyError:
            print('unknown parameter')

    def generate_sensors(self):
        raise NotImplementedError

    def update(self, dic):
        for k, v in dic.iteritems():
            setattr(self, k, v)
            if k in self.events:
                self._sensors[k].value = v
                self._sensors[k].tm = strftime('%Y-%m-%dT%H%M%SZ', gmtime())
                check_event(v, k, self)

    def set(self, var, value, api):
        if var in self.actions:
            try:
                return api(getattr(self, 'set_' + var)(value))
            except ValueError:
                return defer.fail(ValueError)
        else:
            return defer.fail(ValueError)

    def get(self, var):
        if hasattr(self, var):
            return getattr(self, var)
        else:
            return defer.fail(ValueError)

    def event(self, evt, var):
        print('Device event: %s: %s' % (var, evt))


def check_event(v, k, obj):
    # Check that all data is consistent before sending event
    if obj.structure_id != '' and obj.device_id != '':
        obj.event(v, k, obj)
    else:
        if obj.dev_type == 'structure':
            obj.device_id = obj.structure_id
            obj.where_id = obj.structure_id
            if obj.structure_id != '':
                obj.event(v, k, obj)
        # @UndefinedVariable
        reactor.callLater(  # @UndefinedVariable
            1, check_event, *(v, k, obj))
