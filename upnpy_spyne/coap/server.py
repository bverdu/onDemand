# encoding: utf-8
'''
Created on 25 mai 2016

@author: Bertrand Verdu
'''
import time
from twisted.logger import Logger
from twisted.application import internet, service
from upnpy_spyne.utils import joinGroup6
from . import COAP_PORT, COAP_MCAST
from resource import Resource, CoreResource, RegisterResource,\
    Endpoint, Node, parseUriQuery, EndpointLookupResource,\
    ResourceLookupResource
from txthings.coap import Coap as TxCoap
from txthings.ext import link_header
from . import Message, GET

log = Logger()


class CoapServer(service.MultiService):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.services = []
        self.mainservice = None
        #  addr6 = get_default_v6_address()
        self.root = Resource()
        well = Resource()
        self.root.putChild('.well-known', well)
        core = CoreResource(self.root)
        core.parent = self
        well.putChild('core', core)
        self.rd = RegisterResource(self)
        self.root.putChild('rd', self.rd)
        lookup = Resource()
        self.root.putChild('rd-lookup', lookup)
        ep_lookup = EndpointLookupResource(self.rd)
        lookup.putChild('ep', ep_lookup)
        res_lookup = ResourceLookupResource(self.rd)
        lookup.putChild('res', res_lookup)
        endpoint = Endpoint(self.root)
        self.coap = Coap(endpoint)
        self.server = internet.MulticastServer(  # @UndefinedVariable
            COAP_PORT,
            self.coap,
            listenMultiple=True,
            interface='::0')
        self.server.setServiceParent(self)
        self.sensors = {}

    def refresh_sensors(self, sensor=None):
        ts = time.time()
        found = False
        for k, v in self.sensors.items():
            if sensor and sensor == k:
                v[0] = ts + v[1]
                found = True
            else:
                if v[0] < ts:
                    del(self.sensors[k])
        return found

    def discover(self, request):
        if self.refresh_sensors(request.remote[0]):
            return
        log.debug('Discovering: %s at %s' % (request.payload, request.remote))
        try:
            params = parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            return
        if 'ep' not in params:
            params['ep'] = request.remote[0]
        query = Message(code=GET)
        query.opt.uri_path = ('.well-known', 'core')
        query.opt.observe = None
        query.remote = request.remote
        d = self.coap.request(query)
        d.addCallback(self.discovered, params)

    def discovered(self, response, endpoint):
        log.error('Discovered:%r' % endpoint['ep'])
#         print(response.payload)
        if response.opt.content_format is not \
                self.rd.media_types['application/link-format']:
            log.debug('Unsupported content-format!')
            return
        log.error("response: ")
        log.error(response.payload)
        log.error(response.remote)
        log.error("/response.")
        new_endpoint = Node(endpoint['ep'],
                            link_header.parse_link_value(response.payload),
                            endpoint.get('d', ''),
                            endpoint.get('et', ''),
                            endpoint.get('lt', 86400),
                            endpoint.get('con', 'coap://[' +
                                         response.remote[0] +
                                         "]:" + str(response.remote[1])))
        lf = int(endpoint.get('lt', 600))
        self.sensors.update({response.remote[0]: [time.time() + lf, lf]})
        self.rd.add_entry(new_endpoint)


class Coap(TxCoap):

    def startProtocol(self):
        self.transport.setTTL(5)
        joinGroup6(self.transport, COAP_MCAST)
