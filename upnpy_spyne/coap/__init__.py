# encoding: utf-8
'''
Created on 17 févr. 2016
@author: Maciej Wasilak
@author: Bertrand Verdu
'''
import struct
import copy
import collections
from itertools import chain
from lxml import etree as et
from zope.interface import implements
from twisted.internet import reactor, defer
from twisted.internet.protocol import DatagramProtocol
from twisted.web.resource import IResource
from twisted.web.error import UnsupportedMethod, UnexposedMethodError
from twisted.logger import Logger
from upnpy_spyne.utils import joinGroup6

CON = 0  # Confirmable message type.
NON = 1  # Non-confirmable message type
ACK = 2
RST = 3
types = {0: 'CON',
         1: 'NON',
         2: 'ACK',
         3: 'RST'}
EMPTY = 0
GET = 1
POST = 2
PUT = 3
DELETE = 4
VALID = 67
CHANGED = 68
NOT_ACCEPTABLE = 134
REQUEST_ENTITY_INCOMPLETE = 136
PRECONDITION_FAILED = 140
REQUEST_ENTITY_TOO_LARGE = 141
INTERNAL_SERVER_ERROR = 160
NOT_IMPLEMENTED = 161
BAD_GATEWAY = 162
SERVICE_UNAVAILABLE = 163
GATEWAY_TIMEOUT = 164
PROXYING_NOT_SUPPORTED = 165
IF_MATCH = 1
URI_HOST = 3
ETAG = 4
IF_NONE_MATCH = 5
OBSERVE = 6
URI_PORT = 7
LOCATION_PATH = 8
URI_PATH = 11
CONTENT_FORMAT = 12
MAX_AGE = 14
URI_QUERY = 15
ACCEPT = 17
LOCATION_QUERY = 20
BLOCK2 = 23
BLOCK1 = 27
SIZE2 = 28
PROXY_URI = 35
PROXY_SCHEME = 39
SIZE1 = 60
VALID_REQUESTS = [i for i in range(1, 31)]
VALID_RESPONSES = [i for i in range(64, 191)]
SUCCESS_CODES = [i for i in range(64, 95)]
DEFAULT_BLOCK_SIZE_EXP = 2  # Block size 64

COAP_PORT = 5683
COAP_MCAST = 'ff05::c'

log = Logger()


# class Coap(DatagramProtocol):
#
#     def __init__(self, addr):
#         self.addr = addr
#         self.log = Logger()
#         self.non_confirmed = {}
#
#     def startProtocol(self):
#         self.transport.setTTL(5)
#         joinGroup6(self.transport, COAP_MCAST)
#
#     def datagramReceived(self, data, (host, port)):
#
#         #         method, path, version, headers = http_parse_raw(data)
#         if host == self.addr:
#             return
#         self.log.debug("datagram received:%r from %s:%s" % (data, host, port))
#         message = msg_from_datagram(data, (host, port), self)
#         if message.code == 0:
#             self.render_Empty(message)
#         elif message.code > 0 and message.code < 32:
#             self.render_Request(message)
#         elif message.code > 63 and message.code < 192:
#             self.render_Response(message)
#         else:
#             self.log.debug("Unknown message type received: %d" % message.code)
# #                 self.ssdp.update_hosts(
# #                     {'location': ':'.join(("[" + host + "]", str(port))),
# #                      'server': 'coap'},
# #                     ('/' + '/'.join(message.opt.uri_path),
# #                      message.opt.uri_query))
#
#     def render_Request(self, request):
#         if request.mtype in (0, 1):  # CON, NON
#             if request.mid + request.remote in self.non_confirmed:
#                 # Send message again
#                 self.sendMessage(
#                             self.non_confirmed[request.mid + request.remote])
#             else:
#
#         else:
#             response = Message(code=BAD_REQUEST,
#                                payload='Wrong message type for request!')
#             self.respond(response, request)
#
#     def render_Response(self, response):
#         pass
#
#     def render_Empty(self, message):
#         pass


