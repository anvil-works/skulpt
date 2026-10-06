// Objects/exceptions.c: BaseExceptionGroup_new, derive, subset and split_recursive.
Sk.builtin.BaseExceptionGroup = Sk.abstr.buildNativeClass("BaseExceptionGroup", {
    constructor: function BaseExceptionGroup() {
        Sk.builtin.BaseException.call(this);
    },
    base: Sk.builtin.BaseException,
    slots: {
        tp$new(args) {
            if (args.length !== 2) {throw new Sk.builtin.TypeError("BaseExceptionGroup.__new__() takes exactly 2 arguments (" + args.length + " given)");}
            const [message, exceptions] = args;
            if (!Sk.builtin.checkString(message)) {
                throw new Sk.builtin.TypeError("BaseExceptionGroup.__new__() argument 1 must be str, not " + Sk.abstr.typeName(message));
            }
            if (!Sk.builtin.checkSequence(exceptions) || exceptions instanceof Sk.builtin.dict) {
                throw new Sk.builtin.TypeError("second argument (exceptions) must be a sequence");
            }
            const savedRepr = exceptions instanceof Sk.builtin.list || exceptions instanceof Sk.builtin.tuple
                ? null : Sk.misceval.objectRepr(exceptions);
            return Sk.misceval.chain(Sk.misceval.arrayFromIterable(exceptions, true), items => {
                if (!items.length) {throw new Sk.builtin.ValueError("second argument (exceptions) must be a non-empty sequence");}
                let nestedBaseExceptions = false;
                items.forEach((exception, index) => {
                    if (!(exception instanceof Sk.builtin.BaseException)) {
                        throw new Sk.builtin.ValueError("Item " + index + " of second argument (exceptions) is not an exception");
                    }
                    if (!exception.ob$type.$isSubType(Sk.builtin.Exception)) {nestedBaseExceptions = true;}
                });
                let cls = this.ob$type;
                if (cls === Sk.builtin.ExceptionGroup && nestedBaseExceptions) {
                    throw new Sk.builtin.TypeError("Cannot nest BaseExceptions in an ExceptionGroup");
                } else if (cls === Sk.builtin.BaseExceptionGroup && !nestedBaseExceptions) {
                    cls = Sk.builtin.ExceptionGroup;
                } else if (nestedBaseExceptions && cls.$isSubType(Sk.builtin.Exception)) {
                    throw new Sk.builtin.TypeError("Cannot nest BaseExceptions in '" + cls.prototype.tp$name + "'");
                }
                const instance = new cls();
                Sk.builtin.BaseException.call(instance);
                instance.$message = message;
                instance.$exceptions = exceptions.ob$type === Sk.builtin.tuple ? exceptions : new Sk.builtin.tuple(items.slice());
                instance.$exceptionsRepr = savedRepr;
                instance.args = new Sk.builtin.tuple(args.slice());
                return instance;
            });
        },
        tp$str() {
            const count = this.$exceptions.v.length;
            return new Sk.builtin.str(new Sk.builtin.str(this.$message).$jsstr() + " (" + count + " sub-exception" + (count > 1 ? "s" : "") + ")");
        },
        $r() {
            const exceptions = this.args.v.length === 2 && this.args.v[1] instanceof Sk.builtin.list
                ? new Sk.builtin.list(this.$exceptions.v.slice()) : this.$exceptions;
            return new Sk.builtin.str(Sk.abstr.typeName(this) + "(" + Sk.misceval.objectRepr(this.$message) + ", " +
                (this.$exceptionsRepr === null ? Sk.misceval.objectRepr(exceptions) : this.$exceptionsRepr) + ")");
        },
    },
    getsets: {
        message: { $get() { return this.$message; } },
        exceptions: { $get() { return this.$exceptions; } },
    },
    methods: {
        derive: {
            $meth(exceptions) { return Sk.misceval.callsimOrSuspendArray(Sk.builtin.BaseExceptionGroup, [this.$message, exceptions]); },
            $flags: { OneArg: true },
        },
        split: {
            $meth(condition) {
                return Sk.misceval.chain(exceptionGroupSplit(this, condition, true), result => new Sk.builtin.tuple(result));
            },
            $flags: { OneArg: true },
        },
        subgroup: {
            $meth(condition) { return Sk.misceval.chain(exceptionGroupSplit(this, condition, false), result => result[0]); },
            $flags: { OneArg: true },
        },
    },
    classmethods: {
        __class_getitem__: {
            $meth(item) { return new Sk.builtin.GenericAlias(this, item); },
            $flags: { OneArg: true },
        },
    },
});

