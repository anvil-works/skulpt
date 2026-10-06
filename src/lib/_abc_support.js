// Host backend for the weak class registries used by CPython's _py_abc algorithm.
var $builtinmodule = function () {
    const WeakTypeSet = Sk.abstr.buildNativeClass("_abc_support._WeakTypeSet", {
        constructor: function WeakTypeSet() {
            if (typeof WeakRef === "undefined") {
                throw new Sk.builtin.NotImplementedError("ABC registries require host WeakRef support");
            }
            this.$buckets = new Map();
        },
        slots: {
            tp$new(args, kwargs) {
                Sk.abstr.checkNoArgs("_WeakTypeSet", args, kwargs);
                return new WeakTypeSet();
            },
            tp$iter() {
                const values = [];
                for (const [hash, bucket] of this.$buckets) {
                    for (const ref of bucket) {
                        const value = ref.deref();
                        if (value === undefined) {bucket.delete(ref);} else {values.push(value);}
                    }
                    if (!bucket.size) {this.$buckets.delete(hash);}
                }
                return new Sk.builtin.list(values).tp$iter();
            },
            sq$contains(value) {
                if (!Sk.builtin.checkClass(value)) {return false;}
                return this.$contains(value, Sk.abstr.objectHash(value));
            },
        },
        methods: {
            add: {
                $meth(value) {
                    if (!Sk.builtin.checkClass(value)) {throw new Sk.builtin.TypeError("ABC registries contain classes only");}
                    const hash = Sk.abstr.objectHash(value);
                    if (!this.$contains(value, hash)) {
                        let bucket = this.$buckets.get(hash);
                        if (!bucket) {this.$buckets.set(hash, bucket = new Set());}
                        bucket.add(new WeakRef(value));
                    }
                    return Sk.builtin.none.none$;
                },
                $flags: { OneArg: true },
            },
            clear: {
                $meth() { this.$buckets.clear(); return Sk.builtin.none.none$; },
                $flags: { NoArgs: true },
            },
        },
        proto: {
            $contains(value, hash) {
                const bucket = this.$buckets.get(hash);
                if (bucket) {
                    for (const ref of bucket) {
                        const stored = ref.deref();
                        if (stored === undefined) {bucket.delete(ref);} else if (stored === value || Sk.misceval.richCompareBool(stored, value, "Eq")) {return true;}
                    }
                }
                return false;
            },
        },
        flags: { sk$unacceptableBase: true },
    });
    return { _WeakTypeSet: WeakTypeSet };
};
