// Native variadic type parameters mirror Objects/typevarobject.c. Their
// substitution rules live in typing, as they do in CPython.
Sk.builtin.callTypingFunction = function (name, args) {
    return Sk.misceval.chain(Sk.importModule("typing", false, true), module =>
        Sk.misceval.callsimOrSuspendArray(Sk.abstr.gattr(module, new Sk.builtin.str(name)), args));
};

Sk.builtin.ParamSpec = Sk.abstr.buildNativeClass("typing.ParamSpec", {
    constructor: function ParamSpec(name, values) {
        Sk.builtin.initTypeParameter(this, name, values.default);
        this.$bound = values.bound;
        this.$covariant = values.covariant;
        this.$contravariant = values.contravariant;
        this.$inferVariance = values.inferVariance;
    },
    slots: {
        tp$new(args, kwargs) {
            const [name, bound = Sk.builtin.none.none$, defaultValue = Sk.builtin.NoDefault,
                   co = Sk.builtin.bool.false$, contra = Sk.builtin.bool.false$, infer = Sk.builtin.bool.false$] =
                Sk.abstr.copyKeywordsToNamedArgs("ParamSpec", ["name", "bound", "default", "covariant", "contravariant", "infer_variance"], args, kwargs);
            if (args.length > 1 || !Sk.builtin.checkString(name)) {throw new Sk.builtin.TypeError("ParamSpec() requires a string name and keyword-only options");}
            const covariant = Sk.misceval.isTrue(co), contravariant = Sk.misceval.isTrue(contra), inferVariance = Sk.misceval.isTrue(infer);
            if (covariant && contravariant) {throw new Sk.builtin.ValueError("Bivariant types are not supported.");}
            if (inferVariance && (covariant || contravariant)) {throw new Sk.builtin.ValueError("Variance cannot be specified with infer_variance.");}
            return new Sk.builtin.ParamSpec(name, { bound, default: defaultValue, covariant, contravariant, inferVariance });
        },
        $r: Sk.builtin.TypeVar.prototype.$r,
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.makeUnion([this, other], true); },
        nb$reflected_or(other) { return Sk.builtin.makeUnion([other, this], true); },
    },
    getsets: {
        __name__: { $get() { return this.$name; } },
        __bound__: { $get() { return this.$bound; } },
        __default__: { $get() { return this.$getValue("default"); } },
        __covariant__: { $get() { return new Sk.builtin.bool(this.$covariant); } },
        __contravariant__: { $get() { return new Sk.builtin.bool(this.$contravariant); } },
        __infer_variance__: { $get() { return new Sk.builtin.bool(this.$inferVariance); } },
        evaluate_default: { $get() { return this.$evaluate.default || new Sk.builtin.constevaluator(this.$default); } },
        args: { $get() { return new Sk.builtin.ParamSpecArgs(this); } },
        kwargs: { $get() { return new Sk.builtin.ParamSpecKwargs(this); } },
    },
    methods: {
        __typing_subst__: { $meth(arg) { return Sk.builtin.callTypingFunction("_paramspec_subst", [this, arg]); }, $flags: { OneArg: true } },
        __typing_prepare_subst__: { $meth(alias, args) { return Sk.builtin.callTypingFunction("_paramspec_prepare_subst", [this, alias, args]); }, $flags: { MinArgs: 2, MaxArgs: 2 } },
        has_default: { $meth() { return new Sk.builtin.bool(!!this.$evaluate.default || this.$default !== Sk.builtin.NoDefault); }, $flags: { NoArgs: true } },
        __mro_entries__: { $meth() { throw new Sk.builtin.TypeError("Cannot subclass an instance of ParamSpec"); }, $flags: { OneArg: true } },
        __reduce__: { $meth() { return this.$name; }, $flags: { NoArgs: true } },
    },
    proto: { $getValue: Sk.builtin.TypeVar.prototype.$getValue, sk$hasDict: true },
    flags: { sk$unacceptableBase: true },
});

function paramSpecArgumentClass(name, suffix) {
    return Sk.abstr.buildNativeClass("typing." + name, {
        constructor: function ParamSpecArgument(origin) { this.$origin = origin; },
        slots: {
            tp$new(args, kwargs) {
                Sk.abstr.checkNoKwargs(name, kwargs);
                Sk.abstr.checkArgsLen(name, args, 1, 1);
                return new this.constructor(args[0]);
            },
            $r() {
                return new Sk.builtin.str(this.$origin instanceof Sk.builtin.ParamSpec ? this.$origin.$name.v + suffix :
                    Sk.misceval.objectRepr(this.$origin) + suffix);
            },
            tp$hash: Sk.builtin.none.none$,
            tp$richcompare(other, op) {
                if (other.ob$type !== this.ob$type || !["Eq", "NotEq"].includes(op)) {return Sk.builtin.NotImplemented.NotImplemented$;}
                return Sk.misceval.richCompareBool(this.$origin, other.$origin, op);
            },
        },
        getsets: { __origin__: { $get() { return this.$origin; } } },
        methods: {
            __mro_entries__: { $meth() { throw new Sk.builtin.TypeError("Cannot subclass an instance of " + name); }, $flags: { OneArg: true } },
        },
        flags: { sk$unacceptableBase: true },
    });
}
Sk.builtin.ParamSpecArgs = paramSpecArgumentClass("ParamSpecArgs", ".args");
Sk.builtin.ParamSpecKwargs = paramSpecArgumentClass("ParamSpecKwargs", ".kwargs");

