# encoding: utf-8
'''
Created on 18 août 2015

@author: Bertrand Verdu
'''
from collections import OrderedDict
from lxml import etree as et
from onDemand.plugins import Client
from onDemand.protocols.rest import Rest
from onDemand.plugins.nest.structure import Structure
from onDemand.plugins.nest.thermostat import Thermostat
from onDemand.plugins.nest.smoke_co_alarm import SmokeAlarm

datamodel = '''<?xml version="1.0" encoding="UTF-8"?>
<cms:SupportedDataModels xmlns:cms="urn:schemas-upnp-org:dm:cms" ''' +\
    '''xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ''' +\
    '''xsi:schemaLocation="urn: schemas-upnp-org:dm:cms ''' +\
    '''http://www.upnp.org/schemas/dm/cms.xsd">
<SubTree>
<URI>
urn:upnp-org:smgt:1
</URI>
<Location>
/UPnP/SensorMgt
</Location>
<URL>
http://www.upnp.org/specs/smgt/UPnP-smgt-SensorDataModel-v1-Service.pdf
</URL>
<Description>
{description}
</Description>
</SubTree>
</SupportedDataModels>'''

xmllist = '''<?xml version="1.0" encoding="UTF-8"?>
<cms:{pt}List xmlns:cms="urn: schemas-upnp-org:dm:cms" ''' +\
    '''xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ''' +\
    '''xsi:schemaLocation="urn: schemas-upnp-org:dm:cms ''' +\
    '''http://www.upnp.org/schemas/dm/cms.xsd">
<!-- The document contains a list of zero or more elements. -->
{val}
</cms:{pt}List>'''

sensor_events = '''<?xml version="1.0" encoding="utf-8"?>
<SensorEvents xmlns="urn:schemas-upnp-org:smgt:sdmevent" ''' +\
    '''xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ''' +\
    '''xsi:schemaLocation="urn:schemas-upnp-org:smgt:sdmevent ''' +\
    '''http://www.upnp.org/schemas/smgt/sdmevent-v1.xsd">
{sensor_event}
</SensorEvents>'''

sensor_event = '''<sensorevent collectionID="{col_id}" ''' +\
    '''sensorID="{sensor_id}" event="{name}"/>'''


xmlpath = '<{pt}Path>{val}</{pt}Path>'

parameter = '''<Parameter>
<ParameterPath>{resp[0]}</ParameterPath>
<Value>{resp[1]}</Value>
</Parameter>'''


class Iot(Client):

    col_parameters = ('CollectionID', 'CollectionType',
                      'CollectionFriendlyName', 'CollectionInformation',
                      'CollectionUniqueIdentifier', 'CollectionSpecific/')
    sensors_parameters = ('SensorID', 'SensorType', 'SensorEventEnable',
                          'SensorSpecific/', 'SensorURNsNumberOfEntries ',
                          'SensorURNs')
    data_items_parameters = ('ClientID',
                             'ReceiveTimestamp',
                             'Name', 'Type', 'Encoding', 'Description')
    path = '/UPNP/SensorMgt'
    pathlevels = {}
    pathlevels.update({1: ['/UPNP/SensorMgt/SensorEvents',
                           '/UPNP/SensorMgt/SensorCollectionsNumberOfEntries',
                           '/UPNP/SensorMgt/SensorCollections/#/']})
    pathlevels.update(
        {2: pathlevels[1] +
         ['/UPNP/SensorMgt/SensorCollections/SensorsNumberOfEntries']})
    pathlevels.update(
        {3: [p for p in pathlevels[2] if
             p != '/UPNP/SensorMgt/SensorCollections/#/'] +
            [''.join(('/UPNP/SensorMgt/SensorCollections/#/', p))
             for p in col_parameters] +
            ['/UPnP/SensorMgt/SensorCollections/#/Sensors/#/']})
    pathlevels.update({4: pathlevels[3]})
    pathlevels.update(
        {5: [p for p in pathlevels[4] if
             p != '/UPnP/SensorMgt/SensorCollections/#/Sensors/#/'] +
            [''.join(('/UPnP/SensorMgt/SensorCollections/#/Sensors/#/', p))
             for p in sensors_parameters] +
            ['/UPnP/SensorMgt/SensorCollections/#/Sensors/#/SensorURNs/#/']})
    pathlevels.update(
        {6: pathlevels[5] +
         ['/UPnP/SensorMgt/SensorCollections/#/Sensors/#/SensorURNs/' +
          'DataItemsNumberOfEntries']})
    pathlevels.update(
        {7: [p for p in pathlevels[6] if
             p != '/UPnP/SensorMgt/SensorCollections/#/Sensors/#/'] +
            ['/UPnP/SensorMgt/SensorCollections/#/Sensors/#/SensorURNs'] +
            ['/UPnP/SensorMgt/SensorCollections/#/Sensors/#/SensorURNs/' +
             'DataItems/#/']})
    pathlevels.update({8: pathlevels[7]})
    pathlevels.update(
        {9: [p for p in pathlevels[8] if
             p != '/UPnP/SensorMgt/SensorCollections/#/Sensors/#/SensorURNs/' +
             'DataItems/#/'] +
            [''.join(('/UPnP/SensorMgt/SensorCollections/#/Sensors/#/' +
                      'SensorURNs/DataItems/#/', p))
             for p in data_items_parameters]})
    pathlevels.update({0: pathlevels[9]})

    def __init__(self, *args, **kwargs):
        #         kwargs.update({'event_handler': self.got_data})
        #         self._sensors = []
        self._data = {}
        self.events = {}
        if 'sensors' in kwargs:
            self.sensors = kwargs['sensors']
        else:
            self.sensors = []
