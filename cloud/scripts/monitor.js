(function(d){d.each(["backgroundColor","borderBottomColor","borderLeftColor","borderRightColor","borderTopColor","color","outlineColor"],function(f,e){d.fx.step[e]=function(g){if(!g.colorInit){g.start=c(g.elem,e);g.end=b(g.end);g.colorInit=true}g.elem.style[e]="rgb("+[Math.max(Math.min(parseInt((g.pos*(g.end[0]-g.start[0]))+g.start[0]),255),0),Math.max(Math.min(parseInt((g.pos*(g.end[1]-g.start[1]))+g.start[1]),255),0),Math.max(Math.min(parseInt((g.pos*(g.end[2]-g.start[2]))+g.start[2]),255),0)].join(",")+")"}});function b(f){var e;if(f&&f.constructor==Array&&f.length==3){return f}if(e=/rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)/.exec(f)){return[parseInt(e[1]),parseInt(e[2]),parseInt(e[3])]}if(e=/rgb\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*\)/.exec(f)){return[parseFloat(e[1])*2.55,parseFloat(e[2])*2.55,parseFloat(e[3])*2.55]}if(e=/#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(f)){return[parseInt(e[1],16),parseInt(e[2],16),parseInt(e[3],16)]}if(e=/#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(f)){return[parseInt(e[1]+e[1],16),parseInt(e[2]+e[2],16),parseInt(e[3]+e[3],16)]}if(e=/rgba\(0, 0, 0, 0\)/.exec(f)){return a.transparent}return a[d.trim(f).toLowerCase()]}function c(g,e){var f;do{f=d.curCSS(g,e);if(f!=""&&f!="transparent"||d.nodeName(g,"body")){break}e="backgroundColor"}while(g=g.parentNode);return b(f)}var a={aqua:[0,255,255],azure:[240,255,255],beige:[245,245,220],black:[0,0,0],blue:[0,0,255],brown:[165,42,42],cyan:[0,255,255],darkblue:[0,0,139],darkcyan:[0,139,139],darkgrey:[169,169,169],darkgreen:[0,100,0],darkkhaki:[189,183,107],darkmagenta:[139,0,139],darkolivegreen:[85,107,47],darkorange:[255,140,0],darkorchid:[153,50,204],darkred:[139,0,0],darksalmon:[233,150,122],darkviolet:[148,0,211],fuchsia:[255,0,255],gold:[255,215,0],green:[0,128,0],indigo:[75,0,130],khaki:[240,230,140],lightblue:[173,216,230],lightcyan:[224,255,255],lightgreen:[144,238,144],lightgrey:[211,211,211],lightpink:[255,182,193],lightyellow:[255,255,224],lime:[0,255,0],magenta:[255,0,255],maroon:[128,0,0],navy:[0,0,128],olive:[128,128,0],orange:[255,165,0],pink:[255,192,203],purple:[128,0,128],violet:[128,0,128],red:[255,0,0],silver:[192,192,192],white:[255,255,255],yellow:[255,255,0],transparent:[255,255,255]}})(jQuery);

function update_value(machine, name, value, level)
{
	var existing_entry = $("#values-"+machine+" tr.value-"+name);
	if(existing_entry.length == 0)
	{
		var row = $("<tr><td class='level-"+(level||"normal")+"'>&bull;</td><td>"+name+":</td><td>"+value+"</td></tr>");
		var classname = "value-"+name;
		row.addClass(classname);
		var inserted = false;
		$("#values-"+machine+" tr").each(function () {
			var e = $(this);
			if(e.attr("class") > classname)
			{
				e.before(row);
				inserted = true;
				return false;
			}
		})
		if(!inserted)
			$("#values-"+machine).append(row);
		return;
	}
	var cells = existing_entry.find("td");
	cells.last().text(value);
	var colour;
	switch(level)
	{
		case "critical": colour = "#ff7777"; break;
		case "warning": colour = "#ffff77"; break;
		default: colour = "#77ff77"; break;
	}
	existing_entry.stop().css("background-color", colour).animate({ backgroundColor: "#ffffff" }, 2000);
	if(level)
		cells.first().attr("class", "level-"+level);
	else
		cells.first().attr("class", "level-normal");
}

var machines = config.machines;

var conn = new Strophe.Connection("/bosh");

function connection_handler(status, err)
{
	switch(status)
	{
	case Strophe.Status.CONNECTED:
		text = "Connected";
		handle_connected();
		break;
	case Strophe.Status.ERROR:
		text = "Error";
		break;
	case Strophe.Status.CONNECTING:
		text = "Connecting...";
		break;
	case Strophe.Status.CONNFAIL:
		text = "Connection failed";
		break;
	case Strophe.Status.AUTHENTICATING:
		text = "Authenticating...";
		break;
	case Strophe.Status.AUTHFAIL:
		text = "Authentication failed";
		break;
	case Strophe.Status.DISCONNECTING:
		text = "Disconnecting...";
		break;
	case Strophe.Status.DISCONNECTED:
		text = "Disconnected";
		break;
	default:
		text = "Unknown connection status ("+status+")";
	}
	if(err)
		text = text + ": " + err;
	$("#conn-status").text(text);
}

/* PEP code */
var NS_CAPS = "http://jabber.org/protocol/caps";
var NS_DISCO_INFO = "http://jabber.org/protocol/disco#info";
var NS_PUBSUB = "http://jabber.org/protocol/pubsub";
var NS_PUBSUB_EVENT = NS_PUBSUB + "#event";

var NS_USER_TUNE = "http://jabber.org/protocol/tune";
var NS_USER_MOOD = "http://jabber.org/protocol/mood";
var NS_USER_ACTIVITY = "http://jabber.org/protocol/activity";

function xml_escape(xml)
{
	return xml.replace(new RegExp("&", "gm"), '&amp;')
			.replace(new RegExp("<", "gm"), '&lt;')
				.replace(new RegExp(">", "gm"), '&gt;');
}

var client_node = "http://monitor.prosody.im/#webmonitor";
var identity = { category: 'client', name: 'webmonitor', type: 'web' };
var features = [
		"http://jabber.org/protocol/caps",
		"http://jabber.org/protocol/disco#info", 
		"http://jabber.org/protocol/disco#items"
];

for(i=0;i<=config.watches.length;i++)
{
	features.push("http://prosody.im/protocol/monitor#"+config.watches[i]);
	features.push("http://prosody.im/protocol/monitor#"+config.watches[i]+"+notify");
}

var client_ver = b64_sha1(features.join());


function disco_handler(iq)
{
	var reply = $iq({ type: 'result', id: iq.getAttribute('id') })
			.c('query', { xmlns: NS_DISCO_INFO, node: (client_node + '#' + client_ver) })
				.c('identity', identity).up();
	for(var i = 0; i < features.length; i++)
	{
		reply.c('feature', { "var": features[i] }).up();
	}
	reply.up();
	if(iq.getAttribute("from") != "" && iq.getAttribute("from") != null)
		reply.attrs({"to": iq.getAttribute("from")});
	conn.send(reply);
	return true;
}

function update_handler(update)
{
	var value_elem = $(update).find("event items item value[xmlns='http://prosody.im/protocol/monitor']");
	var machine = Strophe.getNodeFromJid(update.getAttribute("from"));
	update_value(machine, value_elem.attr("name"), value_elem.text(), value_elem.attr("level"));
	return true;
}

function presence_handler(presence)
{
	var domain = Strophe.getDomainFromJid(presence.getAttribute("from"));
	var machine = Strophe.getNodeFromJid(presence.getAttribute("from"));
	if(domain != config.domain)
		return true;
	
	if(presence.getAttribute("type") == "unavailable")
	{
		$("#machine-"+machine)
			.removeClass("machine-online")
			.addClass("machine-offline");
	}
	else
	{
		$("#machine-"+machine)
			.removeClass("machine-offline")
			.addClass("machine-online");
	}
	
	return true;
}

function handle_connected()
{
	conn.addHandler(disco_handler, NS_DISCO_INFO, "iq", "get", null, null, null);
	conn.addHandler(update_handler, NS_PUBSUB_EVENT, "message", null, null, null, null);
	conn.addHandler(presence_handler, null, "presence", null, null, null, null);
	conn.send($pres()
		.c('c', { xmlns: NS_CAPS, hash: 'sha-1', node: client_node, ver: client_ver })
	);
}

/* Initialisation */
$(function () {
	for(var i=0;i<machines.length;i++)
	{
		$("<div class='machine machine-offline' id='machine-"+machines[i]+"'> \
			<h1>"+machines[i]+"</h1> \
				<table id='values-"+machines[i]+"'/>")
			.appendTo("body");
	}
	
	conn.connect(config.jid, config.password, connection_handler);
});

