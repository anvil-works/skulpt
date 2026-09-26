const reqskulpt = require('../support/run/require-skulpt').requireSkulpt;

// Import Skulpt
var skulpt = reqskulpt(false);
if (skulpt === null) {
    process.exit(1);
}

// Run the existing execution fixtures through the configured parser.
import('./parser_with_names.mjs').then(({parseModule, scan}) => {
    Sk.configure({sourceParser: parseModule, sourceTokenizer: scan});
    require('./test.js');
}).catch(error => { console.error(error); process.exitCode = 1; });
