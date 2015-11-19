# encoding: utf-8
'''
Created on 12 nov. 2015

@author: Bertrand Verdu
'''
from twisted.internet import defer
from twisted.logger import Logger
from onDemand.protocols.serial import serialBytesProtocol
from onDemand.plugins.zigbee import Frame
from util import byteToInt, intToByte


class CommandFrameException(KeyError):
    pass


class BaseProtocol(serialBytesProtocol):

    def __init__(self, shorthand=True, callback=None, escaped=False,
                 error_callback=None):

        serialBytesProtocol.__init__(self)
        if callback:
            self.callbacks = [callback]
        else:
            self.callbacks = []
        self.setRawMode()
        self.shorthand = shorthand
        self._escaped = escaped
        self.log = Logger()
        self.requests = {}
        self.command_id = 0
        self.buffer = None
#         self.reading = False

    def get_id(self):
        try:
            self.command_id += 1
            return intToByte(self.command_id)
        except ValueError:
            self.command_id = 1
            return intToByte(1)

    def connect(self, f):
        if f.callback:
            self.callbacks.append(f.callback)
        f.proto = self

    def rawDataReceived(self, data):
        for byte in data:
            if self.buffer:
                self.buffer.fill(byte)
                if self.buffer.remaining_bytes() == 0:
                    try:
                        # Try to parse and return result
                        self.buffer.parse()
                        # Ignore empty frames
                        if len(self.buffer.data) == 0:
                            self.buffer = None

                    except ValueError:
                        # Bad frame, so restart
                        self.log.warn('Bad frame: %r'
                                      % self.buffer.raw_data)

                    else:
                        self.read_frame(self.buffer.data)
                    self.buffer = None
#                     self.reading = False
            else:
                if byte == Frame.START_BYTE:
                    #                     self.reading == True
                    self.buffer = Frame(escaped=self._escaped)

    def read_frame(self, frame):
        """
        read_frame: binary data -> {'id':str,
                                         'param':binary data,
                                         ...}
        read_frame takes a data packet received from an XBee device
        and converts it into a dictionary. This dictionary provides
        names for each segment of binary data as specified in the
        api_responses spec.
        """
        # Fetch the first byte, identify the packet
        # If the spec doesn't exist, raise exception
        packet_id = frame[0:1]
        try:
            name = self.api_responses[packet_id]
        except AttributeError:
            raise NotImplementedError(
                "API response specifications could not be found; " +
                "use a derived class which defines 'api_responses'.")
        except KeyError:
            # Check to see if this ID can be found among transmittible packets
            for cmd_name, cmd in list(self.api_frames.items()):
                if cmd['id']['default'] == packet_id:
                    msg = "Incoming frame with id {packet_id} looks like a " +\
                        "command frame of type '{cmd_name}' (these should " +\
                        " not be received). Are you sure your devices " +\
                        "are in API mode?"
                    self.log.error(
                        msg, packet_id=bytes(frame), cmd_name=cmd_name)
                    return

            self.log.error("Unrecognized response packet with id byte {f}",
                           f=frame[0])
            return

        # Current byte index in the data stream
        packet = self.api_frames[name]
        index = 0
        callback = False

        # Result info
        info = {'id': name}
#         packet_spec = packet['structure']

        # Parse the packet in the order specified

        if 'frame_id' in packet:
            callback = True

#         if packet['len'] == 'null_terminated':
#             field_data = b''
#             while frame[index:index + 1] != b'\x00':
#                 field_data += frame[index:index + 1]
#                 index += 1
#             index += 1
#             info[name]
        for field, dic in packet.items():
            if dic['len'] == 'null_terminated':
                field_data = b''

                while frame[index:index] != b'\x00':
                    field_data += frame[index:index]
                    index += 1

                index += 1
                info[field] = field_data
            elif dic['len'] is not None:
                # Store the number of bytes specified

                # Are we trying to read beyond the last data element?
                if index + dic['len'] > len(frame):
                    raise ValueError(
                        "Response packet was shorter than expected")

                field_data = frame[index:index + dic['len']]
                info[field] = field_data

                index += dic['len']
            # If the data field has no length specified, store any
            #  leftover bytes and quit
            else:
                field_data = frame[index:-1]

                # Were there any remaining bytes?
                if field_data:
                    # If so, store them
                    info[field] = field_data
                    index += len(field_data) + 1
                break

        # If there are more bytes than expected, raise an exception
        if index + 1 < len(frame):
            raise ValueError(
                "Response packet was longer than expected; " +
                "expected: %d, got: %d bytes" % (index, len(frame)))

        # Apply parsing rules if any exist
        if 'parsing' in packet:
            for parse_rule in packet['parsing']:
                # Only apply a rule if it is relevant (raw data is available)
                if parse_rule[0] in info:
                    # Apply the parse function to the indicated field and
                    # replace the raw data with the result
                    info[parse_rule[0]] = parse_rule[1](self, info)
        if callback:
            if info['frame_id'] in self.requests:
                self.requests[info['frame_id']].callback(info)
                del self.requests[info['frame_id']]
            else:
                self.log.warn('Response without request: %r' % info)
        elif self.callbacks:
            for callback in self.callbacks:
                callback(info)
        else:
            self.log.debug(info)

    def _build_command(self, cmd, **kwargs):
        """
        _build_command: string (binary data) ... -> binary data
        _build_command will construct a command packet according to the
        specified command's specification in api_commands. It will expect
        named arguments for all fields other than those with a default
        value or a length of 'None'.
        Each field will be written out in the order they are defined
        in the command definition.
        """
        try:
            cmd_spec = self.api_frames[cmd]
        except AttributeError:
            raise NotImplementedError(
                "API command specifications could not be found; " +
                "use a derived class which defines 'api_commands'.")

        packet = b''

        if 'frame_id' in kwargs:
            fid = kwargs['frame_id']
        elif cmd in ['source_route']:
            fid = b'\x00'
        else:
            fid = self.get_id()
        for name, dic in cmd_spec.items():
            if name == 'frame_id':
                data = fid
            elif name in kwargs:
                data = kwargs[name]
            else:
                if dic['len']:
                    if dic['default']:
                        data = dic['default']
                    else:
                        raise KeyError(
                            "The expected field %s of length %d was " +
                            "not provided" % (name, dic['len']))
                else:
                    data = None
            if dic['len'] and len(data) != dic['len']:
                raise ValueError(
                    "The data provided for '%s' was not %d bytes long"
                    % (name, dic['len']))
            if data:
                packet += data

        return packet, fid

    def send(self, cmd, **kwargs):
        """
        send: string param=binary data ... -> None
        When send is called with the proper arguments, an API command
        will be written to the serial port for this XBee device
        containing the proper instructions and data.
        This method must be called with named arguments in accordance
        with the api_command specification. Arguments matching all
        field names other than those in reserved_names (like 'id' and
        'order') should be given, unless they are of variable length
        (of 'None' in the specification. Those are optional).
        """
        # Pass through the keyword arguments
