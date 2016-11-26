# encoding: utf-8
'''
Created on 24 oct. 2016

@author: Bertrand Verdu
'''


# only for tests
# from twisted.internet import gireactor
# gireactor.install()
# /only for tests
import importlib
from twisted.logger import Logger
from onDemand.protocols.dbus import DbusConnection


log = Logger(namespace='onDemand.plugin.mpris')


def get_Mpris(program='vlc', net_type='lan', args=None, **kwargs):

    try:
        m = getattr(importlib.import_module(
            'onDemand.plugins.mpris.' + program), 'Mpris_factory')
    except ImportError:
        from default import Mpris_factory as m
    f = m(program=program, net_type=net_type, args=args, **kwargs)
    edp = DbusConnection()
    if program not in 'omxplayer':
        edp.connect(f)
    else:
        f.con = edp

    return edp, f


if __name__ == '__main__':

    import sys
    from twisted.internet import reactor
    from twisted.logger import globalLogBeginner, textFileLogObserver
    from onDemand.utils import show

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

#     pl = get_Mpris('vlc')[1]
    pl = get_Mpris('omxplayer',
                   args='-b --aspect-mode letterbox -o alsa',
                   cmd='/usr/bin/omxplayer')[1]

    def test_time():
        show(" ".join([str(i) for i in pl.r_time()]), "time")

    def test():
        pl.r_set_avtransport_uri(
            0, 'http://192.168.0.10:8200/MediaItems/111865.mkv', '')
        reactor.callLater(10, test_time)  # @UndefinedVariable
        reactor.callLater(15, pl.r_next)  # @UndefinedVariable
    log.debug('starting')
#     reactor.callWhenRunning(init)  # @UndefinedVariable
    reactor.callLater(5, test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
