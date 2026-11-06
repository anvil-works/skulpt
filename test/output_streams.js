const assert = require("assert");
require("../support/run/require-skulpt").requireSkulpt(false);
require("../dist/skulpt-stdlib");
const fs = require("fs");
const path = require("path");

Sk.configure({
    read(filename) {
        const chunk = Sk.builtinFiles.files[filename];
        if (typeof chunk === "number") {
            Object.assign(Sk.builtinFiles.files, JSON.parse(fs.readFileSync(
                path.join(__dirname, "../dist/skulpt-stdlib-" + chunk + ".json"), "utf8")));
        }
        return Sk.builtinFiles.files[filename];
    },
});

(async () => {
    for (const version of [Sk.python2, Sk.python3]) {
    Sk.configure({ __future__: version });
    const shared = [], out = [], err = [];
    const write = () => Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("streams", false,
        "import sys\nprint('out')\nsys.stderr.write('err\\n')\n", true));
    Sk.configure({ output: text => shared.push(text) });
    await write();
    assert.strictEqual(shared.join(""), "out\nerr\n");
    shared.length = 0;

    Sk.configure({ stdout: text => out.push(text) });
    await write();
    assert.strictEqual(out.join(""), "out\n");
    assert.strictEqual(shared.join(""), "err\n");
    out.length = shared.length = 0;

    Sk.configure({ stderr: text => err.push(text) });
    await write();
    assert.strictEqual(out.join(""), "out\n");
    assert.strictEqual(err.join(""), "err\n");
    assert.strictEqual(shared.length, 0);
    out.length = err.length = 0;

    // An omitted callback persists; null/undefined explicitly return to fallback.
    const replacement = [];
    Sk.configure({ output: text => replacement.push(text), stdout: null });
    await write();
    assert.strictEqual(replacement.join(""), "out\n");
    assert.strictEqual(err.join(""), "err\n");
    replacement.length = 0;
    Sk.configure({ stderr: undefined, filewrite() { throw new Error("stdio must not use filewrite"); } });
    await write();
    assert.strictEqual(replacement.join(""), "out\nerr\n");
    }
    console.log("Python 2/3 output stream configuration tests passed");
})().catch(error => { console.error(error); process.exitCode = 1; });