#         super(Iot, self).__init__(*args, **kwargs)

    def struct_to_sensorStruct(self, dics=[]):
        sensors = {}
        cols = 0
        i = 0
        for dic in dics:
            cols += len(dic)
            s = 0
            for k, v in dic.iteritems():
                sensors.update({'SensorEvents': '',
                                'SensorNumberOfEntries': len(dic),
                                'SensorCollections': {}})
        sStruct = {'UPnP/SensorMgt': {'SensorEvents': '',
                                'SensorCollectionsNumberOfEntries': len(dics),
                                'SensorCollections': sensors}}
        
        

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

    def parse_tree(self, starting_node, depth):
        if depth == 0:
            ad = 8
        else:
            ad = len(starting_node.split(self.path)[1].split('/')) - 1 + depth
        if ad > 1:
            r = [xmlpath.format(pt='Instance', val='/'.join((
                self.path,
                'SensorCollections',
                str(self._structures.keys().index(p)), '')))
                for p in self._structures]
        if ad > 3:
            s = []
            u = []
            for key, structure in self._structures.iteritems():
                i = 0
                id_ = str(self._structures.keys().index(key))
                s.append('/'.join((self.path,
                                   'SensorCollections',
                                   id_,
                                   'Sensors',
                                   str(i),
                                   '')))
                u.append('/'.join((self.path,
                                   'SensorCollections',
                                   id_,
                                   'Sensors',
                                   str(i),
                                   'SensorsURNs',
                                   '0',
                                   '')))
                for dev_id in structure.thermostats:
                    i += 1
                    s.append('/'.join((
                        self.path, 'SensorCollections', id_, 'Sensors', str(i),
                        '')))
                    device = self._devices[dev_id]
                    for j in range(len(device.sensors.keys())):
                        u.append('/'.join((
                            self.path, 'SensorCollections', id_, 'Sensors',
                            str(i), 'SensorsURNs', str(j), '')))
                for dev_id in structure.smoke_co_alarms:
                    i += 1
                    s.append('/'.join((
                        self.path, 'SensorCollections', id_, 'Sensors', str(i),
                        '')))
                    device = self._devices[dev_id]
                    for j in range(len(device.sensors.keys())):
                        u.append('/'.join((
                            self.path, 'SensorCollections', id_, 'Sensors',
                            str(i), 'SensorsURNs', str(j), '')))
            r += [xmlpath.format(pt='Instance', val=p) for p in s]
        if ad > 5:
            r += [xmlpath.format(pt='Instance', val=p) for p in u]
        if ad > 7:
            pp = []
            for p in u:
                for i in range(6):
                    pp.append(''.join((p, 'DataItems/', str(i) + '/')))
            r += [xmlpath.format(pt='Instance', val=p) for p in pp]

        return xmllist.format(pt='InstancePath', val='\n'.join(r))

    def update(self, event):
        #  print('4')
        if 'structures' in event:
            #  print('structure update')
            for id_, value in event['structures'].iteritems():
                #  print('%s -- %s' % (id_, value))
                if id_ in self._structures:
                    self._structures[id_].update(value)
                else:
                    self._structures.update(
                        {id_: Structure(id_, data=value, event=self.event)})

        if 'devices' in event:
            #             print(event)
            for cat, device in event['devices'].iteritems():
                for k, v in device.iteritems():
                    if k in self._devices:
                        self._devices[k].update(v)
                    else:
                        self._devices.update({k: get_device(cat)(
                            k, data=v, event=self.event)})
        #  print('updated')

    def event(self, evt, var, obj, is_alarm=False):
        print('Nest Event from %s %s: %s: %s' %
              (obj.dev_type, obj.name, var, evt))
        if obj.device_id not in self.events:
            self.events.update({obj.device_id: obj.structure_id})
