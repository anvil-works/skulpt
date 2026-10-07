/**
 * @namespace Sk.misceval
 * 
 * @description
 * Various function protocols that include suspension aware options
 * As well as handling some common pyObject operations to Javascript
 *
 */
Sk.misceval = {};
Sk.exportSymbol("Sk.misceval.currentFrame", undefined);

/** @typedef {Sk.builtin.object}*/ var pyObject;

/*
  Suspension object format:
  {resume: function() {...}, // the continuation - returns either another suspension or the return value
   data: <copied down from innermost level>,
   optional: <if true, can be resumed immediately (eg debug stops)>,
   child: <Suspension, or null if we are the innermost level>,
   $blk: <>, $loc: <>, $gbl: <>, $exc: <>, $err: <>, [$cell: <>],
  }
*/

/**
 * @description
 * Hi kids lets make a suspension...
 * 
 * @constructor
 * @param {function(?)=} resume A function to be called on resume. child is resumed first and its return value is passed to this function.
 * @param {Object=} child A child suspension. 'optional' will be copied from here if supplied.
 * @param {Object=} data Data attached to this suspension. Will be copied from child if not supplied.
 */
Sk.misceval.Suspension = function Suspension(resume, child, data) {
    this.$isSuspension = true;
    if (resume !== undefined && child !== undefined) {
        this.resume = function () {
            return resume(child.resume());
        };
    }
    this.child = child;
    this.optional = child !== undefined && child.optional;
    if (data === undefined && child !== undefined) {
        this.data = child.data;
    } else {
        this.data = data;
    }
};
Sk.exportSymbol("Sk.misceval.Suspension", Sk.misceval.Suspension);

/**
 * @description
 * Well this seems pretty obvious by the name what it should do..
 *
 * @param {Sk.misceval.Suspension} susp
 * @param {string=} message
 */
Sk.misceval.retryOptionalSuspensionOrThrow = function (susp, message) {
    while (susp instanceof Sk.misceval.Suspension) {
        if (!susp.optional) {
            const err = new Sk.builtin.SuspensionError(message || "Cannot call a function that blocks or suspends here");
            let prev_susp = susp;
            const tb = [];
            while (prev_susp != null) {
                if (prev_susp.$lineno) {
                    // compile code added attributes so fill the traceback
                    tb.push({ filename: prev_susp.$filename, lineno: prev_susp.$lineno, colno: prev_susp.$colno });
                }
                prev_susp = prev_susp.child;
            }
            tb.reverse();
            err.traceback.push(...tb);
            throw err;
        }
        susp = susp.resume();
    }
    return susp;
};
Sk.exportSymbol("Sk.misceval.retryOptionalSuspensionOrThrow", Sk.misceval.retryOptionalSuspensionOrThrow);

/**
 * @description
 * Check if the given object is valid to use as an index. Only ints, or if the object has an `__index__` method.
 * 
 * @param {pyObject} o - typically an {@link Sk.builtin.int_} legacy code might use a js number
 * @returns {boolean}
 */
Sk.misceval.isIndex = function (o) {
    return o !== null && o !== undefined && (o.nb$index !== undefined || (typeof o === "number" && Number.isInteger(o)));
};
Sk.exportSymbol("Sk.misceval.isIndex", Sk.misceval.isIndex);


function asIndex(index) {
    if (index === null || index === undefined) {
        return;
    } else if (index.sk$int === true) {
        // if we're an int or int subclass use the internal value - as per CPython
        return index.v;
    } else if (index.nb$index !== undefined) {
        return index.nb$index(); // this slot will check the return value is a number / JSBI.BigInt.
    } else if (typeof index === "number" && Number.isInteger(index)) {
        return index;
    }
};

function asIndexOrThrow(index, msg) {
    const i = asIndex(index);
    if (i !== undefined) {
        return i;
    }
    msg = msg || "'{tp$name}' object cannot be interpreted as an integer";
    msg = msg.replace("{tp$name}", Sk.abstr.typeName(index));
    throw new Sk.builtin.TypeError(msg);
}

/**
 * 
 * @param {*} index 
 * 
 * @description
 * will return an integer javascript number
 * if the value is larger than Number.MAX_SAFE_INTEGER will return a BigInt
 * if the object passed is not a valid indexable object then it will return undefined
 * if you want to throw an error instead of returning undefined use {@link Sk.misceval.asIndexOrThrow}
 * If you know you want a number and not a BigInt - use {@link Sk.misceval.asIndexSized}
 */
Sk.misceval.asIndex = asIndex;


/**
 * 
 * @param {*} index 
 * @param {Sk.builtin.Exception=} Err provided an excption type if you wish to throw an exception
 * @param {string} msg an option message if the index passed is not a valid indexable object
 * 
 * @description
 * this function will always return a `Number` whose size is less than `Number.MAX_SAFE_INTEGER`
 * If you provide an err then this function will throw an error if the index is larger than `Number.MAX_SAFE_INTEGER`
 */
Sk.misceval.asIndexSized = function (index, Err, msg) {
    const i = asIndexOrThrow(index, msg);
    if (typeof i === "number") {
        return i; // integer v property will by a javascript number if it is index sized
    }
    if (Err == null) {
        return JSBI.lessThan(i, JSBI.__ZERO) ? -Number.MAX_SAFE_INTEGER : Number.MAX_SAFE_INTEGER;
    }
    throw new Err("cannot fit '" + Sk.abstr.typeName(index) + "' into an index-sized integer");
};

/**
 * @function
 * 
 * @param {pyObject|number} index - typically an {@link Sk.builtin.int_} legacy code might use a js number 
 * @param {string=} msg - an optional message when throwing the TypeError
 * @throws {Sk.builtin.TypeError}
 *
 * @description
 * requires a pyObject - returns a string or integer depending on the size.
 * throws a TypeError that the object cannot be interpreted as an index
 * can provide a custom message
 * include {tp$name} in the custom message which will be replaced by the typeName of the object
 * 
 * - converts the `Sk.builtin.int_` 
 * - if the number is too large to be safe returns a string
 * @returns {number|BigInt|JSBI} 
 */
Sk.misceval.asIndexOrThrow = asIndexOrThrow;

/**
 * return u[v:w]
 * @ignore
 */
Sk.misceval.applySlice = function (u, v, w, canSuspend) {
    return Sk.abstr.objectGetItem(u, new Sk.builtin.slice(v, w, null), canSuspend);
};
Sk.exportSymbol("Sk.misceval.applySlice", Sk.misceval.applySlice);

/**
 * u[v:w] = x
 * @ignore
 */
Sk.misceval.assignSlice = function (u, v, w, x, canSuspend) {
    const slice = new Sk.builtin.slice(v, w);
    if (x === null) {
        return Sk.abstr.objectDelItem(u, slice);
    } else {
        return Sk.abstr.objectSetItem(u, slice, x, canSuspend);
    }
};
Sk.exportSymbol("Sk.misceval.assignSlice", Sk.misceval.assignSlice);

/**
 * Note that this does no validation, just coercion.
 */
