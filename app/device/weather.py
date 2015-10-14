# encoding: utf-8
'''
Created on 23 sept. 2015

@author: Bertrand Verdu
'''
import os
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty, DictProperty, \
    NumericProperty
from kivy.lang import Builder
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout

Builder.load_file(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'weather.kv'))


class WeatherBox(RelativeLayout):
    location = StringProperty('')
    current = StringProperty('')
    weather_data = {}
    forecast_data = None
    weather_api = None
    weather = None
    forecast = None

    def __init__(self, **kwargs):
        super(WeatherBox, self).__init__(**kwargs)
        if 'api' in kwargs:
            self.weather_api = kwargs['api']
        print('?????%s' % self.location)
        print(kwargs)
        self.show_weather()

    def on_location(self, inst, value):
        print('###############%s############' % value)
        if value == '':
            return
        if self.weather_api:
            if self.current != '':
                self.weather_api.unsubscribe(self.current)
            if value != self.current:
                self.weather_api.subscribe(value, self.set_current)
                self.current = value
#             d = self.weather_api.get_current(value.decode('utf-8'))
#             d.addCallback(self.set_current)

    def set_current(self, dic):
        self.weather_data = dic
        if self.weather:
            self.weather.set_current(dic)
        else:
            self.show_weather()

    def show_forecast(self):
        self.forecast = Forecast()
        if self.weather_api:
            d = self.weather_api.get_forecast(self.current)
            d.addCallback(self.forecast.set_forecast)
        self.clear_widgets()
        self.add_widget(self.forecast)
        self.weather = None

    def show_weather(self):

        self.weather = Weather(data=self.weather_data)
        self.clear_widgets()
        self.add_widget(self.weather)
        self.forecast = None


class Weather(Button):
    '''
    classdocs
    '''
    weather = StringProperty('Sunny')
    description = StringProperty()
    temp = StringProperty('28°C', rebind=True)
    wind = StringProperty()
    humidity = StringProperty()
    icon = StringProperty('data/graphics/meteo/sunny.png')
    data = False
    weather_api = ObjectProperty()
    forecast = DictProperty()

    def __init__(self, **kwargs):
        super(Weather, self).__init__(**kwargs)
        self.set_current(kwargs['data'])

    def set_current(self, dic):
        print(dic)
        try:
            print('1')
            self.weather = dic['weather'].encode('utf-8')
#             print(bytes(dic['temp']) + bytes(' °C'))
            print('2')
            self.temp = bytes(dic['temp']) + bytes(' °C')
            print('3')
            self.wind = bytes(dic['wind']) + ' km/h'
            print('4')
            self.humidity = bytes(dic['humidity'])
            print('5')
            self.icon = 'data/graphics/meteo/' + bytes(dic['icon']) + '.png'
        except KeyError:
            print('bad data :%s' % dic)
        except Exception as err:
            print('!!!!!!!!! %s' % err)

    def set_forecast(self, dic):
        print('frc result: %s' % dic)
        self.forecast = dic


class Forecast(BoxLayout):

    def set_forecast(self, value):
        d = []
        for day, data in value.iteritems():
            n = []
            if day == 'timestamp':
                continue
            if len(day.split()) > 1:
                print('night data: %s' % data)
                txt = ''
                temp = ''
                icon = ''
                if 'message' in data:
                    t = data['message'].split('.')
                    txt = t[0]
                    temp = t[1].split(':')[1].strip()
                if 'icon' in data:
                    icon = 'data/graphics/meteo/' + \
                        bytes(data['icon']) + '.png'
                n = [day.capitalize(), temp, txt, icon]
                b = ForecastDay(day=d, night=n)
                self.ids.forecast_box.add_widget(b)
                d = []
            else:
                print('day_data: %s' % data)
                if 'message' in data:
                    t = data['message'].split('.')
                    txt = t[0]
                    for i in t[1:]:
                        if len(i.split(':')) > 1:
                            temp = i.split(':')[1].strip()
                            break
                        else:
                            txt += '.' + i
                if 'icon' in data:
                    icon = 'data/graphics/meteo/' + \
                        bytes(data['icon']) + '.png'
                d = [day.capitalize(), temp, txt, icon]
                print(icon)


class ForecastDay(Button):
    title = StringProperty()
    txt = StringProperty()
    icon = StringProperty()
    temp = StringProperty()
    txt_template = '[size=%d]%s[/size]'
    is_day = True

    def __init__(self, **kwargs):
        super(ForecastDay, self).__init__(**kwargs)
        self.day = kwargs['day']
        self.night = kwargs['night']
        self.switch(True)

    def switch(self, init=False):
        if self.is_day and not init:
            self.title, self.temp, txt, self.icon = self.night
            size = set_font_size(txt)
            self.txt = self.txt_template % (size, txt)
            self.is_day = False
        else:
            self.title, self.temp, txt, self.icon = self.day
            size = set_font_size(txt)
            self.txt = self.txt_template % (size, txt)
            self.is_day = True


def set_font_size(text):
    if len(text) > 40:
        return 10
    elif len(text) > 20:
        return 12
    else:
        return 16

if __name__ == '__main__':
    root = Weather()
    window = root.run()
