require.config({
    baseUrl: '.',
    paths: {
        // Strophe.js src files
		"strophe-base64":       "src/base64",
		"strophe-bosh":         "src/bosh",
		"strophe-core":         "src/core",
		"strophe":              "src/wrapper",
		"strophe-md5":          "src/md5",
		"strophe-sha1":         "src/sha1",
		"strophe-websocket":    "src/websocket",
        "strophe-polyfill":     "src/polyfills",
        
        // Plugins
        "strophe.roster":        "scripts/strophe.roster",
        "strophe.disco":         "scripts/strophe.disco",
        "strophe.pubsub":        "scripts/strophe.pubsub",
        

        // JQuery
		"jquery":		    "bower_components/jquery/dist/jquery",
        "jquery.soap":      "bower_components/jquery.soap/jquery.soap"
    },
    "shim": {
        "jquery.soap": ["jquery"],
        "strophe.roster": ["strophe"],
        "strophe.disco": ["strophe"],
        "strophe.pubsub": ["strophe"]   
        
    }
});

if (typeof(require) === 'function') {
    require(["strophe"], function(Strophe) {
        window.Strophe = Strophe;
    });
}

// Load the main app module to start the app
requirejs(["scripts/upnp+"]);