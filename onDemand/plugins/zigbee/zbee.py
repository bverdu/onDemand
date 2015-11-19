# encoding: utf-8
'''
Created on 12 nov. 2015

@author: Bertrand Verdu
'''
import struct
from collections import OrderedDict
from base import BaseProtocol


class ZigBee(BaseProtocol):
    """
    Provides an implementation of the XBee API for Zigbee S2/Pro modules
    with recent firmware.
    """
    # Packets which can be sent to an XBee
    # Format:
    #      {name of command:
    #         [{name:field name, len:field length, default: default value sent}
    #            ...
    #            ]
    #         ...
    #         }

    def __init__(self, *args, **kwargs):
        # Call the super class constructor to save the serial port
        self.api_responses = {
            self.api_frames[name]['id']['default']: name
            for name in (b'at_response', b'status', b'tx_status', b'rx',
                         b'rx_explicit', b'rx_io_sample', b'sensor_read',
                         b'node_id_indicator', b'remote_at_response')}

        BaseProtocol.__init__(self, *args, **kwargs)
#         super(ZigBee, self).__init__(*args, **kwargs)

    api_frames = {
        "at": OrderedDict([
            ('id',          {'len': 1,    'default': b'\x08'}),
            ('frame_id',    {'len': 1,    'default': b'\x01'}),
            ('command',     {'len': 2,    'default': None}),
            ('parameter',   {'len': None, 'default': None})]),
        "queued_at": OrderedDict([
            ('id',          {'len': 1,    'default': b'\x09'}),
            ('frame_id',    {'len': 1,    'default': b'\x01'}),
            ('command',     {'len': 2,    'default': None}),
            ('parameter',   {'len': None, 'default': None})]),
        "tx": OrderedDict([
            ('id',          {'len': 1,     'default': b'\x10'}),
            ('frame_id',    {'len': 1,     'default': b'\x00'}),
            ('dest_addr',   {'len': 2,     'default': None}),
            ('options',     {'len': 1,     'default': b'\x00'}),
            ('data',        {'len': None,  'default': None})]),
        "tx_explicit": OrderedDict([
            ('id',          {'len': 1,     'default': b'\x11'}),
            ('frame_id',    {'len': 1,     'default': b'\x01'}),
            ('dest_addr_long',
             {'len': 8,  'default': struct.pack('>Q', 0)}),
            ('dest_addr',   {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',     {'len': 1,     'default': b'\x00'}),
            ('data',        {'len': None,  'default': None})]),
        "remote_at": OrderedDict([
            ('id',          {'len': 1,     'default': b'\x17'}),
            ('frame_id',    {'len': 1,     'default': b'\x01'}),
            # dest_addr_long is 8 bytes (64 bits), so use an
            # unsigned long long
            ('dest_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('dest_addr',   {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',     {'len': 1,     'default': b'\x02'}),
            ('command',     {'len': 2,     'default': None}),
            ('parameter',   {'len': None,  'default': None})]),
        "source_route": OrderedDict([
            ('id',          {'len': 1,     'default': b'\x21'}),
            ('frame_id',    {'len': 1,     'default': b'\x00'}),
            # dest_addr_long is 8 bytes (64 bits), so use an
            # unsigned long long
            ('dest_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('dest_addr',   {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',     {'len': 1, 'default': b'\x00'}),
            ('count',       {'len': 1, 'default': b'\x03'}),
            ('address_1',   {'len': 2, 'default': None}),
            ('address_2',   {'len': 2, 'default': None}),
            ('address_3',   {'len': 2, 'default': None})]),
        "at_response": OrderedDict([
            ('id',          {'len': 1, 'default': b'\x88'}),
            ('frame_id',    {'len': 1, 'default': b'\x01'}),
            ('command',     {'len': 2, 'default': b'NI'}),
            ('status',      {'len': 1, 'default': b'\x00'}),
            ('parameter',   {'len': None, 'default': None}),
            ('parsing',     [('parameter', lambda self,
                              original: self._parse_IS_at_response(
                                  original)),
                             ('parameter', lambda self,
                              original: self._parse_ND_at_response(
                                  original))])]),
        "status": OrderedDict([
            ('id',           {'len': 1, 'default': b'\x8a'}),
            ('status',       {'len': 1, 'default': b'\x06'})]),
        "tx_status": OrderedDict([
            ('id',           {'len': 1, 'default': b'\x8b'}),
            ('frame_id',     {'len': 1, 'default': b'\x01'}),
            ('dest_addr',    {'len': 2, 'default': b'\xFF\xFE'}),
            ('retry_count',  {'len': 1, 'default': b'\x00'}),
            ('status',       {'len': 1, 'default': b'\x00'}),
            ('discovery',    {'len': 1, 'default': b'\x01'})]),
        "rx": OrderedDict([
            ('id',          {'len': 1,  'default': b'\x90'}),
            ('source_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('source_addr', {'len': 2,  'default': b'\xFF\xFE'}),
            ('options',     {'len': 1,  'default': b'\x01'}),
            ('rf_data',     {'len': None, 'default': None})]),
        "rx_explicit": OrderedDict([
            ('id',           {'len': 1,     'default': b'\x91'}),
            ('source_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('source_addr', {'len': 2,  'default': b'\xFF\xFE'}),
            ('source_endpoint',  {'len': 1, 'default': b'\xE0'}),
            ('dest_endpoint', {'len': 1,  'default': b'\xE0'}),
            ('cluster',     {'len': 2, 'default': b'\x00\x00'}),
            ('profile',     {'len': 2, 'default': b'\x00\x00'}),
            ('options',     {'len': 1,  'default': b'\x01'}),
            ('rf_data',     {'len': None, 'default': None})]),
        "rx_io_sample": OrderedDict([
            ('id',          {'len': 1,  'default': b'\x92'}),
            ('source_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('source_addr', {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',     {'len': 1, 'default': b'\x01'}),
            ('samples',     {'len': None, 'default': None}),
            ('parsing',     [('samples', lambda self,
                              original: self._parse_samples(
                                  original['samples']))])]),
        "sensor_read": OrderedDict([
            ('id',          {'len': 1,  'default': b'\x94'}),
            ('source_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('source_addr', {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',     {'len': 1, 'default': b'\x01'}),
            ('sensors_data', {'len': None, 'default': None}),
            ('parsing',     [('sensors_data', lambda self,
                              original: self._parse_sensors(
                                  original['sensors_data']))])]),
        "node_id_indicator": OrderedDict([
            ('id',          {'len': 1,  'default': b'\x95'}),
            ('sender_addr_long',
             {'len': 8,
              'default': struct.pack('>Q', 0)}),
            ('sender_addr',
             {'len': 2, 'default': b'\xFF\xFE'}),
            ('options',         {'len': 1, 'default': b'\x01'}),
            ('source_addr',
             {'len': 2, 'default': b'\xFF\xFE'}),
            ('source_addr_long',
             {'len': 8, 'default': struct.pack('>Q', 0)}),
            ('node_id',
             {'len': 'null_terminated', 'default': None}),
            ('parent_source_addr',
             {'len': 2, 'default': b'\xFF\xFE'}),
            ('device_type',     {'len': 1, 'default': b'\x00'}),
            ('source_event',    {'len': 1, 'default': b'\x01'}),
            ('digi_profile_id', {
                'len': 2, 'default': b'\xC1\x05'}),
            ('manufacturer_id',
             {'len': 2, 'default': b'\x10\x1E'})]),
        "remote_at_response": OrderedDict([
            ('id',           {'len': 1, 'default': b'\x97'}),
            ('frame_id',     {'len': 1, 'default': b'\x01'}),
            ('source_addr_long',
             {'len': 8, 'default': struct.pack('>Q', 0)}),
            ('source_addr',  {'len': 2, 'default': b'\xFF\xFE'}),
            ('command',      {'len': 2, 'default': b'NI'}),
            ('status',       {'len': 1, 'default': b'\x00'}),
            ('parameter',    {'len': None, 'default': None}),
            ('parsing', [('parameter', lambda self,
                          original: self._parse_IS_at_response(
                              original))])])
    }

    def connectionMade(self):
        def got_info(data):
            for callback in self.callbacks:
                callback(data)
        d = self.remote_at(
            dest_addr_long=b'\x00\x00\x00\x00\x00\x00\xFF\xFF', command=b'IS')
        d.addCallback(got_info)

    def connect(self, f):
        if f.callback:
            self.callbacks.append(f.callback)
            d = self.remote_at(
                dest_addr_long=f.long_address, command=b'IS')
            d.addCallback(f.callback)
        f.proto = self

    def _parse_IS_at_response(self, packet_info):
        """
        If the given packet is a successful remote AT response for an IS
        command, parse the parameter field as IO data.
        """
        if packet_info['id'] in (b'\x97', b'\x88') and\
                packet_info['command'].lower() == b'is' and\
                packet_info['status'] == b'\x00':
            return self._parse_samples(packet_info['parameter'])
        else:
            return packet_info['parameter']

    def _parse_ND_at_response(self, packet_info):
        """
            If the given packet is a successful AT response for an ND
            command, parse the parameter field.
            """
        if packet_info['id'] == 'at_response' and\
                packet_info['command'].lower() == b'nd' and\
                packet_info['status'] == b'\x00':
            result = {}

            # Parse each field directly
            result['source_addr'] = packet_info['parameter'][0:2]
            result['source_addr_long'] = packet_info['parameter'][2:10]

            # Parse the null-terminated node identifier field
            null_terminator_index = 10
            while packet_info[
                    'parameter'][
                null_terminator_index:null_terminator_index + 1]\
                    != b'\x00':
                null_terminator_index += 1

            # Parse each field thereafter directly
            result['node_identifier'] = packet_info[
                'parameter'][10:null_terminator_index]
            result['parent_address'] = packet_info['parameter'][
                null_terminator_index + 1:null_terminator_index + 3]
            result['device_type'] = packet_info['parameter'][
                null_terminator_index + 3:null_terminator_index + 4]
            result['status'] = packet_info['parameter'][
                null_terminator_index + 4:null_terminator_index + 5]
            result['profile_id'] = packet_info['parameter'][
                null_terminator_index + 5:null_terminator_index + 7]
            result['manufacturer'] = packet_info['parameter'][
                null_terminator_index + 7:null_terminator_index + 9]

            # Simple check to ensure a good parse
            if null_terminator_index + 9 != len(packet_info['parameter']):
                raise ValueError("Improper ND response length: expected {0}" +
                                 ", read {1} bytes".format(
                                     len(packet_info['parameter']),
                                     null_terminator_index + 9))

            return result
        else:
            return packet_info['parameter']

if __name__ == '__main__':

    import sys
    from twisted.internet.serialport import SerialPort
    from twisted.internet import reactor
    from twisted.logger import globalLogBeginner, textFileLogObserver, Logger

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    log = Logger()
    dest_addr_long = b'\x00\x00\x00\x00\x00\x00\xFF\xFF'

    def receive(data):
        f = None
        if data['id'] == b'\x92':
            for s in data['samples']:
                if 'dio-2' in s:
                    if s['dio-2'] and not proto.red:
                        print('red !!!')
                    proto.red = s['dio-2']
                if 'dio-1' in s:
                    if s['dio-1'] and not proto.green:
                        print('green !!!')
                    proto.green = s['dio-1']
#                     if not proto.red:
#                         f = proto.remote_at(dest_addr_long=dest_addr_long,
#                                             command=b'D2', parameter=b'\x05')
#                         proto.red = True
#                 else:
#                     if proto.red:
#                         f = proto.remote_at(dest_addr_long=dest_addr_long,
#                                             command=b'D2', parameter=b'\x04')
#                         proto.red = False
#             if 'adc-0' in s:
#                 if s['adc-0'] > 1000:
#                     print('green')
#                     if not proto.green:
#                         f = proto.remote_at(dest_addr_long=dest_addr_long,
#                                             command=b'D3', parameter=b'\x05')
#
#                         proto.green = True
#                 else:
#                     if proto.green:
#                         f = proto.remote_at(dest_addr_long=dest_addr_long,
#                                             command=b'D3', parameter=b'\x04')
#                         proto.green = False
                if f:
                    f.addCallback(show, 'Digital set')

    global proto
    proto = ZigBee(callback=receive, escaped=True)
    proto.red = False
    proto.green = False

    def show(data, comment='broadcast'):
        log.debug('{desc} frame: {data})', desc=comment, data=data)

    def stop_monitor():
        log.debug('Stop Monitoring...')
        g = proto.remote_at(dest_addr_long=dest_addr_long,
                            command=b'IR', parameter=b'\x00')
        g.addCallback(show, 'IR set')

    def test():
        print('start')
#         d = proto.remote_at(dest_addr_long=dest_addr_long, command=b'NI')
#         d.addCallback(show, 'NI Response')
#         e = proto.remote_at(dest_addr_long=dest_addr_long, command=b'IS')
#         e.addCallback(show, 'IS Response')
#         f = proto.remote_at(dest_addr_long=dest_addr_long,
#                             command=b'IR', parameter=b'\x02\x00')
#         f.addCallback(show, 'IR set')

    f = SerialPort(proto, '/dev/ttyACM0', reactor, baudrate=57600)
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.callLater(30, reactor.stop)  # @UndefinedVariable
#     reactor.callLater(28, stop_monitor)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
