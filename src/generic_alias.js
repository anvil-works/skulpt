Sk.builtin.GenericAlias = Sk.abstr.buildNativeClass("types.GenericAlias", {
    constructor: function GenericAlias(origin, args) {
        this.$origin = origin;
        if (!(args instanceof Sk.builtin.tuple)) {
            args = new Sk.builtin.tuple([args]);
        }
        this.$args = args;
        this.$params = null;
    },
    slots: {
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.typeUnion(this, other); },
        nb$reflected_or(other) { return Sk.builtin.typeUnion(other, this); },
        tp$new(args, kwargs) {
            Sk.abstr.checkNoKwargs("GenericAlias", kwargs);
            Sk.abstr.checkArgsLen("GenericAlias", args, 2, 2);
            return new Sk.builtin.GenericAlias(args[0], args[1]);
        },
        tp$getattr(pyName, canSuspend) {
            if (Sk.builtin.checkString(pyName)) {
                if (!this.attr$exc.includes(pyName.v)) {
                    return this.$origin.tp$getattr(pyName, canSuspend);
                }
            }
            return Sk.generic.getAttr.call(this, pyName, canSuspend);
        },
        $r() {
            const origin_repr = this.ga$repr(this.$origin);
            let arg_repr = "";
            this.$args.v.forEach((arg, i) => {
                arg_repr += i > 0 ? ", " : "";
                arg_repr += this.ga$repr(arg);
            });
            if (!arg_repr) {
                arg_repr = "()";
            }
            return new Sk.builtin.str(origin_repr + "[" + arg_repr + "]");
        },
        tp$doc: "Represent a PEP 585 generic type\n\nE.g. for t = list[int], t.origin is list and t.args is (int,).",
        tp$hash() {
            const h0 = Sk.abstr.objectHash(this.$origin);
            if (h0 == -1) {
                return -1;
            }
            const h1 = Sk.abstr.objectHash(this.$args);
            if (h1 == -1) {
                return -1;
            }
            return h0 ^ h1;
        },
        tp$call(args, kwargs) {
            const obj = Sk.misceval.callsimArray(this.$origin, args, kwargs);
            try {
                obj.tp$setattr(new Sk.builtin.str("__orig_class__"), this);
            } catch (e) {
                if (!(e instanceof Sk.builtin.AttributeError) && !(e instanceof Sk.builtin.TypeError)) {
                    throw e;
                }
            }
            return obj;
        },
        tp$richcompare(other, op) {
            if (!(other instanceof Sk.builtin.GenericAlias) || (op !== "Eq" && op !== "NotEq")) {
                return Sk.builtin.NotImplemented.NotImplemented$;
            }
            const eq = Sk.misceval.richCompareBool(this.$origin, other.$origin, "Eq");
            if (!eq) {
                return op === "Eq" ? eq : !eq;
            }
            const res = Sk.misceval.richCompareBool(this.$args, other.$args, "Eq");
            return op === "Eq" ? res : !res;
        },
        tp$as_sequence_or_mapping: true,
        mp$subscript(item) {
            if (this.$params === null) this.mk$params();
            return Sk.misceval.chain(Sk.builtin.substituteTypeParameters(this, this.$args, this.$params, item),
                args => new Sk.builtin.GenericAlias(this.$origin, args));
        },
    },
    methods: {
        __mro_entries__: {
            $meth(bases) {
                return new Sk.builtin.tuple([this.$origin]);
            },
            $flags: { OneArg: true },
        },
        __instancecheck__: {
            $meth(_) {
                throw new Sk.builtin.TypeError("isinstance() argument 2 cannot be a parameterized generic");
            },
            $flags: { OneArg: true },
        },
        __subclasscheck__: {
            $meth(_) {
                throw new Sk.builtin.TypeError("issubclass() argument 2 cannot be a parameterized generic");
            },
            $flags: { OneArg: true },
        },
    },
    getsets: {
        __parameters__: {
            $get() {
                if (this.$params === null) {
                    this.mk$params();
                }
                return this.$params;
            },
            $doc: "Type variables in the GenericAlias.",
        },
        __origin__: {
            $get() {
                return this.$origin;
            },
        },
        __args__: {
            $get() {
                return this.$args;
            },
        },
    },
    proto: {
        // functions here match similar functions in Objects/genericaliasobject.c
        mk$params() {
            this.$params = Sk.builtin.makeTypeParameters(this.$args);
        },
        ga$repr(item) {
            if (item === Sk.builtin.Ellipsis) {
                return "...";
            }
            if (Sk.abstr.lookupSpecial(item, this.str$orig)) {
                if (Sk.abstr.lookupSpecial(item, this.str$args)) {
                    return Sk.misceval.objectRepr(item);
                }
            }
            const qualname = Sk.abstr.lookupSpecial(item, Sk.builtin.str.$qualname);
            if (qualname === undefined) {
                return Sk.misceval.objectRepr(item);
            }
            const mod = Sk.abstr.lookupSpecial(item, Sk.builtin.str.$module);
            if (mod === undefined || Sk.builtin.checkNone(mod)) {
                return Sk.misceval.objectRepr(item);
            } else if (mod.toString() === "builtins") {
                return qualname.toString();
            }
            return mod.toString() + "." + qualname.toString();
        },
        str$orig: new Sk.builtin.str("__origin__"),
        str$args: new Sk.builtin.str("__args__"),
        attr$exc: [
            "__origin__",
            "__args__",
            "__parameters__",
            "__mro_entries__",
            "__reduce_ex__", // needed so we don't look up object.__reduce_ex__
            "__reduce__",
        ],
    },
});

