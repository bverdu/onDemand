'''
Created on 6 janv. 2015

@author: babe
'''
from twisted.application.service import ServiceMaker

urenderer = ServiceMaker(
    "onDemand",
    "onDemand.tap",
    "An onDemand Device",
    "onDemand")
