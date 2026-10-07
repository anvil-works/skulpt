/* Public AST bridge. Schema and helpers live in ast.py; parser literals retain
 * their Python values rather than passing through JSON number conversion. */
var $builtinmodule = function () {
    function constant(value) {
        switch (value.type) {
            case "int": return new Sk.builtin.int_(String(value.value));
            case "float": return new Sk.builtin.float_(value.value);
            case "complex": return new Sk.builtin.complex(value.real, value.imag);
            case "str": return new Sk.builtin.str(value.value);
            case "bytes": return new Sk.builtin.bytes(Array.from(value.value));
            case "bool": return new Sk.builtin.bool(value.value);
            case "none": return Sk.builtin.none.none$;
            case "ellipsis": return Sk.builtin.Ellipsis;
            case "tuple": return new Sk.builtin.tuple(value.value.map(constant));
            case "frozenset": return new Sk.builtin.frozenset(value.value.map(constant));
        }
    }
    function toPython(value) {
        if (value === null || value === undefined) {return Sk.builtin.none.none$;}
        if (Array.isArray(value)) {return new Sk.builtin.list(value.map(toPython));}
        if (typeof value === "object") {
            if (!value._type && typeof value.type === "string") {return constant(value);}
            const items = [];
            for (const [name, item] of Object.entries(value)) {
                items.push(new Sk.builtin.str(name), toPython(item));
            }
            return new Sk.builtin.dict(items);
        }
        return Sk.ffi.remapToPy(value);
    }
    return {
        _int_field: new Sk.builtin.func(function(value) {
            Sk.abstr.checkArgsLen("_int_field", arguments, 1, 1);
            if (!Sk.builtin.checkInt(value)) {
                throw new Sk.builtin.ValueError("invalid integer value: " + Sk.misceval.objectRepr(value));
            }
            const number = Number(Sk.builtin.asnum$(value));
            if (number < -2147483648 || number > 2147483647) {
                throw new Sk.builtin.OverflowError("Python int too large to convert to C int");
            }
            return new Sk.builtin.int_(number);
        }),
        _list_size: new Sk.builtin.func(function(value) {
            Sk.abstr.checkArgsLen("_list_size", arguments, 1, 1);
            return new Sk.builtin.int_(value.v.length);
        }),
        _list_item: new Sk.builtin.func(function(value, index) {
            Sk.abstr.checkArgsLen("_list_item", arguments, 2, 2);
            return value.v[index.v];
        }),
        _register_type: new Sk.builtin.func(function(type) {
            Sk.abstr.checkArgsLen("_register_type", arguments, 1, 1);
            Sk.builtin.astType = type;
            return Sk.builtin.none.none$;
        }),
        _compile_tree: new Sk.builtin.func(function(tree, filename, mode, flags, optimize) {
            Sk.abstr.checkArgsLen("_compile_tree", arguments, 5, 5);
            const hooks = {
                dictHook(dict) {
                    const result = {};
                    for (const [name, item] of dict.$items()) {
                        // Keep Constant payloads alive in the compiled closure, as
                        // CPython keeps them in co_consts, without re-creating them.
                        if (name.v === "py_value") {
                            result.$pyValue = item;
                        } else {
                            result[name.v] = Sk.ffi.remapToJs(item, hooks);
                        }
                    }
                    return result;
                },
            };
            const compiled = Sk.compile(Sk.ffi.remapToJs(tree, hooks), filename.v, mode.v, true, optimize.v, flags.v);
            return new Sk.builtin.code(filename, compiled);
        }),
        _parse_tree: new Sk.builtin.func(function(source, filename, mode) {
            Sk.abstr.checkArgsLen("_parse_tree", arguments, 3, 3);
            const text = source.$jsstr(), name = filename.$jsstr();
            const tree = mode.v === "eval" ? Sk.parseExpression(text, name)
                : mode.v === "single" ? Sk.parseInteractive(text, name)
                : mode.v === "func_type" ? Sk.parseFunctionType(text, name) : Sk.parseModule(text, name);
            return toPython(tree);
        }),
    };
};
