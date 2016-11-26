# encoding: utf-8
'''
Created on 25 mai 2016

@author: Bertrand Verdu
'''
import fnmatch

import copy
from collections import namedtuple
from itertools import chain
from zope.interface import implements
from twisted.logger import Logger
from twisted.internet import defer, reactor, task
from twisted.web.resource import IResource
from twisted.web.error import UnsupportedMethod, UnexposedMethodError
from txthings.ext import link_header
from . import Message

CREATED = 65
DELETED = 66
CHANGED = 68
CONTENT = 69
CONTINUE = 95
BAD_REQUEST = 128
UNAUTHORIZED = 129
BAD_OPTION = 130
FORBIDDEN = 131
NOT_FOUND = 132
METHOD_NOT_ALLOWED = 133
UNSUPPORTED_CONTENT_FORMAT = 143

DEFAULT_LIFETIME = 86400

log = Logger()

Node = namedtuple('Node', ['name', 'link_format', 'domain',
                           'endpoint_type', 'lifetime', 'context'])


class Resource(object):

    implements(IResource)

    observable = False
    isLeaf = False
    requests = {1: 'GET',
                2: 'POST',
                3: 'PUT',
                4: 'DELETE'}
    requests.update({v: k for k, v in requests.items()})
#     print(requests)

    media_types = {0: 'text/plain',
                   40: 'application/link-format',
                   41: 'application/xml',
                   42: 'application/octet-stream',
                   47: 'application/exi',
                   50: 'application/json'}

    media_types.update({v: k for k, v in media_types.items()})

    def __init__(self, root=None):
        if root:
            self.root = root
        self.visible = False
        self.children = {}
        self.observers = {}
        self.params = {}

    def getChild(self, path, request):
        ''' to Be implemented in subclasses '''
        raise NotImplementedError

    def getChildWithDefault(self, path, request):

        if path in self.children:
            return self.children[path]
        return self.getChild(path, request)

    def putChild(self, path, child):
        self.children[path] = child
#         if not hasattr(child, 'root'):
#             if hasattr(self, 'root'):
#                 child.root = self.root
#             else:
#                 child.root = self

    def render(self, request):
        if request.code not in self.requests:
            raise UnsupportedMethod
        try:
            fct = getattr(
                self, 'render_' + self.requests[request.code])
        except AttributeError:
            raise UnexposedMethodError
        else:
            return fct(request)

    def addParam(self, param):
        self.params.setdefault(param.name, []).append(param)

    def deleteParam(self, name):
        if name in self.params:
            self.params.pop(name)

    def getParam(self, name):
        return self.params.get(name)

    def encode_params(self):
        data = [""]
        param_list = chain.from_iterable(
            sorted(self.params.values(), key=lambda x: x[0].name))
        for param in param_list:
            data.append(param.encode())
        return (';'.join(data))

    def generateResourceList(self, data, path=""):
        #         print(self.children)
        params = self.encode_params() + (";obs" if self.observable else "")
        if self.visible is True:
            if path is "":
                data.append('</>' + params)
            else:
                data.append('<' + path + '>' + params)
        for key in self.children:
            self.children[key].generateResourceList(data, path + "/" + key)


class CoreResource(Resource):
    """
    Example Resource that provides list of links hosted by a server.
    Normally it should be hosted at /.well-known/core

    Resource should be initialized with "root" resource, which can be used
    to generate the list of links.

    For the response, an option "Content-Format" is set to value 40,
    meaning "application/link-format". Without it most clients won't
    be able to automatically interpret the link format.

    Notice that self.visible is not set - that means that resource won't
    be listed in the link format it hosts.
    """

    def __init__(self, root=None):
        super(CoreResource, self).__init__(root)

    def render_POST(self, request):
        ''' simple discovery '''
        if hasattr(self, 'parent'):
            if request.payload == '':
                self.parent.discover(request)
                response = Message(code=CREATED, payload='')
                return defer.succeed(response)
            else:
                return self.parent.rd.render_POST(request)
        else:
            return defer.fail(UnsupportedMethod())

    def render_GET(self, request):
        data = []
        self.root.generateResourceList(data, "")
        payload = ",".join(data)
        response = Message(code=CONTENT, payload=payload)
        response.opt.content_format = self.media_types[
            'application/link-format']
        return defer.succeed(response)


