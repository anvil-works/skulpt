/**
 * @constructor
 * @param {pyObject} func
 * @param {pyObject} iterable
 * @extends Sk.builtin.object
 */
Sk.builtin.filter_ = Sk.abstr.buildIteratorClass("filter", {
    constructor: function filter_(func, iterable) {
        this.$func = func;
        this.$iterable = iterable;
    },
    iternext(canSuspend) {
        // iterate over iterable until we pass the predicate
        // check$filter either returns the item or undefined, possibly suspending.
        const ret = Sk.misceval.iterFor(this.$iterable, (i) => {
            const filtered = this.check$filter(i);
            return filtered && filtered.$isSuspension
                ? Sk.misceval.chain(filtered, (item) => (item ? new Sk.misceval.Break(item) : undefined))
                : filtered ? new Sk.misceval.Break(filtered) : undefined;
        });
        return canSuspend ? ret : Sk.misceval.retryOptionalSuspensionOrThrow(ret);
    },
    slots: {
        tp$doc:
            "Return an iterator yielding those items of iterable for which function(item)\nis true. If function is None, return the items that are true.",
        tp$new(args, kwargs) {
            let [func, iterable] = Sk.abstr.copyKeywordsToNamedArgs("filter", ["predicate", "iterable"], args, kwargs, []);
            func = Sk.builtin.checkNone(func) || func === Sk.builtin.bool ? null : func;
            iterable = Sk.abstr.iter(iterable);
            // in theory you could subclass
            if (this === Sk.builtin.filter_.prototype) {
                return new Sk.builtin.filter_(func, iterable);
            } else {
                const instance = new this.constructor();
                Sk.builtin.filter_.call(instance, func, iterable);
                return instance;
            }
        },
    },
    proto: {
        check$filter(item) {
            let res;
            if (this.$func === null) {
                res = item;
            } else {
                res = Sk.misceval.callsimOrSuspendArray(this.$func, [item]);
            }
            return res && res.$isSuspension
                ? Sk.misceval.chain(res, (ret) => (Sk.misceval.isTrue(ret) ? item : undefined))
                : Sk.misceval.isTrue(res) ? item : undefined;
        },
    },
});

Sk.exportSymbol("Sk.builtin.filter_", Sk.builtin.filter_);
