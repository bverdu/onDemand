# encoding: utf-8
'''
Created on 6 nov. 2016

@author: Bertrand Verdu
'''
from collections import OrderedDict
from twisted.internet import reactor
from twisted.logger import Logger
from onDemand.protocols.lirc import LircdFactory
from onDemand.plugins import Client

log = Logger()


class Lirc_factory(LircdFactory, Client):

    def __init__(self, delay, remotes=['devinput'],
                 direction='both', simul=False):
        if direction in ('emitter', 'both'):
            emitter = remotes[-1]
        else:
            emitter = None
        super(Lirc_factory, self).__init__(delay, simul, emitter)
        self.delay = delay
        self.initialized = False
        self.targets = OrderedDict()
        self.current_target = None
        self.tests = 0
        self.debounced = True
        self.manager = None
        if direction in ('receiver', 'both'):
            self.addCallback(self.got_action, remotes[0])
        log.info('Lirc Module Started')

    def check_modules(self):
        for module in self.manager.modules:
            if hasattr(module, 'remote_fct'):
                self.targets[module.parent.uuid] = module
                if self.current_target is None:
                    self.current_target = module.parent.uuid
        if self.current_target and self.current_target not in self.targets:
            self.next_target()
        reactor.callLater(90, self.check_modules)  # @UndefinedVariable

    def connect(self, manager):
        self.manager = manager
        if not self.initialized:
            reactor.callLater(20, self.check_modules)  # @UndefinedVariable
            self.initialized = True

    def next_target(self):
        if self.current_target is not None:
            if self.current_target in self.targets:
                ind = self.targets.keys().index(self.current_target) + 1
                if ind >= len(self.targets.keys()):
                    ind = 0
                self.current_target = self.targets.keys()[ind]
            elif len(self.targets.keys()) > 0:
                self.current_target = self.targets.keys()[0]
            else:
                self.current_target = None

    def got_action(self, action, internal=False):
        if not self.debounced and not internal:
            return
        if self.current_target is None:
            return
        if not internal:
            self.debounced = False
            reactor.callLater(self.delay, setattr,  # @UndefinedVariable
                              *(self, 'debounced', True,))
        if action == 'KEY_HOMEPAGE':
            self.next_target()
            return
        if self.targets[self.current_target].remote_fct['active']:
            self.tests = 0
            if action in self.targets[self.current_target].remote_fct:
                getattr(self.targets[self.current_target],
                        self.targets[
                            self.current_target].remote_fct[action])()
        else:
            self.tests += 1
            if self.tests < len(self.targets.keys()):
                self.next_target()
                self.got_action(action, True)
#                 reactor.callLater(0.2,  # @UndefinedVariable
#                                   self.got_action,
#                                   action)
            else:
                self.tests = 0


def get_Lirc(receivers=[{'name': 'default', 'addr': '/var/run/lirc/lircd'}],
             emitters=[{'name': 'default', 'addr': '/var/run/lirc/lircd'}],
             delay=0.5, remotes=['devinput'],
             direction='receiver', simul=False, net_type='lan'):

    f = Lirc_factory(delay, remotes, direction, simul)
    if direction in ['receiver', 'both']:
        for receiver in receivers:
            if receiver['name'] == remotes[0]:
                reactor.connectUNIX(receiver['addr'], f)  # @UndefinedVariable
    if direction in ['emitter', 'both']:
        for emitter in emitters:
            if emitter['name'] == remotes[-1]:
                reactor.connectUNIX(emitter['addr'], f)  # @UndefinedVariable

    return None, f

if __name__ == '__main__':

    class Manager(object):
        modules = None

    class Test(object):
        remote_fct = {'active': True, 'KEY_PLAYPAUSE': 'test'}

        def test(self):
            print('test!')

    class svc(object):
        uuid = '12345678'

    manager = Manager()
    test = Test()
    manager.modules = [test]
    test.parent = svc()
    e, f = get_Lirc()
    f.connect(manager)
    reactor.run()  # @UndefinedVariable
