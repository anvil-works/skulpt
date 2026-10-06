// Objects/iterobject.c: anextawaitable proxies each operation to the wrapped
// object's await iterator, translating StopAsyncIteration into the default.
Sk.builtin.anextawaitable = Sk.abstr.buildIteratorClass("anext_awaitable", {
    constructor: function anextawaitable(awaitable, defaultValue) {
        this.$wrapped = awaitable;
        this.$default = defaultValue;
    },
    iternext(canSuspend) {
        const result = Sk.misceval.tryCatch(() => this.$next(), error => {
            if (!(error instanceof Sk.builtin.StopIteration)) {throw error;}
            this.gi$ret = error.$value;
            this.gi$stopIteration = error;
            return undefined;
        });
        return canSuspend ? result : Sk.misceval.retryOptionalSuspensionOrThrow(result);
    },
    methods: {
        __await__: { $meth() { return this; }, $flags: { NoArgs: true } },
        __next__: { $meth() { return this.$next(); }, $flags: { NoArgs: true } },
        send: { $meth(value) { return this.$proxy("send", [value]); }, $flags: { OneArg: true } },
        throw: { $meth(args) { return this.$proxy("throw", args); }, $flags: { FastCall: true, NoKwargs: true } },
        close: { $meth() { return this.$proxy("close", []); }, $flags: { NoArgs: true } },
    },
    proto: {
        $iterator() {
            // Unlike GET_AWAITABLE, the proxy can resume the same coroutine
            // already suspended in an await; its wrapper handles reuse.
            return this.$wrapped instanceof Sk.builtin.coroutine ?
                new Sk.builtin.coroutine_wrapper(this.$wrapped) : Sk.builtin.getAwaitable(this.$wrapped);
        },
        $withDefault(action) {
            return Sk.misceval.tryCatch(action, error => {
                if (error instanceof Sk.builtin.StopAsyncIteration) {throw new Sk.builtin.StopIteration(this.$default);}
                throw error;
            });
        },
        $next() {
            return Sk.misceval.chain(this.$iterator(), iterator => this.$withDefault(() =>
                Sk.misceval.chain(iterator.tp$iternext(true), value => {
                    if (value !== undefined) {return value;}
                    throw iterator.gi$stopIteration || new Sk.builtin.StopIteration(iterator.gi$ret);
                })));
        },
        $proxy(method, args) {
            return Sk.misceval.chain(this.$iterator(), iterator => this.$withDefault(() =>
                Sk.misceval.chain(Sk.abstr.gattr(iterator, new Sk.builtin.str(method), true), callable =>
                    Sk.misceval.callsimOrSuspendArray(callable, args))));
        },
    },
});
