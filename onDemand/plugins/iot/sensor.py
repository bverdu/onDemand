# encoding: utf-8
'''
Created on 4 sept. 2015

@author: Bertrand Verdu
'''


class Sensor(object):
    '''
    classdocs
    '''
    parameters = {'ClientID': 'id_', 'ReceiveTimestamp': 'tm', 'Name': 'name',
                  'Type': 'type_', 'Encoding': 'encoding',
                  'Description': 'desc'}

    def __init__(self, var, name, type_, id_, tm, access='ro',
                 encoding='ascii', desc='', value=None, urn=''):
        '''
        Constructor
        '''
        self.id_ = id_
        self.tm = tm
        self.realname = var
        self.name = name
        self.type_ = type_
        self.encoding = encoding
        self.desc = desc
        self.urn = urn
        self.value = value

    def get_value(self, attr):
        try:
            return getattr(self, self.parameters[attr])
        except KeyError:
            print('unknown parameter')
