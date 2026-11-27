/**
 * Execution context primitives for suspension-safe per-fiber state (`Sk.misceval.context`).
 *
 * Modeled on PEP 567 (Python `contextvars`) so Python's `contextvars` stdlib module
 * and JS hosts can share one fiber-scoped context mechanism across Skulpt suspensions
 * and JS->Python FFI callbacks.
 *
 * Terminology
 * -----------
 * - Context (`Context`):
 *     A per-fiber key/value store mapping `ContextVar` instances to their bound values.
 *     Each independent async execution gets its own `Context` so yielding on a
 *     `Suspension` never leaks state into unrelated timers, events, or fibers.
 *
 * - Context variable (`ContextVar`):
 *     A named key used to read (`get`) and update (`set`/`reset`) a value in whichever
 *     `Context` is currently active, with an optional default value and optional
 *     `onChange` listeners for JS hosts.
 *
 * - Token (`Token`):
 *     A single-use receipt returned by `ContextVar.set(value)` recording the previous
 *     binding (or `Token.MISSING` if unset) so `ContextVar.reset(token)` can restore it
 *     only inside the exact `Context` where the token was created.
 *
 * - Fiber:
 *     One logical chain of Python execution that may pause on Skulpt `Suspension`s
 *     (e.g. a Promise, server call, or timer) and resume across JS event-loop turns.
 *     Fibers are started by `Sk.misceval.asyncToPromise` or a JS->Python FFI callback
 *     (`pyWrappedCallable`).
 *
 * - Slice:
 *     A single synchronous run of a fiber between entering/resuming Python and either
 *     yielding a `Suspension`, returning a value, or throwing.
 *
 * - Root context (`rootContext`):
 *     The ambient top-level `Context` active outside any fiber or `Context.run()` call.
 *     Starts marked `_entered = true` so top-level code cannot re-enter it via
 *     `current().run(...)` or share it mutably with an explicit `asyncToPromise` fiber.
 *
 * - Lazy fiber:
 *     An `asyncToPromise` fiber started with an empty context (`activeContext === null`,
 *     `cowActive === false`). To avoid allocating a `Context` + `Map` on the common
 *     no-context fast path, no `Context` is allocated until code inside the fiber
 *     actually writes a `ContextVar` or calls `current()` ("materializing" the fiber's
 *     private `Context`).
 *
 * - Copy-on-write (COW):
 *     How synchronous JS->Python FFI callbacks (`pyWrappedCallable`) share their
 *     caller's `Context` read-only (`cowActive === true`). Reads see caller bindings
 *     with zero allocations; the first write or `current()` call forks a private copy
 *     so callback mutations cannot leak back into the caller.
 *
 * - Handoff:
 *     Transitioning a `pyWrappedCallable` that hit a non-optional or debug `Suspension`
 *     into an async Promise driven by `Sk.misceval.$driveSuspension`, transferring its
 *     private (or snapshotted) `Context` without triggering an extra `onChange` flip.
 *
 * - Entered / ownership (`_entered`):
 *     Exclusivity flag (matching PEP 567) preventing the same `Context` instance from
 *     being entered concurrently by two fibers or re-entered recursively via `ctx.run`.
 *
 * - Watched variable (`watchedVars`):
 *     A `ContextVar` with at least one `onChange(nextValue, prevValue)` listener.
 *     When `watchedVars.size === 0`, context switches skip all listener work.
 */

const MISSING = Object.freeze({});
const EMPTY_MAP = new Map();
const watchedVars = new Set();

/**
 * Resolve the effective value of `cvar` in `ctx`, falling back to the variable's
 * configured default or `MISSING` when unbound. Used to compute `onChange` diffs.
 */
function effectiveValue(ctx, cvar) {
    if (ctx !== null && ctx._data !== null && ctx._data.has(cvar)) {
        return ctx._data.get(cvar);
    }
    return cvar._hasDefault ? cvar._default : MISSING;
}

/**
 * Notify all `onChange` listeners registered on `cvar` when its effective value
 * changes (`!Object.is(nextVal, prevVal)`). Snapshots the listener set so
 * unsubscribing inside a listener is safe.
 */
function notifyVarListeners(cvar, nextVal, prevVal) {
    const listeners = cvar._listeners;
    if (!listeners || listeners.size === 0 || Object.is(nextVal, prevVal)) {
        return;
    }
    const snapshot = Array.from(listeners);
    for (let i = 0; i < snapshot.length; i++) {
        snapshot[i](nextVal, prevVal);
    }
}

