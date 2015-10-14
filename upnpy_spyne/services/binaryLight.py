'''
Created on 10 avr. 2015

@author: Bertrand Verdu
'''
from spyne.application import Application
from spyne.protocol.soap import Soap11
from upnpy_spyne.services.templates.switchpower import SwitchPower


class BinaryLight(object):
    '''
    classdocs
    '''

    def __init__(self, client):
        def _map_context(ctx):
            ctx.udc = UserDefinedContext(client)
        self.app = Application([SwitchPower],
                               tns=SwitchPower.tns,
                               in_protocol=Soap11(validator='lxml'),
                               out_protocol=Soap11())
        self.app.event_manager.add_listener('method_call', _map_context)


class UserDefinedContext(object):

    def __init__(self, client):
        self.client = client

if __name__ == '__main__':
    import sys
    from twisted.python import log
    from twisted.internet import reactor
    from spyne.server.twisted import TwistedWebResource
    from twisted.web.server import Site
    from onDemand.plugins import he
#     logging.basicConfig(level=logging.DEBUG)
#     logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    log.startLogging(sys.stdout)
    client = he.HE_factory('16234266', 0)
    edp = he.HE_endpoint(reactor, 1, 0x04, 0)
    edp.connect(client)
    app = BinaryLight(client)
    resource = TwistedWebResource(app.app)
    site = Site(resource)
    reactor.listenTCP(8000, site, interface='0.0.0.0')  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
