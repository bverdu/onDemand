# encoding: utf-8

import sys
import smbus
from twisted.internet import stdio, task
from twisted.protocols import basic
from twisted.python import log
# for RPI version 1, use "bus = smbus.SMBus(0)"
fake = True

if not fake:
    bus = smbus.SMBus(1)

# This is the address we setup in the Arduino Program
address = 0x04


def write_block(value):
    if not fake:
        bus.write_i2c_block_data(address, value[0], value[1:])
    else:
        log.msg('send %s to %s' % (value, address))


def read_block():
    if not fake:
        try:
            number = bus.read_i2c_block_data(address, 255, 10)
        except IOError:
            return '0000000000'
        else:
            return ''.join([chr(code) for code in number])
    else:
        return '1234567801'


def read(inpt):
    number = read_block()
    if number != '0000000000':
        inpt.transport.write(
            '\nArduino: Hey RPI, I received this: %s\n' % number)
        inpt.transport.write('>>> ')


def main():
    inpt = KbInput()
    stdio.StandardIO(inpt)
    from twisted.internet import reactor
    log.startLogging(sys.stdout)
    l = task.LoopingCall(read, inpt)
    if fake:
        l.start(20)
    else:
        l.start(0.2)
    reactor.run()


class KbInput(basic.LineReceiver):
    from os import linesep as delimiter

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        t = []
        if len(line) < 11:
            for n in line:
                t.append(ord(n))
            write_block(t)
        self.transport.write(
            "RPI: Hi Arduino, I sent you %s\n"
            % ''.join([chr(code) for code in t]))
        self.transport.write('>>> ')

if __name__ == '__main__':
    main()
