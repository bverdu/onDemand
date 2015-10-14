# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''
from collections import OrderedDict
from lxml import etree as et
from onDemand.plugins import Client
from onDemand.protocols.rest import Rest
from onDemand.utils import dictdiffupdate
from device import Device
from structure import Structure
from thermostat import Thermostat
from smoke_co_alarm import SmokeAlarm
from util import *

__all__ = ['Device', 'Thermostat', 'Nest', 'nest_conv',
           'Structure', 'SmokeAlarm']


class Nest(Rest, Client):

    def __init__(self, *args, **kwargs):
        kwargs.update({'event_handler': self.got_data})
        self._structures = OrderedDict()
        self._devices = OrderedDict()
        self.upnp_devices = []
#         self._sensors = []
        self._data = {}
        self.events = {}
        self.parent = None
        super(Nest, self).__init__(*args, **kwargs)

    def got_data(self, data):
        #  print('1')
        if isinstance(data, dict):
            evt = dictdiffupdate(self._data, data)
            #  print('3')
            if len(evt) > 0 and 'data' in evt:
                self.update(evt['data'])
            self._data = data
        else:
            print(data)

    def update(self, event):
        new = False
        if 'structures' in event:
            #  print('structure update')
            for id_, value in event['structures'].iteritems():
                #  print('%s -- %s' % (id_, value))
                if id_ in self._structures:
                    self._structures[id_].update(value)
                else:
                    new = True
                    self._structures.update(
                        {id_: Structure(id_, data=value, nestapi=self)})

        if 'devices' in event:
            #             print(event)
            for cat, device in event['devices'].iteritems():
                for k, v in device.iteritems():
                    k = bytes(k)
                    if k in self._devices:
                        self._devices[k].update(v)
                    else:
                        new = True
                        self._devices.update({k: get_device(cat)(
                            k, data=v, nestapi=self)})
        if new:
            self.upnp_devices = self._structures.values() +\
                self._devices.values()
            if self.parent:
                self.parent.update()

    def event(self, evt, var, obj, is_alarm=False):
        print('Nest Event from %s %s: %s: %s' %
              (obj.dev_type, obj.name, var, evt))

    '''
    Remote UPnP functions
    '''
    #  HVAC_UserOperatingMode

    def r_set_mode_target(self, mode):
        if mode in ('Off', 'HeatOn', 'CoolOn', 'AutoChangeOver'):
            for dev in self._devices.itervalues():
                if dev.dev_type == 'thermostat':
                    dev.r_set_mode_target(mode)
#                     self.devices(
#                         'thermostats/' + id_, hvac_mode=nest_conv(mode))
        else:
            return 700
        print('set global mode: %s' % mode)

    def r_get_mode_target(self):
        for dev in self._devices.itervalues():
            if dev.dev_type == 'thermostat':
                if dev.hvac_mode != 'off':
                    return upnp_conv(dev.hvac_mode)
        return 'Off'

    def r_get_mode_status(self):
        for dev in self._devices.itervalues():
            if dev.dev_type == 'thermostat':
                if dev.hvac_state != 'off':
                    return upnp_conv(dev.hvac_mode)
        return 'Off'


def get_device(cat):

    devices = {'thermostats': Thermostat,
               'smoke_co_alarms': SmokeAlarm}
    if cat in devices:
        return devices[cat]
    else:
        print('unknown device type: %s' % cat)


if __name__ == '__main__':

    from twisted.internet import reactor

    def test(napi):
        napi.r_set_mode_target('AutoChangeOver')
        print('global get mode result: %s' % napi.r_get_mode_target())
        for dev in napi._devices.values():
            if dev.dev_type == 'thermostat':
                print(dev.r_get_name())

    try:
        from onDemand.test_data import nest_token
    except:
        nest_token = 'PUT YOUR TOKEN HERE'
    napi = Nest(host='https://developer-api.nest.com', token=nest_token)
    reactor.callLater(5, test, napi)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