/**
 * Diff all watched variables across a context switch (`prevCtx` -> `nextCtx`)
 * and invoke `onChange` listeners for any variable whose effective value changed.
 */
function notifyContextSwitch(prevCtx, nextCtx) {
    if (watchedVars.size === 0 || prevCtx === nextCtx) {
        return;
    }
    const vars = Array.from(watchedVars);
    for (let i = 0; i < vars.length; i++) {
        const cvar = vars[i];
        notifyVarListeners(cvar, effectiveValue(nextCtx, cvar), effectiveValue(prevCtx, cvar));
    }
}

/**
 * Pop the top saved frame from `savedCtxStack`/`savedCowStack`, restore
 * `activeContext` and `cowActive`, and notify watched variables if the active
 * context changed.
 */
function restoreStackFrame(exitedCtx) {
    stackTop--;
    const prevCtx = savedCtxStack[stackTop];
    const prevCow = savedCowStack[stackTop];
    savedCtxStack[stackTop] = null;
    activeContext = prevCtx;
    cowActive = prevCow;
    if (watchedVars.size > 0 && exitedCtx !== prevCtx) {
        notifyContextSwitch(exitedCtx, prevCtx);
    }
}

/**
 * Return the active `Context` ready for mutation, materializing a private `Context`
 * (if in a lazy fiber or COW FFI callback) and lazily initializing its `_data` Map.
 */
function ensureWritableContext() {
    const ctx = current();
    if (ctx._data === null) {
        ctx._data = new Map();
    }
    return ctx;
}

/**
 * Claim exclusive ownership of `ctx`, throwing `RuntimeError` if it is already
 * entered by another fiber or an outer `Context.run()` call.
 */
function acquireContext(ctx) {
    if (ctx._entered) {
        throw new Sk.builtin.RuntimeError("cannot enter context: context is already entered");
    }
    ctx._entered = true;
}

/**
 * Release exclusive ownership of `ctx` once its `Context.run()` or fiber completes,
 * throws, or is aborted.
 */
function releaseContext(ctx) {
    if (ctx !== null) {
        ctx._entered = false;
    }
}

/**
 * Execute one synchronous slice `fn()` with `ctx` active (used by `Context.run`
 * and its suspension wrapper), restoring the caller's context on exit or throw.
 */
function runOwnedSlice(ctx, fn) {
    const prevCtx = activeContext;
    const prevCow = cowActive;
    activeContext = ctx;
    cowActive = false;
    try {
        if (watchedVars.size > 0 && prevCtx !== ctx) {
            notifyContextSwitch(prevCtx, ctx);
        }
        return fn();
    } finally {
        activeContext = prevCtx;
        cowActive = prevCow;
        if (watchedVars.size > 0 && prevCtx !== ctx) {
            notifyContextSwitch(ctx, prevCtx);
        }
    }
}

/**
 * Wrap a `Suspension` returned from `Context.prototype.run` so `ctx` stays exited
 * while suspended, automatically re-enters on each `resume()`, and releases
 * `ctx._entered` when the suspension finishes, throws, or is aborted.
 */
function wrapSuspensionForContext(ctx, susp) {
    const wrapped = new Sk.misceval.Suspension(undefined, susp);
    let resumed = false;
    wrapped.$onAbort = function () {
        if (!resumed) {
            resumed = true;
            releaseContext(ctx);
        }
    };
    wrapped.resume = function () {
        if (resumed || !ctx._entered) {
            throw new Sk.builtin.RuntimeError("cannot enter context: context is already entered");
        }
        resumed = true;
        let stillSuspended = false;
        try {
            const res = runOwnedSlice(ctx, function () {
                return susp.resume();
            });
            if (res instanceof Sk.misceval.Suspension) {
                stillSuspended = true;
                return wrapSuspensionForContext(ctx, res);
            }
            return res;
        } finally {
            if (!stillSuspended) {
                releaseContext(ctx);
            }
        }
    };
    return wrapped;
}

/**
 * Walk a `Suspension` and its `.child` chain, invoking any `$onAbort` hooks so
 * `Context.run` ownership is released when a suspension is rejected or discarded
 * without ever being resumed.
 */
function abortSuspension(susp) {
    let cur = susp;
    while (cur != null) {
        if (typeof cur.$onAbort === "function") {
            cur.$onAbort();
        }
        cur = cur.child;
    }
}