Sk.misceval.arrayFromArguments = function (args) {
    // If args is not a single thing return as is
    var it, i;
    var res;
    var arg;
    if (args.length != 1) {
        return args;
    }
    arg = args[0];
    if (arg instanceof Sk.builtin.set) {
        // this is a Sk.builtin.set
        arg = arg.tp$iter().$obj;
    } else if (arg instanceof Sk.builtin.dict) {
        // this is a Sk.builtin.list
        arg = Sk.builtin.dict.prototype["keys"].func_code(arg);
    }

    // shouldn't else if here as the above may output lists to arg.
    if (arg instanceof Sk.builtin.list || arg instanceof Sk.builtin.tuple) {
        return arg.v;
    } else if (Sk.builtin.checkIterable(arg)) {
        // handle arbitrary iterable (strings, generators, etc.)
        res = [];
        for (it = Sk.abstr.iter(arg), i = it.tp$iternext(); i !== undefined; i = it.tp$iternext()) {
            res.push(i);
        }
        return res;
    }

    throw new Sk.builtin.TypeError("'" + Sk.abstr.typeName(arg) + "' object is not iterable");
};
Sk.exportSymbol("Sk.misceval.arrayFromArguments", Sk.misceval.arrayFromArguments);


/**
 * 
 * @constructor
 * 
 * @param {Function} fn
 * @param {boolean=} [handlesOwnSuspensions=false] - Does it handle its own suspension?
 * 
 * @description
 * Create a generic Python iterator that repeatedly calls a given JS function
 * until it returns 'undefined'. This function is useful for user defined Native classes
 * 
 * @example
 * // some immutable tuple like class where the v property is an array
 * MyClass.prototype.tp$iter = function() {
 *   let i = 0;
 *   const len = this.v.length;
 *   return new Sk.miscival.iterator(() => i >= len ? this.v[i++] : undefined);
 * }
 * @extends {Sk.builtin.object}
 * 
 */
Sk.misceval.iterator = Sk.abstr.buildIteratorClass("iterator", {
    constructor : function iterator (fn, handlesOwnSuspensions) {
        this.tp$iternext = handlesOwnSuspensions ? fn : function (canSuspend) {
            let x = fn();
            if (canSuspend || x === undefined || !x.$isSuspension) {
                return x;
            } else {
                return Sk.misceval.retryOptionalSuspensionOrThrow(x);
            }
        };
    }, 
    iternext: function (canSuspend) { /* keep slot __next__ happy */
        return this.tp$iternext(canSuspend);
    },
    flags: { sk$unacceptableBase: true },
});

/**
 * for reversed comparison: Gt -> Lt, etc.
 * @ignore
 */
Sk.misceval.swappedOp_ = {
    "Eq"   : "Eq",
    "NotEq": "NotEq",
    "Lt"   : "Gt",
    "LtE"  : "GtE",
    "Gt"   : "Lt",
    "GtE"  : "LtE",
};

Sk.misceval.opSymbols = {
    Eq: "==",
    NotEq: "!=",
    Lt: "<",
    LtE: "<=",
    Gt: ">",
    GtE: ">=",
    Is: "is",
    IsNot: "is not",
    In_: "in",
    NotIn: "not in",
};

/**
 * @function
 * 
 * @param {pyObject} v
 * @param {pyObject} w
 * @param {string} op - `Eq`, `NotEq`, `Lt`, `LtE`, `Gt`, `GtE`, `Is`, `IsNot`, `In_`, `NotIn`
 * @param {boolean=} canSuspend
 * 
 * @returns {boolean}
 * 
 * @todo This implementation overrides the return value from a user defined dunder method since it returns a boolean
 * whereas Python will return the user defined return value.
 * 
 * @throws {Sk.builtin.TypeError}
 */
