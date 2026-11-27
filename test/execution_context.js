const assert = require("assert");
const fs = require("fs");
const load = require("../support/run/require-skulpt").requireSkulpt;

load(false);
Sk.configure({
    read: (file) => fs.readFileSync(file, "utf8"),
    __future__: Sk.python3,
});

const { Context, ContextVar, Token, current, copy } = Sk.misceval.context;

function deferred() {
    let resolve, reject;
    const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
}

async function runTests() {
    // 1. Basic ContextVar get/set/reset/default/MISSING semantics
    {
        const noDefault = new ContextVar("no_default");
        assert.throws(() => noDefault.get(), (e) => e instanceof Sk.builtin.LookupError);
        assert.strictEqual(noDefault.get("fallback"), "fallback");

        const withDefault = new ContextVar("with_default", { default: 0 });
        assert.strictEqual(withDefault.get(), 0);
        assert.strictEqual(withDefault.get(99), 99);

        const ctx = new Context();
        ctx.run(() => {
            const t1 = withDefault.set(1);
            assert.strictEqual(withDefault.get(), 1);
            assert.strictEqual(t1.oldValue, Token.MISSING);
            const t2 = withDefault.set(2);
            assert.strictEqual(withDefault.get(), 2);
            assert.strictEqual(t2.oldValue, 1);
            withDefault.reset(t2);
            assert.strictEqual(withDefault.get(), 1);
            withDefault.reset(t1);
            assert.strictEqual(withDefault.get(), 0);
            // Reusing a token raises RuntimeError (even in another context or var)
            assert.throws(() => withDefault.reset(t1), (e) => e instanceof Sk.builtin.RuntimeError);
            assert.throws(() => noDefault.reset(t1), (e) => e instanceof Sk.builtin.RuntimeError);
        });
        assert.strictEqual(withDefault.get(), 0);

        // Top-level ambient rootContext is already entered and rejects re-entry
        assert.throws(() => current().run(() => {}), (e) => e instanceof Sk.builtin.RuntimeError);
        await assert.rejects(
            Sk.misceval.asyncToPromise(() => {}, undefined, current()),
            (e) => e instanceof Sk.builtin.RuntimeError
        );

        // Resetting a token in a different context or with a different ContextVar raises ValueError
        let tokenFromCtx1;
        const ctx1 = new Context();
        const ctx2 = new Context();
        ctx1.run(() => {
            tokenFromCtx1 = withDefault.set(42);
        });
        ctx2.run(() => {
            assert.throws(() => withDefault.reset(tokenFromCtx1), (e) => e instanceof Sk.builtin.ValueError);
        });
        ctx1.run(() => {
            assert.throws(() => noDefault.reset(tokenFromCtx1), (e) => e instanceof Sk.builtin.ValueError);
            withDefault.reset(tokenFromCtx1);
        });

        // Re-entering an already-entered Context raises RuntimeError
        assert.throws(() => {
            ctx1.run(() => ctx1.run(() => {}));
        }, (e) => e instanceof Sk.builtin.RuntimeError);

        // Re-entering active fiber's own current() context inside asyncToPromise raises RuntimeError
        await assert.rejects(
            Sk.misceval.asyncToPromise(() => {
                current().run(() => {});
            }),
            (e) => e instanceof Sk.builtin.RuntimeError
        );

        // A throwing onChange listener during fiber push rolls back context stack cleanly
        const throwVar = new ContextVar("throw_on_enter", { default: 0 });
        const unsubThrow = throwVar.onChange((next) => {
            if (next === 1) {
                throw new Error("listener boom");
            }
        });
        try {
            const badCtx = new Context([[throwVar, 1]]);
            await assert.rejects(
                Sk.misceval.asyncToPromise(() => throwVar.get(), undefined, badCtx),
                /listener boom/
            );
            assert.strictEqual(throwVar.get(), 0);
            // badCtx was released despite listener throwing
            unsubThrow();
            assert.strictEqual(badCtx.run(() => throwVar.get()), 1);
        } finally {
            unsubThrow();
        }
    }

    // 2. asyncToPromise isolates concurrent fibers across Sk.promise suspensions & notifies onChange
    {
        const depthVar = new ContextVar("depth", { default: 0 });
        const transitions = [];
        const unsub = depthVar.onChange((next, prev) => {
            transitions.push([prev, next]);
        });

        const d1 = deferred();
        const d2 = deferred();
        const observed = {};

        try {
            const fiber1 = Sk.misceval.asyncToPromise(() => {
                depthVar.set(1);
                observed.f1Before = depthVar.get();
                return Sk.misceval.chain(Sk.misceval.promiseToSuspension(d1.promise), () => {
                    observed.f1After = depthVar.get();
                    depthVar.set(2);
                    return depthVar.get();
                });
            });

            // Immediately after fiber1 suspends, active context is back to root (0)
            observed.whileSuspended = depthVar.get();

            const fiber2 = Sk.misceval.asyncToPromise(() => {
                observed.f2Start = depthVar.get();
                depthVar.set(10);
                return Sk.misceval.chain(Sk.misceval.promiseToSuspension(d2.promise), () => {
                    observed.f2After = depthVar.get();
                    return depthVar.get();
                });
            });

            assert.strictEqual(depthVar.get(), 0);

            d2.resolve();
            assert.strictEqual(await fiber2, 10);
            assert.strictEqual(depthVar.get(), 0);

            d1.resolve();
            assert.strictEqual(await fiber1, 2);
            assert.strictEqual(depthVar.get(), 0);

            assert.deepStrictEqual(observed, {
                f1Before: 1,
                whileSuspended: 0,
                f2Start: 0,
                f2After: 10,
                f1After: 1,
            });
            assert.deepStrictEqual(transitions, [
                [0, 1],   // f1 sets 1
                [1, 0],   // f1 suspends -> root
                [0, 10],  // f2 sets 10
                [10, 0],  // f2 suspends -> root
                [0, 10],  // f2 resumes
                [10, 0],  // f2 finishes -> root
                [0, 1],   // f1 resumes
                [1, 2],   // f1 sets 2
                [2, 0],   // f1 finishes -> root
            ]);
        } finally {
            unsub();
        }
    }

    // 3. Custom suspension handlers (e.g. timer) preserve fiber context when calling r.resume()
    {
        const tagVar = new ContextVar("tag", { default: "root" });
        const customHandlers = {
            "test.delay": (r) =>
                new Promise((resolve, reject) => {
                    // Handler scheduling runs in root context, not the suspended fiber's context
                    assert.strictEqual(tagVar.get(), "root");
                    setTimeout(() => {
                        try {
                            resolve(r.resume());
                        } catch (e) {
                            reject(e);
                        }
                    }, 10);
                }),
            "test.passthrough": () => null,
        };

        const result = await Sk.misceval.asyncToPromise(() => {
            tagVar.set("in-timer");
            const s1 = new Sk.misceval.Suspension();
            s1.data = { type: "test.delay" };
            s1.resume = () => {
                assert.strictEqual(tagVar.get(), "in-timer");
                const s2 = new Sk.misceval.Suspension();
                s2.optional = true;
                s2.data = { type: "test.passthrough" };
                s2.resume = () => tagVar.get();
                return s2;
            };
            return s1;
        }, customHandlers);

        assert.strictEqual(result, "in-timer");
        assert.strictEqual(tagVar.get(), "root");
    }

    // 4. Explicit context passed to asyncToPromise + concurrent entry rejection
    {
        const roleVar = new ContextVar("role", { default: "guest" });
        const d = deferred();
        const explicitCtx = new Context([[roleVar, "admin"]]);

        const p1 = Sk.misceval.asyncToPromise(() => {
            assert.strictEqual(roleVar.get(), "admin");
            return Sk.misceval.chain(Sk.misceval.promiseToSuspension(d.promise), () => roleVar.get());
        }, undefined, explicitCtx);

        // Concurrent entry of the same Context rejects with RuntimeError
        await assert.rejects(
            Sk.misceval.asyncToPromise(() => roleVar.get(), undefined, explicitCtx),
            (e) => e instanceof Sk.builtin.RuntimeError
        );
        assert.throws(() => explicitCtx.run(() => {}), (e) => e instanceof Sk.builtin.RuntimeError);

        d.resolve();
        assert.strictEqual(await p1, "admin");

        // After p1 completes, explicitCtx can be entered again
        assert.strictEqual(explicitCtx.run(() => roleVar.get()), "admin");
    }

    // 5. Context.prototype.run across suspensions (nested inside asyncToPromise)
    {
        const scopeVar = new ContextVar("scope", { default: "root" });
        const d = deferred();
        const innerCtx = new Context([[scopeVar, "inner"]]);
        const trace = [];

        const p = Sk.misceval.asyncToPromise(() => {
            scopeVar.set("outer");
            trace.push("before:" + scopeVar.get());
            return Sk.misceval.chain(
                innerCtx.run(() => {
                    trace.push("inner1:" + scopeVar.get());
                    scopeVar.set("inner-mut");
                    return Sk.misceval.chain(Sk.misceval.promiseToSuspension(d.promise), () => {
                        trace.push("inner2:" + scopeVar.get());
                        return scopeVar.get();
                    });
                }),
                (val) => {
                    trace.push("after:" + scopeVar.get());
                    return val;
                }
            );
        });

        trace.push("suspended:" + scopeVar.get());
        d.resolve();
        assert.strictEqual(await p, "inner-mut");
        assert.deepStrictEqual(trace, [
            "before:outer",
            "inner1:inner",
            "suspended:root",
            "inner2:inner-mut",
            "after:outer",
        ]);
        assert.strictEqual(innerCtx.get(scopeVar), "inner-mut");

        // Aborted suspensions (sync retryOptionalSuspensionOrThrow and rejected custom handler) release Context ownership
        const abortCtx = new Context([[scopeVar, "abort-test"]]);
        const sBlocked = new Sk.misceval.Suspension();
        sBlocked.data = { type: "test.unhandled" };
        sBlocked.resume = () => "never";
        assert.throws(
            () => Sk.misceval.retryOptionalSuspensionOrThrow(abortCtx.run(() => sBlocked)),
            (e) => e instanceof Sk.builtin.SuspensionError
        );
        assert.strictEqual(abortCtx.run(() => scopeVar.get()), "abort-test");

        const sReject = new Sk.misceval.Suspension();
        sReject.data = { type: "test.reject" };
        sReject.resume = () => "never";
        await assert.rejects(
            Sk.misceval.asyncToPromise(
                () => abortCtx.run(() => sReject),
                { "test.reject": () => Promise.reject(new Error("aborted handler")) }
            ),
            /aborted handler/
        );
        assert.strictEqual(abortCtx.run(() => scopeVar.get()), "abort-test");
    }

    // 6. FFI pyWrappedCallable: inherits COW copy on sync re-entry, isolates mutations & blocks outer token reset
    {
        const privVar = new ContextVar("priv", { default: false });
        const d = deferred();
        const dReadOnly = deferred();
        const observed = {};
        let listenerPromise = null;
        let readOnlyPromise = null;
        let outerToken = null;

        Sk.builtins.get_priv = new Sk.builtin.func(() => Sk.ffi.remapToPy(privVar.get()));
        Sk.builtins.set_priv = new Sk.builtin.func((v) => {
            outerToken = privVar.set(Sk.ffi.remapToJs(v));
            return Sk.builtin.none.none$;
        });
        Sk.builtins.try_reset_outer_token = new Sk.builtin.func(() => {
            privVar.reset(outerToken);
            return Sk.builtin.none.none$;
        });
        Sk.builtins.suspend_now = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(d.promise));
        Sk.builtins.suspend_readonly = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(dReadOnly.promise));
        Sk.builtins.record = new Sk.builtin.func((k, v) => {
            observed[Sk.ffi.remapToJs(k)] = Sk.ffi.remapToJs(v);
            return Sk.builtin.none.none$;
        });

        let registered = null;
        let registeredReadOnly = null;
        Sk.builtins.js_host = Sk.ffi.proxy({
            mapValues(arr, fn) {
                return arr.map((x) => fn(x));
            },
            callSync(fn) {
                return fn();
            },
            register(fn) {
                registered = fn;
            },
            registerReadOnly(fn) {
                registeredReadOnly = fn;
            },
            dispatchSync() {
                listenerPromise = registered();
            },
            dispatchReadOnlySync() {
                readOnlyPromise = registeredReadOnly();
            },
        });

        const privTransitions = [];
        const unsubPriv = privVar.onChange((next, prev) => {
            privTransitions.push([prev, next]);
        });

        const pySource = `
# Synchronous JS helper inherits caller's context
set_priv(True)
mapped = js_host.mapValues([1, 2], lambda x: (x, get_priv()))
record("mapped_privs", [p for _, p in mapped])

# Resetting outer token inside COW callback must raise ValueError and not mutate outer context
try:
    js_host.callSync(try_reset_outer_token)
    record("outer_reset_rejected", False)
except ValueError:
    record("outer_reset_rejected", True)
record("still_priv_after_rejected_reset", get_priv())

# Read-only callback that suspends snapshots caller context before caller mutates it
def readonly_listener():
    before = get_priv()
    suspend_readonly()
    return [before, get_priv()]

js_host.registerReadOnly(readonly_listener)
js_host.dispatchReadOnlySync()

set_priv(False)

# Sync-dispatched callback mutating context then suspending must not leak to caller
def listener():
    record("listener_start", get_priv())
    set_priv(True)
    record("listener_before_suspend", get_priv())
    suspend_now()
    record("listener_after_resume", get_priv())
    set_priv(False)
    return "done"

js_host.register(listener)
js_host.dispatchSync()
record("caller_after_dispatch", get_priv())
`;

        try {
            await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("<ffi_ctx>", false, pySource, true));
            observed.rootWhileListenerSuspended = privVar.get();

            // Standalone check while listener is suspended sees root (false)
            assert.strictEqual(privVar.get(), false);

            dReadOnly.resolve();
            observed.readOnlySnapshot = await readOnlyPromise;

            d.resolve();
            assert.strictEqual(await listenerPromise, "done");
            observed.rootAfterListenerDone = privVar.get();

            assert.deepStrictEqual(observed, {
                mapped_privs: [true, true],
                outer_reset_rejected: true,
                still_priv_after_rejected_reset: true,
                listener_start: false,
                listener_before_suspend: true,
                caller_after_dispatch: false,
                rootWhileListenerSuspended: false,
                readOnlySnapshot: [true, true],
                listener_after_resume: true,
                rootAfterListenerDone: false,
            });
            // Verify FFI suspension handoff does not emit a spurious extra onChange round-trip
            assert.deepStrictEqual(privTransitions, [
                [false, true],   // outer set_priv(True)
                [true, false],   // outer set_priv(False)
                [false, true],   // listener set_priv(True)
                [true, false],   // listener suspends -> caller (no extra round-trip!)
                [false, true],   // readOnly listener resumes
                [true, false],   // readOnly listener finishes
                [false, true],   // listener resumes
                [true, false],   // listener set_priv(False)
            ]);

            assert.strictEqual(copy().size(), 0);

            // Throwing onChange listener during FFI handoff must not double-pop or corrupt context stack
            const boomVar = new ContextVar("ffi_handoff_boom", { default: 0 });
            const dBoom = deferred();
            let boomTriggered = false;
            const unsubBoom = boomVar.onChange((next, prev) => {
                if (prev === 1 && next === 0 && !boomTriggered) {
                    boomTriggered = true;
                    throw new Error("handoff listener boom");
                }
            });
            Sk.builtins.set_boom = new Sk.builtin.func(() => {
                boomVar.set(1);
                return Sk.builtin.none.none$;
            });
            Sk.builtins.susp_boom = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(dBoom.promise));
            let boomCb = null;
            Sk.builtins.cap_boom = Sk.ffi.proxy({ set(fn) { boomCb = fn; } });
            try {
                await Sk.misceval.asyncToPromise(() =>
                    Sk.importMainWithBody("<boom_cb>", false, "def f():\n    set_boom()\n    susp_boom()\ncap_boom.set(f)\n", true)
                );
                assert.throws(() => boomCb(), /handoff listener boom/);
                assert.strictEqual(boomVar.get(), 0);
                // Context stack remains intact for subsequent fibers
                assert.strictEqual(await Sk.misceval.asyncToPromise(() => {
                    boomVar.set(2);
                    return boomVar.get();
                }), 2);
                assert.strictEqual(boomVar.get(), 0);
            } finally {
                unsubBoom();
                delete Sk.builtins.set_boom;
                delete Sk.builtins.susp_boom;
                delete Sk.builtins.cap_boom;
            }
        } finally {
            unsubPriv();
            delete Sk.builtins.get_priv;
            delete Sk.builtins.set_priv;
            delete Sk.builtins.try_reset_outer_token;
            delete Sk.builtins.suspend_now;
            delete Sk.builtins.suspend_readonly;
            delete Sk.builtins.record;
            delete Sk.builtins.js_host;
        }
    }

    // 7. Python contextvars + decimal.localcontext isolation across concurrent suspensions
    {
        const dA = deferred();
        const dB = deferred();
        const results = {};

        Sk.builtins.pause_a = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(dA.promise));
        Sk.builtins.pause_b = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(dB.promise));
        Sk.builtins.record_py = new Sk.builtin.func((k, v) => {
            results[Sk.ffi.remapToJs(k)] = Sk.ffi.remapToJs(v);
            return Sk.builtin.none.none$;
        });

        try {
            const setupMod = await Sk.misceval.asyncToPromise(() =>
                Sk.importMainWithBody(
                    "<ctx_py_mod>",
                    false,
                    `
import contextvars
import decimal

cv = contextvars.ContextVar("cv", default="root")

def fiber_a():
    cv.set("A")
    with decimal.localcontext(prec=4):
        before = (cv.get(), str(decimal.Decimal(1) / decimal.Decimal(3)))
        pause_a()
        after = (cv.get(), str(decimal.Decimal(1) / decimal.Decimal(3)))
    record_py("a_before", list(before))
    record_py("a_after", list(after))
    record_py("a_post_local", decimal.getcontext().prec)

def fiber_b():
    start_cv = cv.get()
    start_prec = decimal.getcontext().prec
    cv.set("B")
    with decimal.localcontext(prec=6):
        pause_b()
        during = (cv.get(), str(decimal.Decimal(1) / decimal.Decimal(3)))
    record_py("b_start", [start_cv, start_prec])
    record_py("b_during", list(during))

def run_nested_context():
    cv.set("outer")
    ctx = contextvars.Context()
    def inner():
        cv.set("inner")
        pause_a()
        return cv.get()
    val = ctx.run(inner)
    return (val, cv.get())
`,
                    true
                )
            );

            const modDict = setupMod.$d;
            const pA = Sk.misceval.callAsync(null, modDict.fiber_a);
            const pB = Sk.misceval.callAsync(null, modDict.fiber_b);

            dB.resolve();
            await pB;
            dA.resolve();
            await pA;

            assert.deepStrictEqual(results, {
                b_start: ["root", 28],
                b_during: ["B", "0.333333"],
                a_before: ["A", "0.3333"],
                a_after: ["A", "0.3333"],
                a_post_local: 28,
            });

            // Also test Python Context.run() across a suspension
            const dNested = deferred();
            Sk.builtins.pause_a = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(dNested.promise));
            const pNested = Sk.misceval.callAsync(null, modDict.run_nested_context);
            dNested.resolve();
            const nestedRes = Sk.ffi.remapToJs(await pNested);
            assert.deepStrictEqual(nestedRes, ["inner", "outer"]);
        } finally {
            delete Sk.builtins.pause_a;
            delete Sk.builtins.pause_b;
            delete Sk.builtins.record_py;
        }
    }

    console.log("Execution context tests passed");
}

runTests().catch((err) => {
    console.error(err);
    process.exit(1);
});
