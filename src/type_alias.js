// Objects/typevarobject.c: constevaluator_call.
Sk.builtin.constevaluator = Sk.abstr.buildNativeClass("_typing._ConstEvaluator", {
    constructor: function constevaluator(value) { this.$value = value; },
    slots: {
        tp$new() { throw new Sk.builtin.TypeError("cannot create 'constevaluator' instances"); },
        $r() { return new Sk.builtin.str("<constevaluator " + Sk.misceval.objectRepr(this.$value) + ">"); },
        tp$call(args, kwargs) {
            Sk.abstr.checkNoKwargs("constevaluator.__call__", kwargs);
            Sk.abstr.checkArgsLen("constevaluator.__call__", args, 1, 1);
            const format = Sk.misceval.asIndexSized(args[0], Sk.builtin.OverflowError);
            if (format < -2147483648 || format > 2147483647) {
                throw new Sk.builtin.OverflowError("Python int too large to convert to C int");
            }
            if (format === 4) {
                const repr = Sk.builtin.typingTypeRepr;
                return new Sk.builtin.str(this.$value instanceof Sk.builtin.tuple ?
                    "(" + this.$value.v.map(repr).join(", ") + ")" : repr(this.$value));
            }
            return this.$value;
        },
    },
    flags: { sk$unacceptableBase: true },
});

// _Py_typing_type_repr uses ordinary attribute lookup, including descriptors.
Sk.builtin.typingTypeRepr = function (value) {
    if (value === Sk.builtin.Ellipsis) {return "...";}
    if (value === Sk.builtin.none) {return "None";}
    if (Sk.abstr.lookupAttr(value, new Sk.builtin.str("__origin__")) !== undefined &&
        Sk.abstr.lookupAttr(value, new Sk.builtin.str("__args__")) !== undefined) {return Sk.misceval.objectRepr(value);}
    const qualname = Sk.abstr.lookupAttr(value, Sk.builtin.str.$qualname);
    if (qualname === undefined) {return Sk.misceval.objectRepr(value);}
    const module = Sk.abstr.lookupAttr(value, Sk.builtin.str.$module);
    if (module === undefined || Sk.builtin.checkNone(module)) {return Sk.misceval.objectRepr(value);}
    return (Sk.builtin.checkString(module) && module.v === "builtins" ? "" : new Sk.builtin.str(module).v + ".") +
        new Sk.builtin.str(qualname).v;
};

// Objects/typevarobject.c: typealias_get_value / typealias_alloc.
Sk.builtin.TypeAliasType = Sk.abstr.buildNativeClass("typing.TypeAliasType", {
    constructor: function TypeAliasType(name, value, compute, module, params) {
        this.$name = name;
        this.$value = value;
        this.$compute = compute;
        this.$module = module;
        this.$params = params || new Sk.builtin.tuple([]);
    },
    slots: {
        tp$new(args, kwargs) {
            const [name, value, params = new Sk.builtin.tuple([])] = Sk.abstr.copyKeywordsToNamedArgs(
                "TypeAliasType", ["name", "value", "type_params"], args, kwargs);
            if (args.length > 2 || name === undefined || value === undefined) {
                throw new Sk.builtin.TypeError("TypeAliasType() requires name and value, with keyword-only type_params");
            }
            if (!Sk.builtin.checkString(name)) {throw new Sk.builtin.TypeError("name must be a str");}
            if (!(params instanceof Sk.builtin.tuple)) {throw new Sk.builtin.TypeError("type_params must be a tuple");}
            const frame = Sk.misceval.currentFrame;
            const globals = frame && frame.getGlobals();
            const module = globals && (globals instanceof Sk.builtin.dict ? globals.quick$lookup(Sk.builtin.str.$name) : globals.__name__);
            let seenDefault = false;
            let validate = Sk.builtin.none.none$;
            for (const param of params.v) {
                validate = Sk.misceval.chain(validate, () => {
                    if (![Sk.builtin.TypeVar, Sk.builtin.ParamSpec, Sk.builtin.TypeVarTuple].some(type => param instanceof type)) {throw new Sk.builtin.TypeError("Expected a type param, got " + Sk.misceval.objectRepr(param));}
                    return param.$getValue("default");
                }, defaultValue => {
                    if (defaultValue === Sk.builtin.NoDefault) {
                        if (seenDefault) {throw new Sk.builtin.TypeError("non-default type parameter '" + Sk.misceval.objectRepr(param) + "' follows default type parameter");}
                    } else {seenDefault = true;}
                });
            }
            return Sk.misceval.chain(validate, () => new Sk.builtin.TypeAliasType(name, value, null, module || Sk.builtin.none.none$, params));
        },
        $r() { return this.$name; },
        tp$iter() { return new Sk.builtin.tuple([new Sk.builtin.UnpackAlias(this)]).tp$iter(); },
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.typeUnion(this, other); },
        nb$reflected_or(other) { return Sk.builtin.typeUnion(other, this); },
        tp$as_sequence_or_mapping: true,
        mp$subscript(item) {
            if (!this.$params.v.length) {throw new Sk.builtin.TypeError("Only generic type aliases are subscriptable");}
            return new Sk.builtin.GenericAlias(this, item);
        },
    },
    getsets: {
        __name__: { $get() { return this.$name; } },
        __module__: { $get() {
            return this.$compute ? this.$compute.tp$getattr(Sk.builtin.str.$module) : this.$module;
        } },
        __parameters__: { $get() {
            if (!this.$params.v.some(param => param instanceof Sk.builtin.TypeVarTuple)) return this.$params;
            return new Sk.builtin.tuple(this.$params.v.map(param => param instanceof Sk.builtin.TypeVarTuple ? new Sk.builtin.UnpackAlias(param) : param));
        } },
        __type_params__: { $get() { return this.$params; } },
        __value__: { $get() {
            if (this.$value !== undefined) {return this.$value;}
            return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(this.$compute), value => {
                this.$value = value;
                return value;
            });
        } },
        evaluate_value: { $get() {
            if (this.$compute) {return this.$compute;}
            return new Sk.builtin.constevaluator(this.$value);
        } },
    },
    flags: { sk$unacceptableBase: true },
});