#         if obj.structure_id != '':
#             self.events.append(
#                 (obj.structure_id,
#                  '[' + obj.where_id + ']' + var,
#                  'SOAPDataAvailable'))

    '''
    Remote UPnP functions
    '''

    '''
    Configuration Management Service functions
    '''

    def r_get_supported_dataModels(self):
        return datamodel

    def r_get_supported_parameters(self, starting_node, depth):
        ad = len(starting_node.split(self.path)[1].split('/')) - 1 + depth
        return xmllist.format(
            pt='StructurePath',
            val='\n'.join([xmlpath.format(
                pt='Structure',
                val=p) for p in self.pathlevels[ad]]))

    def r_get_instances(self, starting_node, depth):
        return self.parse_tree(starting_node, depth)

    def r_get_values(self, pathlist_):
        try:
            l = et.XML(pathlist_)
        except:
            return 702
        pathlist = []
        for element in l.iter():
            if element.tag == 'ContentPath':
                pathlist.append(element.text)
        res = []
        for path in pathlist:
            items = path.split('/')
            pl = len(items)
            if items[-1] == '':
                print('partial')
            else:
                if pl not in (4, 5, 6, 8, 9, 10, 12):
                    return 703
                else:
                    di = items[-1]
                    if pl == 4:
                        if di == 'SensorEvents':
                            res.append(
                                (path,
                                 sensor_events.format(sensor_event='\n'.join(
                                     [sensor_event.format(
                                         col_id=v,
                                         sensor_id=k,
                                         name='SOAPDataAvailable')
                                      for k, v in self.events.items()]))))
                            self.events = {}
                        elif di == '/SensorCollectionsNumberOfEntries':
                            res.append((path, len(self._structures)))
                        else:
                            return 703
                    elif pl == 5:
                        if di == 'SensorsNumberOfEntries':
                            res.append((path, len(self._devices) +
                                        len(self._structures)))
                    elif pl == 6:
                        res.append((path, self._structures[
                            self._structures.keys()[
                                int(items[4])]].get_value(di)))
                    elif pl in (8, 9):
                        if items[6] == 0:
                            res.append((path, self._structures[
                                self._structures.keys()[
                                    int(items[6])]].get_value(di)))
                        else:
                            res.append((path, self._devices[
                                self._devices.keys()[
                                    int(items[6])]].get_value(di)))
                    elif pl == 10:
                        if items[6] == 0:
                            res.append((path, self._structures[
                                self._structures.keys()[
                                    int(items[6])]].get_value(
                                di, surn=items[8])))
                        else:
                            res.append((path, self._devices[
                                self._devices.keys()[
                                    int(items[6])]].get_value(
                                di, surn=items[8])))
                    elif pl == 12:
                        if items[6] == 0:
                            res.append((path, self._structures[
                                self._structures.keys()[
                                    int(items[6])]].get_value(
                                di, surn=items[8],
                                param=items[10])))
                        else:
                            res.append((path, self._devices[
                                self._devices.keys()[
                                    int(items[6])]].get_value(
                                di, surn=items[8],
                                param=items[10])))
#                 res.append((items[-1], pl))
        return xmllist.format(
            pt='ParameterValue',
            val='\n'.join([parameter.format(resp=r) for r in res]))

    def r_set_values(self):
        pass

    def r_get_attributes(self):
        pass

    def r_get_configuration_update(self):
        pass

    def r_get_current_configuration_version(self):
        pass

    def r_get_supported_data_models_update(self):
        pass

    def r_get_supported_parameters_update(self):
        pass

    def r_get_alarms_enabled(self):
        pass