Sk.misceval.richCompareBool = function (v, w, op, canSuspend) {
    // v and w must be Python objects. will return Javascript true or false for internal use only
    // if you want to return a value from richCompareBool to Python you must wrap as Sk.builtin.bool first
    Sk.asserts.assert(v.sk$object && w.sk$object, "JS object passed to richCompareBool");
    var ret,
        swapped_shortcut,
        shortcut;

    const v_type = v.ob$type;
    const w_type = w.ob$type;
    const w_is_subclass = w_type !== v_type && w_type.sk$baseClass === undefined && w_type.$isSubType(v_type);

    // Python 2 has specific rules when comparing two different builtin types
    // currently, this code will execute even if the objects are not builtin types
    // but will fall through and not return anything in this section
    if (!Sk.__future__.python3 && v_type !== w_type && (op === "GtE" || op === "Gt" || op === "LtE" || op === "Lt")) {
        // note: sets are omitted here because they can only be compared to other sets
        const numeric_types = [Sk.builtin.float_, Sk.builtin.int_, Sk.builtin.lng, Sk.builtin.bool];
        const sequence_types = [
            Sk.builtin.dict,
            Sk.builtin.enumerate,
            Sk.builtin.filter_,
            Sk.builtin.list,
            Sk.builtin.map_,
            Sk.builtin.str,
            Sk.builtin.tuple,
            Sk.builtin.zip_,
        ];

        const v_num_type = numeric_types.indexOf(v_type);
        const v_seq_type = sequence_types.indexOf(v_type);
        const w_num_type = numeric_types.indexOf(w_type);
        const w_seq_type = sequence_types.indexOf(w_type);

        // NoneTypes are considered less than any other type in Python
        // note: this only handles comparing NoneType with any non-NoneType.
        // Comparing NoneType with NoneType is handled further down.
        if (v === Sk.builtin.none.none$) {
            switch (op) {
                case "Lt":
                    return true;
                case "LtE":
                    return true;
                case "Gt":
                    return false;
                case "GtE":
                    return false;
            }
        }

        if (w === Sk.builtin.none.none$) {
            switch (op) {
                case "Lt":
                    return false;
                case "LtE":
                    return false;
                case "Gt":
                    return true;
                case "GtE":
                    return true;
            }
        }

        // numeric types are always considered smaller than sequence types in Python
        if (v_num_type !== -1 && w_seq_type !== -1) {
            switch (op) {
                case "Lt":
                    return true;
                case "LtE":
                    return true;
                case "Gt":
                    return false;
                case "GtE":
                    return false;
            }
        }

        if (v_seq_type !== -1 && w_num_type !== -1) {
            switch (op) {
                case "Lt":
                    return false;
                case "LtE":
                    return false;
                case "Gt":
                    return true;
                case "GtE":
                    return true;
            }
        }

        // in Python, different sequence types are ordered alphabetically
        // by name so that dict < list < str < tuple
        if (v_seq_type !== -1 && w_seq_type !== -1) {
            switch (op) {
                case "Lt":
                    return v_seq_type < w_seq_type;
                case "LtE":
                    return v_seq_type <= w_seq_type;
                case "Gt":
                    return v_seq_type > w_seq_type;
                case "GtE":
                    return v_seq_type >= w_seq_type;
            }
        }
    }

    // handle identity and membership comparisons
    // no longer called from compile code - left here for backwards compatibliity
    if (op === "Is") {
        return v === w;
    }

    if (op === "IsNot") {
        return v !== w;
    }

    if (op === "In") {
        return Sk.misceval.chain(Sk.abstr.sequenceContains(w, v, canSuspend), Sk.misceval.isTrue);
    }
    if (op === "NotIn") {
        return Sk.misceval.chain(Sk.abstr.sequenceContains(w, v, canSuspend), function (x) {
            return !Sk.misceval.isTrue(x);
        });
    }

    // Call Javascript shortcut method if exists for either object

    var op2shortcut = {
        "Eq"   : "ob$eq",
        "NotEq": "ob$ne",
        "Gt"   : "ob$gt",
        "GtE"  : "ob$ge",
        "Lt"   : "ob$lt",
        "LtE"  : "ob$le"
    };

    shortcut = op2shortcut[op];
    // similar rules apply as with binops - prioritize the reflected ops of subtypes
    // but different to binop - even if the swapped op is the same as the parent still call it
    if (w_is_subclass) {
        swapped_shortcut = op2shortcut[Sk.misceval.swappedOp_[op]];
        if ((ret = w[swapped_shortcut](v)) !== Sk.builtin.NotImplemented.NotImplemented$) {
            return Sk.misceval.isTrue(ret);
        }
    }
    if ((ret= v[shortcut](w)) !== Sk.builtin.NotImplemented.NotImplemented$) {
        return Sk.misceval.isTrue(ret); 
    // techincally this is not correct along with the compile code see #1252
        // richcompare slots could return any pyObject ToDo - would require changing compile code
    }

    if (!w_is_subclass) {
        swapped_shortcut = op2shortcut[Sk.misceval.swappedOp_[op]];
        if ((ret = w[swapped_shortcut](v)) !== Sk.builtin.NotImplemented.NotImplemented$) {
            return Sk.misceval.isTrue(ret);
        }
    }

    if (!Sk.__future__.python3) {
        const vcmp = Sk.abstr.lookupSpecial(v, Sk.builtin.str.$cmp);
        if (vcmp) {
            try {
                ret = Sk.misceval.callsimArray(vcmp, [w]);
                if (Sk.builtin.checkNumber(ret)) {
                    ret = Sk.builtin.asnum$(ret);
                    if (op === "Eq") {
                        return ret === 0;
                    } else if (op === "NotEq") {
                        return ret !== 0;
                    } else if (op === "Lt") {
                        return ret < 0;
                    } else if (op === "Gt") {
                        return ret > 0;
                    } else if (op === "LtE") {
                        return ret <= 0;
                    } else if (op === "GtE") {
                        return ret >= 0;
                    }
                }

                if (ret !== Sk.builtin.NotImplemented.NotImplemented$) {
                    throw new Sk.builtin.TypeError("comparison did not return an int");
                }
            } catch (e) {
                throw new Sk.builtin.TypeError("comparison did not return an int");
            }
        }
        const wcmp = Sk.abstr.lookupSpecial(w, Sk.builtin.str.$cmp);
        if (wcmp) {
            // note, flipped on return value and call
            try {
                ret = Sk.misceval.callsimArray(wcmp, [v]);
                if (Sk.builtin.checkNumber(ret)) {
                    ret = Sk.builtin.asnum$(ret);
                    if (op === "Eq") {
                        return ret === 0;
                    } else if (op === "NotEq") {
                        return ret !== 0;
                    } else if (op === "Lt") {
                        return ret > 0;
                    } else if (op === "Gt") {
                        return ret < 0;
                    } else if (op === "LtE") {
                        return ret >= 0;
                    } else if (op === "GtE") {
                        return ret <= 0;
                    }
                }

                if (ret !== Sk.builtin.NotImplemented.NotImplemented$) {
                    throw new Sk.builtin.TypeError("comparison did not return an int");
                }
            } catch (e) {
                throw new Sk.builtin.TypeError("comparison did not return an int");
            }
        }
        // handle special cases for comparing None with None or Bool with Bool
        if (v === Sk.builtin.none.none$ && w === Sk.builtin.none.none$) {
            // Javascript happens to return the same values when comparing null
            // with null or true/false with true/false as Python does when
            // comparing None with None or True/False with True/False

            if (op === "Eq") {
                return v.v === w.v;
            }
            if (op === "NotEq") {
                return v.v !== w.v;
            }
            if (op === "Gt") {
                return v.v > w.v;
            }
            if (op === "GtE") {
                return v.v >= w.v;
            }
            if (op === "Lt") {
                return v.v < w.v;
            }
            if (op === "LtE") {
                return v.v <= w.v;
            }
        }
    }

    // handle equality comparisons for any remaining objects
    if (op === "Eq") {
        return v === w;
    }
    if (op === "NotEq") {
        return v !== w;
    }

    const vname = Sk.abstr.typeName(v);
    const wname = Sk.abstr.typeName(w);
    throw new Sk.builtin.TypeError("'" + Sk.misceval.opSymbols[op] + "' not supported between instances of '" + vname + "' and '" + wname + "'");
    //throw new Sk.builtin.ValueError("don't know how to compare '" + vname + "' and '" + wname + "'");
};
Sk.exportSymbol("Sk.misceval.richCompareBool", Sk.misceval.richCompareBool);


/**
 * @function
 * @description
 * calls the __repr__ of a pyObject or returns `<unknown>` if a JS object was passed
 * @param {*} obj
 * @returns {string}
 * 
 */
Sk.misceval.objectRepr = function (obj) {
    Sk.asserts.assert(obj !== undefined, "trying to repr undefined");
    if (obj !== null && obj.$r) {
        return obj.$r().v;
    } else {
        try {
            // str goes through the common javascript cases or throws a TypeError;
            return new Sk.builtin.str(obj).v;
        } catch (e) {
            if (e instanceof Sk.builtin.TypeError) {
                return "<unknown>";
            } else {
                throw e;
            }
        }
    }
};
Sk.exportSymbol("Sk.misceval.objectRepr", Sk.misceval.objectRepr);

Sk.misceval.opAllowsEquality = function (op) {
    switch (op) {
        case "LtE":
        case "Eq":
        case "GtE":
            return true;
    }
    return false;
};
Sk.exportSymbol("Sk.misceval.opAllowsEquality", Sk.misceval.opAllowsEquality);


/**
 * @function
 * @description
 * Decides whether a pyObject is True or not
 * @returns {boolean}
 * @param {*} x 
 */
Sk.misceval.isTrue = function (x) {
    if (x === true || x === Sk.builtin.bool.true$) {
        return true;
    }
    if (x === false || x === Sk.builtin.bool.false$) {
        return false;
    }
    if (x === null || x === undefined) {
        return false;
    }
    if (x.nb$bool) {
        return x.nb$bool(); // the slot wrapper takes care of converting to js Boolean
    }
    if (x.sq$length) {
        // the slot wrapper takes care of the error message and converting to js int
        return x.sq$length() !== 0;
    }
    return Boolean(x);
};
Sk.exportSymbol("Sk.misceval.isTrue", Sk.misceval.isTrue);

