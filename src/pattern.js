// Runtime operations for PEP 634 patterns, corresponding to MATCH_SEQUENCE,
// MATCH_MAPPING, _PyEval_MatchKeys and _PyEval_MatchClass in CPython 3.14.
// Helpers return extracted JavaScript arrays, or null for a failed match.
// Python protocol calls use host suspensions, just like ordinary compiled calls.

// Type flags distinguish registered sequences/mappings from objects which only
// happen to implement __getitem__. The first flagged MRO base wins inheritance.
Sk.abstr.patternKind = function (type) {
    for (const base of type.prototype.tp$mro) {
        if (base.sk$patternKind) {return base.sk$patternKind;}
    }
    return 0;
};
Sk.abstr.setPatternKind = function (type, kind) {
    // _PyType_SetFlagsRecursive skips immutable builtin types.
    if (!type.sk$klass || type.sk$patternKind === kind) {return;}
    type.sk$patternKind = kind;
    for (const child of Sk.abstr.typeSubclasses(type)) {
        Sk.abstr.setPatternKind(child, kind);
    }
};
for (const type of [Sk.builtin.list, Sk.builtin.tuple, Sk.builtin.range_]) {type.sk$patternKind = 32;}
for (const type of [Sk.builtin.dict, Sk.builtin.mappingproxy]) {type.sk$patternKind = 64;}
for (const type of [Sk.builtin.bool, Sk.builtin.bytes, Sk.builtin.dict, Sk.builtin.float_, Sk.builtin.frozenset,
                   Sk.builtin.int_, Sk.builtin.list, Sk.builtin.set, Sk.builtin.str, Sk.builtin.tuple]) {
    type.sk$matchSelf = true;
}

// Pattern literals are restricted to constants, negated numbers and complex
// literals. This also gives the symbol table Python equality/hash semantics when
// checking duplicate mapping keys before any dead-code optimisation.
Sk.abstr.patternLiteral = function (node) {
    if (node._type === "Constant") {
        const value = node.value;
        if (value.$pyValue !== undefined) {return value.$pyValue;}
        switch (value.type) {
            case "int": return new Sk.builtin.int_(String(value.value));
            case "float": return new Sk.builtin.float_(value.value);
            case "complex": return new Sk.builtin.complex(value.real, value.imag);
            case "str": return new Sk.builtin.str(value.value);
            case "bytes": return new Sk.builtin.bytes(Array.from(value.value));
            case "bool": return new Sk.builtin.bool(value.value);
            case "none": return Sk.builtin.none.none$;
        }
    } else if (node._type === "UnaryOp" && node.op._type === "USub") {
        const value = Sk.abstr.patternLiteral(node.operand);
        if (node.operand._type === "Constant" && ["int", "float", "complex"].includes(node.operand.value.type)) {
            return Sk.abstr.numberUnaryOp(value, "USub");
        }
    } else if (node._type === "BinOp" && ["Add", "Sub"].includes(node.op._type)) {
        const left = Sk.abstr.patternLiteral(node.left), right = Sk.abstr.patternLiteral(node.right);
        if ((left instanceof Sk.builtin.int_ || left instanceof Sk.builtin.float_) && right instanceof Sk.builtin.complex &&
            node.right._type === "Constant") {
            return Sk.abstr.numberBinOp(left, right, node.op._type);
        }
    }
};

Sk.abstr.matchKeys = function (subject, keys) {
    if (!keys.length) {return [];}
    const seen = new Sk.builtin.dict([]), missing = new Sk.builtin.object(), values = [];
    return Sk.misceval.chain(Sk.abstr.gattr(subject, new Sk.builtin.str("get"), true), get =>
        Sk.misceval.chain(Sk.misceval.iterArray(keys, key => {
            if (seen.mp$lookup(key) !== undefined) {
                throw new Sk.builtin.ValueError("mapping pattern checks duplicate key (" + Sk.misceval.objectRepr(key) + ")");
            }
            seen.mp$ass_subscript(key, Sk.builtin.none.none$);
            return Sk.misceval.chain(Sk.misceval.callsimOrSuspendArray(get, [key, missing]), value => {
                if (value === missing) {return new Sk.misceval.Break(null);}
                values.push(value);
            });
        }), result => result === null ? null : values));
};

Sk.abstr.matchMappingRest = function (subject, keys) {
    const rest = new Sk.builtin.dict([]);
    return Sk.misceval.chain(rest.dict$merge(subject), () => {
        for (const key of keys) {rest.mp$ass_subscript(key, undefined);}
        return rest;
    });
};

Sk.abstr.matchClass = function (subject, type, nargs, keywords) {
    if (!Sk.builtin.checkClass(type)) {throw new Sk.builtin.TypeError("called match pattern must be a class");}
    const name = Sk.abstr.typeName(type.prototype), seen = new Set(), values = [];
    const optionalAttr = (object, attribute) => Sk.misceval.tryCatch(
        () => Sk.abstr.gattr(object, attribute, true), error => {
            if (!(error instanceof Sk.builtin.AttributeError)) {throw error;}
        });
    function attribute(attr) {
        if (attr.ob$type !== Sk.builtin.str) {
            throw new Sk.builtin.TypeError("__match_args__ elements must be strings (got " + Sk.abstr.typeName(attr) + ")");
        }
        if (seen.has(attr.v)) {
            throw new Sk.builtin.TypeError(name + "() got multiple sub-patterns for attribute " + Sk.misceval.objectRepr(attr));
        }
        seen.add(attr.v);
        return Sk.misceval.chain(optionalAttr(subject, attr), value => {
            if (value === undefined) {return new Sk.misceval.Break(null);}
            values.push(value);
        });
    }
    // Like PyObject_IsInstance: exact types bypass a metaclass override, while
    // custom __instancecheck__ may call an Anvil host function and suspend.
    const check = Sk.abstr.lookupSpecial(type, new Sk.builtin.str("__instancecheck__"));
    const instance = subject.ob$type === type ? Sk.builtin.bool.true$ : check !== undefined
        ? Sk.misceval.callsimOrSuspendArray(check, [subject]) : Sk.builtin.isinstance(subject, type);
    return Sk.misceval.chain(instance, result => {
        if (!Sk.misceval.isTrue(result)) {return null;}
        // A keyword-only class pattern does not consult __match_args__.
        const matchArgs = nargs ? optionalAttr(type, new Sk.builtin.str("__match_args__")) : undefined;
        return Sk.misceval.chain(matchArgs, args => {
            const matchSelf = nargs && args === undefined && type.prototype.tp$mro.some(base => base.sk$matchSelf);
            if (args !== undefined && args.ob$type !== Sk.builtin.tuple) {
                throw new Sk.builtin.TypeError(name + ".__match_args__ must be a tuple (got " + Sk.abstr.typeName(args) + ")");
            }
            const allowed = matchSelf ? 1 : args === undefined ? 0 : args.v.length;
            if (nargs > allowed) {
                throw new Sk.builtin.TypeError(name + "() accepts " + allowed + " positional sub-pattern" + (allowed === 1 ? "" : "s") + " (" + nargs + " given)");
            }
            if (matchSelf) {values.push(subject);}
            const positional = matchSelf || !nargs ? [] : args.v.slice(0, nargs);
            const attributes = positional.concat(keywords.map(attr => new Sk.builtin.str(attr)));
            // Validate names as we fetch each attribute: an earlier missing
            // attribute must fail before a later malformed __match_args__ entry.
            return Sk.misceval.chain(Sk.misceval.iterArray(attributes, attribute),
                                     result => result === null ? null : values);
        });
    });
};
