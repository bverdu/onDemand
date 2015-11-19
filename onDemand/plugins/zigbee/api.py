# encoding: utf-8
"""
frame.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

Represents an API frame for communicating with an XBee
"""
import struct
from util import byteToInt, intToByte
from twisted.logger import Logger

log = Logger()


class Frame(object):
    """
    Represents a frame of data to be sent to or which was received 
    from an XBee device
    """

    START_BYTE = b'\x7E'
    ESCAPE_BYTE = b'\x7D'
    XON_BYTE = b'\x11'
    XOFF_BYTE = b'\x13'
    ESCAPE_BYTES = (START_BYTE, ESCAPE_BYTE, XON_BYTE, XOFF_BYTE)

    def __init__(self, data=b'', escaped=False):
        self.data = data
        self.raw_data = b''
        self.escaped = escaped
        self._unescape_next_byte = False

    def checksum(self):
        """
        checksum: None -> single checksum byte

        checksum adds all bytes of the binary, unescaped data in the 
        frame, saves the last byte of the result, and subtracts it from 
        0xFF. The final result is the checksum
        """
        total = 0

        # Add together all bytes
        for byte in self.data:
            total += byteToInt(byte)

        # Only keep the last byte
        total = total & 0xFF

        return intToByte(0xFF - total)

    def verify(self):
        """
        verify: 1 byte -> boolean

        verify checksums the frame, adds the expected checksum, and 
        determines whether the result is correct. The result should 
        be 0xFF.
        """
        total = 0
        # Add together all bytes
        for byte in self.data:
            total += byteToInt(byte)
            
        #  total += byteToInt(self.data[-1])
        

        # Only keep low bits
        total &= 0xFF

        # Check result
        return total == 0xFF

    def len_bytes(self):
        """
        len_data: None -> (MSB, LSB) 16-bit integer length, two bytes

        len_bytes counts the number of bytes to be sent and encodes the 
        data length in two bytes, big-endian (most significant first).
        """
        count = len(self.data)
        return struct.pack("> h", count)

    def output(self):
        """
        output: None -> valid API frame (binary data)

        output will produce a valid API frame for transmission to an 
        XBee module.
        """
        # start is one byte long, length is two bytes
        # data is n bytes long (indicated by length)
        # chksum is one byte long
        data = self.len_bytes() + self.data + self.checksum()

        # Only run the escaoe process if it hasn't been already
        if self.escaped and len(self.raw_data) < 1:
            self.raw_data = Frame.escape(data)

        if self.escaped:
            data = self.raw_data

        # Never escape start byte
        return Frame.START_BYTE + data

    @staticmethod
    def escape(data):
        """
        escape: byte string -> byte string

        When a 'special' byte is encountered in the given data string,
        it is preceded by an escape byte and XORed with 0x20.
        """

        escaped_data = b""
        for byte in data:
            if intToByte(byteToInt(byte)) in Frame.ESCAPE_BYTES:
                escaped_data += Frame.ESCAPE_BYTE
                escaped_data += intToByte(0x20 ^ byteToInt(byte))
            else:
                escaped_data += intToByte(byteToInt(byte))

        return escaped_data

    def fill(self, byte):
        """
        fill: byte -> None

        Adds the given raw byte to this APIFrame. If this APIFrame is marked
        as escaped and this byte is an escape byte, the next byte in a call
        to fill() will be unescaped.
        """

        if self._unescape_next_byte:
            byte = intToByte(byteToInt(byte) ^ 0x20)
            self._unescape_next_byte = False
        elif self.escaped and byte == Frame.ESCAPE_BYTE:
            self._unescape_next_byte = True
            return
        self.raw_data += intToByte(byteToInt(byte))

    def remaining_bytes(self):
        remaining = 3

        if len(self.raw_data) >= 3:
            # First two bytes are the length of the data
            raw_len = self.raw_data[0:2]
            #  print('raw_len: %r' % raw_len)
            data_len = struct.unpack("> h", raw_len)[0]
#             print('data_len: %d' % data_len)

            remaining += data_len

            # Don't forget the checksum
            #  remaining += 1

        return remaining - len(self.raw_data)

    def parse(self):
        """
        parse: None -> None

        Given a valid API frame, parse extracts the data contained
        inside it and verifies it against its checksum
        """
        if len(self.raw_data) < 3:
            print('ValueError')
            raise ValueError(
                "parse() may only be called on a " +
                "frame containing at least 3 bytes of raw data (see fill())")

        # First two bytes are the length of the data
        raw_len = self.raw_data[0:2]

        # Unpack it
        data_len = struct.unpack("> h", raw_len)[0]

        # Read the data
        data = self.raw_data[2:3 + data_len]
#         chksum = self.raw_data[-1]

        # Checksum check
        self.data = data
        if not self.verify():
            print('Bad checksum')
            raise ValueError("Invalid checksum")
        return data
