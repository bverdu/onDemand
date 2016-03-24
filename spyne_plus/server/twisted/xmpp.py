# encoding: utf-8
from __future__ import absolute_import
'''
Created on 17 juin 2015

@author: Bertrand Verdu
'''

import logging


from twisted.logger import Logger
from twisted.internet import defer
from twisted.internet.defer import Deferred


from spyne import MethodContext
from spyne.model import ComplexModelBase
from spyne.server import ServerBase

logging.basicConfig(level=logging.INFO)


UPNP_ERROR = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'\
    + ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" >'\
    + '<s:Header mustUnderstand="1">'\
    + '<uc xmlns="urn:schemas-upnp-org:cloud-1-0" serviceId="%s"/>'\
    + '</s:Header><s:Body><s:Fault><faultcode>%s</faultcode>'\
    + '<faultstring>UpnPError</faultstring><detail>'\
    + '<UPnPError xmlns="urn:schemas-upnp-org:control-1-0">'\
    + '<errorCode>500</errorCode>'\
    + '<errorDescription>%s</errorDescription>'\
    + '</UPnPError></detail>'\
    + '</s:Fault></s:Body></s:Envelope>'
log = Logger()


class TwistedXMPPApp(ServerBase):
    """A server transport that exposes the application
        as a twisted words jabber soap transport.
    """
    transport = 'http://jabber.org/protocol/soap'

    def __init__(self, app):

        super(TwistedXMPPApp, self).__init__(app)
        self._wsdl = None

    def handle_rpc(self, element, serviceId):

        log.debug('call handle_rpc')

        def _cb_deferred(ret, ctx):
            #             print('deferred: %s' % str(ret))
            log.debug('deferred result: %s' % ret.__repr__())
#             om = ctx.descriptor.out_message
#             if ((not issubclass(om, ComplexModelBase)) or
#                     len(om._type_info) <= 1):
#                 ctx.out_object = (ret.encode('utf-8'))
#             else:
#                 ctx.out_object = (r.decode('utf-8') for r in ret)
            ctx.out_object = [ret.encode('utf-8')]
            self.get_out_string(ctx)
            return ctx.out_string

        def _eb_deferred(error, ctx):
            ctx.out_error = error.value
            if isinstance(ctx.out_string, list):
                log.error(''.join(ctx.out_string))
            else:
                log.error(ctx.out_string)
            return ctx.out_string

        initial_ctx = MethodContext(self, MethodContext.SERVER)
        initial_ctx.in_string = element
        for ctx in self.generate_contexts(initial_ctx, 'utf8'):
            # This is standard boilerplate for invoking services.
            if ctx.in_error:
                print(ctx)
            try:
                self.get_in_object(ctx)
            except AttributeError:
                log.error(ctx.out_string)
                return defer.succeed(UPNP_ERROR % (serviceId,
                                                   ctx.in_error.faultcode,
                                                   ctx.in_error.faultstring))
            if ctx.in_error:
                self.get_out_string(ctx)
                log.error(''.join(ctx.out_string))
                continue
            self.get_out_object(ctx)
            if ctx.out_error:
                self.get_out_string(ctx)
                log.error(''.join(ctx.out_string))
                continue
            ret = ctx.out_object[0]
#             print(ret)
            if isinstance(ret, Deferred):
                if ret.called:
                    return defer.succeed(_cb_deferred(ret.result, ctx))
                log.debug('result type async/deferred')
                ret.addCallback(_cb_deferred, ctx)
                ret.addErrback(_eb_deferred, ctx)
                return ret
            else:
                self.get_out_string(ctx)
#                 print('no deferred: %s' % ctx.out_string)
                log.debug('result type sync')
                return defer.succeed(ctx.out_string)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne_plus.protocol.xml').setLevel(logging.DEBUG)
    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)
    from upnpy_spyne.devices.ohSource import Source
    from onDemand.plugins.mpd import get_Mpd
    from twisted.internet.task import react
    from upnpy_spyne.xmpp import XmppService

    def main(reactor):
        s = XmppService(reactor, device)
        s.startService()
        return s.finished

    n, f = get_Mpd(addr='192.168.0.9')
    device = Source(
        'test xmpp renderer',
        f,
        '/home/babe/Projets/eclipse/onDemand/data/')
    react(main)