Sk.misceval.softspace_ = false;
Sk.misceval.print_ = function (x) {
    var s;

    function isspace(c) {
        return c === "\n" || c === "\t" || c === "\r";
    }

    if (Sk.misceval.softspace_) {
        if (x !== "\n") {
            Sk.output(" ");
        }
        Sk.misceval.softspace_ = false;
    }

    s = new Sk.builtin.str(x);

    return Sk.misceval.chain(
        Sk.importModule("sys", false, true),
        function (sys) {
            return Sk.misceval.apply(sys["$d"]["stdout"]["write"], undefined, undefined, undefined, [sys["$d"]["stdout"], s]);
        },
        function () {
            if (s.v.length === 0 || !isspace(s.v[s.v.length - 1]) || s.v[s.v.length - 1] === " ") {
                Sk.misceval.softspace_ = true;
            }
        }
    );
};
Sk.exportSymbol("Sk.misceval.print_", Sk.misceval.print_);

/**
 * @function
 * @description 
 * Get a python object from a given namespace
 * @param {string} name
 * @param {Object=} other generally globals
 * @example
 * Sk.misceval.loadname("foo", Sk.globals);
 */
// Python/ceval.c LOAD_GLOBAL / LOAD_NAME: globals first, then the frame's
// captured builtin mapping; only KeyError means a missing builtin name.
Sk.misceval.getBuiltins = function (globals) {
    let builtins = globals && globals.__builtins__;
    if (builtins === undefined) {
        const frame = Sk.misceval.currentFrame;
        return frame ? frame.getBuiltins() : Sk.misceval.namespaceDict(Sk.builtins);
    }
    if (builtins instanceof Sk.builtin.module) {
        builtins = Sk.misceval.namespaceDict(builtins.$d);
    }
    return builtins;
};
Sk.exportSymbol("Sk.misceval.getBuiltins", Sk.misceval.getBuiltins);

Sk.misceval.lookupBuiltin = function (name, builtins) {
    try {
        return Sk.misceval.retryOptionalSuspensionOrThrow(
            Sk.abstr.objectGetItem(builtins, new Sk.builtin.str(Sk.unfixReserved(name)))
        );
    } catch (err) {
        if (err instanceof Sk.builtin.KeyError) {return undefined;}
        throw err;
    }
};
Sk.exportSymbol("Sk.misceval.lookupBuiltin", Sk.misceval.lookupBuiltin);

Sk.misceval.loadname = function (name, other, builtins) {
    const value = other[name];
    if (value !== undefined) {return value;}
    const builtin = Sk.misceval.lookupBuiltin(name, builtins === undefined ? Sk.misceval.getBuiltins(other) : builtins);
    if (builtin !== undefined) {return builtin;}
    throw new Sk.builtin.NameError("name '" + Sk.unfixReserved(name) + "' is not defined");
};
Sk.exportSymbol("Sk.misceval.loadname", Sk.misceval.loadname);

// LOAD_BUILD_CLASS consults builtins without global-name fallback.
Sk.misceval.loadBuildClass = function (builtins) {
    const builder = Sk.misceval.lookupBuiltin("__build_class__", builtins);
    if (builder === undefined) {throw new Sk.builtin.NameError("__build_class__ not found");}
    return builder;
};
Sk.exportSymbol("Sk.misceval.loadBuildClass", Sk.misceval.loadBuildClass);

// Python/ceval.c IMPORT_NAME uses only the frame's builtin __import__.
Sk.misceval.importName = function (name, globals, locals, fromlist, level, builtins) {
    const importer = Sk.misceval.lookupBuiltin("__import__", builtins);
    if (importer === undefined) {throw new Sk.builtin.ImportError("__import__ not found");}
    return Sk.misceval.callsimOrSuspendArray(importer, [
        new Sk.builtin.str(name), Sk.misceval.namespaceDict(globals), locals,
        fromlist === null ? Sk.builtin.none.none$ : new Sk.builtin.tuple(fromlist.map(name => new Sk.builtin.str(name))),
        new Sk.builtin.int_(level)
    ]);
};
Sk.exportSymbol("Sk.misceval.importName", Sk.misceval.importName);

/**
 *
 * Notes on necessity for 'call()':
 *
 * Classes are callable in python to create an instance of the class. If
 * we're calling "C()" we cannot tell at the call site whether we're
 * calling a standard function, or instantiating a class.
 *
 * JS does not support user-level callables. So, we can't use the normal
 * prototype hierarchy to make the class inherit from a 'class' type
 * where the various tp$getattr, etc. methods would live.
 *
 * Instead, we must copy all the methods from the prototype of our class
 * type onto every instance of the class constructor function object.
 * That way, both "C()" and "C.tp$getattr(...)" can still work. This is
 * of course quite expensive.
 *
 * The alternative would be to indirect all calls (whether classes or
 * regular functions) through something like C.$call(...). In the case
 * of class construction, $call could then call the constructor after
 * munging arguments to pass them on. This would impose a penalty on
 * regular function calls unfortunately, as they would have to do the
 * same thing.
 *
 * Note that the same problem exists for function objects too (a "def"
 * creates a function object that also has properties). It just happens
 * that attributes on classes in python are much more useful and common
 * that the attributes on functions.
 *
 * Also note, that for full python compatibility we have to do the $call
 * method because any python object could have a __call__ method which
 * makes the python object callable too. So, unless we were to make
 * *all* objects simply (function(){...}) and use the dict to create
 * hierarchy, there would be no way to call that python user function. I
 * think I'm prepared to sacrifice __call__ support, or only support it
 * post-ECMA5 or something.
 *
 * Is using (function(){...}) as the only object type too crazy?
 * Probably. Better or worse than having two levels of function
 * invocation for every function call?
 *
 * For a class `C' with instance `inst' we have the following cases:
 *
 * 1. C.attr
 *
 * 2. C.staticmeth()
 *
 * 3. x = C.staticmeth; x()
 *
 * 4. inst = C()
 *
 * 5. inst.attr
 *
 * 6. inst.meth()
 *
 * 7. x = inst.meth; x()
 *
 * 8. inst(), where C defines a __call__
 *
 * Because in general these are accomplished by a helper function
 * (tp$getattr/setattr/slice/ass_slice/etc.) it seems appropriate to add
 * a call that generally just calls through, but sometimes handles the
 * unusual cases. Once ECMA-5 is more broadly supported we can revisit
 * and hopefully optimize.
 *
 * @param {Object} func the thing to call
 * @param {Object=} kwdict **kwargs
 * @param {Object=} varargseq **args
 * @param {Object=} kws keyword args or undef
 * @param {...*} args stuff to pass it
 *
 *
 * @todo I think all the above is out of date.
 * @ignore
 */
Sk.misceval.call = function (func, kwdict, varargseq, kws, args) {
    args = Array.prototype.slice.call(arguments, 4);
    // todo; possibly inline apply to avoid extra stack frame creation
    return Sk.misceval.apply(func, kwdict, varargseq, kws, args);
};
Sk.exportSymbol("Sk.misceval.call", Sk.misceval.call);

/**
 * @param {?Object} suspensionHandlers
 * @param {Object} func the thing to call
 * @param {Object=} kwdict **kwargs
 * @param {Object=} varargseq **args
 * @param {Object=} kws keyword args or undef
 * @param {...*} args stuff to pass it
 *
 *
 * @todo I think all the above is out of date.
 */

