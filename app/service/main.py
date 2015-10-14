# encoding: utf-8
'''
Created on 22 sept. 2015

@author: Bertrand Verdu
'''
import os
import sys
import inspect
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.application.internet import StreamServerEndpointService
from plyer import notification
from kivy.utils import platform
from kivy.app import App


if platform == 'android':
    pkg = os.path.realpath(
        os.path.abspath(os.path.split(__file__)[0]))
    print(pkg)
    parent = os.path.dirname(pkg)
    print(parent)
    if parent not in sys.path:
        print(sys.path)
        sys.path.insert(0, parent)

print(sys.path)

from upnpy_spyne.controller import ControllerAmp


class ServiceFactory(Factory):
    protocol = ControllerAmp

    def __init__(self):
        self.controller = None
        self.protocol.parent = self
        self.wait = 0

    def notified(self):
        self.wait -= 1

    def notify(self, title, message):
        if self.wait > 0:
            reactor.callLater(self.wait + 1,  # @UndefinedVariable
                              self.notify,
                              *(title, message))
            return
        else:
            self.wait += 1
            reactor.callLater(1, self.notified)  # @UndefinedVariable
        if platform == 'win':
            icon = 'logo.ico'
            timeout = 10
        else:
            icon = 'logo.png'
            timeout = 10000
        kwargs = {'app_icon': os.path.join(
            os.path.dirname(os.path.realpath(__file__)), icon),
            'app_name': 'onDemand',
            'title': title,
            'message': message,
            'timeout': timeout}
        notification.notify(**kwargs)

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    endpoint = TCP4ServerEndpoint(reactor, 4343)
    factory = ServiceFactory()
    service = StreamServerEndpointService(endpoint, factory)
    service.startService()
    reactor.run()  # @UndefinedVariable
