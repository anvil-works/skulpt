// Objects/genobject.c: native coroutines use a resumable frame but are not iterable.
Sk.builtin.coroutine = Sk.abstr.buildNativeClass("coroutine", {
    constructor: function coroutine(generator) {
        this.$gen = generator;
    },
    slots: {
        tp$getattr: Sk.generic.getAttr,
        $r() { return new Sk.builtin.str("<coroutine object " + this.$gen.$qualname + ">"); },
    },
    methods: {
        __await__: {
            $meth() { return new Sk.builtin.coroutine_wrapper(this); },
            $flags: { NoArgs: true },
        },
        send: {
            $meth(value) { return this.$send(value); },
            $flags: { OneArg: true },
            $doc: "send(arg) -> send argument into coroutine.",
        },
        throw: {
            $meth(args) {
                this.$checkReusable();
                return Sk.misceval.callsimOrSuspendArray(Sk.abstr.gattr(this.$gen, new Sk.builtin.str("throw")), args);
            },
            $flags: { FastCall: true, NoKwargs: true },
        },
        close: {
            $meth() {
                return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(
                    Sk.abstr.gattr(this.$gen, new Sk.builtin.str("close"))), () => Sk.builtin.none.none$);
            },
            $flags: { NoArgs: true },
            $doc: "close() -> raise GeneratorExit inside coroutine.",
        },
    },
    getsets: {
        cr_running: { $get() { return new Sk.builtin.bool(this.$gen.gi$running); } },
        cr_suspended: { $get() { return new Sk.builtin.bool(this.$gen.gi$started && !this.$gen.gi$closed && !this.$gen.gi$running); } },
        cr_await: { $get() { return !this.$gen.gi$running && this.$gen.gi$yieldfrom && this.$gen.gi$awaited || Sk.builtin.none.none$; } },
        cr_code: {
            $get() {
                const code = this.$gen.gi$scope;
                return code.$code || new Sk.builtin.code(code.$metadata.filename, null, code);
            },
        },
    },
    proto: {
        $checkReusable() {
            if (this.$gen.gi$closed) throw new Sk.builtin.RuntimeError("cannot reuse already awaited coroutine");
        },
        $send(value) {
            this.$checkReusable();
            return Sk.misceval.chain(this.$gen.tp$iternext(true, value), result => {
                if (result === undefined) throw new Sk.builtin.StopIteration(this.$gen.gi$ret);
                return result;
            });
        },
    },
});

Sk.builtin.coroutine_wrapper = Sk.abstr.buildIteratorClass("coroutine_wrapper", {
    constructor: function coroutine_wrapper(coroutine) { this.$coro = coroutine; },
    iternext(canSuspend) {
        const result = Sk.misceval.tryCatch(() => this.$coro.$send(Sk.builtin.none.none$), error => {
            if (!(error instanceof Sk.builtin.StopIteration)) throw error;
            this.gi$ret = error.$value;
            return undefined;
        });
        return canSuspend ? result : Sk.misceval.retryOptionalSuspensionOrThrow(result);
    },
    methods: {
        send: { $meth(value) { return this.$coro.$send(value); }, $flags: { OneArg: true } },
        throw: {
            $meth(args) { return Sk.misceval.callsimOrSuspendArray(Sk.abstr.gattr(this.$coro, new Sk.builtin.str("throw")), args); },
            $flags: { FastCall: true, NoKwargs: true },
        },
        close: {
            $meth() { return Sk.misceval.callsimOrSuspendArray(Sk.abstr.gattr(this.$coro, new Sk.builtin.str("close"))); },
            $flags: { NoArgs: true },
        },
    },
});

// Objects/genobject.c: _PyCoro_GetAwaitableIter.
Sk.builtin.getAwaitable = function (value) {
    if (value instanceof Sk.builtin.coroutine) {
        if (value.$gen.gi$yieldfrom) throw new Sk.builtin.RuntimeError("coroutine is being awaited already");
        return new Sk.builtin.coroutine_wrapper(value);
    }
    const method = Sk.abstr.lookupSpecial(value, new Sk.builtin.str("__await__"));
    if (method === undefined) throw new Sk.builtin.TypeError("'" + Sk.abstr.typeName(value) + "' object can't be awaited");
    return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(method), iterator => {
        if (iterator instanceof Sk.builtin.coroutine) throw new Sk.builtin.TypeError("__await__() returned a coroutine");
        if (!iterator.tp$iternext) throw new Sk.builtin.TypeError("__await__() returned non-iterator of type '" + Sk.abstr.typeName(iterator) + "'");
        return iterator;
    });
};
Sk.exportSymbol("Sk.builtin.coroutine", Sk.builtin.coroutine);