Sk.misceval.callAsync = function (suspensionHandlers, func, kwdict, varargseq, kws, args) {
    args = Array.prototype.slice.call(arguments, 5);
    // todo; possibly inline apply to avoid extra stack frame creation
    return Sk.misceval.applyAsync(suspensionHandlers, func, kwdict, varargseq, kws, args);
};
Sk.exportSymbol("Sk.misceval.callAsync", Sk.misceval.callAsync);

Sk.misceval.callOrSuspend = function (func, kwdict, varargseq, kws, args) {
    args = Array.prototype.slice.call(arguments, 4);
    // todo; possibly inline apply to avoid extra stack frame creation
    return Sk.misceval.applyOrSuspend(func, kwdict, varargseq, kws, args);
};
Sk.exportSymbol("Sk.misceval.callOrSuspend", Sk.misceval.callOrSuspend);

/**
 * @param {Object} func the thing to call
 * @param {...*} args stuff to pass it
 * @ignore
 */
Sk.misceval.callsim = function (func, args) {
    args = Array.prototype.slice.call(arguments, 1);
    return Sk.misceval.apply(func, undefined, undefined, undefined, args);
};
Sk.exportSymbol("Sk.misceval.callsim", Sk.misceval.callsim);

/**
 * @param {Object=} func the thing to call
 * @param {Array=} args an array of arguments to pass to the func
 * @param {Array=} kws an array of string/pyObject pairs to pass to the func as kwargs
 * 
 * @description
 * Call a pyObject - if the object is not callable will throw a TypeError
 * Requires args to be a Javascript array.
 * kws should be an array of string/pyObject pairs as key/values
 */
Sk.misceval.callsimArray = function (func, args, kws) {
    args = args || [];
    return Sk.misceval.retryOptionalSuspensionOrThrow(Sk.misceval.callsimOrSuspendArray(func, args, kws));
};
Sk.exportSymbol("Sk.misceval.callsimArray", Sk.misceval.callsimArray);

/**
 * @param {?Object} suspensionHandlers any custom suspension handlers
 * @param {Object} func the thing to call
 * @param {...*} args stuff to pass it
 */
Sk.misceval.callsimAsync = function (suspensionHandlers, func, args) {
    args = Array.prototype.slice.call(arguments, 2);
    return Sk.misceval.applyAsync(suspensionHandlers, func, undefined, undefined, undefined, args);
};
Sk.exportSymbol("Sk.misceval.callsimAsync", Sk.misceval.callsimAsync);

/**
 * @param {Object} func the thing to call
 * @param {...*} args stuff to pass it
 * @deprecated
 * @ignore
 */
Sk.misceval.callsimOrSuspend = function (func, args) {
    args = Array.prototype.slice.call(arguments, 1);
    return Sk.misceval.applyOrSuspend(func, undefined, undefined, undefined, args);
};
Sk.exportSymbol("Sk.misceval.callsimOrSuspend", Sk.misceval.callsimOrSuspend);

/**
 * @description
 * Does the same thing as callsimOrSuspend without expensive call to
 * Array.slice.  Requires args+kws to be Javascript arrays. 
 * The preferred method for calling a pyObject. 
 * 
 * @param {Object=} func the thing to call
 * @param {Array=} args an array of arguments to pass to the func
 * @param {Array=} kws an array of keyword arguments to pass to the func
 *
 */
Sk.misceval.callsimOrSuspendArray = function (func, args, kws) {
    args = args || [];
    if (func !== undefined && func.tp$call) {
        return func.tp$call(args, kws);
    } else {
        // Slow path handles things like calling native JS fns
        // (perhaps we should stop supporting that), and weird
        // detection of the __call__ method (everything should use tp$call)
        return Sk.misceval.applyOrSuspend(func, undefined, undefined, kws, args);
    }
};
Sk.exportSymbol("Sk.misceval.callsimOrSuspendArray", Sk.misceval.callsimOrSuspendArray);

/**
 * Wrap Sk.misceval.applyOrSuspend, but throw an error if we suspend
 * @ignore
 */
Sk.misceval.apply = function (func, kwdict, varargseq, kws, args) {
    var r = Sk.misceval.applyOrSuspend(func, kwdict, varargseq, kws, args);
    if (r instanceof Sk.misceval.Suspension) {
        return Sk.misceval.retryOptionalSuspensionOrThrow(r);
    } else {
        return r;
    }
};
Sk.exportSymbol("Sk.misceval.apply", Sk.misceval.apply);

Sk.misceval.defaultHandlers = {};


const SUSP_PROMISE = "Sk.promise";
const SUSP_DELAY = "Sk.delay";
const SUSP_YIELD = "Sk.yield";

/**
 * Wraps anything that can return an Sk.misceval.Suspension, and returns a
 * JS Promise with the result. Also takes an object map of suspension handlers:
 * pass in {"suspType": function (susp) {} }, and your function will be called
 * with the Suspension object if susp.type=="suspType". The type "*" will match
 * all otherwise unhandled suspensions.
 *
 * A suspension handler should return a Promise yielding the return value of
 * r.resume() - ie, either the final return value of this call or another
 * Suspension. That is, the null suspension handler is:
 *
 *     function handler(susp) {
 *       return new Promise(function(resolve, reject) {
 *         try {
 *           resolve(susp.resume());
 *         } catch(e) {
 *           reject(e);
 *         }
 *       });
 *     }
 *
 * Alternatively, a handler can return null to perform the default action for
 * that suspension type.
 *
 * (Note: do *not* call asyncToPromise() in a suspension handler; this will
 * create a new Promise object for each such suspension that occurs)
 *
 * asyncToPromise() returns a Promise that will be resolved with the final
 * return value, or rejected with an exception if one is thrown.
 *
 * @param{function()} suspendablefn returns either a result or a Suspension
 * @param{Object=} suspHandlers an object map of suspension handlers
 */
Sk.misceval.asyncToPromise = function (suspendablefn, suspHandlers) {
    return new Promise(function (resolve, reject) {
        try {
            var r = suspendablefn();

            (function handleResponse(r) {
                try {
                    // jsh*nt insists these be defined outside the loop
                    var resume = function () {
                        try {
                            handleResponse(r.resume());
                        } catch (e) {
                            reject(e);
                        }
                    };
                    var resumeWithData = function resolved(x) {
                        try {
                            r.data["result"] = x;
                            resume();
                        } catch (e) {
                            reject(e);
                        }
                    };
                    var resumeWithError = function rejected(e) {
                        try {
                            r.data["error"] = e;
                            resume();
                        } catch (ex) {
                            reject(ex);
                        }
                    };

                    while (r instanceof Sk.misceval.Suspension) {
                        const type = r.data["type"];
                        let handler = suspHandlers && (suspHandlers[type] || suspHandlers["*"]);
                        if (!handler) {
                            handler = Sk.misceval.defaultHandlers[type] || Sk.misceval.defaultHandlers["*"];
                        }

                        if (handler) {
                            var handlerPromise = handler(r);
                            if (handlerPromise) {
                                handlerPromise.then(handleResponse, reject);
                                return;
                            }
                        }

                        if (type === SUSP_PROMISE) {
                            r.data["promise"].then(resumeWithData, resumeWithError);
                            return;
                        } else if (type === SUSP_YIELD) {
                            // Assumes all yields are optional, as Sk.setTimeout might
                            // not be able to yield.
                            //Sk.setTimeout(resume, 0);
                            Sk.global["setImmediate"](resume);
                            return;
                        } else if (type === SUSP_DELAY) {
                            //Sk.setTimeout(resume, 1);
                            Sk.global["setImmediate"](resume);
                            return;
                        } else if (r.optional) {
                            // Unhandled optional suspensions just get
                            // resumed immediately, and we go around the loop again.
                            r = r.resume();
                        } else {
                            // Unhandled, non-optional suspension.
                            throw new Sk.builtin.SuspensionError("Unhandled non-optional suspension of type '" + r.data["type"] + "'");
                        }
                    }

                    resolve(r);
                } catch (e) {
                    reject(e);
                }
            })(r);
        } catch (e) {
            reject(e);
        }
    });
};
Sk.exportSymbol("Sk.misceval.asyncToPromise", Sk.misceval.asyncToPromise);

