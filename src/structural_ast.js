/* Temporary bridge from skulpt-parser's structural AST to the existing compiler. */

Sk.sourceParser = null;
Sk["sourceTokenizer"] = null;

Sk.parseCompilerModule = function (source, filename) {
    if (Sk.sourceParser === null) {
        const parsed = Sk.parse(filename, source);
        return { ast: Sk.astFromParse(parsed.cst, filename, parsed.flags), flags: parsed.flags };
    }
    let tree;
    try {
        tree = Sk.sourceParser(source, {
            filename,
            python2Compat: !Sk.__future__.python3,
            legacyAsyncNames: true,
            printFunction: Sk.__future__.print_function
        });
    } catch (error) {
        // Missing optional capabilities and implementation failures are not Python syntax errors.
        if (!["SyntaxError", "IndentationError", "TabError"].includes(error.name)) {
            throw error;
        }
        const converted = new Sk.builtin[error.name](error.message, filename, error.lineno);
        converted.$msg = new Sk.builtin.str(error.message);
        converted.$filename = new Sk.builtin.str(filename);
        converted.$lineno = new Sk.builtin.int_(error.lineno);
        converted.$offset = new Sk.builtin.int_(error.offset);
        converted.$text = error.text == null ? Sk.builtin.none.none$ : new Sk.builtin.str(error.text);
        throw converted;
    }
    const N = Sk.astnodes;
    const str = (value) => value === null ? null : new Sk.builtin.str(value);
    function unsupported(node, feature) {
        throw new Sk.builtin.SyntaxError(feature + " is not supported by the Skulpt compiler", filename, node.lineno);
    }
    function make(kind, node, ...fields) {
        return new N[kind](...fields, node.lineno, node.col_offset);
    }
    function slice(node) {
        if (node._type === "Slice") {
            return convert(node);
        }
        if (node._type === "Tuple" && node.elts.some((item) => item._type === "Slice")) {
            return new N.ExtSlice(node.elts.map(slice));
        }
        return new N.Index(convert(node));
    }
    function keywords(items) {
        // The old AST builder enforced this; ast.parse defers it to compilation.
        const seen = new Set();
        for (const item of items) {
            if (item.arg !== null) {
                if (seen.has(item.arg)) {
                    throw new Sk.builtin.SyntaxError("keyword argument repeated: " + item.arg, filename, item.lineno);
                }
                seen.add(item.arg);
            }
        }
        return convert(items);
    }
    function constant(node) {
        const value = node.value;
        switch (value.type) {
            case "int": {
                const raw = typeof value.value === "bigint" ? value.value.toString() : value.value;
                const number = value.legacyLong ? new Sk.builtin.lng(raw) : new Sk.builtin.int_(raw);
                return make("Num", node, number);
            }
            case "float": return make("Num", node, new Sk.builtin.float_(value.value));
            case "complex": return make("Num", node, new Sk.builtin.complex(value.real, value.imag));
            case "str": return make("Str", node, str(value.value));
            case "bytes": {
                let bytes = "";
                for (const byte of value.value) {
                    bytes += String.fromCharCode(byte);
                }
                return make("Bytes", node, str(bytes));
            }
            case "bool": return make("NameConstant", node, value.value ? Sk.builtin.bool.true$ : Sk.builtin.bool.false$);
            case "none": return make("NameConstant", node, Sk.builtin.none.none$);
            case "ellipsis": return make("Ellipsis", node);
            default: return unsupported(node, "Constant " + value.type);
        }
    }
    function convert(node) {
        if (node === null) {
            return null;
        }
        if (Array.isArray(node)) {
            return node.map(convert);
        }
        const kind = node._type;
        const c = convert;
        const m = (...fields) => make(kind, node, ...fields);
        switch (kind) {
            case "Module": return new N.Module(c(node.body), null);
            case "FunctionDef":
                if (node.type_params.length) {
                    return unsupported(node, "Type parameters");
                }
                return m(str(node.name), c(node.args), c(node.body), c(node.decorator_list), c(node.returns), null);
            case "ClassDef":
                if (node.type_params.length) {
                    return unsupported(node, "Type parameters");
                }
                return m(str(node.name), c(node.bases), keywords(node.keywords), c(node.body), c(node.decorator_list), null);
            case "Return": case "Yield": case "YieldFrom": return m(c(node.value));
            case "Delete": return m(c(node.targets));
            case "Assign": return m(c(node.targets), c(node.value));
            case "AugAssign": return m(c(node.target), c(node.op), c(node.value));
            case "AnnAssign": return m(c(node.target), c(node.annotation), c(node.value), node.simple);
            case "For": return m(c(node.target), c(node.iter), c(node.body), c(node.orelse));
            case "While": case "If": return m(c(node.test), c(node.body), c(node.orelse));
            case "With": return m(c(node.items), c(node.body));
            case "Raise": return m(c(node.exc), c(node.cause), null, null);
            case "LegacyRaise": return make("Raise", node, c(node.exc), null, c(node.inst), c(node.tback));
            case "Try": return m(c(node.body), c(node.handlers), c(node.orelse), node.finalbody.length ? c(node.finalbody) : null);
            case "Assert": return m(c(node.test), c(node.msg));
            case "Import": return m(c(node.names));
            case "ImportFrom": return m(str(node.module === null ? "" : node.module), c(node.names), node.level);
            case "Global": case "Nonlocal": return m(node.names.map(str));
            case "Expr":
                // Skulpt's standalone debugger statement has no CPython AST node.
                if (node.value._type === "Name" && node.value.id === "debugger") {
                    return make("Debugger", node);
                }
                return m(c(node.value));
            case "Pass": case "Break": case "Continue": return m();
            case "Print": return m(c(node.dest), c(node.values), node.nl);
            case "BoolOp": return m(c(node.op), c(node.values));
            case "BinOp": return m(c(node.left), c(node.op), c(node.right));
            case "UnaryOp": return m(c(node.op), c(node.operand));
            case "Lambda": return m(c(node.args), c(node.body));
            case "IfExp": return m(c(node.test), c(node.body), c(node.orelse));
            case "Dict": return m(c(node.keys), c(node.values));
            case "Set": return m(c(node.elts));
            case "ListComp": case "SetComp": case "GeneratorExp": return m(c(node.elt), c(node.generators));
            case "DictComp": return m(c(node.key), c(node.value), c(node.generators));
            case "Compare": return m(c(node.left), c(node.ops), c(node.comparators));
            case "Call": return m(c(node.func), c(node.args), keywords(node.keywords));
            case "Constant": return constant(node);
            case "FormattedValue": return m(c(node.value), node.conversion === -1 ? null : String.fromCharCode(node.conversion), c(node.format_spec));
            case "JoinedStr": return m(c(node.values));
            case "Attribute": return m(c(node.value), str(node.attr), c(node.ctx));
            case "Subscript": return m(c(node.value), slice(node.slice), c(node.ctx));
            case "Starred": return m(c(node.value), c(node.ctx));
            case "Name": return m(str(node.id), c(node.ctx));
            case "List": case "Tuple": return m(c(node.elts), c(node.ctx));
            case "Slice": return new N.Slice(c(node.lower), c(node.upper), c(node.step));
            case "comprehension":
                if (node.is_async) {
                    return unsupported(node.target, "Async comprehensions");
                }
                return new N.comprehension(c(node.target), c(node.iter), c(node.ifs), 0);
            case "ExceptHandler": {
                const target = node.name === null ? null : make("Name", node, str(node.name), N.Store);
                return m(c(node.type), target, c(node.body));
            }
            case "LegacyExceptHandler": return make("ExceptHandler", node, c(node.type), c(node.target), c(node.body));
            case "arguments":
                if (node.posonlyargs.length) {
                    return unsupported(node.posonlyargs[0], "Positional-only parameters");
                }
                return new N.arguments_(c(node.args), c(node.vararg), c(node.kwonlyargs), c(node.kw_defaults), c(node.kwarg), c(node.defaults));
            case "arg": return m(str(node.arg), c(node.annotation));
            case "keyword": return new N.keyword(str(node.arg), c(node.value));
            case "alias": return new N.alias(str(node.name), str(node.asname));
            case "withitem": return new N.withitem(c(node.context_expr), c(node.optional_vars));
            case "Load": case "Store": case "Del":
            case "And": case "Or":
            case "Add": case "Sub": case "Mult": case "MatMult": case "Div": case "Mod": case "Pow":
            case "LShift": case "RShift": case "BitOr": case "BitXor": case "BitAnd": case "FloorDiv":
            case "Invert": case "Not": case "UAdd": case "USub":
            case "Eq": case "NotEq": case "Lt": case "LtE": case "Gt": case "GtE":
            case "Is": case "IsNot": case "In": case "NotIn": return N[kind];
            default: return unsupported(node, kind);
        }
    }
    return { ast: convert(tree), flags: 0 };
};
