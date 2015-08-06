from twisted.application.service import ServiceMaker

urenderer = ServiceMaker(
    "UpnpRenderer",
    "pyrenderer.tap",
    "An Upnp renderer",
    "UpnpRenderer")