Sk.misceval.applyAsync = function (suspHandlers, func, kwdict, varargseq, kws, args) {
    return Sk.misceval.asyncToPromise(function () {
        return Sk.misceval.applyOrSuspend(func, kwdict, varargseq, kws, args);
    }, suspHandlers);
};
Sk.exportSymbol("Sk.misceval.applyAsync", Sk.misceval.applyAsync);

/**
 * Chain together a set of functions, each of which might return a value or
 * an Sk.misceval.Suspension. Each function is called with the return value of
 * the preceding function, but does not see any suspensions. If a function suspends,
 * Sk.misceval.chain() returns a suspension that will resume the chain once an actual
 * return value is available.
 *
 * The idea is to allow a Promise-like chaining of possibly-suspending steps without
 * repeating boilerplate suspend-and-resume code.
 *
 * For example, imagine we call Sk.misceval.chain(x, f).
 *  - If x is a value, we return f(x).
 *  - If x is a suspension, we suspend. We will suspend and resume until we get a
 *    return value, and then we will return f(<resumed-value).
 * This can be expanded to an arbitrary number of functions
 * (eg Sk.misceval.chain(x, f, g), which is equivalent to chain(chain(x, f), g).)
 * @template T
 * @param {T}              initialValue
 * @param {...function(T)} chainedFns
 */

Sk.misceval.chain = function (initialValue, chainedFns) {
    // We try to minimse overhead when nothing suspends (the common case)
    var i = 1,
        value = initialValue,
        j,
        fs;

    while (true) {
        if (i == arguments.length) {
            return value;
        }
        if (value && value.$isSuspension) {
            break;
        } // oops, slow case
        value = arguments[i](value);
        i++;
    }

    // Okay, we've suspended at least once, so we're taking the slow(er) path.

    // Copy our remaining arguments into an array (inline, because passing
    // "arguments" out of a function kills the V8 optimiser).
    // (discussion: https://github.com/skulpt/skulpt/pull/552)
    fs = new Array(arguments.length - i);

    for (j = 0; j < arguments.length - i; j++) {
        fs[j] = arguments[i + j];
    }

    j = 0;

    return (function nextStep(r) {
        while (j < fs.length) {
            if (r instanceof Sk.misceval.Suspension) {
                return new Sk.misceval.Suspension(nextStep, r);
            }

            r = fs[j](r);
            j++;
        }

        return r;
    })(value);
};
Sk.exportSymbol("Sk.misceval.chain", Sk.misceval.chain);

/**
 * Catch any exceptions thrown by a function, or by resuming any suspension it
 * returns.
 *
 *     var result = Sk.misceval.tryCatch(asyncFunc, function(err) {
 *       console.log(err);
 *     });
 *
 * Optional cleanUp runs once after tryFn or catchFn finishes, including all
 * suspensions. Cleanup may suspend; its exception replaces any pending result
 * or exception, as with a Python finally clause.
 */
Sk.misceval.tryCatch = function (tryFn, catchFn, cleanUp) {
    if (cleanUp !== undefined) {
        var failed = false;
        var error;
        var result = Sk.misceval.tryCatch(
            function () { return Sk.misceval.tryCatch(tryFn, catchFn); },
            function (e) { failed = true; error = e; }
        );
        return Sk.misceval.chain(result, function (value) {
            return Sk.misceval.chain(cleanUp(), function () {
                if (failed) {
                    throw error;
                }
                return value;
            });
        });
    }
    var r;

    try {
        r = tryFn();
    } catch (e) {
        return catchFn(e);
    }

    if (r instanceof Sk.misceval.Suspension) {
        var susp = new Sk.misceval.Suspension(undefined, r);
        susp.resume = function () {
            return Sk.misceval.tryCatch(r.resume, catchFn);
        };
        return susp;
    } else {
        return r;
    }
};
Sk.exportSymbol("Sk.misceval.tryCatch", Sk.misceval.tryCatch);

/**
 * @function
 * @description
 * Perform a suspension-aware for-each on an iterator, without
 * blowing up the stack.
 * forFn() is called for each element in the iterator, with two
 * arguments: the current element and the previous return value
 * of forFn() (or initialValue on the first call). In this way,
 * iterFor() can be used as a simple for loop, or alternatively
 * as a 'reduce' operation. The return value of the final call to
 * forFn() will be the return value of iterFor() (after all
 * suspensions are resumed, that is; if the iterator is empty then
 * initialValue will be returned.)
 *
 * The iteration can be terminated early, by returning
 * an instance of Sk.misceval.Break. If an argument is given to
 * the Sk.misceval.Break() constructor, that value will be
 * returned from iterFor(). It is therefore possible to use
 * iterFor() on infinite iterators.
 *
 * @param {*} iter
 * @param {function(pyObject,*=)} forFn
 * @param {*=} initialValue
 */
Sk.misceval.iterFor = function (iter, forFn, initialValue) {
    var prevValue = initialValue;

    var breakOrIterNext = function (r) {
        prevValue = r;
        return r instanceof Sk.misceval.Break ? r : iter.tp$iternext(true);
    };

    return (function nextStep(i) {
        while (i !== undefined) {
            if (i instanceof Sk.misceval.Suspension) {
                return new Sk.misceval.Suspension(nextStep, i);
            }

            if (i === Sk.misceval.Break || i instanceof Sk.misceval.Break) {
                return i.brValue;
            }

            i = Sk.misceval.chain(forFn(i, prevValue), breakOrIterNext);
        }
        return prevValue;
    })(iter.tp$iternext(true));
};
Sk.exportSymbol("Sk.misceval.iterFor", Sk.misceval.iterFor);


/**
 * @function
 * @description
 * 
 * As per iterFor but with an array rather than a python iterable
 * Useful for iterating over args where doing so could result in a suspension
 *
 * @param {Array} args
 * @param {function(pyObject,*=)} forFn
 * @param {*=} initialValue
 */
Sk.misceval.iterArray = function (args, forFn, initialValue) {
    Sk.asserts.assert(Array.isArray(args), "iterArgs requires an array");
    let i = 0;
    return Sk.misceval.iterFor({tp$iternext: () => args[i++]}, forFn, initialValue);
};

/**
 * @function
 *
 * @description
 * Convert a Python iterable into a javascript array
 *
 * @param {pyObject} iterable
 * @param {boolean=} canSuspend - Can this function suspend
 *
 * @returns {!Array}
 */
