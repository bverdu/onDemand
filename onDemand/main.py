# encoding: utf-8
'''
Created on 17 avr. 2015

@author: Bertrand Verdu
'''
# import importlib
import logging

from twisted.application import service
from util import Subservices

logging.basicConfig(level=logging.INFO)


def makeService(args):
    '''
    Create and launch main service
    '''
    return Main(args['datadir'])


class Main(service.MultiService):
    '''
    Main Service
    '''

    def __init__(self, path):
        super(Main, self).__init__()
        self.ui = None
        self.manager = Subservices(self, path)
        for service in self.manager.get_services():
            self.add_service(service)

    def add_service(self, service):
        self.services.append(service)
        service.parent = self
#         if hasattr(service, 'register_art_url'):
#             mainService.register_art_url = sub_service.register_art_url

    def remove_service(self, service_name):
        index = None
        for i, service in enumerate(self.services):
            if service.name == service_name:
                index = i
                break
        if index:
            del self.services[i]
