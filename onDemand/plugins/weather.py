# encoding: utf-8
'''
Created on 23 sept. 2015

@author: Bertrand Verdu
'''
import json
import time
from collections import OrderedDict
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.internet import reactor, defer
from onDemand.util.data import remove_unicode


CONDITION = 'http://api.wunderground.com/api/{api_key}' +\
            '/geolookup/conditions/lang:{lang}/q/{location}.json'
FORECAST = 'http://api.wunderground.com/api/{api_key}' +\
    '/forecast/lang:{lang}/q/{location}.json'
# conv = {'ë': 'e', '-': '_', 'ê': 'e'}


class Weather(object):
    '''
    classdocs
    '''

    def __init__(self, location='France/Paris', language='FR',
                 key=''):
        '''
        Constructor
        '''
        self.location = location
        self.current = {}
        self.forecast = {}
        self.subscriptions = []
        self.language = language
        self.key = key
        self.agent = Agent(reactor)
        self.headers = Headers({'User-Agent': ['onDemand Weather Plugin']})

#     def format_location(self, location):
#         l = ''
#         try:
#             for char in location:
#                 if char in u'-ëïïîöôéèà&!§,?:êüûâä':
#                     #                 print(char.encode('utf-8'))
#                     #                 print(conv(char.encode('utf-8')))
#                     l += conv(char.decode('utf-8'))
#                 else:
#                     l += char
#         except UnicodeDecodeError:
#             print('cas 2')
#             l = ''
#             for char in location.decode('utf-8'):
#                 if char in u'-ëïïîöôéèà&!§,?:êüûâä':
#                     #                 print(char.encode('utf-8'))
#                     #                 print(conv(char.encode('utf-8')))
#                     l += conv(char)
#                 else:
#                     l += char
#         return bytes(l)

    def get_current(self, location='', callback=None):
        if location == '':
            location = self.location
        location = remove_unicode(location)
        print(location[-1])

        def got_current(res, loc):
            print('got result for: %s' % loc)
            res.update({'timestamp': time.time()})
            self.current.update({loc: res})
            return res
        if location in self.subscriptions and callback:
            reactor.callLater(  # @UndefinedVariable
                305, self.get_current, *(location, callback))
#         location = self.format_location(location)
        request = CONDITION.format(
            api_key=self.key, lang=self.language, location=location)
        print('%s ? %s' % (location, self.current))
        if location in self.current:
            print('cached')
            if time.time() - self.current[location]['timestamp'] < 300:
                print('cached result')
                if callback:
                    callback(self.current[location])
                    return
                return defer.succeed(self.current[location])
        d = self.agent.request('GET', request, self.headers, None)
        d.addCallback(readBody)
        d.addCallback(self.extract, True)
        d.addCallback(got_current, location)
        if callback:
            d.addCallback(callback)
            return
        return d

    def get_forecast(self, location):
        print('forecast_request!')

        def got_forecast(res, loc):
            print('got forecast: %s' % res)
            res.update({'timestamp': time.time()})
            self.forecast.update({loc: res})
            return res
        location = remove_unicode(location)
#         location = self.format_location(location)
        request = FORECAST.format(
            api_key=self.key, lang=self.language, location=location)
        if location in self.forecast:
            if time.time() - self.forecast[location]['timestamp'] < 300:
                return defer.succeed(self.forecast[self.location])
        d = self.agent.request('GET', request, self.headers, None)
        d.addCallback(readBody)
        d.addCallback(self.extract, False)
        d.addCallback(got_forecast, location)
        return d

    def extract(self, jsondata, current=True):
        res = json.loads(jsondata)
        try:
            if current:
                self.current.update(
                    {self.location:
                        {'temp': res['current_observation']['temp_c'],
                         'humidity': res['current_observation'][
                            'relative_humidity'],
                         'weather': res['current_observation']['weather'],
                         'wind': res['current_observation']['wind_kph'],
                         'icon': res['current_observation']['icon_url'].split(
                            '/')[-1][:-4]}})
                return self.current[self.location]
            else:
                dic = OrderedDict()
                for day in res['forecast']['txt_forecast']['forecastday']:
                    dic.update({day['title']:
                                {'icon': day['icon_url'].split('/')[-1][:-4],
                                 'message': day['fcttext_metric']}})
                self.forecast.update({self.location: dic})
                return dic
        except KeyError:
            return {}

    def subscribe(self, location, callback):
        if location not in self.subscriptions:
            self.subscriptions.append(location)
        self.get_current(location, callback)

    def unsubscribe(self, location):
        self.subscriptions.remove(location)


# def conv(char):
#     if char in u'ëêéè':
#         return 'e'
#     elif char in u'ïî':
#         return 'i'
#     elif char in u':;,.!§%$£=+-+°&~#"':
#         return '_'
#     elif char in u'öô':
#         return 'o'
#     elif char in u'äâ':
#         return 'a'
#     elif char in u'üûù':
#         return 'u'

if __name__ == '__main__':

    try:
        from onDemand.test_data import wu_apikey
    except:
        wu_apikey = 'PUT WEATHER UNDERGROUND API KEY HERE'

    def show(res):
        for k, v in res.iteritems():
            #             if k == 'current_observation':
            #                 for key, val in v.iteritems():
            #                     print('%s : %s' % (key, val))
            print('%s:  %s' % (k, v))

    def test():
        w = Weather(u'France/Aspres_sur_Buëch', key=wu_apikey)
        d = w.get_current()
        d.addCallback(show)
        reactor.callLater(3, reactor.stop)  # @UndefinedVariable

    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