Sk.misceval.arrayFromIterable = function (iterable, canSuspend) {
    if (iterable === undefined) {
        return [];
    }
    if (iterable.ht$type === undefined && iterable.sk$asarray !== undefined) {
        // use sk$asarray only if we're a builtin
        return iterable.sk$asarray();
    }
    const L = [];
    const ret = Sk.misceval.chain(
        Sk.misceval.iterFor(Sk.abstr.iter(iterable), (i) => {
            L.push(i);
        }),
        () => L
    );
    return canSuspend ? ret : Sk.misceval.retryOptionalSuspensionOrThrow(ret);
};

/**
 * A special value to return from an iterFor() function,
 * to abort the iteration. Optionally supply a value for iterFor() to return
 * (defaults to 'undefined')
 *
 * @constructor
 * @param {*=}  brValue
 */
Sk.misceval.Break = function (brValue) {
    if (!(this instanceof Sk.misceval.Break)) {
        return new Sk.misceval.Break(brValue);
    }

    this.brValue = brValue;
};
Sk.exportSymbol("Sk.misceval.Break", Sk.misceval.Break);

/**
 * same as Sk.misceval.call except args is an actual array, rather than
 * varargs.
 * @deprecated
 * @ignore
 */
Sk.misceval.applyOrSuspend = function (func, kwdict, varargseq, kws, args) {
    var fcall;
    var it, i;

    if (func == null || func === Sk.builtin.none.none$) {
        throw new Sk.builtin.TypeError("'" + Sk.abstr.typeName(func) + "' object is not callable");
    }

    if (typeof func === "function" && func.tp$call === undefined) {
        func = new Sk.builtin.func(func);
    }

    fcall = func.tp$call;
    if (fcall !== undefined) {
        if (varargseq) {
            for (it = varargseq.tp$iter(), i = it.tp$iternext(); i !== undefined; i = it.tp$iternext()) {
                args.push(i);
            }
        }

        if (kwdict) {
            for (it = Sk.abstr.iter(kwdict), i = it.tp$iternext(); i !== undefined; i = it.tp$iternext()) {
                if (!Sk.builtin.checkString(i)) {
                    throw new Sk.builtin.TypeError("Function keywords must be strings");
                }
                kws.push(i.v);
                kws.push(Sk.abstr.objectGetItem(kwdict, i, false));
            }
        }
        return fcall.call(func, args, kws, kwdict);
    }

    // todo; can we push this into a tp$call somewhere so there's
    // not redundant checks everywhere for all of these __x__ ones?
    fcall = func.__call__;
    if (fcall !== undefined) {
        // func is actually the object here because we got __call__
        // from it. todo; should probably use descr_get here
        args.unshift(func);
        return Sk.misceval.apply(fcall, kwdict, varargseq, kws, args);
    }

    throw new Sk.builtin.TypeError("'" + Sk.abstr.typeName(func) + "' object is not callable");
};
Sk.exportSymbol("Sk.misceval.applyOrSuspend", Sk.misceval.applyOrSuspend);

/**
 * Do the boilerplate suspension stuff.
 */
Sk.misceval.promiseToSuspension = function (promise) {
    var suspension = new Sk.misceval.Suspension();

    suspension.resume = function () {
        if (suspension.data["error"]) {
            throw suspension.data["error"];
        }

        return suspension.data["result"];
    };

    suspension.data = {
        type: "Sk.promise",
        promise: promise,
    };

    return suspension;
};
Sk.exportSymbol("Sk.misceval.promiseToSuspension", Sk.misceval.promiseToSuspension);


function _isIE() {
    const navigator = Sk.global.navigator || {};
    const ua = navigator.userAgent || "";
    return ua.indexOf("MSIE ") > -1 || ua.indexOf("Trident/") > -1;
}
/** Return the scope that owns a declared closure cell, including empty cells. */
Sk.misceval.cellOwner = function (closure, name) {
    while (!Object.prototype.hasOwnProperty.call(closure, name)) {
        closure = Object.getPrototypeOf(closure);
    }
    return closure;
};
Sk.exportSymbol("Sk.misceval.cellOwner", Sk.misceval.cellOwner);

// Preserve the shared cell dictionaries rather than copying their contents.
// Functions and inlined comprehension scopes use the same closure linkage.
Sk.misceval.makeClosure = function (closure, closure2) {
    if (closure2 !== undefined && closure2 !== closure) {
        Object.setPrototypeOf(closure, closure2);
    }
    return closure;
};
Sk.exportSymbol("Sk.misceval.makeClosure", Sk.misceval.makeClosure);

// The compiler uses property access for module/class namespaces. Keep that
// interface backed by the actual Python mapping, so locals()/globals() and
// exec namespace mutations observe the same mapping in both directions.
const namespaceCache = new WeakMap();
Sk.misceval.namespaceToJs = function (namespace, globals) {
    let entry = namespaceCache.get(namespace);
    if (entry === undefined) {
        const dict = namespace.mp$subscript !== undefined ? namespace : new Sk.builtin.dict(
            Object.keys(namespace).filter(name => namespace[name] !== undefined).flatMap(name => [new Sk.builtin.str(Sk.unfixReserved(name)), namespace[name]])
        );
        entry = { dict };
        namespaceCache.set(namespace, entry);
    }
    const role = globals ? "globals" : "locals";
    if (entry[role] === undefined) {
        const dict = entry.dict;
        const read = name => {
            const key = new Sk.builtin.str(Sk.unfixReserved(name));
            if (globals) {
                return Sk.builtin.dict.prototype.mp$lookup.call(dict, key);
            }
            try {
                return Sk.misceval.retryOptionalSuspensionOrThrow(Sk.abstr.objectGetItem(dict, key));
            } catch (err) {
                if (err instanceof Sk.builtin.KeyError) {
                    return undefined;
                }
                throw err;
            }
        };
        entry[role] = new Proxy({}, {
            get(target, name) {
                // Generated Python identifiers are reserved-name mangled; these
                // unmangled properties belong to the JS execution machinery.
                if (typeof name !== "string" || name === "constructor" || name[0] === "$") {
                    return Reflect.get(target, name);
                }
                const value = read(name);
                return value === undefined ? Reflect.get(target, name) : value;
            },
            set(target, name, value) {
                const key = new Sk.builtin.str(Sk.unfixReserved(name));
                if (globals) {
                    Sk.builtin.dict.prototype.mp$ass_subscript.call(dict, key, value);
                } else {
                    Sk.abstr.objectSetItem(dict, key, value);
                }
                return true;
            },
            deleteProperty(target, name) {
                const key = new Sk.builtin.str(Sk.unfixReserved(name));
                try {
                    if (globals) {
                        Sk.builtin.dict.prototype.mp$ass_subscript.call(dict, key, undefined);
                    } else {
                        Sk.abstr.objectSetItem(dict, key, undefined);
                    }
                } catch (err) {
                    // CPython DELETE_NAME replaces any mapping deletion
                    // failure with NameError; DELETE_GLOBAL only handles KeyError.
                    if (!globals || err instanceof Sk.builtin.KeyError) {
                        throw new Sk.builtin.NameError("name '" + key.$jsstr() + "' is not defined");
                    }
                    throw err;
                }
                return true;
            },
            ownKeys() {
                const keys = globals ? dict.sk$asarray() : Sk.misceval.arrayFromIterable(
                    Sk.misceval.callsimArray(Sk.abstr.gattr(dict, Sk.builtin.str.$keys))
                );
                return keys.filter(Sk.builtin.checkString).map(key => key.$mangled);
            },
            getOwnPropertyDescriptor(target, name) {
                const value = read(name);
                return value === undefined ? undefined : { value, writable: true, enumerable: true, configurable: true };
            },
        });
        namespaceCache.set(entry[role], entry);
    }
    return entry[role];
};
Sk.exportSymbol("Sk.misceval.namespaceToJs", Sk.misceval.namespaceToJs);

