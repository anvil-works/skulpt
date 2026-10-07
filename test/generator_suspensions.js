const assert = require("assert");
const fs = require("fs");
const load = require("../support/run/require-skulpt").requireSkulpt;
load(false);
const events = [];
Sk.builtins.suspend_probe = new Sk.builtin.func(function (phase) {
    events.push("start " + phase.v);
    const suspension = new Sk.misceval.Suspension();
    suspension.data = { type: "generator test" };
    suspension.resume = () => {
        assert.strictEqual(Sk.globals.g.gi$running, true);
        assert.strictEqual(Sk.globals.child.gi$running, true);
        events.push("finish " + phase.v);
        return Sk.builtin.none.none$;
    };
    return suspension;
});
Sk.configure({ read: (file) => fs.readFileSync(file, "utf8"), __future__: Sk.python3 });
const source = `
def inner():
    try:
        suspend_probe('body')
        try:
            yield 1
        except ValueError:
            suspend_probe('throw')
            yield 2
    finally:
        suspend_probe('close')
child = inner()
def outer():
    yield from child
g = outer()
assert next(g) == 1
assert not g.gi_running and not child.gi_running
assert g.throw(ValueError) == 2
assert not g.gi_running and not child.gi_running
g.close()
assert not g.gi_running and not child.gi_running
assert list(g) == []
`;
let result = Sk.importMainWithBody("<generator suspension test>", false, source, true);
while (result instanceof Sk.misceval.Suspension) {
    assert.strictEqual(Sk.globals.g.gi$running, true);
    assert.throws(() => Sk.globals.g.tp$iternext(true), (e) => e instanceof Sk.builtin.ValueError);
    result = result.resume();
}
assert.deepStrictEqual(events, ["start body", "finish body", "start throw", "finish throw", "start close", "finish close"]);

// Yield itself needs a saved frame even in synchronous compiled code.
Sk.importMainWithBody("<synchronous generator test>", false, "def gen():\n    yield 42\nassert list(gen()) == [42]\n", false);
// Native async suspension must retain comprehension state in both compiler modes.
const asyncSource = fs.readFileSync("test/async_comprehension_suspensions.py", "utf8");
for (const canSuspend of [false, true]) {
    Sk.importMainWithBody("<async comprehension suspension test>", false, asyncSource, canSuspend);
}
// Compiled top-level await has a module namespace and a native coroutine frame.
const topLevelSource = fs.readFileSync("test/top_level_await_suspensions.py", "utf8");
for (const canSuspend of [false, true]) {
    const compiled = Sk.compile(topLevelSource, "<top-level await suspension test>", "exec", canSuspend, 0, 0x2000);
    const entry = Sk.global["eval"](compiled.code);
    const namespace = Sk.misceval.namespaceToJs({});
    const coroutine = entry(namespace);
    assert(coroutine instanceof Sk.builtin.coroutine);
    assert.strictEqual(namespace.Pause, undefined);
    assert.strictEqual(coroutine.$send(Sk.builtin.none.none$).v, "pause");
    assert.strictEqual(namespace.answer, undefined);
    assert.throws(() => coroutine.$send(Sk.builtin.none.none$), error => error instanceof Sk.builtin.StopIteration);
    assert.strictEqual(namespace.answer.v, 42);
}
console.log("Generator suspension tests passed");