class Message(object):
    """A CoAP Message."""

    def __init__(self, mtype=None, mid=None, code=EMPTY, payload='', token=''):
        self.version = 1
        self.mtype = mtype
        self.mid = mid
        self.code = code
        self.token = token
        self.payload = payload
        self.opt = Options()

        self.response_type = None
        self.remote = None
        self.prepath = None
        self.postpath = None

        if self.payload is None:
            self.payload = ''

    def encode(self):
        """Create binary representation of message from Message object."""
        if self.mtype is None or self.mid is None:
            raise TypeError(
                "Message Type and Message ID must not be None.")
        rawdata = chr((self.version << 6) + (
            (self.mtype & 0x03) << 4) + (len(self.token) & 0x0F))
        rawdata += struct.pack('!BH', self.code, self.mid)
        rawdata += self.token
        rawdata += self.opt.encode()
        if len(self.payload) > 0:
            rawdata += chr(0xFF)
            rawdata += self.payload
        return rawdata

    def extractBlock(self, number, size_exp):
        """Extract block from current message."""
        size = 2 ** (size_exp + 4)
        start = number * size
        if start < len(self.payload):
            end = start + size if start + size < len(
                self.payload) else len(self.payload)
            block = copy.deepcopy(self)
            block.payload = block.payload[start:end]
            block.mid = None
            more = True if end < len(self.payload) else False
            if block.code in VALID_REQUESTS:
                block.opt.block1 = (number, more, size_exp)
            else:
                block.opt.block2 = (number, more, size_exp)
            return block

    def appendRequestBlock(self, next_block):
        """Append next block to current request message.
           Used when assembling incoming blockwise requests."""
        if self.code in VALID_REQUESTS:
            block1 = next_block.opt.block1
            if block1.block_number * (
                    2 ** (block1.size_exponent + 4)) == len(self.payload):
                self.payload += next_block.payload
                self.opt.block1 = block1
                self.token = next_block.token
                self.mid = next_block.mid
                self.response_type = None
            else:
                raise NotImplementedError
        else:
            raise ValueError("Fatal Error: called appendRequestBlock " +
                             "on non-request message!!!")

    def appendResponseBlock(self, next_block):
        """Append next block to current response message.
           Used when assembling incoming blockwise responses."""
        if self.code in VALID_RESPONSES:
            # @TODO: check etags for consistency
            block2 = next_block.opt.block2
            if block2.block_number * (
                    2 ** (block2.size_exponent + 4)) != len(self.payload):
                raise NotImplementedError

            if next_block.opt.etag != self.opt.etag:
                raise ResourceChangedError("Resource no more available")

            self.payload += next_block.payload
            self.opt.block2 = block2
            self.token = next_block.token
            self.mid = next_block.mid
        else:
            raise ValueError("Called appendResponseBlock " +
                             "on non-response message!!!")

    def generateNextBlock2Request(self, response):
        """Generate a request for next response block.
           This method is used by client after receiving
           blockwise response from server with "more" flag set."""
        request = copy.deepcopy(self)
        request.payload = ""
        request.mid = None
        if response.opt.block2.block_number == 0 and\
                response.opt.block2.size_exponent > DEFAULT_BLOCK_SIZE_EXP:
            new_size_exponent = DEFAULT_BLOCK_SIZE_EXP
            new_block_number = 2 ** (
                response.opt.block2.size_exponent - new_size_exponent)
            request.opt.block2 = (new_block_number, False, new_size_exponent)
        else:
            request.opt.block2 = (response.opt.block2.block_number + 1,
                                  False, response.opt.block2.size_exponent)
        request.opt.deleteOption(BLOCK1)
        request.opt.deleteOption(OBSERVE)
        return request

    def generateNextBlock1Response(self):
        """Generate a response to acknowledge incoming request block.
           This method is used by server after receiving
           blockwise request from client with "more" flag set."""
        response = Message(code=CHANGED, token=self.token)
        response.remote = self.remote
        if self.opt.block1.block_number == 0 and\
                self.opt.block1.size_exponent > DEFAULT_BLOCK_SIZE_EXP:
            new_size_exponent = DEFAULT_BLOCK_SIZE_EXP
            response.opt.block1 = (0, True, new_size_exponent)
        else:
            response.opt.block1 = (self.opt.block1.block_number, True,
                                   self.opt.block1.size_exponent)
        return response


