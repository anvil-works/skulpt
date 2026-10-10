// Shared helper for the live-reload node tests: loads a built Skulpt
// (dist/skulpt.min.js by default, or the directory in SKULPT_DIST) and
// configures it for Python 3, with the stdlib read from skulpt-stdlib.js.
const fs = require("fs");
const path = require("path");

function loadSkulpt() {
    const distDir = process.env.SKULPT_DIST || path.join(__dirname, "../../dist");
    require(path.resolve(distDir, "skulpt.min.js"));
    require(path.resolve(distDir, "skulpt-stdlib.js"));
    const output = [];
    Sk.configure({
        __future__: Sk.python3,
        output: (s) => output.push(s),
        read: (fname) => {
            if (Sk.builtinFiles && Sk.builtinFiles.files[fname] !== undefined) {
                return Sk.builtinFiles.files[fname];
            }
            if (fs.existsSync(fname)) {
                return fs.readFileSync(fname, "utf8");
            }
            throw new Sk.builtin.ImportError("No module named " + fname);
        },
        yieldLimit: null,
        execLimit: null,
    });
    return { Sk, output };
}

let modCounter = 0;

// Import `source` as a fresh module and resolve to the module object.
function importModule(source, name) {
    name = name || "livemod" + modCounter++;
    return Sk.misceval.asyncToPromise(() => Sk.importMainWithBody(name, false, source, true));
}

// Compile `source` and run its module scope with (globals, locals), as the
// live-reload snippet runner does. Restores Sk.globals afterwards.
function runScope(source, globals, locals, filename) {
    const co = Sk.compile(source, filename || "snippet.py", "exec", true);
    const modscope = Sk.global["eval"](co.code);
    const savedGlobals = Sk.globals;
    return Sk.misceval.asyncToPromise(() => modscope(globals, locals)).finally(() => {
        Sk.globals = savedGlobals;
    });
}

function call(fn, ...args) {
    return Sk.misceval.asyncToPromise(() => Sk.misceval.callsimOrSuspendArray(fn, args));
}

function py(v) {
    return Sk.ffi.toPy(v);
}

function js(v) {
    return Sk.ffi.toJs(v);
}

function getattr(obj, name) {
    return Sk.abstr.gattr(obj, new Sk.builtin.str(name));
}

module.exports = { loadSkulpt, importModule, runScope, call, py, js, getattr };
