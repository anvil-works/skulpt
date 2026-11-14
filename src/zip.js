/**
 * @constructor
 * @param {Array} JS Array of iterator objects
 * @extends Sk.builtin.object
 */
Sk.builtin.zip_ = Sk.abstr.buildIteratorClass("zip", {
    constructor: function zip_(iters, strict) {
        this.$iters = iters;
        this.$strict = strict;
        if (iters.length === 0) {
            this.tp$iternext = () => undefined;
        }
    },
    iternext(canSuspend) {
        const tup = [];
        const ret = Sk.misceval.chain(
            Sk.misceval.iterArray(this.$iters, (it) =>
                Sk.misceval.chain(it.tp$iternext(canSuspend), (i) => {
                    if (i === undefined) {
                        return new Sk.misceval.Break(true);
                    }
                    tup.push(i);
                })
            ),
            (endzip) => {
                if (!endzip) {return new Sk.builtin.tuple(tup);}
                if (!this.$strict) {return undefined;}
                // Python/bltinmodule.c: zip_next's strict exhaustion check.
                const index = tup.length;
                if (index) {
                    throw new Sk.builtin.ValueError("zip() argument " + (index + 1) +
                        " is shorter than argument" + (index === 1 ? " 1" : "s 1-" + index));
                }
                let argument = 1;
                return Sk.misceval.chain(Sk.misceval.iterArray(this.$iters.slice(1), it =>
                    Sk.misceval.chain(it.tp$iternext(canSuspend), item => {
                        if (item !== undefined) {
                            throw new Sk.builtin.ValueError("zip() argument " + (argument + 1) +
                                " is longer than argument" + (argument === 1 ? " 1" : "s 1-" + argument));
                        }
                        argument++;
                    })), () => undefined);
            }
        );
        return canSuspend ? ret : Sk.misceval.retryOptionalSuspensionOrThrow(ret);
    },
    slots: {
        tp$doc:
            "zip(iter1 [,iter2 [...]]) --> zip object\n\nReturn a zip object whose .__next__() method returns a tuple where\nthe i-th element comes from the i-th iterable argument.  The .__next__()\nmethod continues until the shortest iterable in the argument sequence\nis exhausted and then it raises StopIteration.",
        tp$new(args, kwargs) {
            const [strict = Sk.builtin.bool.false$] = Sk.abstr.copyKeywordsToNamedArgs("zip", ["strict"], [], kwargs);
            const checkLengths = Sk.misceval.isTrue(strict);
            const iters = [];
            for (const arg of args) {iters.push(Sk.abstr.iter(arg));}
            if (this === Sk.builtin.zip_.prototype) {
                return new Sk.builtin.zip_(iters, checkLengths);
            } else {
                const instance = new this.constructor();
                Sk.builtin.zip_.call(instance, iters, checkLengths);
                return instance;
            }
        },
    },
});
Sk.exportSymbol("Sk.builtin.zip_", Sk.builtin.zip_);

