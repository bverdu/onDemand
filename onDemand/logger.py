'''
Created on 10 nov. 2014

@author: babe
'''
import sys
from twisted.python.log import FileLogObserver


class myObserver(object):
    __slots__ = ['error', 'info']

    def __init__(self):
        self.error = FileLogObserver(sys.stderr)
        self.info = FileLogObserver(sys.stdout)

    def standard(self, msg):
        try:
            level = msg['loglevel']
        except:
            if msg['isError']:
                self.error.emit(msg)
            else:
                return
        else:
            if level == 'debug':
                return
            else:
                self.info.emit(msg)

    def minimal(self, msg):
        if msg['isError']:
            self.error.emit(msg)

    def debug(self, msg):
        if msg['isError']:
            self.error.emit(msg)
        else:
            self.info.emit(msg)


def standard():
    return myObserver().standard


def minimal():
    return myObserver().minimal


def debug():
    return myObserver().debug
