var config;
if (typeof(require) === 'undefined') {
    /* XXX: Hack to work around r.js's stupid parsing.
     * We want to save the configuration in a variable so that we can reuse it in
     * tests/main.js.
     */
    require = {
        config: function (c) {
            config = c;
        }
    };
}
require.config({
    baseUrl: '.',
    paths: {
        // Strophe.js src files
		/*"strophe-base64":       "src/base64",
		"strophe-bosh":         "src/bosh",
		"strophe-core":         "src/core",
		"strophe":              "src/wrapper",
		"strophe-md5":          "src/md5",
		"strophe-sha1":         "src/sha1",
		"strophe-websocket":    "src/websocket",
        "strophe-polyfill":     "src/polyfills",*/
        
        // Strophe
        
        "strophe":              "scripts/strophe.min",
        
        // Strophe Plugins
        "strophe.roster":       "scripts/strophe.roster",
        //"strophe.disco":         "scripts/strophe.disco",
        //"strophe.pubsub":        "scripts/strophe.pubsub",
        

        // JQuery
		//"jquery":		    "bower_components/jquery/dist/jquery",
        "jquery":               "scripts/jquery.min",
        
        // Bootstrap
        //"bootstrap":        "bower_components/bootstrap/dist/js/bootstrap"
        "bootstrap":            "scripts/bootstrap.min"
        
        // Bootstrap Plugins
        //"bootstrap.toggle":  "bower_components/bootstrap-toggle/js/bootstrap-toggle"
    },
    "shim": {
        "strophe.roster": ["strophe"],
        "strophe.disco": ["strophe"],
        "strophe.pubsub": ["strophe"],
        "bootstrap": ["jquery"]
        //"bootstrap.toggle": ["jquery", "bootstrap"]
        
    }
});

if (typeof(require) === 'function') {
    require(["strophe"], function(Strophe) {
        window.Strophe = Strophe;
    });
}

// Load the main app module to start the app
requirejs(["scripts/upnp+"]);