class OpaqueOption(object):
    """Opaque CoAP option - used to represent opaque options.
       This is a default option type."""

    def __init__(self, number, value=""):
        self.value = value
        self.number = number

    def encode(self):
        rawdata = self.value
        return rawdata

    def decode(self, rawdata):
        self.value = rawdata  # if rawdata is not None else ""

    def _length(self):
        return len(self.value)
    length = property(_length)


class StringOption(object):
    """String CoAP option - used to represent string options."""

    def __init__(self, number, value=""):
        self.value = value
        self.number = number

    def encode(self):
        rawdata = self.value
        return rawdata

    def decode(self, rawdata):
        self.value = rawdata  # if rawdata is not None else ""

    def _length(self):
        return len(self.value)
    length = property(_length)


class UintOption(object):
    """Uint CoAP option - used to represent uint options."""

    def __init__(self, number, value=0):
        self.value = value
        self.number = number

    def encode(self):
        rawdata = struct.pack("!L", self.value)
        return rawdata.lstrip(chr(0))

    def decode(self, rawdata):
        value = 0
        for byte in rawdata:
            value = (value * 256) + ord(byte)
        self.value = value
        return self

    def _length(self):
        if self.value > 0:
            return (self.value.bit_length() - 1) // 8 + 1
        else:
            return 0
    length = property(_length)


class BlockOption(object):
    """Block CoAP option - special option used only for Block1 and Block2 options.
       Currently it is the only type of CoAP options that has
       internal structure."""
    BlockwiseTuple = collections.namedtuple('BlockwiseTuple',
                                            ['block_number',
                                             'more',
                                             'size_exponent'])

    def __init__(self, number, value=(0, None, 0)):
        self.value = self.BlockwiseTuple._make(value)
        self.number = number

    def encode(self):
        as_integer = (self.value[0] << 4) + (
            self.value[1] * 0x08) + self.value[2]
        rawdata = struct.pack("!L", as_integer)
        return rawdata.lstrip(chr(0))

    def decode(self, rawdata):
        as_integer = 0
        for byte in rawdata:
            as_integer = (as_integer * 256) + ord(byte)
        self.value = self.BlockwiseTuple(
            block_number=(as_integer >> 4),
            more=bool(as_integer & 0x08), size_exponent=(as_integer & 0x07))

    def _length(self):
        return ((self.value[0].bit_length() + 3) / 8 + 1)
    length = property(_length)


