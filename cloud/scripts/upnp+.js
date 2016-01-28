/*global $, jQuery*/
/*global define*/
/*jslint devel: true*/
/*jslint bitwise: true*/
define(function (require) {
    "use strict";
    var $ = require('jquery'),
        strophe = require('strophe'),
        bootstrap = require('bootstrap'),
        Mustache = require('mustache'),
        Strophe = strophe.Strophe,
        $pres = strophe.$pres,
        $iq = strophe.$iq,
        $msg = strophe.$msg,
        $build = strophe.$build,
        b64_sha1 = strophe.SHA1.b64_sha1,
        BOSH_SERVICE = 'http://bosh.metajack.im:5280/xmpp-httpbind',
        uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(
            /[xy]/g,
            function (c) {
                var r = Math.random() * 16 | 0,
                    v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            }
        ),
        connection = null,
        userjid = null,
        fulljid = null,
        subscriptions = {},
        service_id = 0,
        rindex = 0,
        devices = [],
        devices_obj = {},
        identity = { category: 'client', name: 'LazyTech_Demo', type: 'web' },
        empty_features = [
            "http://jabber.org/protocol/caps",
		    "http://jabber.org/protocol/disco#info",
		    "http://jabber.org/protocol/disco#items"
        ],
        empty_ver = b64_sha1(empty_features.join()),
        features = empty_features.slice(),
        my_ver = empty_ver,
        /* PEP constants */
        NS_CAPS = "http://jabber.org/protocol/caps",
        NS_DISCO_INFO = "http://jabber.org/protocol/disco#info",
        NS_PUBSUB = "http://jabber.org/protocol/pubsub",
        NS_PUBSUB_EVENT = NS_PUBSUB + "#event";
        

    function log(msg) {
        $('#log').append('<div></div>').append(document.createTextNode(msg));
    }
    
    // util function to create remote call functions
    
    function UpnpControl(addr, svc, name, args) {
        var iq = $iq({to: addr, type: 'set'})
            .c('s:Envelope',
                {'xmlns:s': 'http://schemas.xmlsoap.org/soap/envelope/',
                    's:encodingStyle': 'http://schemas.xmlsoap.org/soap/encoding/'})
            .c('s:Header', {mustUnderstand: '1'})
            .c('uc', {xmlns: 'urn:schemas-upnp-org:cloud-1-0',
                     serviceId: svc.serviceId})
            .up().up().c('s:Body')
            .c('u:' + name, {'xmlns:u': svc.serviceType}),
            param;
        // log(args)
        for (param in args) {
            if (args.hasOwnProperty(param)) {
                iq.c(param, null, args[param]);
            }
        }
        return iq;
    }
    // utility functions
    
    function isTrue(value) {
        if (typeof (value) === 'string') {
            value = value.toLowerCase();
        }
        switch (value) {
        case true:
        case "true":
        case 1:
        case "1":
        case "on":
        case "yes":
            return true;
        default:
            return false;
        }
    }
    function handle_event(field) {
        return function (value) {
            $('#' + field).val(value);
            console.log('txt');
        };
    }
    function handle_boolean_event(off_input, on_input) {
        var on_btn = "#" + on_input,
            off_btn = "#" + off_input;
        return function (value) {
            if (isTrue(value)) {
                log('True');
                $(on_btn).removeClass('btn-default');
                $(on_btn).addClass('btn-primary');
                $(off_btn).removeClass('btn-primary');
                $(off_btn).addClass('btn-default');
            } else {
                log('False');
                $(off_btn).removeClass('btn-default');
                $(off_btn).addClass('btn-primary');
                $(on_btn).removeClass('btn-primary');
                $(on_btn).addClass('btn-default');
            }
            console.log('bool');
        };
    }
    function handle_result(fields) {
        var i, off_btn, on_btn;
        return function (res) {
            //console.log(res);
            if (res.childNodes.length < 1) {
                return true;
            }
            var responses = res.childNodes[0].childNodes[0].childNodes[0].childNodes;
            for (i = 0; i < responses.length; i += 1) {
                log(fields[responses[i].nodeName] + ' --> ' + responses[i].childNodes[0].nodeValue);
                if ($("#" + fields[responses[i].nodeName]).attr('type') === 'text') {
                    $("#" + fields[responses[i].nodeName]).val(responses[i].childNodes[0].nodeValue);
                } else {
                    console.log('yyyy');
                    off_btn = "#" + fields[responses[i].nodeName];
                    on_btn = off_btn.slice(0, off_btn.length - 1)
                        + (Number(off_btn[off_btn.length - 1]) + 1).toString();
                    log(off_btn);
                    log(on_btn);
                    if (isTrue(responses[i].childNodes[0].nodeValue)) {
                        $(on_btn).removeClass('btn-default');
                        $(on_btn).addClass('btn-primary');
                        $(off_btn).removeClass('btn-primary');
                        $(off_btn).addClass('btn-default');
                    } else {
                        $(off_btn).removeClass('btn-default');
                        $(off_btn).addClass('btn-primary');
                        $(on_btn).removeClass('btn-primary');
                        $(on_btn).addClass('btn-default');
                    }
                }
            }
        };
            /*for (field in fields) {
                $('#' + fields[field]).val('test');
            }*/
            //console.log(res);
    }
    function process_event(eventitems) {
        var nodename = eventitems.attr('node'),
        //console.log(eventitems);
            item = eventitems.find('item').first(),
            i;
        item.find('property').each(function () {
            for (i = 0; i < subscriptions[nodename].length; i += 1) {
                if (this.firstChild.firstChild !== null) {
                    console.log(subscriptions[nodename][i]);
                    subscriptions[nodename][i](this.firstChild.firstChild.nodeValue);
                    log(nodename + ' --> ' + this.firstChild.firstChild.nodeValue);
                }
            }
        });
        
    }
    function process_events(events) {
        //console.log(events);
        events.each(function () {
            process_event($(this).find('items').first());
        });
    }
    
    function set_fct(f) {
        log(f);
    }
    function build_from_template(dev, dom_element, template) {
        
    }
    
    function build_genericDevice(dev, dom_element) {
        var name = $("<h2></h2>")
            .addClass('text-center')
            .append(document.createTextNode(dev.friendlyName)),
            frame = $("<div></div>")
            .addClass('col-md-12 bg-info pre-scrollable')
            .css({"padding": "5px", "border-radius": "8px",
                  "overflow-y": "auto", "margin-top": "10px"})
            .append(name),
            service, action, act, inpts, inpt, lbl, start_class, event, i, j,
            n, btn, outpts, boo, outpt, uid_str;
        for (service in dev.services) {
            if (dev.services.hasOwnProperty(service)) {
                frame.append("<hr>");
                frame.append($('<div></div>')
                             .addClass("col-md-12")
                             .append($("<h4>" + service + "</h4>")));
                for (action in dev.services[service].actions) {
                    if (dev.services[service].actions.hasOwnProperty(action)) {
                        act = $("<form></form>").addClass("form-inline col-md-11 pull-right");
                        if (dev.services[service].actions[action]['in'].length > 0) {
                            inpts = dev.services[service].actions[action]['in'];
                            inpt = $("<div></div").addClass('form-group col-md-12');
                            lbl = false;
                            start_class = " btn-primary";
                            event = false;
                            for (i = 0; i < inpts.length; i += 1) {
                                for (n in inpts[i]) {
                                    //log("event: " + inpts[i][n]);
                                    //act.append($("<span></span>").text(n));
                                    //console.log(dev.services[service].events);
                                    if (inpts[i].hasOwnProperty(n)) {
                                        if (dev.services[service]
                                                .events.hasOwnProperty(inpts[i][n])) {
                                            event = inpts[i][n];
                                        }
                                        service_id += 1;
                                        if (dev.services[service]
                                                .stateVariables[inpts[i][n]] === "boolean") {
                                            if (!lbl) {
                                                btn = $('<button></button>')
                                                    .addClass('btn btn-info col-md-6')
                                                    .attr({type: 'button'})
                                                    .text(action);
                                                //btn.data('service', dev.services[service]);
                                                inpt.append(btn);
                                                lbl = true;
                                            }
                                            rindex += 2;
                                            if (event) {
                                                log('registering input ' + event + ' for ' + action);
                                                dev.services[service]
                                                    .events[event].push(handle_boolean_event(
                                                        action + rindex.toString(),
                                                        action + (rindex + 1).toString()
                                                    ));
                                                start_class = "btn-default";
                                            }

                                            inpt.append($("<div></div>")
                                                        .css({"padding-left": "0",
                                                             "padding-right": "0"})
                                                        .addClass("col-md-6")
                                                        .append($("<div></div>")
                                                        .addClass("btn-group btn-group-justified")
                                                        .append($("<div></div>")
                                                                .addClass("btn-group")
                                                                .append($("<button></button>")
                                                                    .addClass(
                                                                "col-md-6 btn remote btn-primary"
                                                            )
                                                                    .attr({type: "button",
                                                                          "id": action + rindex.toString(),
                                                                          param: 'no'})
                                                                    .data({service: dev.services[service],
                                                                      action: action,
                                                                      param_name: n})
                                                                    .text('Off')))
                                                        .append($("<div></div>")
                                                                .addClass("btn-group")
                                                                .append($("<button></button>")
                                                                    .addClass("col-md-6 btn remote " + start_class)
                                                                    .attr({type: "button",
                                                                          "id": action + (rindex + 1).toString(),
                                                                          param: 'no'})
                                                                    .data({service: dev.services[service],
                                                                      action: action,
                                                                      param_name: n})
                                                                    .text('On')))));
                                        } else {
                                            if (!lbl) {
                                                lbl = $('<button></button>')
                                                    .addClass('btn remote btn-info')
                                                    .data({service: dev.services[service],
                                                        params: {},
                                                        callbacks: {}})
                                                    .attr({type: 'button',
                                                        style: "width: 50%",
                                                        param: 'yes'})
                                                    .text(action);
                                                inpt.append(lbl);
                                            }
                                            lbl.data('params')[n] = action + service_id.toString();
                                            inpt.append($("<input></input>").addClass("form-control")
                                                        .attr({type: 'text',
                                                               id: action + service_id.toString(),
                                                               placeholder: n,
                                                               style: 'width: 50%;'}));
                                        }
                                    }
                                }
                            }
                        } else {
                            inpt = null;
                        }
                        if (dev.services[service].actions[action].out.length > 0) {
                            outpts = dev.services[service].actions[action].out;
                            if (inpt === null) {
                                outpt = $("<div></div").addClass('form-group col-md-12');
                                lbl = false;
                                boo = false;
                                event = false;
                            }
                            for (j = 0; j < outpts.length; j += 1) {
                                event = false;
                                boo = false;
                                for (n in outpts[j]) {
                                    if (outpts[j].hasOwnProperty(n)) {
                                        if (dev.services[service].events
                                                .hasOwnProperty(outpts[j][n])) {
                                            event = outpts[j][n];
                                        }
                                        service_id += 1;
                                        if (inpt !== null) {
                                            inpt.append($("<input></input>").addClass("col-md-6")
                                                        .attr({type: 'text',
                                                               id: action + service_id.toString(),
                                                               placeholder: n,
                                                               style: "width: 50%",
                                                              disabled: true})
                                                        .prop('disabled', true));
                                        } else {
                                            if (!lbl) {
                                                lbl = $('<button></button>')
                                                        .addClass('btn remote btn-success col-md-6')
                                                        .data({service: dev.services[service],
                                                              callbacks: {}})
                                                        .attr({type: 'button',
                                                               style: "width: 50%",
                                                              param: 'yes'})
                                                        .text(action);
                                                outpt.append(lbl);
                                            }
                                            if (dev.services[service]
                                                    .stateVariables[
                                                        outpts[j][n]
                                                    ] === "boolean") {
                                                boo = true;
                                            }
                                            if (event) {
                                                log('registering output ' + event + ' for ' + action);
                                                if (boo) {
                                                    dev.services[service].events[event]
                                                        .push(handle_boolean_event(
                                                            action + service_id.toString(),
                                                            action + (service_id + 1).toString()
                                                        ));
                                                } else {
                                                    dev.services[service].events[event]
                                                        .push(handle_event(action + service_id.toString()));
                                                }
                                            }
                                            lbl.data('callbacks')[n] = action + service_id.toString();
                                            if (boo) {
                                                outpt.append($("<div></div>")
                                                            .css({"padding-left": "0",
                                                                 "padding-right": "0"})
                                                            .addClass("col-md-6")
                                                            .append($("<div></div>")
                                                            .addClass("btn-group btn-group-justified")
                                                            .append($("<div></div>")
                                                                    .addClass("btn-group")
                                                                    .append($("<button></button>")
                                                                        .addClass(
                                                                    "col-md-6 btn btn-primary"
                                                                )
                                                                        .attr({"id": action + service_id
                                                                               .toString()})
                                                                        .prop('disabled', true)
                                                                        .text('Off')))
                                                            .append($("<div></div>")
                                                                    .addClass("btn-group")
                                                                    .append($("<button></button>")
                                                                        .addClass("col-md-6 btn btn-default")
                                                                        .attr({"id": action + (
                                                                    service_id + 1
                                                                ).toString()}
                                                                             )
                                                                        .prop('disabled', true)
                                                                        .text('On')))));
                                                service_id += 1;

                                            } else {
                                                outpt.append($("<input></input>").addClass("form-control")
                                                            .attr({type: 'text',
                                                                   id: action + service_id.toString(),
                                                                   placeholder: n,
                                                                   style: "width: 50%"})
                                                             .prop('disabled', true));
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            outpt = null;
                        }
                        if ((inpt === outpt) && (outpt === null)) {
                            inpt = $("<div></div").addClass('form-group col-md-12')
                                .append($("<button></button>")
                                        .addClass("btn remote btn-info col-md-12")
                                        .data("service", dev.services[service])
                                        .attr({type: "button",
                                              param: "yes"})
                                        .text(action));
                        }
                        frame.append(act.append(inpt).append(outpt));
                    }
                }
            }
        }
        uid_str = dev.UDN.split(':');
        dom_element.append($("<div></div>")
                           .addClass("col-md-4")
                           .attr('id', uid_str[uid_str.length - 1])
                           .css("margin-bottom", "10px")
                           .append(frame));
    }
    
    function build_binaryLight(dev, dom_element) {
        var name = dev.friendlyName;
        dom_element.append(document.createElement('div').addClass('col-md-4').append('<h1>' + name + '</h1>'));
    }
    

    
    // service class
    
    function Service(nodes, desc, addr, widget) {
        service_id += 1;
        this.id = service_id.toString();
        this.addr = addr;
        this.widget = $('#' + widget);
        var i = 0,
            j = 0,
            k = 0,
            l = 0,
            m = 0,
            t,
            actions,
            stateVariables,
            sname,
            stype,
            name,
            arg,
            args,
            argname,
            argtype,
            inputs,
            outputs;
        for (i = 0; i < nodes.length; i += 1) {
            //console.log(nodes[i].nodeName);
            this[nodes[i].nodeName] = nodes[i].childNodes[0].nodeValue;
        }
        t = this.serviceId.split(":");
        log("*" + t[t.length - 1]);
        this.stateVariables = {};
        this.actions = {};
        this.events = {};
        for (j = 0; j < desc.childNodes.length; j += 1) {
            switch (desc.childNodes[j].nodeName) {
            case 'actionList':
                actions = desc.childNodes[j].childNodes;
                break;
            case 'serviceStateTable':
                stateVariables = desc.childNodes[j].childNodes;
                break;
            default:
                break;
            }
            
        }
        for (l = 0; l < stateVariables.length; l += 1) {
            sname =  stateVariables[l].getElementsByTagName('name'
                )[0].childNodes[0].nodeValue;
            stype = stateVariables[l].getElementsByTagName('dataType'
                )[0].childNodes[0].nodeValue;
            this.stateVariables[sname] = stype;
            //console.log(stateVariables[l]);
            if (stateVariables[l].
                    getAttribute("sendEvents") === "yes") {
                this.registerEvent(sname);
            }
        }
        for (m = 0; m < actions.length; m += 1) {
            inputs = [];
            outputs = [];
            // console.log(actions[i]);
            name = actions[m].getElementsByTagName('name')[0]
                        .childNodes[0].nodeValue;
            log("___" + name);
            args =  actions[m].getElementsByTagName('argumentList'
                )[0].childNodes;
            for (k = 0; k < args.length; k += 1) {
                //console.log(args[j]);
                argname = args[k].getElementsByTagName('name'
                    )[0].childNodes[0].nodeValue;
                argtype = args[k].getElementsByTagName('relatedStateVariable'
                    )[0].childNodes[0].nodeValue;
                arg = {};
                arg[argname] = argtype;
                if (args[k].getElementsByTagName('direction')[0].
                               childNodes[0].nodeValue === "out") {
                    outputs.push(arg);
                } else {
                    inputs.push(arg);
                }
                /*if (argtype in this.events) {
                    this.events[argtype] = 
                } */
            }
            this.actions[name] = {'in': inputs, 'out': outputs};
        }
       
    }
    Service.prototype.setData = function (name, data) {
        if (this.stateVariables[name] === 'boolean') {
            if (data === '0') {
                $(name + this.id).text = 'ON';
            } else {
                $(name + this.id).text = 'OFF';
            }
        } else {
            $(name + this.id).text = data;
        }
    };
    
    Service.prototype.registerEvent = function (param) {
        //log('register: ' + param);
        this.events[param] = [];
    };
    Service.prototype.event = function (name, value) {
        var i = 0;
        if (this.events.hasOwnProperty(name)) {
            for (i = 0; i > this.events[name].length; i += 1) {
                this.events[name][i](value);
            }
        }
    };
    
    Service.prototype.call = function (action, params, clbk) {
        var iq = new UpnpControl(this.addr, this, action, params);
        connection.sendIQ(iq, clbk);
    };
    
    
    // device class
    
    function Device(addr, desc) {
        this.address = addr;
        var query = desc.childNodes[0],
            root = query.childNodes[0].childNodes,
            dev_tree = root[1].childNodes,
            service_index = 0,
            i = 0,
            j = 0,
            s,
            t,
            a,
            evtlist,
            evt;
        this.events = {};
        this.services = {};
        //console.log(desc);
        for (i = 0; i < dev_tree.length; i += 1) {
            // log(dev_tree[i].nodeName);
            switch (dev_tree[i].nodeName) {
            case 'serviceList':
                log('Services :');
                for (j = 0;
                        j < dev_tree[i].childNodes.length; j += 1) {
                    service_index += 1;
                    s = new Service(
                        dev_tree[i].childNodes[j].childNodes,
                        query.childNodes[service_index],
                        this.address,
                        this.UDN
                    );
                    a = s.serviceId.split(":");
                    evtlist = {};
                    t = a[a.length - 1];
                    this.services[t] = s;
                    //console.log(s.events);
                    for (evt in s.events) {
                        if (s.events.hasOwnProperty(evt)) {
                            evtlist[evt] = s.events[evt];
                        }
                    }
                    if (Object.keys(evtlist).length > 0) {
                        this.events[s.serviceType] = evtlist;
                    }
                }
                break;
            case 'iconList':
                // log ('Icon !');
                break;
            default:
                this[dev_tree[i].nodeName] = dev_tree[i]
                                .childNodes[0].nodeValue;
                break;
            }
        }
        //this.build_dom($('#objects'));
        console.log('device created');
    }
    
    Device.prototype.toHtml = function () {
        //console.log(this.friendlyName);
        return document.createTextNode(this.friendLyName);
    };
    
    Device.prototype.build_dom = function (dom_element) {
        if (this.deviceType === "urn:schemas-upnp-org:device:BinaryLight:1") {
            //build_binaryLight(this, dom_element);
            //log('Light !');
            build_genericDevice(this, dom_element);
        } else {
            build_genericDevice(this, dom_element);
        }
    };
    
    function display_device(device, dom_element) {
        //console.log(device.events);
        var uid_str = device.UDN.split(":"),
            start = -1,
            my_idx,
            i,
            actions,
            act,
            template_name = "templates/" + device.deviceType.split(":")[3].toLowerCase() + ".html",
            template_req,
            colors = ['yellow', 'green', 'red', 'blue', 'white', 'pink'],
            low = device.friendlyName.toLowerCase(),
            color = "#fcfb85";
        for (i = 0; i < colors.length; i += 1) {
            if (low.indexOf(colors[i]) > -1) {
                color = colors[i];
                console.log(color);
                break;
            }
        }
        template_req = $.get(template_name, function (template) {
            var svc,
                evt,
                rendered = Mustache.render(template,
                                       {device: device,
                                        color: color,
                                        getid: function () {
                            if (start === -1) {
                                start = rindex;
                                my_idx = start;
                            }
                            rindex += 1;
                            my_idx += 1;
                            return my_idx;
                        },
                                            curid: function () {
                            return my_idx;
                        }
                        }
                    );
            console.log(rendered);
            dom_element.append($("<div></div>")
                       .addClass("col-md-4")
                       .attr('id', uid_str[uid_str.length - 1])
                       .append(rendered));
            actions = 0;
            for (svc in device.services) {
                if (device.services.hasOwnProperty(svc)) {
                    actions += Object.keys(device.services[svc].actions).length;
                }
            }
            for (i = start + 1; i < start + actions + 1; i += 1) {
                if ($("#inpt_" + i.toString()).length > 0) {
                    act = $("#inpt_" + i.toString());
                    console.log('found action: ');
                    console.log(act.data());
                    console.log(device.services);
                    act.data('service', device.services[act.data('svctype')]);
                    console.log(act.data());
                }
            }
            for (svc in device.events) {
                if (device.events.hasOwnProperty(svc)) {
                    for (evt in device.events[svc]) {
                        if (device.events[svc].hasOwnProperty(evt)) {
                            start += 1;
                            if (typeof window["evt_fct_" + start.toString()] !== 'undefined') {
                                console.log('the winner is: evt_fct_' + start.toString());
                                console.log(window["evt_fct_" + start.toString()]);
                                device.events[svc][evt][0] = window["evt_fct_" + start.toString()];
                            }
                        }
                    }
                }
            }
            /*for (i = 0; i < evts.length; i += 1) {
                start += 1;
                if (typeof window["evt_fct_" + start.toString()] !== 'undefined') {
                    console.log('the winner is: evt_fct_' + start.toString());
                    console.log(window["evt_fct_" + start.toString()]);
                    device.events[evts[i].service][evts[i].name][0] = window["evt_fct_" + start.toString()];
                }

            }*/
            //dom_element.html(rendered);
        }, 'html');
        template_req.fail(function () {
            build_genericDevice(device, dom_element);
        });
    }
    
    function onPresence(presence) {
        
        var elems = presence.getElementsByTagName('ConfigIdCloud'),
            from = presence.getAttribute('from'),
            res_name = Strophe.getResourceFromJid(from),
            pos,
            str_array,
            iq;
        if (res_name === fulljid) {
            return true;
        }
        log('got PRESENCE from:  ' + from);
        if (presence.hasAttribute('type')) {
            log('type = ' + presence.getAttribute('type'));
            if (presence.getAttribute('type') === 'unavailable') {
                console.log(res_name);
                console.log(devices);
                pos = devices.indexOf(res_name);
                console.log(pos);
                if (pos !== -1) {
                    str_array = res_name.split(':');
                    log('goodbye ' + str_array[str_array.length - 1]);
                    $('#' + str_array[str_array.length - 1]).remove();
                    devices.splice(pos, 1);
                }
                return true;
            }
        }
        if (elems.length > 0) {
            /*for (l = 0; index < devices.length; l++) {
                if (devices[l] === from){
                    return true;
                }
            }*/
            if (devices.indexOf(res_name) !== -1) {
                log('Already discovered');
                return true;
            }
            log('Discovering:  ' + res_name);
            devices.push(res_name);
            iq = $iq({ to: presence.getAttribute('from'), type: 'get'}).c(
                'query',
                { xmlns: "urn:schemas-upnp-org:cloud-1-0",
                    type: "description",
                    name: res_name
                    }
            );
            /*global onDescription */
            connection.sendIQ(iq, onDescription);
        }
        return true;
    }
    
    function subscribed(node, clbk) {
        return function (iq) {
            if (iq.getAttribute('type') === 'result') {
                subscriptions[node] = clbk;
            } else {
                log('error subscribing ' + node);
            }
        };
    }
    function subscribe(host, rnode, callback_fct) {
        var iq = $iq({to: host, type: 'set'})
            .c('pubsub', {xmlns: 'http://jabber.org/protocol/pubsub'})
            .c('subscribe', {node: rnode, jid: connection.jid});
        connection.sendIQ(iq, subscribed(rnode, callback_fct));
    }
    
    function onDescription(desc) {
        var device = new Device(desc.getAttribute('from'), desc), evt, s;
        log('Discovered: ' + desc.getAttribute('from'));
        display_device(device, $('#objects'));
        //console.log(device);
        for (s in device.events) {
            if (device.events.hasOwnProperty(s)) {
                for (evt in device.events[s]) {
                    if (device.events[s].hasOwnProperty(evt)) {
                        features.push([desc.getAttribute('from'),  s, evt]
                                      .join("/"));
                        features.push([desc.getAttribute('from'),  s, evt]
                                      .join("/") + "+notify");
                        subscriptions[[desc.getAttribute('from'),  s, evt]
                                      .join("/")] = device.events[s][evt];
                    }
                }
                
            /*for (var evt in device.events[s]){
                subscribe('pubsub.' + Strophe.getDomainFromJid(
                    desc.getAttribute('from')),
                    [desc.getAttribute('from'),  s, evt].join("/"),
                    device.events[s][evt]);
            }*/
            }
        }
        my_ver = b64_sha1(features.join());
        connection.send($pres().c('c', {xmlns: NS_CAPS, hash: 'sha-1',
                                        node: 'https://lazytech.io',
                                        ver: my_ver}));
//        var serv = {};
//        for (svc in device.services) {
//            serv = device.services[svc];
//            break;
//        } 
    }
    
    function onIq(iq) {
        /*log('got IQ');
        console.log('got iq');
        console.log(iq);*/
        return true;
    }
    
    function onDisco(iq) {
        log('Disco Time!');
        console.log(iq);
        var response = $iq({type: 'result', id: iq.getAttribute('id')})
            .c('query', {xmlns: NS_DISCO_INFO, node: ('https://lazytech.io' + '#' + my_ver)})
            .c('identity', identity)
            .up(), i;
        for (i = 0; i < features.length; i += 1) {
            response.c('feature', {'var': features[i]}).up();
        }
        if (iq.hasAttribute("from")) {
            response.up().attrs({to: iq.getAttribute("from")});
        }
        connection.send(response);
        return true;
    }
    function onEvent(message) {
        var events = $(message).find('event');
        if (events.length > 0) {
            process_events(events);
        }
        console.log('event processed');
        return true;
    }
    
    function onMsg(message) {
        var events = $(message).find('event');
        if (events.length > 0) {
            process_events(events);
        }
        return true;
    }
    
    function discovered(iq) {
        var to = iq.getAttribute('to'),
            from = iq.getAttribute('from'),
            type = iq.getAttribute('type'),
            elems = iq.getElementsByTagName('query');
        return true;
    }

    function rawInput(data) {
        log('RECV: ' + data);
    }

    function rawOutput(data) {
        log('SENT: ' + data);
    }
    
    function refresh_dom(device) {
        switch (device.type) {
        case "urn:schemas-upnp-org:device:BinaryLight:1":
            log('Light !');
            break;
        default:
            log('device !');
            break;
        }
    }

    function onConnect(status) {
        if (status === Strophe.Status.CONNECTING) {
            log('Connecting...');
        } else if (status === Strophe.Status.CONNFAIL) {
            log('Strophe failed to connect.');
            $('#connect').get(0).value = 'connect';
        } else if (status === Strophe.Status.DISCONNECTING) {
            log('Strophe is disconnecting.');
        } else if (status === Strophe.Status.DISCONNECTED) {
            log('Strophe is disconnected.');
            $('#credentials').removeClass('hidden');
            $('#connect').removeClass('btn-danger');
            $('#connect').addClass('btn-success');
            $('#connect').get(0).value = 'connect';
            $('#connect').get(0).firstChild.data = "Sign In";
            $('#objects').empty();
            devices = [];
            my_ver = empty_ver;
            features = empty_features.slice();
            rindex = 0;
            connection.reset();
        } else if (status === Strophe.Status.CONNECTED) {
            log('Connected.');
            $('#credentials').addClass('hidden');
            $('#connect').removeClass('btn-success');
            $('#connect').addClass('btn-danger');
            $('#connect').get(0).value = 'disconnect';
            $('#connect').get(0).firstChild.data = "Sign Out";
            connection.addHandler(onPresence, null, 'presence', null, null, null);
            //connection.addHandler(onIq, null, 'iq', null, null, null);
            //connection.addHandler(onMsg, null, 'message', null, null, null);
            connection.addHandler(onEvent, NS_PUBSUB_EVENT, 'message', null, null, null);
            connection.addHandler(onDisco, NS_DISCO_INFO, "iq", "get", null, null, null);
            //log('send Presence: ' + Strophe.$pres().tree().attributes[0]);
            log('Sending Presence...');
            //connection.send(Strophe.$pres().tree());
            connection.send($pres()
                            .c('c',
                               {xmlns: NS_CAPS, hash: 'sha-1',
                                node: 'https://lazytech.io', ver: my_ver }));
            
            //var iq = Strophe.$iq(
            /*var iq = $iq(
                {to: userjid, 'type': 'get'}).c('query', { xmlns: Strophe.NS.DISCO_ITEMS });
            connection.sendIQ(iq, discovered);*/
            //connection.disconnect();
        }
    }
    $("#objects").on('click', '.remote', function () {
        console.log("click!");
        var args = {}, clbks = {}, param, param_name;
        if ($(this).attr("param") === 'yes') {
            for (param in $(this).data('params')) {
                if ($(this).data('params').hasOwnProperty(param)) {
                    args[param] = $('#' + $(this).data('params')[param]).val();
                    log(param + ' --> ' + $('#' + $(this).data('params')[param]).val());
                }
            }
            log('call ' + $(this).text() + ' ' + args + $(this).data('service').addr);
            $(this).data('service').call($(this).text(), args, handle_result(
                $(this).data('callbacks')
            ));
        } else {
            log('call ' + $(this)
                .data('action') + ' ' + $(this)
                .text() + ' ' + $(this).data('service').addr);
            param_name = $(this).data('param_name');
            args = {};
            log(param_name);
            if ($(this).text() === 'On') {
                args[param_name] = 'true';
            } else {
                args[param_name] = 'false';
            }
            $(this).data('service').call($(this).data('action'), args, function () {});
            
        }
        //log('Clicked: ' + $(this).text() + $(this).data('service').serviceId);
    });
    $(document).ready(function () {
        
        connection = new Strophe.Connection(BOSH_SERVICE);
        /*connection.rawInput = rawInput;
        connection.rawOutput = rawOutput;*/
        $('#connect').bind('click', function () {
            var button = $('#connect').get(0), text = button.firstChild;
            if (button.value === 'connect') {
                /*button.value = 'disconnect';
                text.data = 'Sign Off';*/
                userjid = $('#inputuser').get(0).value;
                fulljid = userjid + "/urn:schemas-upnp-org:cloud-1-0:ControlPoint:1:uuid:" + uuid;
                log('My Full JID is ' + fulljid);
                connection.connect(fulljid, $('#pass').get(0).value, onConnect);
            } else {
                /*button.value = 'connect';
                text.data = "Sign In";*/
                connection.disconnect();
            }
        });
    });
});
