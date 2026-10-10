// Tests for Sk.builtin.func.prototype.$replaceCode and for bound methods
// reading im_func.tp$call on every call (Anvil live reload).
//
// Run: node test/live_reload/test_replace_code.js   (after `npm run build`)
const assert = require("assert");
const { loadSkulpt, importModule, runScope, call, py, js, getattr } = require("./load_skulpt");

loadSkulpt();

const tests = [];
function test(name, fn) {
    tests.push({ name, fn });
}

const str = (s) => new Sk.builtin.str(s);
const callKw = (fn, args, kws) =>
    Sk.misceval.asyncToPromise(() => Sk.misceval.callsimOrSuspendArray(fn, args, kws));
const list = async (it) => js(await call(Sk.builtins.list, it));
const hasattr = (o, n) => o.tp$getattr(str(n)) !== undefined;

// Compile `source` as a snippet in `mod`'s globals with fresh locals, as the
// live-reload runner does, and return the capture object.
async function snippet(mod, source) {
    const capture = {};
    await runScope(source, mod.$d, capture, "snippet.py");
    return capture;
}

test("plain function: existing references run the new code", async () => {
    const m = await importModule(`
def f(x):
    return x + 1
holder = [f]
def via_global(x):
    return f(x)
`);
    const old = m.$d.f;
    const cap = await snippet(m, `
def f(x):
    return x * 100
`);
    assert.strictEqual(js(await call(old, py(2))), 3);
    old.$replaceCode(cap.f);
    assert.strictEqual(m.$d.f, old, "identity kept");
    assert.strictEqual(js(await call(m.$d.holder.v[0], py(2))), 200);
    assert.strictEqual(js(await call(m.$d.via_global, py(3))), 300);
    assert.strictEqual(old.func_globals, m.$d);
});

test("bound method created before the replace calls the new code", async () => {
    const m = await importModule(`
class K:
    def __init__(self):
        self.v = 7
    def m(self, a):
        return ("old", self.v, a)
k = K()
bound = k.m
`);
    const oldFn = m.$d.K.prototype.m;
    const bound = m.$d.bound;
    const cap = await snippet(m, `
def m(self, a, b=1):
    return ("new", self.v, a, b)
`);
    oldFn.$replaceCode(cap.m);
    assert.deepStrictEqual(js(await call(bound, py(5))), ["new", 7, 5, 1]);
    assert.deepStrictEqual(js(await callKw(bound, [py(5)], ["b", py(2)])), ["new", 7, 5, 2]);
    // newly created bound methods too
    assert.deepStrictEqual(js(await call(getattr(m.$d.k, "m"), py(1))), ["new", 7, 1, 1]);
});

test("defaults and kw-only defaults come from the new code", async () => {
    const m = await importModule(`
D = 10
def f(a, b=1, *, c=2):
    return (a, b, c)
`);
    const old = m.$d.f;
    const cap = await snippet(m, `
def f(a, b=D, *, c=20, d=30):
    return (a, b, c, d)
`);
    old.$replaceCode(cap.f);
    assert.deepStrictEqual(js(await call(old, py(0))), [0, 10, 20, 30]);
    assert.deepStrictEqual(js(await callKw(old, [py(0)], ["d", py(4)])), [0, 10, 20, 4]);
    assert.deepStrictEqual(js(getattr(old, "__defaults__")), [10]);

    // fewer defaults than before: a now-required argument is required
    const cap2 = await snippet(m, `
def f(a, b):
    return a + b
`);
    old.$replaceCode(cap2.f);
    assert.ok(Sk.builtin.checkNone(getattr(old, "__defaults__")));
    await assert.rejects(call(old, py(1)), (e) => e instanceof Sk.builtin.TypeError);
    assert.strictEqual(js(await call(old, py(1), py(2))), 3);

    // defaults reassigned on the new function (e.g. by a decorator) are taken
    const cap3 = await snippet(m, `
def f(a=1):
    return a
f.__defaults__ = (99,)
`);
    old.$replaceCode(cap3.f);
    assert.strictEqual(js(await call(old)), 99);
});

test("varargs/kwargs signature changes", async () => {
    const m = await importModule(`
def f(a):
    return a
`);
    const old = m.$d.f;
    const cap = await snippet(m, `
def f(*args, **kw):
    return (list(args), sorted(kw.items()))
`);
    old.$replaceCode(cap.f);
    assert.deepStrictEqual(js(await callKw(old, [py(1), py(2)], ["z", py(3)])), [[1, 2], [["z", 3]]]);
});

