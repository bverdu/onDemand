# encoding: utf-8
'''
Created on 1 juin 2016

@author: Bertrand Verdu
'''
from collections import OrderedDict
from twisted.logger import Logger
from twisted.internet import defer, reactor, task
from txthings.coap import Message, GET, PUT, POST, responses

SUCCESS_CODES = [i for i in range(64, 95)]

log = Logger()


class Sensor(object):
    '''
    classdocs
    '''

    def __init__(self, agent, params, eventhandler=None, poll=0):
        '''
        Constructor
        '''
        self.name = params['name']
        self.agent = agent
        self.datatype = params['datatype']
        self.path = params['path']
        self.remote = params['remote']
        self.unit = params['unit']
        self.cache = None
        self.timeout = None
        self.previous = None
        self.observe = poll
        if eventhandler:
            self.eventhandler = [eventhandler]
            d = task.deferLater(reactor, 1, self.get, True)
            d.addCallback(self.event)
        else:
            self.eventhandler = []

    def observe(self, handler):
        self.eventhandler.append(handler)
        return self.get(True)

    def clear_cache(self):
        log.debug('cache cleared')
        self.cache = None
        self.timeout = None

    def respond(self, data, check=False, obs=False):

        if data.code in SUCCESS_CODES:
            if check:
                #  log.debug(self.previous)
                if self.previous:
                    if data.payload == self.previous:
                        return
            timeout = 60
            resp = {'value': data.payload,
                    'status': ''.join(responses[data.code].split()[1:]),
                    'datatype': self.datatype,
                    'unit': self.unit}
            for opt in data.opt.optionList():
                if opt.number == 14:  # Max age
                    timeout = int(opt.value)
                    break
                # log.debug("option %d: %r" % (opt.number, opt.value))
            self.cache = resp
            self.previous = resp['value']
            if self.timeout:
                self.timeout.cancel()
            self.timeout = reactor.callLater(timeout,  # @UndefinedVariable
                                             self.clear_cache)
            if obs:
                r = {'obs': self.observable}
                r.update(resp)
                return r
            return resp
        else:
            return {'status': 'Error',
                    'code': ''.join(responses[data.code].split()[1:])}

    def receive_event(self, data):
        self.event(self.respond(data))

    def event(self, data, poll=0):
        if poll > 0:
            d = task.deferLater(reactor, self.observe, self.get,
                                *(False, True))
            d.addCallback(self.event, self.observe)
        if not data:
            return
        if data['status'] != 'Content':
            log.error('Error in Get methode: %s: %s' % (self.name,
                                                        data['code']))
            return
        r = {'name': self.name}
        r.update(data)
        for handler in self.eventhandler:
            handler(r)

    def check_observable(self, res):
        log.debug('check!')
        if res.opt.getOption(6):
            self.observable = True
        else:
            log.debug('not observable')
            self.observable = False
            if self.observe > 0:
                d = task.deferLater(reactor, self.observe, self.get,
                                    *(False, True))
                d.addCallback(self.event, self.observe)
        return res

    def get(self, observe=False, check=False):

        print(self.path)

        if self.cache and not observe:
            log.debug("cached")
            return defer.succeed(self.cache)
        else:
            query = Message(code=GET)
            query.opt.uri_path = self.path
            query.remote = self.remote
            if observe:
                query.opt.observe = 0x0
                d = self.agent.request(
                    query, observeCallback=self.receive_event)
                d.addCallback(self.check_observable)
            else:
                query.opt.observe = None
                d = self.agent.request(query)
        d.addCallback(self.respond, check, observe)
        return d


class Parameter(Sensor):
    '''
    classdocs
    '''

    def put(self, value):

        query = Message(code=PUT)
        query.opt.uri_path = self.path
        query.remote = self.remote
        query.payload = value
        d = self.agent.request(query)
        d.addCallback(self.respond)
        return d


class Actuator(Parameter):

    def post(self, value=None):

        query = Message(code=POST)
        print(self.path)
        query.opt.uri_path = self.path
        if value:
            query.payload = value
        query.remote = self.remote
        d = self.agent.request(query)
        d.addCallback(self.respond)
        return d


class Call_Proxy(object):

    def __init__(self, fct):
        self.command = fct
        print(fct)

    def get_value(self, dic):
        return dic['value']

    def __call__(self, *args):
        new_args = []
        for arg in args:
            if isinstance(arg, bool):
                new_args.append(str(int(arg)))
            else:
                new_args.append(str(arg))
        d = self.command(*new_args)
        d.addCallback(self.get_value)
        return d