Sk.misceval.namespaceDict = function (namespace) {
    Sk.misceval.namespaceToJs(namespace);
    return namespaceCache.get(namespace).dict;
};
Sk.exportSymbol("Sk.misceval.namespaceDict", Sk.misceval.namespaceDict);

Sk.misceval.localsSnapshot = function (items) {
    return new Sk.builtin.dict(items.filter(item => item[1] !== undefined).flatMap(item => [new Sk.builtin.str(item[0]), item[1]]));
};
Sk.exportSymbol("Sk.misceval.localsSnapshot", Sk.misceval.localsSnapshot);

/**
 * @function
 * @description
 * Constructs a class object given a code object representing the body
 * of the class, the name of the class, and the list of bases.
 *
 * There are no "old-style" classes in Skulpt, so use the user-specified
 * metaclass (todo;) if there is one, the type of the 0th base class if
 * there's bases, or otherwise the 'type' type.
 *
 * The func code object is passed a (js) dict for its locals which it
 * stores everything into.
 *
 * The metaclass is then called as metaclass(name, bases, locals) and
 * should return a newly constructed class object.
 *
 */
Sk.misceval.buildClass = function (globals, func, name, bases, cell, kws, closure2) {
    const _name = new Sk.builtin.str(name);
    const _bases = update_bases(bases); // todo this function should go through the bases and check for __mro_entries__

    kws = kws || [];
    bases = bases || [];
    let meta;
    let is_class = true;
    const meta_idx = kws.indexOf("metaclass");
    if (meta_idx > -1) {
        meta = kws[meta_idx + 1];
        // https://twitter.com/Rich_Harris/status/1125850391155965952
        // the order of key value pairs doesn't matter for kws
        // and this is orders of magnitured faster than splice
        kws[meta_idx] = kws[kws.length - 2];
        kws[meta_idx + 1] = kws[kws.length - 1];
        kws.pop();
        kws.pop();
        is_class = Sk.builtin.checkClass(meta);
    } else {
        if (!bases.length) {
            /* if there are no bases, use type: */
            meta = Sk.builtin.type;
        } else {
            /* else get the type of the first base */
            meta = bases[0].ob$type;
        }
    }

    if (is_class) {
        meta = calculate_meta(meta, bases); // we should do this in type as well
    }
    /* else: meta is not a class, so we cannot do the metaclass
       calculation, so we will use the explicitly given object as it is */

    let ns = null; // namespace
    if (meta !== Sk.builtin.type) {
        // slow path we have a metaclass use the __prepare__ mechanism
        ns = do_prepare(meta, _name, _bases, kws, is_class);
    }

    if (ns === null) {
        ns = new Sk.builtin.dict([]);
    }
    const locals = Sk.misceval.namespaceToJs(ns);

    const l_cell = cell === undefined ? {} : cell;

    // Look up enclosing free variables without overwriting local cells or
    // copying their current values. Nested classes can share both dictionaries.
    if (closure2 !== undefined && closure2 !== l_cell) {
        Object.setPrototypeOf(l_cell, closure2);
    }

    // pass the locals to the code object which populates the namespace of the class
    let bodyResult;
    if (func instanceof Sk.builtin.func) {
        func.$classLocals = locals;
        try {
            bodyResult = Sk.misceval.callsimArray(func);
        } finally {
            delete func.$classLocals;
        }
    } else {
        // Native stdlib modules supply a JS body without compiler-emitted
        // __module__ initialization; preserve their existing buildClass API.
        if (globals.__name__ !== undefined) {locals.__module__ = globals.__name__;}
        bodyResult = func(globals, locals, l_cell);
        if (bodyResult === undefined) {bodyResult = locals.__classcell__;}
    }
    const classcell = bodyResult instanceof Sk.builtin.cell ? bodyResult : undefined;

    const klass = Sk.misceval.callsimOrSuspendArray(meta, [_name, _bases, ns], kws);

    // type.__new__ must populate the cell, including when called by a metaclass.
    return Sk.misceval.chain(klass, (resolvedKlass) => {
        if (classcell !== undefined && Sk.builtin.checkClass(resolvedKlass)) {
            const value = classcell.$closure.__class__;
            if (value === undefined) {
                throw new Sk.builtin.RuntimeError("__class__ not set defining '" + name + "'. Was __classcell__ propagated to type.__new__?");
            }
            if (value !== resolvedKlass) {
                throw new Sk.builtin.TypeError("__class__ set to a different class defining '" + name + "'");
            }
        }
        return resolvedKlass;
    });
};
Sk.exportSymbol("Sk.misceval.buildClass", Sk.misceval.buildClass);

function update_bases(bases) {
    /** @todo this function should go through the bases and check for __mro_entries__ */
    return new Sk.builtin.tuple(bases);
}

function calculate_meta(meta, bases) {
    let winner = meta;
    bases.forEach((base) => {
        let tmptype = base.ob$type;
        if (winner.$isSubType(tmptype)) {
            // continue
        } else if (tmptype.$isSubType(winner)) {
            winner = tmptype;
        } else {
            throw new Sk.builtin.TypeError("metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases");
        }
    });
    return winner;
}

function do_prepare(meta, _name, _bases, kws, is_class) {
    // we have a metaclass
    const prep = meta.tp$getattr(Sk.builtin.str.$prepare);
    let ns = null;
    if (prep === undefined) {
        // unusual case - the metaclass is not a typeobject
        return ns;
    }
    ns = Sk.misceval.callsimArray(prep, [_name, _bases], kws);
    if (!Sk.builtin.checkMapping(ns)) {
        throw new Sk.builtin.TypeError(is_class ? meta.prototype.tp$name : "<metaclass>" + ".__prepare__() must return a mapping not '" + Sk.abstr.typeName(ns) + "'");
    }
    return ns;
}

// Python/codegen.c: interactive expressions call sys.displayhook (PRINT_EXPR).
Sk.misceval.displayhook = function (value) {
    return Sk.misceval.chain(Sk.importModule("sys", false, true), sys => {
        const hook = sys.tp$getattr(new Sk.builtin.str("displayhook"));
        if (hook === undefined) {
            throw new Sk.builtin.RuntimeError("lost sys.displayhook");
        }
        return Sk.misceval.callsimOrSuspendArray(hook, [value]);
    });
};
Sk.exportSymbol("Sk.misceval.displayhook", Sk.misceval.displayhook);