test("closures: the new function's cells are used, and stay live", async () => {
    const m = await importModule(`
def make_old():
    x = "old-cell"
    def f():
        return x
    return f
f = make_old()
`);
    const old = m.$d.f;
    assert.strictEqual(js(await call(old)), "old-cell");
    const cap = await snippet(m, `
def make_new():
    y = ["new-cell"]
    def f():
        return y[0]
    def setter(v):
        y[0] = v
    return f, setter
`);
    const [newF, setter] = (await call(cap.make_new)).v;
    old.$replaceCode(newF);
    assert.strictEqual(js(await call(old)), "new-cell");
    await call(setter, py("rebound"));
    assert.strictEqual(js(await call(old)), "rebound", "cell contents shared with the new closure");

    // closure -> no closure (fast-call code reads $free from this.func_closure)
    const cap2 = await snippet(m, `
def f():
    return "no closure"
`);
    old.$replaceCode(cap2.f);
    assert.strictEqual(old.func_closure, undefined);
    assert.strictEqual(js(await call(old)), "no closure");
});

test("function -> generator, generator -> function, generator -> generator", async () => {
    const m = await importModule(`
def f(n):
    return n
class K:
    def m(self, n):
        return n
k = K()
bound = k.m
`);
    const old = m.$d.f;
    const oldM = m.$d.K.prototype.m;
    const cap = await snippet(m, `
def f(n, step=1):
    yield n
    yield n + step
def m(self, n):
    yield n * 2
`);
    old.$replaceCode(cap.f);
    oldM.$replaceCode(cap.m);
    assert.ok(!old.func_code.co_fastcall);
    assert.deepStrictEqual(await list(await call(old, py(3))), [3, 4]);
    assert.deepStrictEqual(await list(await call(old, py(3), py(5))), [3, 8]);
    assert.deepStrictEqual(await list(await call(m.$d.bound, py(4))), [8]);

    const cap2 = await snippet(m, `
def f(n):
    yield -n
`);
    old.$replaceCode(cap2.f);
    assert.deepStrictEqual(await list(await call(old, py(3))), [-3]);

    const cap3 = await snippet(m, `
def f(n):
    return ("plain", n)
def m(self, n):
    return ("plain method", n)
`);
    old.$replaceCode(cap3.f);
    oldM.$replaceCode(cap3.m);
    assert.ok(old.func_code.co_fastcall);
    assert.strictEqual(old.func_globals, m.$d, "globals restored after generator (null globals)");
    assert.deepStrictEqual(js(await call(old, py(3))), ["plain", 3]);
    assert.deepStrictEqual(js(await call(m.$d.bound, py(4))), ["plain method", 4]);
});

test("a generator started before the replace keeps running the old code", async () => {
    const m = await importModule(`
def g():
    yield "old1"
    yield "old2"
`);
    const old = m.$d.g;
    const it = await call(old);
    const first = await call(Sk.builtins.next, it);
    const cap = await snippet(m, `
def g():
    yield "new"
`);
    old.$replaceCode(cap.g);
    assert.strictEqual(js(first), "old1");
    assert.strictEqual(js(await call(Sk.builtins.next, it)), "old2");
    assert.deepStrictEqual(await list(await call(old)), ["new"]);
});

test("attribute dict is replaced", async () => {
    const m = await importModule(`
def f():
    pass
f.route = "/old"
f.only_old = 1
`);
    const old = m.$d.f;
    const cap = await snippet(m, `
def f():
    pass
f.route = "/new"
`);
    old.$replaceCode(cap.f);
    assert.strictEqual(js(getattr(old, "route")), "/new");
    assert.ok(!hasattr(old, "only_old"));
    assert.strictEqual(getattr(old, "__dict__"), getattr(cap.f, "__dict__"));
});

test("name, qualname, doc, module and annotations are copied", async () => {
    const m = await importModule(`
class K:
    def m(self) -> int:
        "old doc"
        return 1
`);
    const old = m.$d.K.prototype.m;
    // A class snippet with a stub metaclass, as Stage 3 builds them, so the
    // new method's qualname is K.m.
    const cap0 = await snippet(m, `
def _stub(seed):
    class S(type):
        def __new__(mcls, name, bases, ns):
            return ns
    return S
`);
    const cap = { _S: await call(cap0._stub, py(0)) };
    await runScope(`
class K(metaclass=_S):
    def m(self, a: str = "x") -> str:
        "new doc"
        return a
`, m.$d, cap, "snippet.py");
    const newM = cap.K.mp$subscript(str("m"));
    old.$replaceCode(newM);
    assert.strictEqual(js(getattr(old, "__qualname__")), "K.m");
    assert.strictEqual(js(getattr(old, "__name__")), "m");
    assert.strictEqual(js(getattr(old, "__doc__")), "new doc");
    assert.strictEqual(js(getattr(old, "__module__")), js(getattr(newM, "__module__")));
    const ann = getattr(old, "__annotations__");
    assert.deepStrictEqual(Object.keys(js(ann)).sort(), ["a", "return"]);
    assert.strictEqual(js(Sk.misceval.objectRepr(old)), "<function K.m>");

    // Docstring removed: None, as in a fresh def
    const cap2 = await snippet(m, `
def m(self):
    return 2
`);
    old.$replaceCode(cap2.m);
    assert.ok(Sk.builtin.checkNone(getattr(old, "__doc__")));
    assert.strictEqual(js(getattr(getattr(old, "__annotations__"), "__len__").tp$call([])), 0);
});