class Composite(object):

    def __init__(self, endpoint, server):
        self.state_variables = []
        self.coap = server.coap
        self.actions = OrderedDict()
        self._actions = {}
        self.events = {}
        self.initialized = False
        self.port = int(endpoint.context.split(':')[-1])
        self.host = endpoint.context.split(']')[0].split('[')[-1]
        self.name = endpoint.name
        self.endpoint_type = endpoint.endpoint_type
        self.generate_service(endpoint)

    def update_config(self):
        log.error("update config in instance without parent")
        pass

    def __getattr__(self, attr):
        if attr.startswith('r_'):
            if attr in self._actions:
                return Call_Proxy(self._actions[attr])
        raise AttributeError

    def event(self, event):
        log.error("event!")
        if event['name'] in self.events:
            log.error("%s: %s" % (event['name'], event['value']))
            if self.events[event['name']][1] == 'boolean':
                setattr(self.parent.controller, self.events[
                    event['name']][0], bool(int(event['value'])))
            else:
                setattr(self.parent.controller, self.events[
                        event['name']][0], event['value'])

    def generate_service(self, endpoint):
        order = sorted(endpoint.link_format.keys())
        print(endpoint.link_format.keys())
        print(order)
        for link in order:
            val = endpoint.link_format[link]
#         for link, val in endpoint.link_format.items():
            unit = ''
            datatype = 'string'
            put = True
            if 'if' in val:
                if val['if'] == 'core.a':
                    unit = 'on/off'
                    datatype = 'boolean'
                    agent = Actuator
                elif val['if'] == 'core.p':
                    agent = Parameter
                elif val['if'] == 'core.s':
                    agent = Sensor
                else:
                    continue
            elif 'rt' in val:
                if val['rt'] == 'Control':
                    agent = Actuator
                    if 'PUT' not in val['title']:
                        unit = 'on/off'
                        datatype = 'boolean'
                    else:
                        unit = val['rt']
                else:
                    unit = val['rt']
                    agent = Sensor
            else:
                continue
            var = val['title'].split(':')[0].replace(' ', '_').replace(
                '(', '').replace(')', '')
            params = {'remote': (self.host, self.port,),
                      'name': var,
                      'path': link[1:].split('/'),
                      'unit': unit,
                      'datatype': datatype}
            instance = agent(self.coap, params, self.event)
#             var = link[1:].split('/')[-1]
#             var = val['title'] + " (" + link + ")"

            if 'obs' in val:
                self.state_variables.append((var, datatype,
                                             None, True))
                self.events[var] = (var.lower(), datatype,)
            else:
                self.state_variables.append((var, datatype))
            if hasattr(instance, 'get'):
                self.actions.update({'Get_' + var:
                                     [(var + "_result",
                                       "out",
                                       var)]})
                self._actions['r_Get_' + var] = instance.get
            if hasattr(instance, 'put') and put:
                self.actions.update({'Set_' + var:
                                     [(var + "_val",
                                       "in",
                                       var)]})
                self._actions['r_Set_' + var] = instance.put
            if hasattr(instance, 'post'):
                self.actions.update({'Toggle_' + var:
                                     [(var + "_result",
                                       "out",
                                       var)]})
                self._actions['r_Toggle_' + var] = instance.post
        self.initialized = True
        self.update_config()


if __name__ == '__main__':

    import sys
    from txthings.coap import Coap
    import txthings.resource as resource
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    def show(res):
        log.debug('; '.join([':'.join(t) for t in res.items()]))
        if 'value' in res:
            return res['value']
        return res['code']

    def get(agent, obs=False):
        d = agent.get(obs)
        d.addCallback(show)

    def put(value, agent):
        d = agent.put(value)
        d.addCallback(show)

    def post(agent):
        d = agent.post()
        d.addCallback(show)

    def test(agent):
        d = agent.get()
        d.addCallback(show)
        d.addCallback(lambda val: '0' if val == '1' else '1')
        d.addCallback(put, agent)

    resource = resource.Endpoint(None)
    protocol = Coap(resource)
    params = {'remote': (b'fd42:1:2108:0:212:4b00:79b:f04', 5683),
              'name': 'test',
              'path': ['sen', 'bar', 'pres'],
              'unit': 'P',
              'datatype': 'string'}

    agent = Actuator(protocol, params, show, 0)
    reactor.listenUDP(0, protocol, "::0")  # @UndefinedVariable
    reactor.callLater(2, get, agent)  # @UndefinedVariable
#     reactor.callLater(8, post, agent)  # @UndefinedVariable
    reactor.callLater(15, test, agent)  # @UndefinedVariable
#     reactor.callWhenRunning(post, agent)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
