const assert = require("assert");
const load = require("../support/run/require-skulpt").requireSkulpt;
load(false);

// Hosts reuse Skulpt across runs and can configure either version repeatedly.
// Verify that builtin removal is tolerant and the Python view stays shared.
for (const version of [Sk.python3, Sk.python3, Sk.python2, Sk.python2, Sk.python3]) {
    Sk.configure({ __future__: version });
    const namespace = Sk.misceval.namespaceDict(Sk.builtins);
    const get = name => namespace.mp$lookup(new Sk.builtin.str(name));
    assert.strictEqual(get("map"), Sk.builtins.map);
    if (version.python3) {
        assert.strictEqual(get("BlockingIOError"), Sk.builtin.BlockingIOError);
        assert.notStrictEqual(get("BaseExceptionGroup"), undefined);
        assert.notStrictEqual(get("ExceptionGroup"), undefined);
        assert.strictEqual(get("bytes"), Sk.builtin.bytes);
        assert.strictEqual(get("reduce"), undefined);
    } else {
        assert.strictEqual(get("BlockingIOError"), undefined);
        assert.strictEqual(get("BaseExceptionGroup"), undefined);
        assert.strictEqual(get("ExceptionGroup"), undefined);
        assert.strictEqual(get("bytes"), undefined);
        assert.notStrictEqual(get("reduce"), undefined);
    }
}
console.log("Builtin reconfiguration tests passed");
