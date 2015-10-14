'''
Created on 22 janv. 2015

@author: Bertrand Verdu
'''
from twisted.python import log
from upnpy_spyne.services import Service


# class Product(product_template):
class Product(Service):
    version = (1, 0)
    serviceType = "urn:av-openhome-org:service:Product:1"
    serviceId = "urn:av-openhome-org:serviceId:Product"
    serviceUrl = "PR"
#     frienlyName = "Oh_Product"
    type = 'Product'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(Product, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.productroom = self.client.room
        self.active = self.client.active_source
        self.index = self.client.sourceindex
        self.sources = self.client.sources
        self.sourcexml = self.client.sourcexml
        self.sourcecount = len(self.sources)
        self.attributes = 'Info Time Volume'
        self.client.oh_product_event = self.upnp_event
        self.wait_connection

    def wait_connection(self):
        try:
            self.manufacturername,\
                self.manufacturerinfo,\
                self.manufacturerurl, \
                self.manufacturerimageurl = self.client.manufacturer()
            self.modelname,\
                self.modelinfo,\
                self.modelurl,\
                self.modelimageurl = self.client.model()
        except TypeError:
            reactor.callLater(1, self.wait_connection)  # @UndefinedVariable

    def upnp_event(self, var, evt):
        log.msg('Product event val: %s evt:%s' % (var, evt))
        setattr(self, var, evt)
