// Proof (no Skulpt change needed): a compiled module scope can be called with
// (module.$d, captureLocals) as its globals and locals, the way exec(code, g, l)
// does. Anvil's live reload (Stage 3 onwards) relies on this:
//  - defs land in the capture object, never in the live module;
//  - the new functions read the live module's globals at call time;
//  - defaults are evaluated against the live globals;
//  - generators, closures and suspensions work;
//  - a stub metaclass passed in the locals lets a `class X(metaclass=stub):`
//    snippet hand back its namespace without building a class, and zero-arg
//    super() in a harvested method finds the live class through the globals.
//
// Run: node test/live_reload/scope_proof.js   (after `npm run build`)
const assert = require("assert");
const { loadSkulpt, importModule, runScope, call, js, getattr } = require("./load_skulpt");

loadSkulpt();

async function main() {
    const mod = await importModule(`
import time
X = 1
calls = []
def helper():
    return "old-helper"
def register(f):
    calls.append(f.__name__)
    return f
class Base:
    def m(self):
        return 1
class C(Base):
    LIMIT = 5
    def m(self):
        return super().m() + 1
`);
    const g = mod.$d;
    const before = Object.keys(g).sort();

    const capture = {};
    // Stub metaclass for the class snippet: seeds the body namespace with the
    // live class's own attributes and returns the namespace instead of a class.
    await runScope(`
def _make_stub(seed):
    class _Stub(type):
        @classmethod
        def __prepare__(mcls, name, bases, **kw):
            return dict(seed)
        def __new__(mcls, name, bases, ns, **kw):
            return ns
    return _Stub
`, g, capture, "stub.py");
    const stub = await call(capture._make_stub, getattr(g.C, "__dict__"));

    const savedSkGlobals = Sk.globals;
    const capture2 = Object.assign(Object.create(null), { _Stub: stub });
    // (An import in the snippet would land in the capture, not the module, so
    // functions defined there could not see it: exec semantics. Snippets only
    // contain defs; Stage 5 runs new imports in the real module scope.)
    await runScope(`
def f(a=X):
    return helper() + ":" + str(a)
@register
def decorated():
    return "deco"
def gen(n):
    for i in range(n):
        yield helper() + str(i)
def outer():
    k = X * 10
    def inner():
        return k + X
    return inner
def sleeper():
    time.sleep(0.01)
    return helper()
class C(metaclass=_Stub):
    def m(self, lim=LIMIT):
        return super().m() + 100 + lim
`, g, capture2, "app/mod.py#1");

    // Sk.globals is restored by runScope (the runner must do the same).
    assert.strictEqual(Sk.globals, savedSkGlobals);

    // Nothing was written to the live module (except by the decorator's side
    // effect). `__class__` is excluded: Skulpt's zero-arg super() support writes
    // $gbl.__class__ (the known one-slot-per-module super() bug in the plan).
    const noClass = (ks) => ks.filter((k) => k !== "__class__");
    assert.deepStrictEqual(noClass(Object.keys(g).sort()), noClass(before), "no names added to the live module");
    assert.strictEqual(js(g.calls).join(","), "decorated", "decorator ran against the live globals");
    for (const name of ["f", "decorated", "gen", "outer", "sleeper", "C"]) {
        assert.ok(capture2[name] !== undefined, name + " landed in the capture");
    }
    // The new functions' globals are the live module's dict.
    assert.strictEqual(capture2.f.func_globals, g);

    // Globals are read live at call time.
    assert.strictEqual(js(await call(capture2.f)), "old-helper:1");
    await runScope(`
def helper():
    return "new-helper"
X = 2
`, g, g, "app/mod.py#2");
    assert.strictEqual(js(await call(capture2.f)), "new-helper:1", "default stays as evaluated; helper read live");

    // Generator reading globals.
    const it = await call(capture2.gen, Sk.ffi.toPy(2));
    assert.deepStrictEqual(js(await call(Sk.builtins.list, it)), ["new-helper0", "new-helper1"]);

    // Closure: cell + global.
    const inner = await call(capture2.outer);
    assert.strictEqual(js(await call(inner)), 22);

    // Suspension (time.sleep) inside a snippet function.
    assert.strictEqual(js(await call(capture2.sleeper)), "new-helper");

    // Class snippet: namespace came back, not a class; seeded LIMIT was visible.
    const ns = capture2.C;
    assert.ok(ns instanceof Sk.builtin.dict, "stub returned the namespace");
    const newM = ns.mp$subscript(new Sk.builtin.str("m"));
    // Install the harvested method on the live class: zero-arg super() finds
    // the live C via $gbl.C.
    g.C.tp$setattr(new Sk.builtin.str("m"), newM);
    const inst = await call(g.C);
    const bound = getattr(inst, "m");
    assert.strictEqual(js(await call(bound)), 1 + 100 + 5);
    assert.strictEqual(capture2.C, ns);
    assert.strictEqual(g.C.prototype.hasOwnProperty("m"), true);

    console.log("scope_proof: all checks passed");
}

main().catch((e) => {
    console.error("scope_proof FAILED:", e && e.toString ? e.toString() : e);
    if (e && e.traceback) {
        console.error(JSON.stringify(e.traceback));
    }
    if (e && e.stack) {
        console.error(e.stack);
    }
    process.exit(1);
});
