# encoding: utf-8
'''
Created on 17 avr. 2015

@author: Bertrand Verdu
'''
#  import logging
import config
from twisted.application import service
from utils import load_yaml
from util.main import get_subservices

# logging.basicConfig(level=logging.INFO)


def makeService(args):
    '''
    Create and launch main service
    '''
    mainService = service.MultiService()
    load_yaml(args['datadir'])
    services = get_subservices()()
    mainService.config = config
    for sub_service in services:
        mainService.services.append(sub_service)
        sub_service.parent = mainService
        if hasattr(sub_service, 'register_art_url'):
            mainService.register_art_url = sub_service.register_art_url

    return mainService