test("fast-call and non-fast-call code: tp$call is re-bound each way", async () => {
    const m = await importModule(`
def f(a):
    return a + 1
def g():
    yield 1
`);
    const f = m.$d.f;
    // compiled non-generator defs are fast-call; generators are not
    assert.strictEqual(f.func_code.co_fastcall, 1);
    assert.ok(!m.$d.g.func_code.co_fastcall);

    // compiled -> native JS function (non-fast-call, $funcCall's JS fast path)
    const native = new Sk.builtin.func(function (a) {
        return py("native:" + js(a));
    });
    f.$replaceCode(native);
    assert.strictEqual(js(await call(f, py(1))), "native:1");
    assert.strictEqual(f.func_globals, null);

    // native -> compiled
    const cap = await snippet(m, `
def f(a):
    return a * 3
`);
    f.$replaceCode(cap.f);
    assert.strictEqual(js(await call(f, py(2))), 6);
    assert.strictEqual(f.memoised, 1);
});

test("suspensions: a replaced function and method can suspend (time.sleep)", async () => {
    const m = await importModule(`
import time
def f():
    return "old"
class K:
    def m(self):
        return "old"
bound = K().m
`);
    const cap = await snippet(m, `
def f(n=2):
    out = []
    for i in range(n):
        time.sleep(0.005)
        out.append(i)
    return out
def m(self):
    time.sleep(0.005)
    return "slept"
`);
    m.$d.f.$replaceCode(cap.f);
    m.$d.K.prototype.m.$replaceCode(cap.m);
    assert.deepStrictEqual(js(await call(m.$d.f)), [0, 1]);
    assert.strictEqual(js(await call(m.$d.bound)), "slept");

    // a generator replacement that suspends
    const cap2 = await snippet(m, `
def f():
    time.sleep(0.005)
    yield "gen slept"
`);
    m.$d.f.$replaceCode(cap2.f);
    assert.deepStrictEqual(await list(await call(m.$d.f)), ["gen slept"]);
});

test("zero-arg super() works in a replaced method", async () => {
    const m = await importModule(`
class B:
    def m(self):
        return "B"
class C(B):
    def m(self):
        return "C-old"
bound = C().m
`);
    const cap0 = await snippet(m, `
def _stub():
    class S(type):
        def __new__(mcls, name, bases, ns):
            return ns
    return S
`);
    const cap = { _S: await call(cap0._stub) };
    await runScope(`
class C(metaclass=_S):
    def m(self):
        return "C-new+" + super().m()
`, m.$d, cap, "snippet.py");
    m.$d.C.prototype.m.$replaceCode(cap.C.mp$subscript(str("m")));
    assert.strictEqual(js(await call(m.$d.bound)), "C-new+B");
});

test("bound methods follow a tp$call reassigned on the function (poisoning)", async () => {
    const m = await importModule(`
class K:
    def m(self):
        return 1
bound = K().m
`);
    const fn = m.$d.K.prototype.m;
    fn.tp$call = function () {
        throw new Sk.builtin.RuntimeError("stale function");
    };
    await assert.rejects(call(m.$d.bound), (e) => e instanceof Sk.builtin.RuntimeError);
    // lifting the poison by replacing code re-binds tp$call
    const cap = await snippet(m, `
def m(self):
    return "revived"
`);
    fn.$replaceCode(cap.m);
    assert.strictEqual(js(await call(m.$d.bound)), "revived");
});

test("method objects still work for other callables", async () => {
    const m = await importModule(`
class Callable:
    def __call__(self, *a):
        return a
class K:
    def m(self):
        pass
MethodType = type(K().m)
c = Callable()
bm = MethodType(c, "self")
`);
    assert.deepStrictEqual(js(await call(m.$d.bm, py(1))), ["self", 1]);
});

test("$replaceCode rejects non-functions", async () => {
    const m = await importModule(`
def f():
    pass
`);
    assert.throws(() => m.$d.f.$replaceCode(py(1)), (e) => e instanceof Sk.builtin.TypeError);
});

(async () => {
    let failed = 0;
    for (const t of tests) {
        try {
            await t.fn();
            console.log("PASS " + t.name);
        } catch (e) {
            failed++;
            console.log("FAIL " + t.name);
            console.log("     " + (e && e.toString ? e.toString() : e));
            if (e && e.traceback) {
                console.log("     " + JSON.stringify(e.traceback));
            }
            if (e && e.stack && !(e instanceof Sk.builtin.BaseException)) {
                console.log(e.stack);
            }
        }
    }
    console.log(`\nreplace_code: ${tests.length - failed} passed, ${failed} failed`);
    process.exit(failed ? 1 : 0);
})();