// Objects/genericaliasobject.c: _Py_make_parameters.
Sk.builtin.makeTypeParameters = function (args) {
    const parameters = [];
    const argumentsArray = args instanceof Sk.builtin.list ? Sk.misceval.arrayFromIterable(args) : args.v;
    for (const arg of argumentsArray) {
        if (Sk.builtin.checkClass(arg)) continue;
        if (Sk.abstr.lookupAttr(arg, new Sk.builtin.str("__typing_subst__")) !== undefined) {
            if (!parameters.includes(arg)) parameters.push(arg);
            continue;
        }
        let nested = Sk.abstr.lookupAttr(arg, new Sk.builtin.str("__parameters__"));
        if (nested === undefined && (arg instanceof Sk.builtin.tuple || arg instanceof Sk.builtin.list)) {
            nested = Sk.builtin.makeTypeParameters(arg);
        }
        if (nested instanceof Sk.builtin.tuple) {
            for (const param of nested.v) if (!parameters.includes(param)) parameters.push(param);
        }
    }
    return new Sk.builtin.tuple(parameters);
};

// _Py_subs_parameters: prepare defaults, then substitute in argument order.
Sk.builtin.substituteTypeParameters = function (self, args, parameters, item) {
    if (!parameters.v.length) throw new Sk.builtin.TypeError(Sk.misceval.objectRepr(self) + " is not a generic class");
    let items = item instanceof Sk.builtin.tuple ? item : new Sk.builtin.tuple([item]);
    let result;
    for (const param of parameters.v) {
        result = Sk.misceval.chain(result, () => {
            const prepare = Sk.abstr.lookupAttr(param, new Sk.builtin.str("__typing_prepare_subst__"));
            if (prepare !== undefined && !Sk.builtin.checkNone(prepare)) {
                const preparedArgs = items instanceof Sk.builtin.tuple ? items : new Sk.builtin.tuple([items]);
                return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(prepare, [self, preparedArgs]), value => { items = value; });
            }
        });
    }
    return Sk.misceval.chain(result, () => {
        const values = items instanceof Sk.builtin.tuple ? items.v : [items];
        if (values.length !== parameters.v.length) {
            throw new Sk.builtin.TypeError("Too " + (values.length > parameters.v.length ? "many" : "few") + " arguments for " +
                Sk.misceval.objectRepr(self) + "; actual " + values.length + ", expected " + parameters.v.length);
        }
        const substituted = [];
        let pending;
        const argumentsArray = args instanceof Sk.builtin.list ? Sk.misceval.arrayFromIterable(args) : args.v;
        for (const arg of argumentsArray) {
            pending = Sk.misceval.chain(pending, () => {
                if (Sk.builtin.checkClass(arg)) return arg;
                if (arg instanceof Sk.builtin.tuple || arg instanceof Sk.builtin.list) {
                    return Sk.misceval.chain(Sk.builtin.substituteTypeParameters(self, arg, parameters, items),
                        value => arg instanceof Sk.builtin.list ? new Sk.builtin.list(value.v) : value);
                }
                const subst = Sk.abstr.lookupAttr(arg, new Sk.builtin.str("__typing_subst__"));
                if (subst !== undefined) {
                    const index = parameters.v.indexOf(arg);
                    if (index < 0) throw new Sk.builtin.TypeError("stale __parameters__ in " + Sk.misceval.objectRepr(self));
                    return Sk.misceval.callsimOrSuspendArray(subst, [values[index]]);
                }
                const nested = Sk.abstr.lookupAttr(arg, new Sk.builtin.str("__parameters__"));
                if (!(nested instanceof Sk.builtin.tuple) || !nested.v.length) return arg;
                const replacements = nested.v.map(param => {
                    const index = parameters.v.indexOf(param);
                    return index < 0 ? param : values[index];
                });
                return Sk.abstr.objectGetItem(arg, new Sk.builtin.tuple(replacements), true);
            }, value => { substituted.push(value); });
        }
        return Sk.misceval.chain(pending, () => new Sk.builtin.tuple(substituted));
    });
};
