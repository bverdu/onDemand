# encoding: utf-8
'''
Created on 2 sept. 2015

@author: Bertrand Verdu
'''
from twisted.internet import defer, reactor


class Device(object):
    '''
    classdocs
    '''
    events = ()

    def __init__(self, data={}, event=None):
        self.parameters = {}
        self.device_id = ''
        self.structure_id = ''
        self.where_id = ''
        if event:
            self.event = event
        self.update(data)

    def update(self, dic):
        for k, v in dic.iteritems():
            setattr(self, k, v)
            if k in self.events:
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
