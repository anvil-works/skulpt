// Objects/unionobject.c: preserve argument order, but compare/hash as sets.
Sk.builtin.UnionType = Sk.abstr.buildNativeClass("typing.Union", {
    constructor: function Union(args, hashable, unhashable) {
        this.$args = new Sk.builtin.tuple(args);
        // Freezing the private builder set must not rehash its Python keys.
        this.$hashable = new Sk.builtin.frozenset();
        this.$hashable.v = hashable.v;
        this.$hashEntries = Object.entries(hashable.v.buckets).flatMap(([hash, bucket]) =>
            bucket.map(([arg]) => [arg, Number(hash)]));
        this.$unhashable = unhashable;
    },
    slots: {
        tp$new() { throw new Sk.builtin.TypeError("cannot create 'typing.Union' instances"); },
        tp$as_number: true,
        nb$or(other) { return Sk.builtin.makeUnion([this, other], true); },
        nb$reflected_or(other) { return Sk.builtin.makeUnion([other, this], true); },
        $r() {
            return new Sk.builtin.str(this.$args.v.map(arg => arg === Sk.builtin.none ? "None" :
                Sk.builtin.GenericAlias.prototype.ga$repr(arg)).join(" | "));
        },
        tp$hash() {
            if (this.$unhashable.length) {
                for (const arg of this.$unhashable) Sk.abstr.objectHash(arg);
                throw new Sk.builtin.TypeError("union contains " + this.$unhashable.length + " unhashable elements");
            }
            return Sk.builtin.frozenset.$hashValues(this.$hashEntries.map(entry => entry[1]));
        },
        tp$richcompare(other, op) {
            if (!(other instanceof Sk.builtin.UnionType) || (op !== "Eq" && op !== "NotEq")) {
                return Sk.builtin.NotImplemented.NotImplemented$;
            }
            const equal = this.$hashEntries.length === other.$hashEntries.length &&
                this.$hashEntries.every(([arg, hash]) => other.$hashable.v.get$bucket_item(arg, hash) !== undefined) &&
                this.$unhashable.length === other.$unhashable.length &&
                this.$unhashable.every(arg => unionContains(other.$unhashable, arg)) &&
                other.$unhashable.every(arg => unionContains(this.$unhashable, arg));
            return op === "Eq" ? equal : !equal;
        },
        tp$as_sequence_or_mapping: true,
        mp$subscript() {
            throw new Sk.builtin.TypeError("There are no type variables left in " + Sk.misceval.objectRepr(this));
        },
    },
    classmethods: {
        __class_getitem__: {
            $meth(args) {
                return Sk.builtin.makeUnion(args.ob$type === Sk.builtin.tuple ? args.v : [args], true);
            },
            $flags: { OneArg: true },
        },
    },
    getsets: {
        __args__: { $get() { return this.$args; } },
        __parameters__: { $get() {
            for (const arg of this.$args.v) {
                if (Sk.builtin.checkClass(arg)) continue;
                const parameters = Sk.abstr.lookupAttr(arg, new Sk.builtin.str("__parameters__"));
                if (parameters && Sk.misceval.isTrue(parameters)) {
                    throw new Sk.builtin.NotImplementedError("union type-parameter substitution is not yet supported");
                }
            }
            return new Sk.builtin.tuple([]);
        } },
        __origin__: { $get() { return Sk.builtin.UnionType; } },
        __name__: { $get() { return new Sk.builtin.str("Union"); } },
        __qualname__: { $get() { return new Sk.builtin.str("Union"); } },
    },
    flags: { sk$unacceptableBase: true },
});

function unionContains(args, arg) {
    return args.some(value => value === arg || Sk.misceval.richCompareBool(value, arg, "Eq"));
}

// _Py_union_type_or and unionbuilder_add_single_unchecked.
Sk.builtin.typeUnion = function (left, right) {
    const unionable = value => Sk.builtin.checkNone(value) || Sk.builtin.checkClass(value) ||
        value instanceof Sk.builtin.GenericAlias || value instanceof Sk.builtin.UnionType;
    if (!Sk.__future__.python3 || !unionable(left) || !unionable(right)) {
        return Sk.builtin.NotImplemented.NotImplemented$;
    }
    return Sk.builtin.makeUnion([left, right], false);
};

Sk.builtin.makeUnion = function (values, checked) {
    const args = [], hashable = new Sk.builtin.set(), unhashable = [];
    function add(arg) {
        if (Sk.builtin.checkNone(arg)) arg = Sk.builtin.none;
        if (arg instanceof Sk.builtin.UnionType) {
            arg.$args.v.forEach(add);
            return;
        }
        if (checked) {
            if (Sk.builtin.checkString(arg)) {
                throw new Sk.builtin.NotImplementedError("union string arguments require typing ForwardRef support");
            }
            if (arg.ob$type === Sk.builtin.tuple) {
                throw new Sk.builtin.TypeError("Union[arg, ...]: each arg must be a type. Got " + Sk.misceval.objectRepr(arg) + ".");
            }
        }
        let canHash = true;
        try { Sk.abstr.objectHash(arg); } catch (_) { canHash = false; }
        if (canHash) {
            if (hashable.sq$contains(arg)) return;
            hashable.set$add(arg);
        } else {
            if (unionContains(unhashable, arg)) return;
            unhashable.push(arg);
        }
        args.push(arg);
    }
    values.forEach(add);
    if (!args.length) throw new Sk.builtin.TypeError("Cannot take a Union of no types.");
    return args.length === 1 ? args[0] : new Sk.builtin.UnionType(args, hashable, unhashable);
};
