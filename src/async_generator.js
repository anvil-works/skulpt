// Objects/genobject.c: user yields are wrapped, unlike values yielded by await.
Sk.builtin.async_generator_wrapped_value = function (value) { this.value = value; };

Sk.builtin.async_generator = Sk.abstr.buildNativeClass("async_generator", {
    constructor: function async_generator(generator) {
        this.$gen = generator;
        this.ag$running = false;
        this.ag$closed = false;
    },
    slots: {
        tp$getattr: Sk.generic.getAttr,
        $r() { return new Sk.builtin.str("<async_generator object " + this.$gen.$qualname + ">"); },
    },
    methods: {
        __aiter__: { $meth() { return this; }, $flags: { NoArgs: true } },
        __anext__: {
            $meth() { return new Sk.builtin.async_generator_asend(this, Sk.builtin.none.none$); },
            $flags: { NoArgs: true },
        },
        asend: {
            $meth(value) { return new Sk.builtin.async_generator_asend(this, value); },
            $flags: { OneArg: true },
        },
        athrow: {
            $meth(args) {
                return new Sk.builtin.async_generator_athrow(this, args);
            },
            $flags: { FastCall: true, NoKwargs: true },
        },
        aclose: {
            $meth() { return new Sk.builtin.async_generator_athrow(this, null); },
            $flags: { NoArgs: true },
        },
    },
    getsets: {
        __name__: {
            $get() { return this.$gen.$name; },
            $set(value) {
                if (!Sk.builtin.checkString(value)) throw new Sk.builtin.TypeError("__name__ must be set to a string object");
                this.$gen.$name = value;
            },
        },
        __qualname__: {
            $get() { return this.$gen.$qualname; },
            $set(value) {
                if (!Sk.builtin.checkString(value)) throw new Sk.builtin.TypeError("__qualname__ must be set to a string object");
                this.$gen.$qualname = value;
            },
        },
        ag_running: { $get() { return new Sk.builtin.bool(this.ag$running); } },
        ag_await: { $get() { return !this.$gen.gi$running && this.$gen.gi$yieldfrom && this.$gen.gi$awaited || Sk.builtin.none.none$; } },
        ag_code: {
            $get() { return this.$gen.gi$scope.$code || new Sk.builtin.code(this.$gen.gi$scope.$metadata.filename, null, this.$gen.gi$scope); },
        },
    },
});

// ASend and AThrow share iterator/await and wrapped-value handling. Their
// initial send differs: inject a value, an exception, or GeneratorExit.
function makeAsyncGeneratorAwaitable(name, throwOperation) {
    return Sk.abstr.buildIteratorClass(name, {
        constructor: function async_generator_awaitable(generator, value) {
            this.$agen = generator;
            this.$value = value;
            this.$state = "init";
        },
        iternext(canSuspend) {
            const result = Sk.misceval.tryCatch(() => this.$send(Sk.builtin.none.none$), error => {
                if (!(error instanceof Sk.builtin.StopIteration)) throw error;
                this.gi$ret = error.$value;
                this.gi$stopIteration = error;
                return undefined;
            });
            return canSuspend ? result : Sk.misceval.retryOptionalSuspensionOrThrow(result);
        },
        methods: {
            // The generic iterator __next__ wrapper discards StopIteration's
            // value; the async yield result must preserve it, including None.
            __next__: { $meth() { return this.$send(Sk.builtin.none.none$); }, $flags: { NoArgs: true } },
            __await__: { $meth() { return this; }, $flags: { NoArgs: true } },
            send: { $meth(value) { return this.$send(value); }, $flags: { OneArg: true } },
            throw: {
                $meth(args) {
                    Sk.abstr.checkArgsLen("throw", args, 1, 3);
                    return this.$throw(args);
                },
                $flags: { FastCall: true, NoKwargs: true },
            },
            close: {
                $meth() {
                    if (this.$state === "closed") return Sk.builtin.none.none$;
                    return Sk.misceval.tryCatch(() => Sk.misceval.chain(this.$throw([new Sk.builtin.GeneratorExit()]), () => {
                        throw new Sk.builtin.RuntimeError("coroutine ignored GeneratorExit");
                    }), error => {
                        if (error instanceof Sk.builtin.StopIteration || error instanceof Sk.builtin.StopAsyncIteration || error instanceof Sk.builtin.GeneratorExit) return Sk.builtin.none.none$;
                        throw error;
                    });
                },
                $flags: { NoArgs: true },
            },
        },
        proto: {
            $checkState() {
                if (this.$state === "closed") {
                    throw new Sk.builtin.RuntimeError("cannot reuse already awaited " + (throwOperation ? "aclose()/athrow()" : "__anext__()/asend()"));
                }
                if (this.$state === "init" && this.$agen.ag$running) {
                    this.$state = "closed";
                    const method = throwOperation ? (this.$value === null ? "aclose" : "athrow") : "anext";
                    throw new Sk.builtin.RuntimeError(method + "(): asynchronous generator is already running");
                }
            },
            $run(action) {
                const closing = throwOperation && this.$value === null;
                return Sk.misceval.tryCatch(() => Sk.misceval.chain(action(), value => {
                    if (value === undefined) throw new Sk.builtin.StopAsyncIteration();
                    if (value instanceof Sk.builtin.async_generator_wrapped_value) {
                        if (closing) throw new Sk.builtin.RuntimeError("async generator ignored GeneratorExit");
                        throw new Sk.builtin.StopIteration(value.value);
                    }
                    return value;
                }), error => {
                    this.$agen.ag$running = false;
                    this.$state = "closed";
                    if (error instanceof Sk.builtin.StopAsyncIteration || error instanceof Sk.builtin.GeneratorExit) {
                        this.$agen.ag$closed = true;
                        if (closing) throw new Sk.builtin.StopIteration();
                    }
                    throw error;
                });
            },
            $send(value) {
                if (throwOperation && this.$state !== "closed" && this.$agen.$gen.gi$closed) {
                    this.$state = "closed";
                    throw new Sk.builtin.StopIteration();
                }
                this.$checkState();
                const initial = this.$state === "init";
                if (initial && throwOperation) {
                    if (this.$agen.ag$closed) {
                        this.$state = "closed";
                        throw new Sk.builtin.StopAsyncIteration();
                    }
                    if (value !== Sk.builtin.none.none$) throw new Sk.builtin.RuntimeError("can't send non-None value to a just-started coroutine");
                }
                this.$state = "iter";
                this.$agen.ag$running = true;
                if (initial && throwOperation) {
                    if (this.$value === null) this.$agen.ag$closed = true;
                    const args = this.$value === null ? [new Sk.builtin.GeneratorExit()] : this.$value;
                    if (this.$value !== null) Sk.abstr.checkArgsLen("athrow", args, 1, 3);
                    return this.$run(() => this.$agen.$gen.gi$throwArgs(args[0], args[1], args[2], false));
                }
                if (initial && value === Sk.builtin.none.none$) value = this.$value;
                return this.$run(() => this.$agen.$gen.tp$iternext(true, value));
            },
            $throw(args) {
                this.$checkState();
                this.$state = "iter";
                this.$agen.ag$running = true;
                return this.$run(() => this.$agen.$gen.gi$throwArgs(args[0], args[1], args[2]));
            },
        },
    });
}
Sk.builtin.async_generator_asend = makeAsyncGeneratorAwaitable("async_generator_asend", false);
Sk.builtin.async_generator_athrow = makeAsyncGeneratorAwaitable("async_generator_athrow", true);
Sk.exportSymbol("Sk.builtin.async_generator", Sk.builtin.async_generator);
