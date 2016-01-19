#!/usr/bin/python2.7
# encoding: utf-8
'''
onDemand -- shortdesc

onDemand is a description

It defines classes_and_methods

@author:     user_name

@copyright:  2015 organization_name. All rights reserved.

@license:    license

@contact:    user_email
@deffield    updated: Updated
'''
import os
import sys
from twisted.scripts.twistd import run

try:
    import _preamble
    y = _preamble
    del y
except ImportError:
    sys.exc_clear()

sys.path.insert(0, os.path.abspath(os.getcwd()))  # @UndefinedVariable
try:
    i = sys.argv[1:].index('--logger')
    tmp = sys.argv[1:]
    l = tmp.pop(i)
    d = tmp.pop(i)
    i = tmp.index('-r')
    r = tmp.pop(i)
    reactor = tmp.pop(i)
#     sys.argv[1:] = [r, reactor,
#                     '--nodaemon',
#                     '--pidfile',
#                     ' ',
#                     '--originalname',
#                     '-n',
#                     'onDemand']+tmp
    sys.argv[1:] = [l, d, r, reactor,
                    '--nodaemon',
                    '--pidfile=',
                    '--originalname',
                    '-n',
                    'onDemand'] + tmp
except:
    #     sys.argv[1:] = ['-r', 'epoll', '--originalname',
    #                     '-n', 'onDemand'] + sys.argv[1:]
    sys.argv[1:] = ['-r', 'epoll', '--originalname',
                    '--logger', 'onDemand.logger.info',
                    '-n', 'onDemand'] + sys.argv[1:]

# import tracemalloc
# tracemalloc.start()
# from twisted.scripts.twistd import run
run()