class NodeCollection(object):

    def __init__(self, struct, devicelist):
        self.collection = struct
        self.devices = devicelist

    def get(self, var, path):
        print('get')


def get_device(cat):

    devices = {'thermostats': Thermostat,
               'smoke_co_alarms': SmokeAlarm}
    if cat in devices:
        return devices[cat]
    else:
        print('unknown device type: %s' % cat)


def dictdiffupdate(old, new):
    #  print('2')
    #  print(new.keys())
    diff = {}
    for k, v in new.iteritems():
        if k not in old:
            #  print('not: %s' % k)
            diff.update({k: v})
        elif isinstance(v, dict):
            #  print('dict')
            d = dictdiffupdate(old[k], v)
            if len(d) > 0:
                diff.update({k: d})
        else:
            #  print('basic')
            if v != old[k]:
                diff.update({k: v})
    return diff

if __name__ == '__main__':

    from twisted.internet import reactor
    d = {
        'path': '/',
        'data':
        {
            'structures': {
                'fwo7ooZml1BE5o_zUEVOOAmD6p4_K' +
                'Kcf5h-hyF9S9gGD8gz61GVajg':
                {
                    'name': 'Chave',
                    'away': 'home',
                    'time_zone': 'Europe/Paris',
                    'smoke_co_alarms': ['kpv19WDjBwPi-fbhzZ5CpbuE3_EunExt'],
                    'postal_code': '13005',
                    'thermostats': ['o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
                                    'o4WARbb6TBZmNT32aMeJ8ruE3_EunExt'],
                    'country_code': 'FR',
                    'structure_id': 'fwo7ooZml1BE5o_zUEVOOAmD6p4_KKcf5h-hy' +
                    'F9S9gGD8gz61GVajg',
                    'wheres':
                    {
                        'UDex0umsLcPn9ADdpOYzBnIjWcVYlkRcBasUHCKLxFAZnU3k8GF90g':
                        {
                            'where_id': 'UDex0umsLcPn9ADdpOYzBnIjWcVYlkRcBasUHC' +
                            'KLxFAZnU3k8GF90g',
                            'name': 'Entryway'}}}},
            'devices': {
                'thermostats': {
                    'o4WARbb6TBa0Z81uC9faoLuE3_EunExt':
                    {
                        'locale': 'fr-CA',
                        'hvac_state': 'cooling',
                        'away_temperature_high_c': 24.0,
                        'humidity': 50,
                        'away_temperature_high_f': 76,
                        'away_temperature_low_f': 55,
                        'temperature_scale': 'C',
                        'away_temperature_low_c': 12.5,
                        'can_heat': True,
                        'where_id': 'UDex0umsLcPn9ADdpOYzBnIjWcVYlkR' +
                        'cBasUHCKLxFAg782GQma1gw',
                        'software_version': '4.1',
                        'ambient_temperature_c': 27.0,
                        'has_fan': True,
                        'ambient_temperature_f': 81,
                        'is_online': True,
                        'structure_id': 'fwo7ooZml1BE5o_zUEVOOAmD6p4' +
                        '_KKcf5h-hyF9S9gGD8gz61GVajg',
                        'device_id': 'o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
                        'target_temperature_c': 21.0,
                        'name': 'Living Room (5DC5)',
                        'can_cool': True,
                        'target_temperature_f': 70,
                        'fan_timer_active': False,
                        'is_using_emergency_heat': False,
                        'target_temperature_low_c': 19.0,
                        'target_temperature_low_f': 66,
                        'hvac_mode': 'heat',
                        'target_temperature_high_f': 79,
                        'name_long': 'Living Room Thermostat (5DC5)',
                        'target_temperature_high_c': 26.0,
                        'has_leaf': True}}}}}

    dict_two = {
        'path': '/',
        'data': {
                'structures': {
                    'fwo7ooZml1BE5o_zUEVOOAmD6p4_K' +
                    'Kcf5h-hyF9S9gGD8gz61GVajg':
                    {
                        'name': 'Chave',
                        'away': 'home',
                        'time_zone': 'Europe/Paris',
                        'smoke_co_alarms': [
                            'kpv19WDjBwPi-fbhzZ5CpbuE3_EunExt'
                        ],
                        'postal_code': '13006',
                        'thermostats': ['o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
                                        'o4WARbb6TBZmNT32aMeJ8ruE3_EunExt'],
                        'country_code': 'FR',
                        'structure_id': 'fwo7ooZml1BE5o_zUEVOOAmD6p4_KKcf5h' +
                        '-hyF9S9gGD8gz61GVajg',
                        'wheres':
                        {
                            'UDex0umsLcPn9ADdpOYzBnIjWcVYlkRcBasUHCKLxFAZnU' +
                            '3k8GF90g': {
                                'where_id': 'UDex0umsLcPn9ADdpOYzBnIjWcVYlkRcB' +
                                'asUHCKLxFAZnU3k8GF90g',
                                'name': 'Entryway'}}}},
                'devices': {
                    'thermostats': {
                        'o4WARbb6TBa0Z81uC9faoLuE3_EunExt':
                        {
                            'locale': 'fr-CA',
                            'hvac_state': 'cooling',
                            'away_temperature_high_c': 24.0,
                            'humidity': 50,
                            'away_temperature_high_f': 76,
                            'away_temperature_low_f': 55,
                            'temperature_scale': 'C',
                            'away_temperature_low_c': 12.5,
                            'can_heat': True,
                            'where_id': 'UDex0umsLcPn9ADdpOYzBnIjWcVYlkRcBa' +
                            'sUHCKLxFAg782GQma1gw',
                            'software_version': '4.1',
                            'ambient_temperature_c': 29.0,
                            'has_fan': True,
                            'ambient_temperature_f': 81,
                            'is_online': True,
                            'structure_id': 'fwo7ooZml1BE5o_zUEVOOAmD6p4_K' +
                            'Kcf5h-hyF9S9gGD8gz61GVajg',
                            'device_id': 'o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
                            'target_temperature_c': 21.0,
                            'name': 'Living Room (5DC5)',
                            'can_cool': True,
                            'target_temperature_f': 70,
                            'fan_timer_active': False,
                            'is_using_emergency_heat': False,
                            'target_temperature_low_c': 19.0,
                            'target_temperature_low_f': 66,
                            'hvac_mode': 'heat',
                            'target_temperature_high_f': 79,
                            'name_long': 'Living Room Thermostat (5DC5)',
                            'target_temperature_high_c': 26.0,
                            'has_leaf': True}}}}}

