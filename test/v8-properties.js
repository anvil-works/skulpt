// Runtime shape check, separate from Python unit tests.
// Run with node --allow-natives-syntax; see https://github.com/skulpt/skulpt/pull/1143
const fs = require("fs");
const vm = require("vm");
const hasFastProperties = new Function("object", "return %HasFastProperties(object);");
const coreFile = process.argv[2] || "dist/skulpt.min.js";

async function run() {
    const context = vm.createContext({ console, setTimeout, clearTimeout });
    vm.runInContext(fs.readFileSync(coreFile, "utf8"), context);
    const Sk = context.Sk;
    const check = (stage) => {
        const targets = [
            ["Sk", Sk],
            ["Sk.builtin", Sk.builtin],
            ["Sk.builtins", Sk.builtins],
            ["Sk.misceval", Sk.misceval],
            ["Sk.abstr", Sk.abstr],
            ["Sk.ffi", Sk.ffi],
            ["Sk.generic", Sk.generic],
            ["Sk.token", Sk.token],
        ];
        for (const [name, obj] of targets) {
            if (!hasFastProperties(obj)) {
                throw new Error(name + " has dictionary properties " + stage);
            }
        }
    };
    check("after core startup");
    vm.runInContext(fs.readFileSync("dist/skulpt-stdlib.js", "utf8"), context);
    check("after stdlib loading");
    // Verify host custom builtins and overrides of shared builtins survive Py3 <-> Py2 switches.
    const customBuiltin = new Sk.builtin.func(() => new Sk.builtin.int_(42));
    const origOpen = Sk.builtins.open;
    const customOpen = new Sk.builtin.func(() => Sk.builtin.none.none$);
    Sk.builtins.host_custom = customBuiltin;
    Sk.builtins.open = customOpen;
    for (const future of [Sk.python3, Sk.python2, Sk.python3]) {
        Sk.configure({
            __future__: future,
            read: (filename) => {
                let source = Sk.builtinFiles.files[filename];
                if (typeof source === "number") {
                    const chunk = JSON.parse(fs.readFileSync(`dist/skulpt-stdlib-${source}.json`, "utf8"));
                    Object.assign(Sk.builtinFiles.files, chunk);
                    source = Sk.builtinFiles.files[filename];
                }
                if (source === undefined) {
                    throw new Error("File not found: " + filename);
                }
                return source;
            },
            output: () => {},
        });
        if (Sk.builtins.host_custom !== customBuiltin || Sk.builtins.open !== customOpen) {
            throw new Error("Sk.builtins lost host customization across Python version switch");
        }
        check("after Python configuration");
        await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("v8_smoke", false,
            "import re\nimport math\nfrom datetime import datetime\nvalues = [i * i for i in range(10)]\n", true));
        check("after imports and execution");
    }
    Sk.builtins.open = origOpen;
    console.log(coreFile + ": V8 fast properties retained");
}

run().catch((error) => {
    console.error(error.toString());
    process.exitCode = 1;
});