/**
 * Single-use receipt returned by `ContextVar.prototype.set()` for restoring the
 * previous value with `ContextVar.prototype.reset()`.
 */
class Token {
    /**
     * @param {Context} context
     * @param {ContextVar} cvar
     * @param {*} oldValue
     */
    constructor(context, cvar, oldValue) {
        this._context = context;
        this.var = cvar;
        this.oldValue = oldValue;
        this.used = false;
    }
}
Token.MISSING = MISSING;

/**
 * Scoped context variable backed by the currently active execution `Context`.
 */
class ContextVar {
    /**
     * @param {string} name
     * @param {Object=} options
     */
    constructor(name, options) {
        if (typeof name !== "string") {
            throw new Sk.builtin.TypeError("ContextVar name must be a string");
        }
        this.name = name;
        if (options !== undefined && options !== null && Object.prototype.hasOwnProperty.call(options, "default")) {
            this._hasDefault = true;
            this._default = options["default"];
        } else {
            this._hasDefault = false;
            this._default = MISSING;
        }
        this._listeners = null;
    }

    /**
     * Return the value bound to this variable in the currently active `Context`,
     * or `defaultValue` / the configured default if unbound; throws `LookupError`
     * if no default is available.
     *
     * @param {*=} defaultValue
     * @return {*}
     */
    get(defaultValue) {
        if (activeContext !== null && activeContext._data !== null && activeContext._data.has(this)) {
            return activeContext._data.get(this);
        }
        if (arguments.length > 0 && defaultValue !== MISSING) {
            return defaultValue;
        }
        if (this._hasDefault) {
            return this._default;
        }
        throw new Sk.builtin.LookupError(this.name);
    }

    /**
     * Bind `value` in the currently active `Context` (materializing a lazy fiber
     * or forking a COW FFI callback if needed) and return a single-use reset `Token`.
     *
     * @param {*} value
     * @return {Token}
     */
    set(value) {
        const prevEffective = effectiveValue(activeContext, this);
        const ctx = ensureWritableContext();
        const oldValue = ctx._data.has(this) ? ctx._data.get(this) : MISSING;
        ctx._data.set(this, value);
        notifyVarListeners(this, value, prevEffective);
        return new Token(ctx, this, oldValue);
    }

    /**
     * Restore this variable in the currently active `Context` to its state before
     * `token` was created. Validates single-use (`RuntimeError`), matching variable,
     * and matching `Context` (`ValueError`) in CPython precedence order.
     *
     * @param {Token} token
     */
    reset(token) {
        if (!(token instanceof Token)) {
            throw new Sk.builtin.TypeError("expected an instance of Token");
        }
        if (token.used) {
            throw new Sk.builtin.RuntimeError("Token has already been used once");
        }
        if (token.var !== this) {
            throw new Sk.builtin.ValueError("Token was created by a different ContextVar");
        }
        // A COW callback has not forked its own Context yet, so no token belongs to it.
        if (cowActive || token._context !== activeContext) {
            throw new Sk.builtin.ValueError("Token was created in a different Context");
        }
        const prevEffective = effectiveValue(activeContext, this);
        token.used = true;
        if (token.oldValue === MISSING) {
            activeContext._data.delete(this);
        } else {
            activeContext._data.set(this, token.oldValue);
        }
        notifyVarListeners(this, effectiveValue(activeContext, this), prevEffective);
    }

    /**
     * Subscribe to effective value changes for this variable across `set()`, `reset()`,
     * and execution-context switches (including suspension yields and resumes).
     * Listener is called with `(nextValue, prevValue)` where unset values resolve
     * to the variable's default (or `ContextVar.MISSING` if no default was configured).
     *
     * @param {function(*, *)} listener
     * @return {function()} unsubscribe callback
     */
    onChange(listener) {
        if (typeof listener !== "function") {
            throw new Sk.builtin.TypeError("onChange listener must be a function");
        }
        if (this._listeners === null) {
            this._listeners = new Set();
        }
        this._listeners.add(listener);
        watchedVars.add(this);
        const self = this;
        return function unsubscribe() {
            if (self._listeners !== null) {
                self._listeners.delete(listener);
                if (self._listeners.size === 0) {
                    watchedVars.delete(self);
                }
            }
        };
    }
}
ContextVar.MISSING = MISSING;