class RegisterResource(Resource):
    """
    This class implements Registration function (point 5.2 of the draft).
    """

    def __init__(self, parent=None):
        super(RegisterResource, self).__init__()
        self.visible = True
        self.addParam(LinkParam("title", "Resource Directory"))
        self.directory = {}
        self.eid = 0
        self.parent = parent
        self.entries = {}

    def render_POST(self, request):
        """
        Add new entry to resource directory.
        """
        if request.opt.content_format is not \
                self.media_types['application/link-format']:
            log.debug('Unsupported content-format!')
            response = Message(code=UNSUPPORTED_CONTENT_FORMAT, payload='')
            return defer.succeed(response)
        try:
            params = parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            response = Message(code=BAD_REQUEST,
                               payload="Bad or ambiguous query options!")
            return defer.succeed(response)

        if 'ep' not in params:
            log.debug("No 'ep' query option in request.")
            response = Message(code=BAD_REQUEST,
                               payload="No 'ep' query option in request.")
            return defer.succeed(response)
        print(params)
        endpoint = Node(params['ep'],
                        link_header.parse_link_value(
            request.payload),
            params.get('d', ''),
            params.get('et', ''),
            params.get('lt', DEFAULT_LIFETIME),
            params.get('con', 'coap://' +
                       request.remote[0] +
                       ":" + str(request.remote[1])))
        return self.add_entry(endpoint)

    def remove_entry(self, endpoint):
        print(self.directory)
        if endpoint in self.directory:
            location = self.directory.pop(endpoint)
            del self.children[location]
            if self.parent and self.parent.mainservice:
                self.parent.mainservice.proxy.remove(endpoint)

    def add_entry(self, endpoint):
        log.debug(endpoint.name)
        print(self.entries)
        new = False
        if endpoint.name in self.entries:
            log.debug("new param for %s" % endpoint.name)
            for parm in endpoint:
                log.debug(str(parm))
            self.entries[endpoint.name].update(*endpoint)
        else:
            new = True
            self.directory[endpoint.name] = str(self.eid)
            self.eid += 1
            entry = DirectoryEntryResource(self, *endpoint)
            self.putChild(self.directory[endpoint.name], entry)
            self.entries[endpoint.name] = entry
        response = Message(code=CREATED, payload='')
        response.opt.location_path = ('rd', self.directory[endpoint.name])
        if new:
            if self.parent and self.parent.mainservice.proxy:
                self.parent.mainservice.proxy.append(endpoint.context,
                                                     endpoint)
        return defer.succeed(response)


class DirectoryEntryResource(Resource):
    """
    Simple implementation of Resource Directory
                        (draft-ietf-core-resource-directory-07).

    This class implements Update and Removal functions (points 5.3 and 5.4
    of the draft).
    """

    def __init__(self, parent, endpoint, link_format, domain, endpoint_type,
                 lifetime, context):
        super(DirectoryEntryResource, self).__init__()
        self.visible = False
        self.parent = parent
        self.endpoint = endpoint
        self.link_format = link_format
        self.domain = domain
        self.endpoint_type = endpoint_type
        self.context = context
        self.timeout = reactor.callLater(  # @UndefinedVariable
            int(lifetime), self.parent.remove_entry, self.endpoint)

    def render_GET(self, request):
        """
        Return endPoint links
        """
        try:
            parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            response = Message(
                code=BAD_REQUEST, payload="Bad or ambiguous query options!")
            return defer.succeed(response)
        pl = []
        for k, v in self.link_format.items():
            pl.append('<' + k + '>;' + ';'.join(
                '='.join((key, val)) for key, val in v.items()))
