config = {
	// List of machines to monitor
	machines: ["heavyhorse", "silver", "snikket", "router", "mobile"],

	// List of variables this client wants to subscribe to (these could be discovered
	// automatically if I implemented it...)
	watches: ["load", "battery", "ac", "usb", "memory_used", "memory_free",
	          "mb_sent", "mb_received", "c2s", "s2s-in", "s2s-out", "cputemp"],
	
	// The domain the machines are on (they don't have to be on the same
	// domain, but keeping it simple here).
	domain: "monitor.prosody.im",

	// Hard-coded for demo
	jid: "monitor@monitor.prosody.im",
	password: "ilovemonitoring",
};
