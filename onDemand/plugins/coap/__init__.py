# encoding: utf-8
'''
Created on 17 févr. 2016

@author: Bertrand Verdu
'''
from lxml import etree as et
from onDemand.plugins import Client


class RootManager(Client):
    ''' Manage collection, groups and authorizations of Sensors'''

    def __init__(self):
        super(RootManager, self).__init__()
        self._events = ''
        self._num_collections = 0
        self.collections = {}
        self.groups = {}
        self._tree = {'UpnP':
                      {'SensorMgt':
                       {'SensorEvents': '',
                        'SensorCollectionsNumberOfEntries': 0,
                        'SensorCollections': {},
                        'SensorGroupSets': {}}}}

    def register(self, uid, sensors):
        if uid not in self.collections:
            self.collections.update({uid: SensorCollection(uid)})
        for sensor in sensors:
            try:
                self.collections[uid].update(sensor)
            except:
                continue
            self.update_tree(uid)

    def update_tree(self, col_id):
        if col_id in self._tree['UpnP']['SensorMgt']['SensorCollections']:
            self._tree['UpnP'
                       ]['SensorMgt'
                         ]['SensorCollections'
                           ][col_id].update(self.collections[col_id]._tree)
        else:
            self._tree['UpnP'
                       ]['SensorMgt'
                         ]['SensorCollections'
                           ].update({col_id: self.collections[col_id]._tree})


class SensorCollection(object):

    def __init__(self, uid):
        self.uid = uid
        self.coltype = ''
        self.friendlyName = 'New Collection'
        self.info = ''
        self.num_sensors = 0
        self.sensors = {}
        self._tree = {'CollectionID': uid,
                      'CollectionType': '',
                      'CollectionFriendlyName': self.friendlyName,
                      'CollectionInformation': '',
                      'CollectionUniqueIdentifier': uid,
                      'CollectionSpecific': [],
                      'SensorsNumberOfEntries': 0,
                      'Sensors': {}}

    def update(self, sensor):
        if sensor.col != self.uid:
            raise KeyError
        if sensor.uid not in self.sensors:
            self.sensors.update({sensor.uid: sensor})
        else:
            self.sensors[sensor.uid] = sensor
        self.update_tree(sensor)

    def update_tree(self, sensor):
        pass