#         print(pl)
        response = Message(code=CONTENT, payload=','.join(pl))
        response.opt.content_format = self.media_types[
            'application/link-format']
        return defer.succeed(response)

    def render_PUT(self, request):
        """
        Update this resource directory entry.
        """
        try:
            params = parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            response = Message(
                code=BAD_REQUEST, payload="Bad or ambiguous query options!")
            return defer.succeed(response)

        lifetime = params.get('lt', DEFAULT_LIFETIME)
        self.timeout.cancel()
        self.timeout = reactor.callLater(  # @UndefinedVariable
            float(lifetime), self.removeResource)
        self.endpoint_type = params.get('et', '')
        self.context = params.get('con',
                                  'coap://' +
                                  request.remote[0] +
                                  ":" + str(request.remote[1]))
        response = Message(code=CHANGED, payload='')
        log.debug("RD entry updated: endpoint=%s, lifetime=%d" %
                  (self.endpoint, lifetime))
        return defer.succeed(response)

    def render_DELETE(self, request):
        """
        Delete this resource directory entry.
        """
        log.debug("RD entry deleted: endpoint=%s" % self.endpoint)
        self.removeResource()
        response = Message(code=DELETED, payload='')
        return defer.succeed(response)

    def removeResource(self):
        """
        Remove this resource. Used by both expiry and deletion.
        """
        location = self.parent.directory.pop(self.endpoint)
        del(self.parent.children[location])

    def update(self, endpoint, link_format, domain, endpoint_type,
               lifetime, context):
        self.timeout.cancel()
        self.endpoint = endpoint
        self.link_format = link_format
        self.domain = domain
        self.endpoint_type = endpoint_type
        self.context = context
        self.timeout = reactor.callLater(  # @UndefinedVariable
            int(lifetime), self.parent.remove_entry, self.endpoint)


class EndpointLookupResource(Resource):
    """
    Simple implementation of Resource Directory
                    (draft-ietf-core-resource-directory-01).

    This class implements Endpoint Lookup function (point 7 of the draft).
    """

    def __init__(self, directory_resource):
        super(EndpointLookupResource, self).__init__()
        self.visible = True
        self.directory = directory_resource

    def render_GET(self, request):
        """
        Return list of endpoints matching params specified in URI query.
        """
        try:
            params = parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            response = Message(code=BAD_REQUEST,
                               payload="Bad or ambiguous query options!")
            return defer.succeed(response)

        ep_pattern = params.get('ep', '*')
        d_pattern = params.get('d', '*')
        et_pattern = params.get('et', '*')

        link_format = []
        first_entry = True
        for entry in self.directory.children.values():
            if fnmatch.fnmatch(entry.endpoint, ep_pattern) and \
                    fnmatch.fnmatch(entry.domain, d_pattern) and \
                    fnmatch.fnmatch(entry.endpoint_type, et_pattern):
                if first_entry is True:
                    first_entry = False
                else:
                    link_format.append(',')
                link_format.append('<')
                link_format.append(entry.context)
                link_format.append('>;ep="')
                link_format.append(entry.endpoint)
                link_format.append('"')

        response = Message(code=CONTENT, payload=''.join(link_format))
        response.opt.content_format = self.media_types[
            'application/link-format']
        return defer.succeed(response)


