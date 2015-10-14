# -*- coding: utf-8 -*-

'''
Created on 14 nov. 2014

@author: Bertrand Verdu
'''
import os
import time
import ConfigParser
from datetime import datetime, timedelta
from twisted.logger import Logger
from twisted.internet import task
from mimetypes import guess_type
from upnpy_spyne.utils import get_default_v4_address
import config

log = Logger()


def dictdiffupdate(old, new):
    diff = {}
    for k, v in new.iteritems():
        if k not in old:
            #  print('not: %s' % k)
            diff.update({k: v})
        elif isinstance(v, dict):
            #  print('dict')
            d = dictdiffupdate(old[k], v)
            if len(d) > 0:
                diff.update({k: d})
        else:
            #  print('basic')
            if v != old[k]:
                diff.update({k: v})
    return diff


def load_yaml(datapath, filename='map.conf', conf=config):

    import yaml

    config.datadir = datapath

    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    try:
        confmap = yaml.load(
            open(os.path.join(datapath, filename)), Loader=Loader)
    except:
        confmap = {}
        log.error('No suitable map file found at {path}',
                  path='/'.join((datapath, filename)))
    try:
        scenarios = yaml.load(
            open(os.path.join(datapath, 'scenarios.conf')), Loader=Loader)
    except:
        scenarios = {}
        log.error(
            'No suitable scenario file found at {path}',
            path='/'.join((datapath, 'scenarios.conf')))
    #     print(confmap)
    #     print(scenarios)
    for setting, value in confmap.iteritems():
        if setting == 'config':
            for k, v in value.iteritems():
                setattr(conf, k, v)
        else:
            setattr(conf, setting, value)


def save_yaml(datapath, filename='map.conf', conf=config):

    import yaml

    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper

    settings = ('auto', 'media_types', 'controller', 'lirc', 'first_start',
                'network', 'cloud_user', 'cloud_secret', 'shared_dirs')
    dic = {'config': {}}
    for attr, value in conf.__dict__.iteritems():
        if not attr.startswith('_'):
            if attr in settings:
                dic['config'].update({attr: value})
            else:
                dic.update({attr: value})
    yaml.dump(dic, open(os.path.join(datapath, filename), 'w+'), Dumper=Dumper)
    #     log.debug('{doc}', doc=yaml.dump(dic))


def load_config(datapath):
    parser = ConfigParser.ConfigParser(allow_no_value=True)
    successlist = parser.read(
        ['/etc/ondemand/pyrenderer.conf', os.path.join(datapath, 'config')])
#     print(successlist)
    if len(successlist) > 0:
        for section in parser.sections():
            for option in parser.options(section):
                if section == 'triggers':
                    for opt in parser.options(option):
                        if opt == 'functions':
                            f = []
                            fctlist = parser.get(option, opt).split()
                            for func in fctlist:
                                f.append(
                                    {'id': func,
                                     'name': parser.get(func, 'name'),
                                     'time': int(parser.get(func, 'time')),
                                     'args': tuple(
                                         parser.get(func, 'args').split()),
                                     'state': parser.get(func, 'state'),
                                     'qty': int(parser.get(func, 'qty'))})
                            if len(f) > 0:
                                config.triggers[option] = {'functions': f}
                elif section in ('lirc', 'mpd'):
                    setattr(config,
                            section + '_' + option,
                            parser.get(section, option))
#     print(config.lirc_emitter)
#     print(config.triggers)


def save_config():
    pass


def mpdtime_to_upnptime(mpdtime, playing='', reltime='0:00:00.000'):
    st = str(mpdtime)
    try:
        mpdtime = float(mpdtime)
        mpdtime = int(st.split('.')[0])
    except:
        return reltime
    if playing == 'PLAYING':
        # Dirty workaround, shame on me !
        hrs = mpdtime / 3600
        mn = (mpdtime - hrs * 3600) / 60
        sec = (mpdtime - mn * 60) + 2
        if len(st.split('.')) > 1:
            msec = '.' + '{:0<3}'.format(st.split('.')[1][:3])
        else:
            msec = '.000'
        return ':'.join(['{:0>2}'.format(str(hrs)),
                         '{:0>2}'.format(str(mn)),
                         '{:0>2}'.format(str(sec))]) + msec
    else:
        hrs = mpdtime / 3600
        mn = (mpdtime - hrs * 3600) / 60
        sec = (mpdtime - mn * 60)
        if len(st.split('.')) > 1:
            msec = '.' + '{:0<3}'.format(st.split('.')[1][:3])
        else:
            msec = '.000'
        return ':'.join(['{:0>2}'.format(str(hrs)),
                         '{:0>2}'.format(str(mn)),
                         '{:0>2}'.format(str(sec))]) + msec