Sk.builtin.TypeVarTuple = Sk.abstr.buildNativeClass("typing.TypeVarTuple", {
    constructor: function TypeVarTuple(name, defaultValue) {
        Sk.builtin.initTypeParameter(this, name, defaultValue);
    },
    slots: {
        tp$new(args, kwargs) {
            const [name, defaultValue = Sk.builtin.NoDefault] = Sk.abstr.copyKeywordsToNamedArgs("TypeVarTuple", ["name", "default"], args, kwargs);
            if (args.length > 1 || !Sk.builtin.checkString(name)) {throw new Sk.builtin.TypeError("TypeVarTuple() requires a string name and keyword-only default");}
            return new Sk.builtin.TypeVarTuple(name, defaultValue);
        },
        $r() { return this.$name; },
        tp$iter() { return new Sk.builtin.tuple([new Sk.builtin.UnpackAlias(this)]).tp$iter(); },
    },
    getsets: {
        __name__: { $get() { return this.$name; } },
        __default__: { $get() { return this.$getValue("default"); } },
        evaluate_default: { $get() { return this.$evaluate.default || new Sk.builtin.constevaluator(this.$default); } },
    },
    methods: {
        __typing_subst__: { $meth() { throw new Sk.builtin.TypeError("Substitution of bare TypeVarTuple is not supported"); }, $flags: { OneArg: true } },
        __typing_prepare_subst__: { $meth(alias, args) { return Sk.builtin.callTypingFunction("_typevartuple_prepare_subst", [this, alias, args]); }, $flags: { MinArgs: 2, MaxArgs: 2 } },
        has_default: { $meth() { return new Sk.builtin.bool(!!this.$evaluate.default || this.$default !== Sk.builtin.NoDefault); }, $flags: { NoArgs: true } },
        __mro_entries__: { $meth() { throw new Sk.builtin.TypeError("Cannot subclass an instance of TypeVarTuple"); }, $flags: { OneArg: true } },
        __reduce__: { $meth() { return this.$name; }, $flags: { NoArgs: true } },
    },
    proto: { $getValue: Sk.builtin.TypeVar.prototype.$getValue, sk$hasDict: true },
    flags: { sk$unacceptableBase: true },
});

Sk.builtin.UnpackAlias = Sk.abstr.buildNativeClass("typing._UnpackGenericAlias", {
    constructor: function UnpackAlias(value) { this.$value = value; },
    slots: {
        tp$new() { throw new Sk.builtin.TypeError("cannot create Unpack aliases directly"); },
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.makeUnion([this, other], true); },
        nb$reflected_or(other) { return Sk.builtin.makeUnion([other, this], true); },
        $r() { return new Sk.builtin.str("typing.Unpack[" + Sk.builtin.typingTypeRepr(this.$value) + "]"); },
        tp$hash() { return Sk.abstr.objectHash(this.$value); },
        tp$richcompare(other, op) {
            if (!(other instanceof Sk.builtin.UnpackAlias) || !["Eq", "NotEq"].includes(op)) {return Sk.builtin.NotImplemented.NotImplemented$;}
            return Sk.misceval.richCompareBool(this.$value, other.$value, op);
        },
        tp$as_sequence_or_mapping: true,
        mp$subscript(item) {
            if (this.$value instanceof Sk.builtin.TypeVarTuple) {return item;}
            return Sk.misceval.chain(Sk.abstr.objectGetItem(this.$value, item, true), value => new Sk.builtin.UnpackAlias(value));
        },
    },
    getsets: {
        __args__: { $get() { return new Sk.builtin.tuple([this.$value]); } },
        __origin__: { $get() { return Sk.builtin.Unpack; } },
        __parameters__: { $get() { return Sk.builtin.makeTypeParameters(new Sk.builtin.tuple([this.$value])); } },
        __typing_is_unpacked_typevartuple__: { $get() { return new Sk.builtin.bool(this.$value instanceof Sk.builtin.TypeVarTuple); } },
        __typing_unpacked_tuple_args__: { $get() {
            if (!(this.$value instanceof Sk.builtin.GenericAlias)) {return Sk.builtin.none.none$;}
            if (this.$value.$origin !== Sk.builtin.tuple) {throw new Sk.builtin.TypeError("Unpack[...] must be used with a tuple type");}
            return this.$value.$args;
        } },
    },
    flags: { sk$unacceptableBase: true },
});
Sk.builtin.UnpackType = Sk.abstr.buildNativeClass("typing._UnpackSpecialForm", {
    constructor: function UnpackType() {},
    slots: {
        tp$new() { throw new Sk.builtin.TypeError("cannot create Unpack forms directly"); },
        $r() { return new Sk.builtin.str("typing.Unpack"); },
        tp$as_sequence_or_mapping: true,
        mp$subscript(value) {
            if (value.ob$type === Sk.builtin.tuple) {throw new Sk.builtin.TypeError("Unpack accepts only a single type.");}
            if (Sk.builtin.checkNone(value)) {value = Sk.builtin.none;}
            if (Sk.builtin.checkString(value)) {throw new Sk.builtin.NotImplementedError("string type arguments require ForwardRef support");}
            return new Sk.builtin.UnpackAlias(value);
        },
    },
    flags: { sk$unacceptableBase: true },
});
Sk.builtin.Unpack = new Sk.builtin.UnpackType();