#         if self.reading:
#             return task.deferLater(.5, self.send, cmd, **kwargs)
        packet, fid = self._build_command(cmd, **kwargs)
        d = defer.Deferred()
        self.requests.update({fid: d})
        f = Frame(packet).output()
        self.transport.write(f)
        return d

    def _parse_samples_header(self, io_bytes):
        """
        _parse_samples_header: binary data in XBee IO data format ->
                        (int, [int ...], [int ...], int, int)
        _parse_samples_header will read the first three bytes of the
        binary data given and will return the number of samples which
        follow, a list of enabled digital inputs, a list of enabled
        analog inputs, the dio_mask, and the size of the header in bytes
        """
        header_size = 4

        # number of samples (always 1?) is the first byte
        sample_count = byteToInt(io_bytes[0])

        # part of byte 1 and byte 2 are the DIO mask ( 9 bits )
        dio_mask = (
            byteToInt(io_bytes[1]) << 8 | byteToInt(io_bytes[2])) & 0x01FF

        # upper 7 bits of byte 1 is the AIO mask
        aio_mask = byteToInt(io_bytes[3]) & 0xFE >> 1
#         print(byteToInt(io_bytes[3]) & 0xFE >> 1)
#         print(aio_mask)

        # sorted lists of enabled channels; value is position of bit in mask
        dio_chans = []
        aio_chans = []

        for i in range(0, 9):
            if dio_mask & (1 << i):
                dio_chans.append(i)

        dio_chans.sort()

        for i in range(0, 7):
            if aio_mask & (1 << i):
                aio_chans.append(i)

        aio_chans.sort()

        return (sample_count, dio_chans, aio_chans, dio_mask, header_size)

    def _parse_samples(self, io_bytes):
        """
        _parse_samples: binary data in XBee IO data format ->
                        [ {"dio-0":True,
                           "dio-1":False,
                           "adc-0":100"}, ...]
        _parse_samples reads binary data from an XBee device in the IO
        data format specified by the API. It will then return a
        dictionary indicating the status of each enabled IO port.
        """

        sample_count, dio_chans, aio_chans, dio_mask, header_size = \
            self._parse_samples_header(io_bytes)

        samples = []

        # split the sample data into a list, so it can be pop()'d
#         self.log.debug('%r' % io_bytes)
        sample_bytes = [byteToInt(c) for c in io_bytes[header_size:]]
#         self.log.debug('%r' % sample_bytes)
#         self.log.debug('%r' % aio_chans)

        # repeat for every sample provided
        for sample_ind in range(0, sample_count):  # @UnusedVariable
            tmp_samples = {}

            if dio_chans:
                # we have digital data
                digital_data_set = (
                    sample_bytes.pop(0) << 8 | sample_bytes.pop(0))
                digital_values = dio_mask & digital_data_set

                for i in dio_chans:
                    tmp_samples['dio-{0}'.format(i)] = True if (
                        digital_values >> i) & 1 else False

            for i in aio_chans:
                analog_sample = (
                    sample_bytes.pop(0) << 8 | sample_bytes.pop(0))
                tmp_samples['adc-{0}'.format(i)] = int(
                    (analog_sample * 1200.0) / 1023.0)

            samples.append(tmp_samples)

        return samples

    def _parse_sensor_data(self, io_bytes):
        # TODO
        return [{'data': io_bytes}]

    def __getattr__(self, name):
        """
        If a method by the name of a valid api command is called,
        the arguments will be automatically sent to an appropriate
        send() call
        """

        # If api_commands is not defined, raise NotImplementedError\
        #  If its not defined, _getattr__ will be called with its name
        if name == 'api_frames':
            raise NotImplementedError(
                "API command specifications could not be found; use a " +
                "derived class which defines 'api_commands'.")

        # Is shorthand enabled, and is the called name a command?
        if self.shorthand and name in self.api_frames:
            # If so, simply return a function which passes its arguments
            # to an appropriate send() call
            return lambda **kwargs: self.send(name, **kwargs)
        else:
            raise AttributeError("XBee has no attribute '%s'" % name)