#     print(dictdiffupdate(d, dict_two))
    def test(napi):
        #         print(napi.get_paths('/UPNP/SensorMgt', 1)
        #         print(napi.get_paths('/UPNP/SensorMgt', 2))
        #         print(napi.get_paths('/UPNP/SensorMgt', 3))
        #         print(napi.get_paths('/UPNP/SensorMgt', 4))
        print(napi.r_get_supported_parameters('/UPNP/SensorMgt', 0))
        print(napi.r_get_instances('/UPNP/SensorMgt', 0))
#         print(napi.r_get_values([
#             '/UPNP/SensorMgt/',
#             '/UPNP/SensorMgt/SensorCollections/0/Sensors/2/SensorsURNs' +
#             '/0/DataItems/4/Name',
#             '/UPNP/SensorMgt/SensorCollections/1/CollectionFriendlyName',
#             '/UPNP/SensorMgt/SensorCollections/0/']))
        print(napi.r_get_values('''<?xml version="1.0" encoding="UTF-8"?>
<cms:ContentPathList xmlns:cms="urn:schemas-upnp-org:dm:cms"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:schemaLocation="urn:schemas-upnp-org:dm:cms
http://www.upnp.org/schemas/dm/cms.xsd">
<ContentPath>/UPNP/SensorMgt/</ContentPath>
<ContentPath>/UPNP/SensorMgt/SensorEvents</ContentPath>
<ContentPath>/UPNP/SensorMgt/SensorCollections/0/Sensors/2/SensorsURNs/0/DataItems/4/Name</ContentPath>
<ContentPath>/UPNP/SensorMgt/SensorCollections/1/CollectionFriendlyName</ContentPath>
<ContentPath>/UPNP/SensorMgt/SensorCollections/0/</ContentPath>
</cms:ContentPathList>'''))

    try:
        from onDemand.test_data import nest_token
    except:
        nest_token = 'PUT YOUR TOKEN HERE'
    napi = Iot(host='https://developer-api.nest.com', token=nest_token)
    reactor.callLater(5, test, napi)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
