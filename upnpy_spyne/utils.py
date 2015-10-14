# -*- coding: utf-8 -*-
'''
Created on 5 sept. 2014

@author: Bertrand Verdu
'''

import urlparse
import socket
# from twisted.python import log
from lxml import etree as et
from lxml.builder import ElementMaker
from struct import pack, unpack
from base64 import b64encode, b64decode
from mimetypes import guess_type
import upnpy_spyne


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
                    if len(element[0].tag.split('}')) > 0:
                        element[0].tag = element[0].tag.split('}')[-1]
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                if element.tag in self.keys():
                    self.update(
                        {element.tag: self[element.tag] + [aDict]
                         if isinstance(self[element.tag], list)
                         else [self[element.tag]] + [aDict]})
                else:
                    self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                d = {}
                for item in element.items():
                    if len(item[0].split('}')) > 0:
                        d.update({item[0].split('}')[-1]: item[1]})
                    else:
                        d.update({item[0]: item[1]})

#                 d = dict(element.items())
#                 print(d)
                d.update({'text': element.text})
                if element.tag in self.keys():
                    self.update({element.tag + '1': d})
                else:
                    self.update({element.tag: d})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                if len(element.tag.split('}')) > 0:
                    element.tag = element.tag.split('}')[-1]
                if element.tag in self.keys():
                    self.update({element.tag + '1': element.text})
                else:
                    self.update({element.tag: element.text})


def http_parse_raw(data):
    lines = data.split('\r\n')

    version, respCode, respText = None, None, None
    headers = {}

    for x in range(len(lines)):
        if x == 0:
            version, respCode, respText = lines[0].split()
            try:
                respCode = int(respCode)
            except ValueError:
                respCode = respCode
        elif x > 0 and lines[x].strip() != '':
            sep = lines[x].index(':')
            hk = lines[x][:sep].lower()
            hv = lines[x][sep + 1:].strip()

            if hk in headers.keys():
                headers[hk] = [headers[hk], hv]
            else:
                headers[hk] = hv

    return version, respCode, respText, headers


def get_default_address(host):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((host, 6666))
        address = s.getsockname()[0]
        s.close()
    except socket.gaierror:
        return None
    return address


def get_default_v4_address():
    return get_default_address("8.0.0.8")


def make_element(name, text):
    elem = et.Element(name)
    elem.text = text
    return elem


def get_version():
    return upnpy_spyne.__version__


def twisted_absolute_path(path, request):
    """Hack to fix twisted not accepting absolute URIs"""
    parsed = urlparse.urlparse(request.uri)
    if parsed.scheme != '':
        path_parts = parsed.path.lstrip('/').split('/')
        request.prepath = path_parts[0:1]
        request.postpath = path_parts[1:]
        path = request.prepath[0]
    return path, request


def headers_join(headers):
    msg = ""
    for hk, hv in headers.items():
        msg += str(hk) + ': ' + str(hv) + '\r\n'
    return msg


def build_notification_type(uuid, nt):
    if nt == '':
        return 'uuid:' + uuid, 'uuid:' + uuid
    return 'uuid:' + uuid + '::' + nt, nt


def make_event(evt, schema=None):
    ret = []
    if schema is not None:
        event = et.Element('Event', {'xmlns': schema})
        inst = et.Element('InstanceID', {'val': "0"})
        for item in evt['data']:
            e = et.Element(item['vname'])
            for k in item['value']:
                try:
                    sub = et.fromstring(item['value'][k])
                    e.append(sub)
                except:
                    e.set(k, str(item['value'][k]))
            inst.append(e)
    else:
        for item in evt['data']:
            inst = et.Element(item['vname'])
            for k in item['value']:
                try:
                    sub = et.fromstring(item['value'][k])
                    inst.append(sub)
                except:
                    inst.set(k, str(item['value'][k]))

#         inst.append(
#             et.Element(
#                 item['vname'],
#                 attrib={
#                     key: str(item['value'][key]) for key in item['value']}))
    if evt['evtype'] != 'last_change':
        try:
            ret.append((evt['evtype'] + '_value',
                        str(item['value']['text'])))
        except KeyError:
            ret.append((evt['evtype'] + '_value', str(item['value']['val'])))
    if schema is not None:
        event.append(inst)
    else:
        event = inst
#             setattr(self,
#                         evt['evtype']+'_value',  str(item['value']['text']))
#             except KeyError:
#             setattr(self, evt['evtype']+'_value',  str(item['value']['val']))
    return [(evt['evtype'], et.tostring(event))] + ret