def upnptime_to_mpdtime(upnptime):
    tim = upnptime.split('.')
    hmsm = tim[0].split(':')
#     if len(tim) > 1:
#         mpdtime = str((int(hmsm[0])*3600+int(hmsm[1])*60+int(hmsm[2])))\
#             + '.' + '{:0<3}'.format(tim[1][:3])
#     else:
#         mpdtime = str(int(hmsm[0])*3600+int(hmsm[1])*60+int(hmsm[2]))
    mpdtime = str(int(hmsm[0]) * 3600 + int(hmsm[1]) * 60 + int(hmsm[2]))
    return mpdtime


def mpristime_to_upnptime(mprtime, playing='', reltime='0:00:00.000'):
    try:
        mprtime = int(mprtime)
    except:
        return reltime
    tmst = (
        timedelta(hours=-1) + datetime.fromtimestamp(mprtime / 1000000.000000))
    if playing == 'Playing':
        # Dirty workaround, shame on me !
        return str(tmst.hour)\
            + ':'\
            + '{:0>2}'.format(str(tmst.minute))\
            + ':'\
            + '{:0>2}'.format(str(tmst.second + 2))\
            + '.'\
            + str(tmst.microsecond)
    else:
        return str(tmst.hour)\
            + ':'\
            + '{:0>2}'.format(str(tmst.minute))\
            + ':'\
            + '{:0>2}'.format(str(tmst.second))\
            + '.'\
            + str(tmst.microsecond)


def upnptime_to_mpristime(upnptime):
    tim = upnptime.split('.')
    hmsm = tim[0].split(':')
    if len(tim) > 1:
        mpristime = (int(hmsm[0]) * 3600 + int(hmsm[1])
                     * 60 + int(hmsm[2]))\
            * 1000000 + int('{:0<6}'.format(tim[1]))
    else:
        mpristime = (int(hmsm[0]) * 3600 + int(hmsm[1])
                     * 60 + int(hmsm[2]))\
            * 1000000
    return mpristime


def mpris_decode(dic):
    d = {}
    for k in dic.keys():
        key = k.split(':')
        if key[0] == 'xesam':
            if key[1] == 'contentCreated':
                d.update({'date': unicode(dic[k])})
                continue
            d.update({key[1]: unicode(dic[k])})
        elif k[0] == 'mpris':
            if k[1] == 'length':
                d.update({'duration': int(dic[k])})
            else:
                d.update({key[1]: unicode(dic[k])})
        else:
            d.update({k: unicode(dic[k])})
            log.warn('unknown tag: %s' % k)
    return d


def mpris_encode(dic):
    xesam = ['album', 'albumArtist', 'artist', 'asText',
             'url', 'title', 'contentCreated', 'genre']
    d = {}
    for k in dic.keys():
        if k == 'duration':
            d.update({'mpris:length': dic[k]})
        else:
            if k in xesam:
                d.update({'xesam:' + k: dic[k]})
    return d


def mpd_decode(dic):
    d = {}
    if isinstance(dic, list):
        log.error('bad info: {dic}', dic=dic)
        return d
    for k in dic.keys():
        if k == 'albumArtURI':
            d.update({k: dic[k]})
        if k == 'Time':
            hrs = int(dic[k]) / 3600
            mn = (int(dic[k]) - hrs * 3600) / 60
            sec = (int(dic[k]) - mn * 60)
            t = ':'.join(['{:0>2}'.format(str(hrs)),
                          '{:0>2}'.format(str(mn)),
                          '{:0>2}'.format(str(sec))])
            d.update({'duration': t})
        elif k in ('Title', 'Date', 'Genre', 'Artist',
                   'Album', 'Composer', 'Id', 'Pos'):
            d.update({k.lower(): dic[k]})  # .decode('utf-8')
        elif k in ('Url', 'file'):
            d.update({'url': dic[k]})   # .decode('utf-8')
            c = dic[k].split('.')[-1]
            if len(c) < 5:
                d.update({'codec': dic[k].split('.')[-1]})
            if dic[k].split('/')[0] in ('http:', 'http'):
                try:
                    d.update(
                        {'protocolInfo': dic[k].split(':')[0] +
                         '-get:*:' +
                         guess_type(dic[k])[0] +
                         ':*'})
                except:
                    pass
            else:
                try:
                    d.update(
                        {'protocolInfo': 'internal:' +
                         get_default_v4_address() +
                         ':' +
                         guess_type(dic[k])[0] +
                         ':local'})
                except:
                    pass
    if 'duration' not in d.keys():
        d.update({'duration': '00:00:00.000'})
    return d