class Options(object):
    """Represent CoAP Header Options."""
    option_formats = {3:  StringOption,
                      6:  UintOption,
                      7:  UintOption,
                      8:  StringOption,
                      11: StringOption,
                      12: UintOption,
                      14: UintOption,
                      15: StringOption,
                      16: UintOption,
                      20: StringOption,
                      23: BlockOption,
                      27: BlockOption,
                      28: UintOption,
                      35: StringOption,
                      39: StringOption,
                      60: UintOption}

    def __init__(self):
        self._options = {}

    def decode(self, rawdata):
        """Decode all options in message from raw binary data."""
        option_number = 0

        while len(rawdata) > 0:
            if ord(rawdata[0]) == 0xFF:
                return rawdata[1:]
            dllen = ord(rawdata[0])
            delta = (dllen & 0xF0) >> 4
            length = (dllen & 0x0F)
            rawdata = rawdata[1:]
            (delta, rawdata) = readExtendedFieldValue(delta, rawdata)
            (length, rawdata) = readExtendedFieldValue(length, rawdata)
            option_number += delta
            option = self.option_formats.get(
                option_number, OpaqueOption)(option_number)
            option.decode(rawdata[:length])
            self.addOption(option)
            rawdata = rawdata[length:]
        return ''

    def encode(self):
        """Encode all options in option header into string of bytes."""
        data = []
        current_opt_num = 0
        option_list = self.optionList()
        for option in option_list:
            delta, extended_delta = writeExtendedFieldValue(
                option.number - current_opt_num)
            length, extended_length = writeExtendedFieldValue(option.length)
            data.append(chr(((delta & 0x0F) << 4) + (length & 0x0F)))
            data.append(extended_delta)
            data.append(extended_length)
            data.append(option.encode())
            current_opt_num = option.number
        return (''.join(data))

    def addOption(self, option):
        """Add option into option header."""
        self._options.setdefault(option.number, []).append(option)

    def deleteOption(self, number):
        """Delete option from option header."""
        if number in self._options:
            self._options.pop(number)

    def getOption(self, number):
        """Get option with specified number."""
        return self._options.get(number)

    def optionList(self):
        return chain.from_iterable(sorted(self._options.values(),
                                          key=lambda x: x[0].number))

    def _setUriPath(self, segments):
        """Convenience setter: Uri-Path option"""
        if isinstance(segments, basestring):
            raise ValueError("URI Path should be passed as a list " +
                             "or tuple of segments")
        self.deleteOption(number=URI_PATH)
        for segment in segments:
            self.addOption(StringOption(number=URI_PATH, value=str(segment)))

    def _getUriPath(self):
        """Convenience getter: Uri-Path option"""
        segment_list = []
        uri_path = self.getOption(number=URI_PATH)
        if uri_path is not None:
            for segment in uri_path:
                segment_list.append(segment.value)
        return segment_list

    uri_path = property(_getUriPath, _setUriPath)

    def _setUriQuery(self, segments):
        """Convenience setter: Uri-Query option"""
        if isinstance(segments, basestring):
            raise ValueError("URI Query should be passed as a list " +
                             "or tuple of segments")
        self.deleteOption(number=URI_QUERY)
        for segment in segments:
            self.addOption(StringOption(number=URI_QUERY, value=str(segment)))

    def _getUriQuery(self):
        """Convenience getter: Uri-Query option"""
        segment_list = []
        uri_query = self.getOption(number=URI_QUERY)
        if uri_query is not None:
            for segment in uri_query:
                segment_list.append(segment.value)
        return segment_list

    uri_query = property(_getUriQuery, _setUriQuery)

    def _setBlock2(self, block_tuple):
        """Convenience setter: Block2 option"""
        self.deleteOption(number=BLOCK2)
        self.addOption(BlockOption(number=BLOCK2, value=block_tuple))

    def _getBlock2(self):
        """Convenience getter: Block2 option"""
        block2 = self.getOption(number=BLOCK2)
        if block2 is not None:
            return block2[0].value
        else:
            return None

    block2 = property(_getBlock2, _setBlock2)

    def _setBlock1(self, block_tuple):
        """Convenience setter: Block1 option"""
        self.deleteOption(number=BLOCK1)
        self.addOption(BlockOption(number=BLOCK1, value=block_tuple))

    def _getBlock1(self):
        """Convenience getter: Block1 option"""
        block1 = self.getOption(number=BLOCK1)
        if block1 is not None:
            return block1[0].value
        else:
            return None

    block1 = property(_getBlock1, _setBlock1)

    def _setContentFormat(self, content_format):
        """Convenience setter: Content-Format option"""
        self.deleteOption(number=CONTENT_FORMAT)
        self.addOption(UintOption(number=CONTENT_FORMAT, value=content_format))

    def _getContentFormat(self):
        """Convenience getter: Content-Format option"""
        content_format = self.getOption(number=CONTENT_FORMAT)
        if content_format is not None:
            return content_format[0].value
        else:
            return None

    content_format = property(_getContentFormat, _setContentFormat)

    def _setETag(self, etag):
        """Convenience setter: ETag option"""
        self.deleteOption(number=ETAG)
        if etag is not None:
            self.addOption(OpaqueOption(number=ETAG, value=etag))

    def _getETag(self):
        """Convenience getter: ETag option"""
        etag = self.getOption(number=ETAG)
        if etag is not None:
            return etag[0].value
        else:
            return None

    etag = property(_getETag, _setETag, None,
                    "Access to a single ETag on the message" +
                    "(as used in responses)")

    def _setETags(self, etags):
        self.deleteOption(number=ETAG)
        for tag in etags:
            self.addOption(OpaqueOption(number=ETAG, value=tag))

    def _getETags(self):
        etag = self.getOption(number=ETAG)
        return [] if etag is None else [tag.value for tag in etag]

    etags = property(_getETags, _setETags, None,
                     "Access to a list of ETags on the message " +
                     "(as used in requests)")

    def _setObserve(self, observe):
        self.deleteOption(number=OBSERVE)
        if observe is not None:
            self.addOption(UintOption(number=OBSERVE, value=observe))

    def _getObserve(self):
        observe = self.getOption(number=OBSERVE)
        if observe is not None:
            return observe[0].value
        else:
            return None

    observe = property(_getObserve, _setObserve)

    def _setAccept(self, accept):
        self.deleteOption(number=ACCEPT)
        if accept is not None:
            self.addOption(UintOption(number=ACCEPT, value=accept))

    def _getAccept(self):
        accept = self.getOption(number=ACCEPT)
        if accept is not None:
            return accept[0].value
        else:
            return None

    accept = property(_getAccept, _setAccept)

    def _setLocationPath(self, segments):
        """Convenience setter: Location-Path option"""
        if isinstance(segments, basestring):
            raise ValueError("Location Path should be passed as a list " +
                             "or tuple of segments")
        self.deleteOption(number=LOCATION_PATH)
        for segment in segments:
            self.addOption(StringOption(number=LOCATION_PATH,
                                        value=str(segment)))

    def _getLocationPath(self):
        """Convenience getter: Location-Path option"""
        segment_list = []
        location_path = self.getOption(number=LOCATION_PATH)
        if location_path is not None:
            for segment in location_path:
                segment_list.append(segment.value)
        return segment_list

    location_path = property(_getLocationPath, _setLocationPath)


