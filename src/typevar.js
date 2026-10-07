Sk.builtin.NoDefaultType = Sk.abstr.buildNativeClass("NoDefaultType", {
    constructor: function NoDefaultType() { return Sk.builtin.NoDefault; },
    slots: {
        tp$new(args, kwargs) {
            Sk.abstr.checkNoArgs("NoDefaultType", args, kwargs);
            return Sk.builtin.NoDefault;
        },
        $r() { return new Sk.builtin.str("typing.NoDefault"); },
    },
    flags: { sk$unacceptableBase: true },
});
Sk.builtin.NoDefault = Object.create(Sk.builtin.NoDefaultType.prototype);

// Shared managed state for the three native type-parameter kinds.
Sk.builtin.initTypeParameter = function (parameter, name, defaultValue) {
    parameter.$name = name;
    parameter.$default = defaultValue;
    parameter.$evaluate = {};
    parameter.$d = new Sk.builtin.dict();
    const frame = Sk.misceval.currentFrame;
    const globals = frame && frame.getGlobals();
    const module = globals && (globals instanceof Sk.builtin.dict ? globals.quick$lookup(Sk.builtin.str.$name) : globals.__name__);
    parameter.$d.dict$setItem(Sk.builtin.str.$module, module || Sk.builtin.none.none$);
};

// Objects/typevarobject.c: typevar_alloc and lazy bound/default/constraint getters.
Sk.builtin.TypeVar = Sk.abstr.buildNativeClass("typing.TypeVar", {
    constructor: function TypeVar(name, values) {
        Sk.builtin.initTypeParameter(this, name, values.default);
        this.$bound = values.bound;
        this.$constraints = values.constraints;
        this.$covariant = values.covariant;
        this.$contravariant = values.contravariant;
        this.$inferVariance = values.inferVariance;
    },
    slots: {
        tp$new(args, kwargs) {
            const [name, bound = Sk.builtin.none.none$, defaultValue = Sk.builtin.NoDefault,
                   co = Sk.builtin.bool.false$, contra = Sk.builtin.bool.false$, infer = Sk.builtin.bool.false$] =
                Sk.abstr.copyKeywordsToNamedArgs("TypeVar", ["name", "bound", "default", "covariant", "contravariant", "infer_variance"], args.slice(0, 1), kwargs);
            if (name === undefined || !Sk.builtin.checkString(name)) {throw new Sk.builtin.TypeError("TypeVar() requires a string name");}
            const covariant = Sk.misceval.isTrue(co), contravariant = Sk.misceval.isTrue(contra), inferVariance = Sk.misceval.isTrue(infer);
            if (covariant && contravariant) {throw new Sk.builtin.ValueError("Bivariant types are not supported.");}
            if (inferVariance && (covariant || contravariant)) {throw new Sk.builtin.ValueError("Variance cannot be specified with infer_variance.");}
            const constraints = new Sk.builtin.tuple(args.slice(1));
            // typevar_new_impl validates the bound before constraint arity.
            // Constraints themselves remain unevaluated, as in CPython 3.14.
            return Sk.misceval.chain(
                Sk.builtin.checkNone(bound) ? bound : Sk.builtin.callTypingFunction("_type_check", [bound, new Sk.builtin.str("Bound must be a type.")]),
                checkedBound => {
                    if (constraints.v.length === 1) {throw new Sk.builtin.TypeError("A single constraint is not allowed");}
                    if (constraints.v.length && !Sk.builtin.checkNone(checkedBound)) {throw new Sk.builtin.TypeError("Constraints cannot be combined with bound=...");}
                    return new Sk.builtin.TypeVar(name, { bound: checkedBound, constraints, default: defaultValue, covariant, contravariant, inferVariance });
                }
            );
        },
        $r() {
            return new Sk.builtin.str((this.$inferVariance ? "" : this.$covariant ? "+" : this.$contravariant ? "-" : "~") + this.$name.v);
        },
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.makeUnion([this, other], true); },
        nb$reflected_or(other) { return Sk.builtin.makeUnion([other, this], true); },
    },
    getsets: {
        __name__: { $get() { return this.$name; } },
        __bound__: { $get() { return this.$getValue("bound"); } },
        __constraints__: { $get() { return this.$getValue("constraints"); } },
        __default__: { $get() { return this.$getValue("default"); } },
        __covariant__: { $get() { return new Sk.builtin.bool(this.$covariant); } },
        __contravariant__: { $get() { return new Sk.builtin.bool(this.$contravariant); } },
        __infer_variance__: { $get() { return new Sk.builtin.bool(this.$inferVariance); } },
        evaluate_bound: { $get() { return this.$evaluate.bound || (Sk.builtin.checkNone(this.$bound) ? Sk.builtin.none.none$ : new Sk.builtin.constevaluator(this.$bound)); } },
        evaluate_constraints: { $get() { return this.$evaluate.constraints || (this.$constraints.v.length ? new Sk.builtin.constevaluator(this.$constraints) : Sk.builtin.none.none$); } },
        evaluate_default: { $get() { return this.$evaluate.default || new Sk.builtin.constevaluator(this.$default); } },
    },
    methods: {
        __typing_subst__: {
            $meth(arg) {
                return Sk.builtin.callTypingFunction("_typevar_subst", [this, arg]);
            },
            $flags: { OneArg: true },
        },
        __typing_prepare_subst__: {
            $meth(alias, args) {
                const parameters = Sk.abstr.gattr(alias, new Sk.builtin.str("__parameters__"));
                const index = parameters.v.indexOf(this);
                if (index < 0) {throw new Sk.builtin.ValueError("sequence.index(x): x not in sequence");}
                if (index < args.v.length) {return args;}
                if (index === args.v.length) {
                    return Sk.misceval.chain(this.$getValue("default"), value => {
                        if (value === Sk.builtin.NoDefault) {throw new Sk.builtin.TypeError("Too few arguments for " + Sk.misceval.objectRepr(alias) + "; actual " + args.v.length + ", expected at least " + (index + 1));}
                        return new Sk.builtin.tuple(args.v.concat([value]));
                    });
                }
                throw new Sk.builtin.TypeError("Too few arguments for " + Sk.misceval.objectRepr(alias) + "; actual " + args.v.length + ", expected at least " + (index + 1));
            },
            $flags: { MinArgs: 2, MaxArgs: 2 },
        },
        has_default: {
            $meth() { return new Sk.builtin.bool(!!this.$evaluate.default || this.$default !== Sk.builtin.NoDefault); },
            $flags: { NoArgs: true },
        },
        __instancecheck__: {
            $meth() { throw new Sk.builtin.TypeError("typing.TypeVar cannot be used with isinstance()"); },
            $flags: { OneArg: true },
        },
        __subclasscheck__: {
            $meth() { throw new Sk.builtin.TypeError("typing.TypeVar cannot be used with issubclass()"); },
            $flags: { OneArg: true },
        },
        __mro_entries__: {
            $meth() { throw new Sk.builtin.TypeError("Cannot subclass an instance of TypeVar"); },
            $flags: { OneArg: true },
        },
        __reduce__: { $meth() { return this.$name; }, $flags: { NoArgs: true } },
    },
    proto: {
        $getValue(field) {
            if (this["$" + field] !== undefined) {return this["$" + field];}
            return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(this.$evaluate[field]), value => {
                this["$" + field] = value;
                return value;
            });
        },
        sk$hasDict: true,
    },
    flags: { sk$unacceptableBase: true },
});
