'''
Created on 10 nov. 2014

@author: Bertrand Verdu
'''
import sys
from zope.interface import provider
from twisted.logger import globalLogPublisher,\
    LogLevelFilterPredicate,\
    FilteringLogObserver,\
    LogLevel,\
    ILogObserver,\
    formatTime, \
    timeFormatRFC3339, \
    formatEventAsClassicLogText


@provider(ILogObserver)
class stdoutFileLogObserver(object):
    """
    Log observer that writes event to stdout or stderr.
    """

    def __init__(self, timeFormat=timeFormatRFC3339):
        """
        @param formatEvent: A callable that formats an event.
        @type formatEvent: L{callable} that takes an C{event} argument and
            returns a formatted event as L{unicode}.
        """
        self._encoding = "utf-8"
        self.timeFormat = timeFormat
        self._err = sys.stderr
        self._out = sys.stdout

    def __call__(self, event):
        """
        Write event to file.

        @param event: An event.
        @type event: L{dict}
        """
        text = formatEventAsClassicLogText(
            event, formatTime=lambda e: formatTime(e, self.timeFormat))
        if text is None:
            text = u""

        if "log_failure" in event:
            try:
                traceback = event["log_failure"].getTraceback()
            except Exception:
                traceback = u"(UNABLE TO OBTAIN TRACEBACK FROM EVENT)\n"
            text = u"\n".join((text, traceback))

        if self._encoding is not None:
            text = text.encode(self._encoding)

        if text:
            if event['log_level'] > LogLevel.warn:
                self._err.write(text)
                self._err.flush()
            else:
                self._out.write(text)
                self._out.flush()


def getLogger(level):

    loglevel = getattr(LogLevel, level)
    filter_ = LogLevelFilterPredicate(defaultLogLevel=loglevel)
    if loglevel > LogLevel.debug:
        filter_.setLogLevelForNamespace('stdout', LogLevel.warn)
    observer = FilteringLogObserver(stdoutFileLogObserver(), [filter_])
#     observer = FilteringLogObserver(globalLogPublisher, [filter])
#     log = Logger()

#     globalLogBeginner.beginLoggingTo([observer])
    globalLogPublisher.addObserver(observer)
    return lambda event: None


def debug():
    return getLogger('debug')


def info():
    return getLogger('info')


def warn():
    return getLogger('warn')


def error():
    return getLogger('error')


def critical():
    return getLogger('critical')