class ResourceLookupResource(Resource):
    """
    Simple implementation of Resource Directory
                    (draft-ietf-core-resource-directory).

    This class implements Resource Lookup function (point 7 of the draft).
    """

    def __init__(self, directory_resource):
        super(ResourceLookupResource, self).__init__()
        self.visible = True
        self.directory = directory_resource

    def render_GET(self, request):
        """
        Return list of resources matching params specified in URI query.
        """
        try:
            params = parseUriQuery(request.opt.uri_query)
        except ValueError:
            log.debug("Bad or ambiguous query options!")
            response = Message(code=BAD_REQUEST,
                               payload="Bad or ambiguous query options!")
            return defer.succeed(response)

        # Endpoint parameters
        ep_pattern = params.get('ep', '*')
        d_pattern = params.get('d', '*')
        et_pattern = params.get('et', '*')

        # Resource parameters
        rt_pattern = params.get('rt', '*')
        title_pattern = params.get('title', '*')
        if_pattern = params.get('if', '*')

        link_format = []
        first_entry = True
        for entry in self.directory.children.values():
            if fnmatch.fnmatch(entry.endpoint, ep_pattern) and \
                    fnmatch.fnmatch(entry.domain, d_pattern) and \
                    fnmatch.fnmatch(entry.endpoint_type, et_pattern):
                for uri, params in entry.link_format.items():
                    if fnmatch.fnmatch(params.get('rt', ''), rt_pattern) and \
                            fnmatch.fnmatch(params.get('title', ''),
                                            title_pattern) and \
                            fnmatch.fnmatch(params.get('if', ''), if_pattern):
                        if first_entry is True:
                            first_entry = False
                        else:
                            link_format.append(',')
                        link_format.append('<')
                        link_format.append(entry.context)
                        link_format.append(uri)
                        link_format.append('>')
                        for name, value in params.items():
                            link_format.append(';')
                            link_format.append(name)
                            if value:
                                link_format.append('="')
                                link_format.append(value)
                            link_format.append('"')

        response = Message(code=CONTENT, payload=''.join(link_format))
        response.opt.content_format = self.media_types[
            'application/link-format']
        return defer.succeed(response)


class LinkParam(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def decode(self, rawdata):
        pass

    def encode(self):
        return '%s="%s"' % (self.name, self.value)


class Endpoint(object):

    counter = 0

    def __init__(self, root_resource):
        """
        Initialize endpoint.
        """
        self.resource = root_resource

    def render(self, request):
        """
        Redirect because a Site is always a directory.
        """
        request.redirect(request.prePathURL() + '/')
        # TODO: check this finish method
        request.finish()

    def getChildWithDefault(self, pathEl, request):
        """
        Emulate a resource's getChild method.
        """
        request.site = self
        return self.resource.getChildWithDefault(pathEl, request)

    def getResourceFor(self, request):
        """
        Get a resource for a request.

        This iterates through the resource heirarchy, calling
        getChildWithDefault on each resource it finds for a path element,
        stopping when it hits an element where isLeaf is true.
        """
        # request.en = self
        # Sitepath is used to determine cookie names between distributed
        # servers and disconnected sites.
        request.sitepath = copy.copy(request.prepath)
        return getChildForRequest(self.resource, request)


def parseUriContent(payloads):
    res = []
    for payload in payloads:
        pl = {}
        values = payload.split(';')
        for value in values:
            if '<' in value:
                if 'link' in pl:
                    raise ValueError(
                        'Several links in same result, cancelling')
                link = value.split('>')[0][1:]
                pl.update({'link': link})
            else:
                opt, val = value.split('=')
                pl.update({opt: val.strip("'").strip('"')})
        res.append(pl)
    return res


def parseUriQuery(query_list):
    query_dict = {}
    for query in query_list:
        name, value = query.split('=', 1)
        if name in query_dict:
            raise ValueError('Multiple query segments with same name')
        else:
            query_dict[name] = value.strip("'").strip('"')
    return query_dict


def getChildForRequest(resource, request):
    """
    Traverse resource tree to find who will handle the request.
    """
    while request.postpath and not resource.isLeaf:
        pathElement = request.postpath.pop(0)
        request.prepath.append(pathElement)
        resource = resource.getChildWithDefault(pathElement, request)
    return resource