class ResourceChangedError(Exception):
    pass


def msg_from_datagram(rawdata, remote=None, protocol=None):
    """Create Message object from binary representation of message."""
    (tkl, code, _id) = struct.unpack('!BBH', rawdata[:4])
    version = (tkl & 0xC0) >> 6
    if version != 1:
        raise ValueError("Fatal Error: Protocol Version must be 1")
    mtype = (tkl & 0x30) >> 4
    token_length = (tkl & 0x0F)
    msg = Message(mtype=mtype, mid=_id, code=code)
    msg.token = rawdata[4:4 + token_length]
    msg.payload = msg.opt.decode(rawdata[4 + token_length:])
    msg.remote = remote
    msg.protocol = protocol
    return msg


def readExtendedFieldValue(value, rawdata):
    """Used to decode large values of option delta and option length
       from raw binary form."""
    if value >= 0 and value < 13:
        return (value, rawdata)
    elif value == 13:
        return (ord(rawdata[0]) + 13, rawdata[1:])
    elif value == 14:
        return (struct.unpack('!H', rawdata[:2])[0] + 269, rawdata[2:])
    else:
        raise ValueError("Value out of range.")


def writeExtendedFieldValue(value):
    """Used to encode large values of option delta and option length
       into raw binary form.
       In CoAP option delta and length can be represented by a variable
       number of bytes depending on the value."""
    if value >= 0 and value < 13:
        return (value, '')
    elif value >= 13 and value < 269:
        return (13, struct.pack('!B', value - 13))
    elif value >= 269 and value < 65804:
        return (14, struct.pack('!H', value - 269))
    else:
        raise ValueError("Value out of range.")