def dbus_func_failed(err, func):
    try:
        msg = err.getErrorMessage()
    except AttributeError:
        msg = err.message
    log.error('dbus call function : %s failed: %s' % (func, msg))


def trigger(obj, func, name, *args):
    from twisted.internet import reactor

    def cleanState(res, obj, typ=2):
        log.debug('clean state: {obj}', obj=obj)
        if typ in (0, 2):
            try:
                config.state.remove(obj)
            except:
                log.debug('%s not in state' % obj)
        if typ in (1, 2):
            if obj in config.cancellable.keys():
                k = config.cancellable.pop(obj)
                for d in k:
                    log.debug('deferred %s not cancellable anymore' % d)
                del k
        log.debug('cancellable: %s' % config.cancellable)

    if name in config.triggers.keys():
        if name == config.last:
            return func(*(args))
        config.last = name
        log.debug('enter trigger %s ' % name)
        maxtime = 0.0
        for el in config.triggers[name]['functions']:
            fct = getattr(obj, el['name'])
            fargs = el['args']
            if el['state'] is not None:
                if el['state'] in config.state:
                    if '-' + el['state'] in config.cancellable.keys():
                        k = config.cancellable.pop('-' + el['state'])
                        for d in k:
                            log.debug('cancelling : %s' % d)
                            d.cancel()
                        del k
                    return func(*(args))
                elif el['state'][1:] in config.state:
                    if el['time'] > 0:
                        d = task.deferLater(reactor,
                                            el['time'],
                                            cleanState,
                                            *(None, el['state'][1:]))
                elif el['state'][0] != '-':
                    config.state.append(el['state'])
                    log.debug('append state: %s' % el['state'])
                else:
                    return func(*(args))
                if el['time'] < 0:
                    log.debug('eltime: %s' % el['time'])
                    if -el['time'] > maxtime:
                        maxtime = -el['time']
                    for i in range(el['qty']):
                        if el['state'] not in\
                                config.cancellable.keys():
                            config.cancellable[el['state']] = []
                        if i > 0 or el['qty'] == 1:
                            d = task.deferLater(
                                reactor,
                                float(i),
                                fct,
                                *(fargs))
                            config.cancellable[el['state']].append(d)
                            d.addBoth(cleanState,
                                      *(el['state'], 1))
                        else:
                            reactor.callLater(  # @UndefinedVariable
                                float(i),
                                fct,
                                *(fargs))
                else:
                    for i in range(el['qty']):
                        dd = task.deferLater(
                            reactor,
                            float(el['time']) + float(i),
                            fct,
                            *(fargs))
                        if el['state'] not in\
                                config.cancellable.keys():
                            config.cancellable[el['state']] = []
                        config.cancellable[el['state']].append(dd)
                        dd.addBoth(cleanState,
                                   *(el['state'], 1))
        log.debug('config state: %s' % config.state)
        log.debug('maxtime = %s' % maxtime)
        log.debug('cancellable list: %s' % config.cancellable)
        ddd = task.deferLater(
            reactor, maxtime, func, *(args))
        if maxtime > 0 and el['state'] is not None:
            config.cancellable[el['state']].append(ddd)
            ddd.addBoth(
                cleanState,
                *(el['state'], 1))
        return ddd
    else:
        return func(*(args))


class XmlListConfig(list):

    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if len(element) > 0:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                d = dict(element.items())
                d.update({'text': element.text})
                self.update({element.tag: d})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                self.update({element.tag: element.text})


class Timer(object):
    '''
    class doc
    '''

    def __init__(self, initial=0.000):
        self._time = time.time() - initial
        self.stopped = False
        self._current = self._time

    def set(self, initial=0.000):
        self._time = time.time() - initial
        self.stopped = False

    def stop(self):
        self.stopped = True
        self._current = time.time() - self._time

    def get(self):
        if self.stopped:
            t = self._current
        else:
            t = time.time() - self._time
        return t

    def resume(self):
        self.set(self._current)


class FakeSensor(object):
    ''' test temp sensor with initiated value '''

    def __init__(self, desc, unit, value):
        self.desc = desc
        self.unit = unit
        self.value = value

    def get(self):
        return self.desc, self.value, self.unit


if __name__ == '__main__':

    print(mpdtime_to_upnptime('812.12554'))
    print(upnptime_to_mpdtime('00:13:12.232544'))
