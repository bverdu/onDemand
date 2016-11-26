# encoding: utf-8
'''
Created on 6 nov. 2016

@author: Bertrand Verdu
'''
import os
from twisted.logger import Logger
from twisted.internet import reactor, endpoints
from twisted.application.internet import StreamServerEndpointService
from twisted.web import server, static
from twisted.web.resource import Resource
from twisted.web.template import Element, renderer, XMLFile, flattenString
from twisted.python.filepath import FilePath
from onDemand import config

__updated__ = ""

log = Logger()


class Local_server(StreamServerEndpointService):
    '''
    local http server
    '''

    def __init__(self, res):
        '''
        Initialization of web server
        '''
        self.resource = res
#         self.resource = static.File(res.datadir + '/web')

        edp = endpoints.serverFromString(reactor, b'tcp:4242')
        StreamServerEndpointService.__init__(
            self, edp, server.Site(self.resource))
        self._choosenPort = None

    def privilegedStartService(self):
        r = super(Local_server, self).privilegedStartService()
        self._waitingForPort.addCallback(self.portCatcher)
        return r

    def portCatcher(self, port):
        self._choosenPort = port.getHost().port
#         log.error('Port: {porc}', porc=self._choosenPort)
        return port

    def getPort(self):
        return self._choosenPort

    def startService(self):
        '''
        '''
        super(Local_server, self).startService()
#         log.error('start: {porc}', porc=self._choosenPort)
        self.weburl = "http://%s:" + str(self.getPort())
        log.info("web url = %s" % self.weburl % '127.0.0.1')


class SystemResource(Resource):
    isLeaf = False

    def __init__(self):
        Resource.__init__(self)
        self.static_files = static.File(
            os.path.join(config.datadir, 'web', 'dist'))
        self.putChild(
            b'dist', self.static_files)
        self.templates = os.path.join(
            config.datadir, 'web', 'templates', 'index.xml')
        self.devices = {}
        self.places = {}
        self.groups = {}
        self.loaded = False

    def load_config(self):

        for _id in config.collections:
            self.places[_id] = getattr(config, _id)
        for _id in self.places.keys():
            if 'devices' in getattr(config, _id):
                self.groups[_id] = getattr(config, _id)
            else:
                self.devices[_id] = getattr(config, _id)
        for _id, device in self.groups.iteritems():
            self.devices[_id] = device
        self.loaded = True

    def stop(self):
        if not self.running:
            return
        log.info("Stopping local web Server")
        self.site_port.stopListening()
        self.running = False

    def render_GET(self, request):
        if not self.loaded:
            self.load_config()
        d = flattenString(None, MainPage(self, self.templates))
        d.addCallback(
            lambda page: request.write(''.join(('<!DOCTYPE html>\n', page,))))
        d.addCallback(lambda ignored: request.finish())
        return server.NOT_DONE_YET

    def render_POST(self, request):
        log.debug("Post: %s" % "; ".join(request.args))
        for k, v in request.args.items():
            log.debug("%s: %s" % (k, v))

#         save_yaml(config.datadir, 'test.yaml')
        return self.render_GET(request)

    def getChild(self, path, request):
        if path == '':
            return self
        return Resource.getChild(self, path, request)


class MainPage(Element):

    def __init__(self, resource, template_path):
        super(MainPage, self).__init__(loader=XMLFile(FilePath(template_path)))
        self.resource = resource

    @renderer
    def network_options(self, request, tag):
        local_enabled, local_disabled = btn_toggle(
            config.network in ('lan', 'both',))
        cloud = config.network in ('cloud', 'both',)
        cloud_enabled, cloud_disabled = btn_toggle(cloud)
        collapsed = 'well collapse in' if cloud else 'well collapse'
        cloud_user, cloud_server = config.cloud_user.strip().split('@')
        return tag.fillSlots(local_enabled=local_enabled,
                             local_disabled=local_disabled,
                             cloud_enabled=cloud_enabled,
                             cloud_disabled=cloud_disabled,
                             collapsed=collapsed,
                             cloud_server=cloud_server,
                             cloud_user=cloud_user)


def btn_toggle(enabled):
    if enabled:
        return "btn btn-sm btn-primary active", "btn btn-sm btn-default"
    return "btn btn-sm btn-default", "btn btn-sm btn-primary active"


def load_yaml(datapath, filename='map.conf', conf=config):

    import yaml

    config.datadir = datapath

    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    confmap = yaml.load(
        open(os.path.join(datapath, filename)), Loader=Loader)
    try:
        confmap = yaml.load(
            open(os.path.join(datapath, filename)), Loader=Loader)
    except:
        confmap = {}
        log.error('No suitable map file found at {path}',
                  path='/'.join((datapath, filename)))
    try:
        scenarios = yaml.load(  # @UnusedVariable
            open(os.path.join(datapath, 'scenarios.conf')), Loader=Loader)
    except:
        scenarios = {}  # @UnusedVariable
        log.error(
            'No suitable scenario file found at {path}',
            path='/'.join((datapath, 'scenarios.conf')))
    #     print(confmap)
    #     print(scenarios)
    for setting, value in confmap.iteritems():
        if setting == 'config':
            for k, v in value.iteritems():
                setattr(conf, k, v)
                conf.config_changed.append(k)
        else:
            setattr(conf, setting, value)
            conf.objects.append(setting)
    return confmap


def save_yaml(datapath=None, filename='map.conf', conf=config):

    import yaml

    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper
    if datapath is None:
        datapath = conf.datadir
#     settings = conf.config_changed
    dic = {'config': {}}
    for k in conf.config_changed:
        dic['config'].update({k: getattr(conf, k)})
    for k in conf.objects:
        dic.update({k: getattr(conf, k)})
#     for attr, value in conf.__dict__.iteritems():
#         if not attr.startswith('_'):
#             if attr in settings:
#                 dic['config'].update({attr: value})
#             elif attr == 'collections' or isinstance(value, dict):
#                 dic.update({attr: value})
    print(dic['config'])
    yaml.dump(dic, open(os.path.join(datapath, filename), 'w+'),
              Dumper=Dumper, default_flow_style=False)

if __name__ == "__main__":
    import sys
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    config.network = "cloud"
    config.datadir = "/home/babe/Projets/eclipse/onDemand/data/"

    def renderDone(output):
        print(output)
#     flattenString(None, MainPage(
#                                  '/home/babe/Projets/eclipse/onDemand/data/web/templates/index.xml')
#                   ).addCallback(renderDone)
    res = SystemResource()
    service = Local_server(res)
    reactor.callWhenRunning(service.startService)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
