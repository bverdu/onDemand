'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from twisted.internet import reactor
from upnpy_spyne.services import Service


class Time(Service):
    version = (1, 0)
    serviceType = "urn:av-openhome-org:service:Time:1"
    serviceId = "urn:av-openhome-org:serviceId:Time"
    serviceUrl = "Time"
    type = 'Time'
    upnp_type = 'oh'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(Time, self).__init__(
            self.type, self.serviceType,
            xml=xmlfile, client=client, appname=name)
        self.client = client
        self.client.oh_eventTIME = self.upnp_event
        self.trackcount = 0
        self.duration = 0
        self.seconds = 0
        self.polling = False
        self.stopped = False

    def upnp_event(self, evt, var):
        log.msg('time event: %s  ==> %s' % (var, evt))
        if var == 'trackcount':
            self.trackcount += 1
            self.seconds = 0
            if not self.polling:
                reactor.callLater(1,  # @UndefinedVariable
                                  self.event_time)
        else:
            setattr(self, var, evt)

    def event_time(self):
        nt = self.client.get_reltime('seconds')
        if self.seconds != nt:
            self.seconds = nt
        if nt == 0:
            if self.stopped:
                self.polling = False
                self.stopped = False
                return
            else:
                self.stopped = True
        else:
            self.stopped = False
        self.polling = True
        reactor.callLater(1,  # @UndefinedVariable
                          self.event_time)