// CPython creates ExceptionGroup as a heap type with these two bases. Use the
// ordinary type constructor so subclass checks and mutable class state share MRO.
Sk.builtin.ExceptionGroup = Sk.builtin.type.prototype.tp$new.call(Sk.builtin.type.prototype, [
    new Sk.builtin.str("ExceptionGroup"),
    new Sk.builtin.tuple([Sk.builtin.BaseExceptionGroup, Sk.builtin.Exception]),
    new Sk.builtin.dict([new Sk.builtin.str("__module__"), new Sk.builtin.str("builtins")]),
]);

function exceptionGroupSplit(group, condition, constructRest) {
    const exceptionClass = cls => Sk.builtin.checkClass(cls) && cls.$isSubType(Sk.builtin.BaseException);
    let match;
    if (Sk.builtin.checkCallable(condition) && !Sk.builtin.checkClass(condition)) {
        match = exception => Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(condition, [exception]), Sk.misceval.isTrue);
    } else if (exceptionClass(condition)) {
        match = exception => exception.ob$type.$isSubType(condition);
    } else if (condition.ob$type === Sk.builtin.tuple && condition.v.every(exceptionClass)) {
        match = exception => condition.v.some(cls => exception.ob$type.$isSubType(cls));
    } else {
        throw new Sk.builtin.TypeError("expected an exception type, a tuple of exception types, or a callable (other than a class)");
    }
    const none = Sk.builtin.none.none$;
    function splitRecursive(exception) {
        return Sk.misceval.chain(match(exception), matched => {
            if (matched) {return [exception, none];}
            if (!(exception instanceof Sk.builtin.BaseExceptionGroup)) {return [none, constructRest ? exception : none];}
            const matching = [], rest = [];
            let index = 0;
            function visitChildren() {
                while (index < exception.$exceptions.v.length) {
                    const child = splitRecursive(exception.$exceptions.v[index++]);
                    if (child && child.$isSuspension) {
                        return Sk.misceval.chain(child, collect, visitChildren);
                    }
                    collect(child);
                }
                return Sk.misceval.chain(exceptionGroupSubset(exception, matching), matching =>
                    Sk.misceval.chain(constructRest ? exceptionGroupSubset(exception, rest) : none, rest => [matching, rest]));
            }
            function collect([matched, unmatched]) {
                if (matched !== none) {matching.push(matched);}
                if (unmatched !== none) {rest.push(unmatched);}
            }
            return visitChildren();
        });
    }
    return splitRecursive(group);
}

function exceptionGroupSubset(original, exceptions) {
    if (!exceptions.length) {return Sk.builtin.none.none$;}
    return Sk.misceval.chain(Sk.abstr.gattr(original, new Sk.builtin.str("derive"), true),
                             derive => Sk.misceval.callsimOrSuspendArray(derive, [new Sk.builtin.list(exceptions)]), derived => {
                                 if (!(derived instanceof Sk.builtin.BaseExceptionGroup)) {
                                     throw new Sk.builtin.TypeError("derive must return an instance of BaseExceptionGroup");
                                 }
                                 derived.traceback = original.traceback;
                                 derived.context = original.context;
                                 derived.$cause = original.$cause;
                                 // PyException_SetCause suppresses context even when the cause is None.
                                 derived.$suppressContext = true;
                                 const notes = Sk.misceval.tryCatch(() => Sk.abstr.gattr(original, new Sk.builtin.str("__notes__"), true), error => {
                                     if (!(error instanceof Sk.builtin.AttributeError)) {throw error;}
                                 });
                                 return Sk.misceval.chain(notes, notes => {
                                     if (Sk.builtin.checkSequence(notes) && !(notes instanceof Sk.builtin.dict)) {
                                         return Sk.misceval.chain(Sk.misceval.arrayFromIterable(notes, true), items =>
                                             Sk.abstr.sattr(derived, new Sk.builtin.str("__notes__"), new Sk.builtin.list(items), true), () => derived);
                                     }
                                     return derived;
                                 });
                             });
}