#     return [(evt['evtype'], event)] + ret


def didl_decode(didl_str):
    e = ElementMaker(nsmap={
        None: 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
#     et.register_namespace('', 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/')
#     et.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
#     et.register_namespace('upnp', 'urn:schemas-upnp-org:metadata-1-0/upnp/')
    r = []
#     try:
#         root = et.XML(didl_str.encode('utf-8'))
#     except UnicodeDecodeError:
    root = et.XML(didl_str)
#     t = XmlDictConfig(root[0])
    for item in root:
        #         x = et.Element('DIDL-Lite')
        x = e('DIDL-Lite', item)
#         x.append(item)
        md = et.tostring(x)
        t = XmlDictConfig(item)
        d = {}
        for k in t.keys():
            if k == 'res':
                if 'protocolInfo' in t[k].keys():
                    d.update({'protocolInfo': t[k]['protocolInfo']})
                if 'duration' in t[k].keys():
                    d.update({'duration': str(t[k]['duration'])})
                if 'text' in t[k].keys():
                    d.update({'url': t[k]['text'].strip()})
    #                 pass
            elif k == 'albumArtURI':
                #  log.err(t[k])
                d.update({'albumArtURI': t[k]})
            else:
                d.update({k: t[k]})
        if 'title' not in d:
            d.update({'title': 'Unknown Title'})
        d.update({'metadata': md})
        r.append(d)
    return r


def didl_encode(dics):
    #     log.err(dics)
    if not isinstance(dics, list):
        dics = [dics]
#         log.err(dics)
    UPNP = "{urn:schemas-upnp-org:metadata-1-0/upnp/}"
    DC = "{http://purl.org/dc/elements/1.1/}"
    DLNA = "{urn:schemas-dlna-org:metadata-1-0/}"
    upnp = ['class', "artist", "actor", "author", "producer", "director",
            "genre", "album", "playlist", "albumArtURI",
            "artistDiscographyURI"]
    dc = ['title', 'rights', 'type', 'description', 'date', 'creator']
    res = ['duration', 'protocolInfo', 'sampleFrequency', 'nrAudioChannels',
           'size', 'resolution']
    defaultns = ElementMaker(nsmap={  # @UnusedVariable
        None: 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
    dcns = ElementMaker(  # @UnusedVariable
        nsmap={'dc': 'http://purl.org/dc/elements/1.1/'})
    upnpns = ElementMaker(nsmap={  # @UnusedVariable
        'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
    dlnans = ElementMaker(  # @UnusedVariable
        nsmap={'dlna': 'urn:schemas-dlna-org:metadata-1-0/'})
#     x = defaultns('DIDL-Lite')
    x = et.Element(
        'DIDL-Lite',
        nsmap={None: 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/',
               'dc': 'http://purl.org/dc/elements/1.1/',
               'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
    for dic in dics:
        #         log.err(dic)
        #         i = et.Element('item')
        i = et.SubElement(x, 'item',
                          attrib={'id': 'azertyuiop',
                                  'parentID': 'qwertyuiop',
                                  'restricted': '1'})
        if 'title' in dic.keys():
            #             t = dcns('title')
            t = et.SubElement(
                i,
                DC + 'title')
            try:
                t.text = dic['title'].decode('utf-8')
            except:
                t.text = dic['title']
#             log.err(t.text)
            i.append(t)
        r = et.SubElement(i, 'res')
        for k in dic.keys():
            if k == 'title':
                continue
            elif k in res:
                r.set(k, dic[k])
            elif k in ['url', 'file']:
                try:
                    t = guess_type(dic[k])[0].split('/')[0]
                    if t == 'audio':
                        typ = 'audioItem.musicTrack'
                    else:
                        typ = 'videoItem'
                except:
                    typ = 'videoidem'
                t = et.Element(UPNP + 'class')
#               t = et.Element(
#                   'upnp:class',
#                   {'xmlns:upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
                t.text = ''.join(('object.item.', typ))
                i.insert(1, t)
                try:
                    r.text = dic[k].decode('utf-8')
                except:
                    r.text = dic[k]
#                 log.err(r.text)
            elif k in dc:
                el = et.Element(DC + k)
                try:
                    el.text = dic[k].decode('utf-8')
                except:
                    el.text = dic[k]
                i.append(el)
            elif k in upnp:
                if k == 'class':
                    continue
                attr = {}
                map = {  # @ReservedAssignment
                    'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'}
                if k == 'albumArtURI':
                    albumuri = dic[k]
                    if not albumuri:
                        continue
                    if albumuri.split('.')[-1].lower() in ('jpg', 'jpeg'):
                        profileid = 'JPEG_TN'
                    else:
                        profileid = albumuri.split('.')[-1].upper() + '_TN'
                    attr.update({DLNA + 'profileID': profileid})
                    map.update({'dlna': 'urn:schemas-dlna-org:metadata-1-0/'})
#                   attr.update(
#                       {'dlna:profileID': profileid,
#                        'xmlns:dlna': 'urn:schemas-dlna-org:metadata-1-0/'})
#               attr.update(
#                   {'xmlns:upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/'})
                el = et.Element(UPNP + k, attrib=attr, nsmap=map)
#                 el = upnpns(k, {dlnans('profileID'): profileid})
                try:
                    el.text = dic[k].decode('utf-8')
                except:
                    el.text = dic[k]
#                 log.err(e.text)
                i.append(el)
        i.append(r)
        x.append(i)
    return et.tostring(x)


def dict2xml(d):
    #     print(d)
    children = []
    xml = ''
    root = None
    if isinstance(d, dict):
        for key, value in d.items():
            root = key
            if isinstance(value, dict):
                children.append(dict2xml(value))
                root = key
            elif isinstance(value, list):
                children.append(dict2xml(value))
            else:
                xml = xml + '<' + key + '>' +\
                    (str(value) if not isinstance(value, bool) else
                     str(int(value))) + '</' + key + '>'
    else:
        for value in d:
            children.append(dict2xml(value))
    if len(children) > 0:
        suffix = ''
        xml = ''
        if root is not None:
            xml = '<' + root + '>'
            suffix = '</' + root + '>'
        for child in children:
            xml += child
        xml += suffix
    return xml


def id_array(idlist):
    idarray = ''
    if not isinstance(idlist, list):
        idlist = [idlist]
    for i in idlist:
        idarray += pack('>I', i)
    return b64encode(idarray)


def id_array_decode(idarray):
    if not isinstance(idarray, str):
        idarray = str(idarray.encode('utf-8'))
    return [int(unpack('>I', i)[0]) for i in map(
        ''.join, zip(*[iter(b64decode(idarray))] * 4))]
#     t = []
#     for i in map(''.join, zip(*[iter(b64decode(idarray))]*4)):
#         t.append(unpack('>I', i)[0])
#     return t

if __name__ == '__main__':
    test = '<DIDL-Lite \
    xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" \
    xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" \
    xmlns:dc="http://purl.org/dc/elements/1.1/" \
    xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" \
    xmlns:sec="http://www.sec.co.kr/">\
    <item id="64$0$3$3$0$3" \
    parentID="64$0$3$3$0" \
    restricted="1">\
    <upnp:class>object.item.videoItem</upnp:class>\
    <dc:title>blz-al7&#233;àvol01ep04</dc:title>\
    <dc:date>2014-01-24T19:47:37</dc:date>\
    <res protocolInfo="http-get:*:video/x-matroska:DLNA.ORG_FLAGS=\
    01700000000000000000000000000000;DLNA.ORG_OP=01" \
    sampleFrequency="48000" nrAudioChannels="2" size="261902231" \
    resolution="640x480" duration="0:23:05.000">\
    http://192.168.0.10:8200/MediaItems/780.mkv\
    </res>\
    </item>\
    </DIDL-Lite>'
    t = didl_decode(test)
    print(t)
    print(t[0]['metadata'])
    print('\n' + test)
    print('\n' + didl_encode(t))
#     test2 = {'xesam:title': 'toto'}
#     r = mpris_decode(test2)
#     print('\n\n'+str(r))
#     print('\n'+str(mpris_encode(r)))
#     y = {}
#     print(didl_encode(y))
    p = [{'name': 'Salon' + 'UpnpAv' + '0',
          'type': 'UpnpAv',  'visible': True}]
    sources = [{'name': 'Salon' + 'UpnpAv' + '0',
                        'type': 'UpnpAv',
                        'visible': True}]
#     s = [(n, 'Source') for n in p]
    s = {'Sourcelist': [{'Source': n} for n in p]}
    print(s)
    print(dict2xml({'Sourcelist': [{'Source': n} for n in sources]}))
    a = id_array([2, 25, 32])
    print(a)
    print(id_array_decode('AAAABA=='))
#     b = b64decode(a)
#     for t in zip(*[iter(b)]*4):
#         print(len(''.join(t)))
#         print(unpack('>I', ''.join(t))[0])
#     for b in range(len(a)/4):
#         toto += unpack('>I', b64decode('a[:b*4])')
#     print('result: %s' % toto)
