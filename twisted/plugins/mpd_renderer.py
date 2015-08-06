'''
Created on 6 janv. 2015

@author: babe
'''
from twisted.application.service import ServiceMaker

urenderer = ServiceMaker(
    "UpnpRenderer_mpd",
    "mpdrenderer.tap",
    "An Upnp mpd renderer",
    "UpnpRenderer_mpd")
