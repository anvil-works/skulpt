// Objects/typevarobject.c: typealias_get_value / typealias_alloc.
Sk.builtin.TypeAliasType = Sk.abstr.buildNativeClass("typing.TypeAliasType", {
    constructor: function TypeAliasType(name, value, compute, module) {
        this.$name = name;
        this.$value = value;
        this.$compute = compute;
        this.$module = module;
    },
    slots: {
        tp$new(args, kwargs) {
            const [name, value, params = new Sk.builtin.tuple([])] = Sk.abstr.copyKeywordsToNamedArgs(
                "TypeAliasType", ["name", "value", "type_params"], args, kwargs);
            if (args.length > 2 || name === undefined || value === undefined) {
                throw new Sk.builtin.TypeError("TypeAliasType() requires name and value, with keyword-only type_params");
            }
            if (!Sk.builtin.checkString(name)) throw new Sk.builtin.TypeError("name must be a str");
            if (!(params instanceof Sk.builtin.tuple)) throw new Sk.builtin.TypeError("type_params must be a tuple");
            if (params.v.length) throw new Sk.builtin.NotImplementedError("generic type aliases require type-parameter support");
            const frame = Sk.misceval.currentFrame;
            const globals = frame && frame.getGlobals();
            const module = globals && (globals instanceof Sk.builtin.dict ? globals.quick$lookup(Sk.builtin.str.$name) : globals.__name__);
            return new Sk.builtin.TypeAliasType(name, value, null, module || Sk.builtin.none.none$);
        },
        $r() { return this.$name; },
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.typeUnion(this, other); },
        nb$reflected_or(other) { return Sk.builtin.typeUnion(other, this); },
        tp$as_sequence_or_mapping: true,
        mp$subscript() { throw new Sk.builtin.TypeError("Only generic type aliases are subscriptable"); },
    },
    getsets: {
        __name__: { $get() { return this.$name; } },
        __module__: { $get() {
            return this.$compute ? this.$compute.tp$getattr(Sk.builtin.str.$module) : this.$module;
        } },
        __parameters__: { $get() { return new Sk.builtin.tuple([]); } },
        __type_params__: { $get() { return new Sk.builtin.tuple([]); } },
        __value__: { $get() {
            if (this.$value !== undefined) return this.$value;
            return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(this.$compute), value => {
                this.$value = value;
                return value;
            });
        } },
        evaluate_value: { $get() {
            if (this.$compute) return this.$compute;
            return new Sk.builtin.func((format = new Sk.builtin.int_(1)) => {
                if (Sk.misceval.richCompareBool(format, new Sk.builtin.int_(3), "Gt")) {
                    throw new Sk.builtin.NotImplementedError("string annotation formats require annotationlib support");
                }
                return this.$value;
            });
        } },
    },
    flags: { sk$unacceptableBase: true },
});