/**
 * Execution context mapping `ContextVar` keys to values for a single fiber.
 * Its internal `_data` Map is allocated lazily (`null` while empty).
 */
class Context {
    /**
     * @param {(Context|Map|Array)=} entries
     */
    constructor(entries) {
        if (entries instanceof Context) {
            this._data = entries._data !== null && entries._data.size > 0 ? new Map(entries._data) : null;
        } else if (entries !== undefined && entries !== null) {
            this._data = new Map(entries);
        } else {
            this._data = null;
        }
        this._entered = false;
    }

    /**
     * Read `cvar` directly from this `Context`, returning `defaultValue` if absent.
     *
     * @param {ContextVar} cvar
     * @param {*=} defaultValue
     * @return {*}
     */
    get(cvar, defaultValue) {
        if (this._data !== null && this._data.has(cvar)) {
            return this._data.get(cvar);
        }
        return defaultValue;
    }

    /**
     * Return whether `cvar` has an explicit binding in this `Context`.
     *
     * @param {ContextVar} cvar
     * @return {boolean}
     */
    has(cvar) {
        return this._data !== null && this._data.has(cvar);
    }

    /**
     * Return a shallow copy of this `Context` with `_entered = false`.
     *
     * @return {Context}
     */
    copy() {
        return new Context(this);
    }

    /**
     * Return the number of `ContextVar` bindings stored in this `Context`.
     *
     * @return {number}
     */
    size() {
        return this._data !== null ? this._data.size : 0;
    }

    /**
     * Iterate over bound `ContextVar` keys in this `Context`.
     *
     * @return {Iterator}
     */
    keys() {
        return (this._data !== null ? this._data : EMPTY_MAP).keys();
    }

    /**
     * Iterate over bound values in this `Context`.
     *
     * @return {Iterator}
     */
    values() {
        return (this._data !== null ? this._data : EMPTY_MAP).values();
    }

    /**
     * Iterate over `[ContextVar, value]` pairs in this `Context`.
     *
     * @return {Iterator}
     */
    entries() {
        return (this._data !== null ? this._data : EMPTY_MAP).entries();
    }

    /**
     * Run `fn(...args)` inside this `Context`. If `fn` returns a `Sk.misceval.Suspension`,
     * this `Context` is exited while suspended and automatically re-entered on each
     * resume until the suspension completes, throws, or is aborted.
     *
     * @param {function(...*)} fn
     * @param {...*} args
     * @return {*}
     */
    run(fn) {
        if (typeof fn !== "function") {
            throw new Sk.builtin.TypeError("Context.run expects a callable");
        }
        const args = arguments.length > 1 ? Array.prototype.slice.call(arguments, 1) : null;
        acquireContext(this);
        let suspended = false;
        try {
            const res = runOwnedSlice(this, function () {
                return args === null ? fn() : fn.apply(undefined, args);
            });
            if (res instanceof Sk.misceval.Suspension) {
                suspended = true;
                return wrapSuspensionForContext(this, res);
            }
            return res;
        } finally {
            if (!suspended) {
                releaseContext(this);
            }
        }
    }
}

/**
 * Active-state invariants (see Terminology above):
 * - `activeContext === rootContext`, `cowActive === false`: ambient top-level context.
 * - `activeContext === null`, `cowActive === false`: unmaterialized lazy fiber.
 * - `cowActive === true`: synchronous FFI `pyWrappedCallable` borrowing `activeContext`
 *   read-only until first write or `current()`.
 *
 * `savedCtxStack` and `savedCowStack` reuse module-level arrays indexed by `stackTop`
 * so entering and exiting slices allocates nothing on the hot path.
 */
const rootContext = new Context();
rootContext._entered = true;
let activeContext = rootContext;
let cowActive = false;

const savedCtxStack = [];
const savedCowStack = [];
let stackTop = 0;

/**
 * Return the currently active execution `Context`. Materializes a private `Context`
 * (marked `_entered = true`) if called inside a lazy fiber or COW FFI callback.
 *
 * @return {Context}
 */
function current() {
    if (cowActive) {
        activeContext = activeContext !== null ? activeContext.copy() : new Context();
        activeContext._entered = true;
        cowActive = false;
    } else if (activeContext === null) {
        activeContext = new Context();
        activeContext._entered = true;
    }
    return activeContext;
}

/**
 * Return a shallow copy of the currently active execution `Context`.
 *
 * @return {Context}
 */
