function $builtinmodule() {
    const {
        str: pyStr,
        none: { none$: pyNone },
        NotImplemented: { NotImplemented$: pyNotImplemented },
        dict: pyDict,
        list: pyList,
        tuple: pyTuple,
        TypeError,
        KeyError,
        LookupError,
        checkString,
    } = Sk.builtin;

    const {
        buildNativeClass,
        setUpModuleMethods,
        checkNoArgs,
        checkNoKwargs,
        checkArgsLen,
        copyKeywordsToNamedArgs,
    } = Sk.abstr;

    const {
        callsimArray: pyCall,
        callsimOrSuspendArray: pyCallOrSuspend,
        richCompareBool,
    } = Sk.misceval;

    const {
        Context: JsContext,
        ContextVar: JsContextVar,
        Token: JsContextToken,
        copy: jsCopyContext,
    } = Sk.misceval.context;

    const keysStr = new pyStr("keys");
    const valuesStr = new pyStr("values");
    const itemsStr = new pyStr("items");

    // JsContext is shared with internal stdlib/host JS ContextVars (e.g. decimal);
    // only Python-created ContextVars are exposed via Python Context mapping views.
    const pyVarRegistry = new WeakMap();

    const _MissingType = buildNativeClass("contextvars._TokenMissing", {
        constructor: function _TokenMissing() {},
        flags: { sk$unacceptableBase: true },
        slots: {
            $r() {
                return new pyStr("<Token.MISSING>");
            },
        },
    });
    const TOKEN_MISSING = new _MissingType();

    const Token = buildNativeClass("contextvars.Token", {
        constructor: function Token(pyVar, jsToken) {
            this.$var = pyVar;
            this.$token = jsToken;
        },
        flags: { sk$unacceptableBase: true },
        slots: {
            tp$new() {
                throw new TypeError("cannot create 'contextvars.Token' instances");
            },
            $r() {
                const used = this.$token.used ? " used" : "";
                const varRepr = Sk.misceval.objectRepr(this.$var);
                return new pyStr("<Token" + used + " var=" + varRepr + ">");
            },
        },
        proto: {
            MISSING: TOKEN_MISSING,
        },
        getsets: {
            var: {
                $get() {
                    return this.$var;
                },
            },
            old_value: {
                $get() {
                    if (this.$token.oldValue === JsContextToken.MISSING) {
                        return TOKEN_MISSING;
                    }
                    return this.$token.oldValue;
                },
            },
        },
        classmethods: Sk.generic.classGetItem,
    });

    const ContextVar = buildNativeClass("contextvars.ContextVar", {
        constructor: function ContextVar(name, jsVar, hasDefault, defaultVal) {
            this.$name = name;
            this.$jsVar = jsVar;
            this.$hasDefault = hasDefault;
            this.$default = defaultVal;
            pyVarRegistry.set(jsVar, this);
        },
        flags: { sk$unacceptableBase: true },
        slots: {
            tp$new(args, kwargs) {
                if (args.length > 1) {
                    throw new TypeError("ContextVar() takes at most 1 positional argument (" + args.length + " given)");
                }
                const parsed = copyKeywordsToNamedArgs("ContextVar", ["name", "default"], args, kwargs, [
                    JsContextVar.MISSING,
                ]);
                const pyName = parsed[0];
                const defaultVal = parsed[1];
                if (!checkString(pyName)) {
                    throw new TypeError("context variable name must be a str");
                }
                const hasDefault = defaultVal !== JsContextVar.MISSING;
                const jsVar = hasDefault
                    ? new JsContextVar(pyName.v, { default: defaultVal })
                    : new JsContextVar(pyName.v);
                return new ContextVar(pyName, jsVar, hasDefault, defaultVal);
            },
            $r() {
                const nameRepr = Sk.misceval.objectRepr(this.$name);
                if (this.$hasDefault) {
                    const defRepr = Sk.misceval.objectRepr(this.$default);
                    return new pyStr("<ContextVar name=" + nameRepr + " default=" + defRepr + ">");
                }
                return new pyStr("<ContextVar name=" + nameRepr + ">");
            },
        },
        getsets: {
            name: {
                $get() {
                    return this.$name;
                },
            },
        },
        methods: {
            get: {
                $meth(args, kwargs) {
                    checkNoKwargs("get", kwargs);
                    checkArgsLen("get", args, 0, 1);
                    const defaultVal = args.length === 1 ? args[0] : JsContextVar.MISSING;
                    try {
                        return this.$jsVar.get(defaultVal);
                    } catch (e) {
                        if (e instanceof LookupError) {
                            throw new LookupError(this);
                        }
                        throw e;
                    }
                },
                $flags: { FastCall: true },
            },
            set: {
                $meth(value) {
                    const jsToken = this.$jsVar.set(value);
                    return new Token(this, jsToken);
                },
                $flags: { OneArg: true },
            },
            reset: {
                $meth(token) {
                    if (!(token instanceof Token)) {
                        throw new TypeError("expected an instance of Token and got " + Sk.abstr.typeName(token));
                    }
                    this.$jsVar.reset(token.$token);
                    return pyNone;
                },
                $flags: { OneArg: true },
            },
        },
        classmethods: Sk.generic.classGetItem,
    });

    function checkContextVarKey(key) {
        if (!(key instanceof ContextVar)) {
            throw new TypeError("a ContextVar key was expected, got " + Sk.abstr.typeName(key));
        }
    }

    function forEachPyEntry(jsCtx, fn) {
        for (const pair of jsCtx.entries()) {
            const pyVar = pyVarRegistry.get(pair[0]);
            if (pyVar !== undefined) {
                fn(pyVar, pair[1]);
            }
        }
    }

    function countPyEntries(jsCtx) {
        let count = 0;
        forEachPyEntry(jsCtx, () => {
            count++;
        });
        return count;
    }

    function snapshotPyDict(jsCtx) {
        const flat = [];
        forEachPyEntry(jsCtx, (pyVar, value) => {
            flat.push(pyVar, value);
        });
        return new pyDict(flat);
    }

    const Context = buildNativeClass("contextvars.Context", {
        constructor: function Context(jsCtx) {
            this.$ctx = jsCtx || new JsContext();
        },
        flags: { sk$unacceptableBase: true },
        slots: {
            tp$new(args, kwargs) {
                checkNoArgs("Context", args, kwargs);
                return new Context(new JsContext());
            },
            tp$hash: pyNone,
            sq$length() {
                return countPyEntries(this.$ctx);
            },
            mp$length() {
                return countPyEntries(this.$ctx);
            },
            sq$contains(key) {
                checkContextVarKey(key);
                return this.$ctx.has(key.$jsVar);
            },
            mp$subscript(key) {
                checkContextVarKey(key);
                if (!this.$ctx.has(key.$jsVar)) {
                    throw new KeyError(key);
                }
                return this.$ctx.get(key.$jsVar);
            },
            tp$iter() {
                const keys = [];
                forEachPyEntry(this.$ctx, (pyVar) => {
                    keys.push(pyVar);
                });
                return new pyList(keys).tp$iter();
            },
            tp$richcompare(other, op) {
                if ((op !== "Eq" && op !== "NotEq") || !(other instanceof Context)) {
                    return pyNotImplemented;
                }
                if (this === other) {
                    return op === "Eq";
                }
                let equal = countPyEntries(this.$ctx) === countPyEntries(other.$ctx);
                if (equal) {
                    for (const pair of this.$ctx.entries()) {
                        const pyVar = pyVarRegistry.get(pair[0]);
                        if (pyVar === undefined) {
                            continue;
                        }
                        if (!other.$ctx.has(pyVar.$jsVar)) {
                            equal = false;
                            break;
                        }
                        const valA = pair[1];
                        const valB = other.$ctx.get(pyVar.$jsVar);
                        if (valA !== valB && !richCompareBool(valA, valB, "Eq")) {
                            equal = false;
                            break;
                        }
                    }
                }
                return op === "Eq" ? equal : !equal;
            },
            $r() {
                // Match CPython's repr for contextvars.Context.
                return new pyStr("<_contextvars.Context object>");
            },
        },
        methods: {
            run: {
                $meth(args, kwargs) {
                    if (args.length < 1) {
                        throw new TypeError("run() takes at least 1 positional argument (0 given)");
                    }
                    const callable = args[0];
                    const callArgs = args.slice(1);
                    return this.$ctx.run(() => pyCallOrSuspend(callable, callArgs, kwargs));
                },
                $flags: { FastCall: true },
            },
            copy: {
                $meth() {
                    return new Context(this.$ctx.copy());
                },
                $flags: { NoArgs: true },
            },
            get: {
                $meth(args, kwargs) {
                    checkNoKwargs("get", kwargs);
                    checkArgsLen("get", args, 1, 2);
                    const key = args[0];
                    const defaultVal = args.length === 2 ? args[1] : pyNone;
                    checkContextVarKey(key);
                    if (!this.$ctx.has(key.$jsVar)) {
                        return defaultVal;
                    }
                    return this.$ctx.get(key.$jsVar);
                },
                $flags: { FastCall: true },
            },
            keys: {
                $meth() {
                    const snap = snapshotPyDict(this.$ctx);
                    return pyCall(snap.tp$getattr(keysStr), []);
                },
                $flags: { NoArgs: true },
            },
            values: {
                $meth() {
                    const snap = snapshotPyDict(this.$ctx);
                    return pyCall(snap.tp$getattr(valuesStr), []);
                },
                $flags: { NoArgs: true },
            },
            items: {
                $meth() {
                    const snap = snapshotPyDict(this.$ctx);
                    return pyCall(snap.tp$getattr(itemsStr), []);
                },
                $flags: { NoArgs: true },
            },
        },
    });

    const contextvars = {
        __name__: new pyStr("contextvars"),
        __all__: new pyTuple([
            new pyStr("Context"),
            new pyStr("ContextVar"),
            new pyStr("Token"),
            new pyStr("copy_context"),
        ]),
        Context,
        ContextVar,
        Token,
    };

    setUpModuleMethods("contextvars", contextvars, {
        copy_context: {
            $meth() {
                return new Context(jsCopyContext());
            },
            $flags: { NoArgs: true },
        },
    });

    return contextvars;
}
