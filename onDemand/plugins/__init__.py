# -*- coding: utf-8 -*-
'''
Created on 13 October 2014

@author: bverdu
'''
from collections import OrderedDict
from twisted.internet import reactor, task, defer

__version__ = '0.1a'


class Client(object):
    parent = None

    def __getattribute__(self, attr):
        method = super(Client, self).__getattribute__(attr)
        try:
            trigger = super(Client, self).__getattribute__('on_' + attr)
        except:
            return method
        else:
            return Scenario(method, trigger)
        if self.parent:
            self.parent.last = self


class Scenario(object):

    def __init__(self, method, callback):
        self.before = []
        self.after = []
        self.method = method
        for action in callback:
            if action.schedule < 0:
                self.before.append(
                    (action.schedule, action.callable, action.fct_args))
            else:
                self.after.append(
                    (action.schedule, action.callable, action.fct_args))

    def __call__(self, *args, **kwargs):
        t = 0
        time = 0
        deferreds = []
        for action in self.before:
            if t != 0:
                t = t + action[0]
                delay = t
            else:
                t = -action[0]
                time = t
                delay = 0
            deferreds.append(
                task.deferLater(reactor, delay, action[1], action[2]))
        f = task.deferLater(reactor, time, self.method, *args, **kwargs)
        for action in self.after:
            deferreds.append(task.deferLater(
                reactor,
                action[0] + time,
                action[1], action[2]))
        d = defer.gatherResults(deferreds)
        d.addCallback(lambda ignored: None)
        return f


class Trigger(object):
    schedule = 0
    callable = None
    fct_args = None

    def __init__(self, schedule, fct, fct_args):
        self.schedule = schedule
        self.callable = fct
        self.fct_args = fct_args


if __name__ == '__main__':
    def show(*args, **kwargs):
        print(args)

    class test(Client):

        def test_1(self, *args, **kwargs):
            print('test 1: %s %s' % (args, kwargs))

        on_test_1 = [
            Trigger(-1, show, 'one'),
            Trigger(0, show, 'two'),
            Trigger(2, show, 'three')]

        def test_2(self, *args, **kwargs):
            print('test 2: %s %s' % (args, kwargs))

    def testclient():
        client = test()
        client.test_1('coucou', tata=2)
        client.test_2('ttt', 'ddd')
    reactor.callWhenRunning(testclient)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