function copy() {
    return activeContext !== null ? activeContext.copy() : new Context();
}

/**
 * Snapshot the active `Context` for a new `asyncToPromise` fiber only if it holds
 * at least one binding; otherwise return `null` so the new fiber stays lazy.
 */
function snapshotIfNonEmpty() {
    if (activeContext === null || activeContext._data === null || activeContext._data.size === 0) {
        return null;
    }
    return activeContext.copy();
}

/**
 * Enter a fiber slice (`fiberCtx` is an acquired `Context`, or `null` for a lazy
 * fiber). Rolls back the stack push cleanly if an `onChange` listener throws.
 */
function pushFiber(fiberCtx) {
    const prevCtx = activeContext;
    savedCtxStack[stackTop] = prevCtx;
    savedCowStack[stackTop] = cowActive;
    stackTop++;
    activeContext = fiberCtx;
    cowActive = false;
    if (watchedVars.size > 0 && prevCtx !== fiberCtx) {
        try {
            notifyContextSwitch(prevCtx, fiberCtx);
        } catch (e) {
            restoreStackFrame(fiberCtx);
            throw e;
        }
    }
}

/**
 * Exit a fiber slice and restore the caller's context. If a lazy fiber (`fiberCtx === null`)
 * materialized a `Context` during the slice, returns that newly created `Context` so
 * `asyncToPromise` / `$driveSuspension` can reuse it across subsequent resumes.
 */
function popFiber(fiberCtx) {
    const exitedCtx = activeContext;
    const materialized = fiberCtx === null && exitedCtx !== null ? exitedCtx : null;
    try {
        restoreStackFrame(exitedCtx);
    } catch (e) {
        if (materialized !== null) {
            releaseContext(materialized);
        }
        throw e;
    }
    return materialized;
}

/**
 * Enter a copy-on-write FFI callback (`pyWrappedCallable`), borrowing the caller's
 * active `Context` read-only with zero allocations.
 */
function pushCow() {
    savedCtxStack[stackTop] = activeContext;
    savedCowStack[stackTop] = cowActive;
    stackTop++;
    cowActive = true;
}

/**
 * Exit a synchronous COW FFI callback, releasing its private `Context` if it forked
 * one and restoring the caller's saved frame.
 */
function popCow() {
    const exitedCtx = activeContext;
    if (!cowActive && exitedCtx !== null) {
        releaseContext(exitedCtx);
    }
    restoreStackFrame(exitedCtx);
}

/**
 * Exit a COW FFI callback that is handing a `Suspension` off to
 * `Sk.misceval.$driveSuspension`. Returns an already-acquired `Context` if the
 * callback mutated context or inherited non-empty caller bindings, or `null`
 * to stay in lazy-fiber mode.
 *
 * @return {?Context}
 */
function popCowForHandoff() {
    const exitedCtx = activeContext;
    let handedCtx = null;
    if (!cowActive) {
        // Callback materialized its own Context (`_entered` is already true).
        handedCtx = exitedCtx;
    } else if (exitedCtx !== null && exitedCtx._data !== null && exitedCtx._data.size > 0) {
        handedCtx = exitedCtx.copy();
        handedCtx._entered = true;
    }
    try {
        restoreStackFrame(exitedCtx);
    } catch (e) {
        releaseContext(handedCtx);
        throw e;
    }
    return handedCtx;
}

/**
 * @namespace Sk.misceval.context
 */
Sk.misceval.context = {
    Context: Context,
    ContextVar: ContextVar,
    Token: Token,
    current: current,
    copy: copy,
    $acquire: acquireContext,
    $release: releaseContext,
    $abortSuspension: abortSuspension,
    $snapshotIfNonEmpty: snapshotIfNonEmpty,
    $pushFiber: pushFiber,
    $popFiber: popFiber,
    $pushCow: pushCow,
    $popCow: popCow,
    $popCowForHandoff: popCowForHandoff,
};
Sk.exportSymbol("Sk.misceval.context", Sk.misceval.context);
Sk.exportSymbol("Sk.misceval.context.Context", Context);
Sk.exportSymbol("Sk.misceval.context.ContextVar", ContextVar);
Sk.exportSymbol("Sk.misceval.context.Token", Token);
Sk.exportSymbol("Sk.misceval.context.current", current);
Sk.exportSymbol("Sk.misceval.context.copy", copy);
