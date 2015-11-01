# encoding: utf-8
'''
Created on 30 août 2015

@author: Bertrand Verdu
'''
from twisted.logger import Logger
from twisted.internet import serialport
from twisted.protocols.basic import LineOnlyReceiver


class serialProtocol(LineOnlyReceiver):

    def __init__(self):
        self.log = Logger()
        self.__callbacks = {}

    def connectionMade(self):
        self.log.debug('serial connected')

    def lineReceived(self, line):
        for name in self.__callbacks:
            self.__callbacks[name](line)

    def send(self, data):
        self.transport.write(data)

    def addCallback(self, name, func):
        self.__callbacks.update({name: func})

    def remCallback(self, name):
        if name in self.__callbacks:
            del self.__callbacks[name]
            
class serialEndPoint(serialport.SerialPort):
    
    def __init__(self, *args, **kwargs):
        super(serialEndPoint, self).__init__(*args, **kwargs)
        
    def connect(self, name, func):
        self.protocol.addCallback(name, func)
        
    def disconnect(self, name):
        self.protocol.remCallback(name)
    

if __name__ == '__main__':
    pass
