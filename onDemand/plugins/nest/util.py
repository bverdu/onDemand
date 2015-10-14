# encoding: utf-8
'''
Created on 16 sept. 2015

@author: Bertrand Verdu
'''
CONV_DICT = {'Off': 'off', 'HeatOn': 'heat', 'CoolOn': 'cool',
             'AutoChangeOver': 'heat-cool'}

UPNP_DICT = {'off': 'Off', 'heat': 'HeatOn', 'cool': 'CoolOn',
             'heat-cool': 'AutoChangeOver', 'heating': 'HeatOn',
             'cooling': 'CoolOn'}


def nest_conv(upnp_value):
    return CONV_DICT[upnp_value]


def upnp_conv(nest_value):
    return UPNP_DICT[nest_value]
