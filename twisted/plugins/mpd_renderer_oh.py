'''
Created on 6 janv. 2015

@author: babe
'''
from twisted.application.service import ServiceMaker

urenderer = ServiceMaker(
    "ohRenderer_mpd",
    "mpdrenderer.tap_oh",
    "An OpenHome mpd renderer",
    "ohRenderer_mpd")
