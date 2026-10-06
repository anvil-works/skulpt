// SPDX-License-Identifier: Python-2.0 AND MIT
// Annotation expression unparser, ported from CPython 3.14 Python/ast_unparse.c
// at 18ef0f0cb52. This is the compiler's limited unparser, not ast.unparse.

const PR_TUPLE = 0, PR_TEST = 1, PR_OR = 2, PR_AND = 3, PR_NOT = 4,
    PR_CMP = 5, PR_EXPR = 6, PR_BXOR = 7, PR_BAND = 8, PR_SHIFT = 9,
    PR_ARITH = 10, PR_TERM = 11, PR_FACTOR = 12, PR_POWER = 13,
    PR_AWAIT = 14, PR_ATOM = 15;

const binaryOps = {
    Add: [" + ", PR_ARITH], Sub: [" - ", PR_ARITH], Mult: [" * ", PR_TERM],
    MatMult: [" @ ", PR_TERM], Div: [" / ", PR_TERM], Mod: [" % ", PR_TERM],
    FloorDiv: [" // ", PR_TERM], LShift: [" << ", PR_SHIFT], RShift: [" >> ", PR_SHIFT],
    BitOr: [" | ", PR_EXPR], BitXor: [" ^ ", PR_BXOR], BitAnd: [" & ", PR_BAND],
    Pow: [" ** ", PR_POWER],
};
const comparisonOps = { Eq: " == ", NotEq: " != ", Lt: " < ", LtE: " <= ",
    Gt: " > ", GtE: " >= ", Is: " is ", IsNot: " is not ", In: " in ", NotIn: " not in " };

function parenthesize(text, level, priority) {
    return level > priority ? "(" + text + ")" : text;
}

function appendAstArgs(args) {
    const parts = [];
    const positional = args.posonlyargs.concat(args.args);
    for (let i = 0; i < positional.length; i++) {
        let text = positional[i].arg;
        const di = i - positional.length + args.defaults.length;
        if (di >= 0) {text += "=" + appendAstExpr(args.defaults[di], PR_TEST);}
        parts.push(text);
        if (args.posonlyargs.length && i + 1 === args.posonlyargs.length) {parts.push("/");}
    }
    if (args.vararg || args.kwonlyargs.length) {parts.push("*" + (args.vararg ? args.vararg.arg : ""));}
    for (let i = 0; i < args.kwonlyargs.length; i++) {
        let text = args.kwonlyargs[i].arg;
        if (args.kw_defaults[i]) {text += "=" + appendAstExpr(args.kw_defaults[i], PR_TEST);}
        parts.push(text);
    }
    if (args.kwarg) {parts.push("**" + args.kwarg.arg);}
    return parts.join(", ");
}

function appendAstComprehensions(generators) {
    return generators.map(gen => (gen.is_async ? " async for " : " for ") +
        appendAstExpr(gen.target, PR_TUPLE) + " in " + appendAstExpr(gen.iter, PR_TEST + 1) +
        gen.ifs.map(test => " if " + appendAstExpr(test, PR_TEST + 1)).join("")).join("");
}

function appendAstConstant(e) {
    const value = e.value;
    let object;
    switch (value.type) {
        case "int": return String(value.value);
        case "float": object = new Sk.builtin.float_(value.value); break;
        case "complex": object = new Sk.builtin.complex(value.real, value.imag); break;
        case "str": return (e.kind || "") + Sk.misceval.objectRepr(new Sk.builtin.str(value.value));
        case "bytes": return Sk.misceval.objectRepr(new Sk.builtin.bytes(Array.from(value.value)));
        case "bool": return value.value ? "True" : "False";
        case "none": return "None";
        case "ellipsis": return "...";
        default: throw new Sk.builtin.SystemError("unknown annotation constant kind");
    }
    // Infinite numeric constants must reparse as infinity rather than a name.
    return Sk.misceval.objectRepr(object).replace(/inf/g, "1e309");
}

function appendInterpolation(e) {
    const text = e._type === "Interpolation" ? e.str.value : appendAstExpr(e.value, PR_TEST + 1);
    let result = (text.startsWith("{") ? "{ " : "{") + text;
    if (e.conversion >= 0) {result += "!" + String.fromCharCode(e.conversion);}
    if (e.format_spec) {result += ":" + buildFtStringBody(e.format_spec.values);}
    return result + "}";
}

function buildFtStringBody(values) {
    return values.map(e => e._type === "Constant" ? e.value.value.replace(/[{}]/g, brace => brace + brace)
        : e._type === "JoinedStr" ? appendJoinedStr(e) : appendInterpolation(e)).join("");
}

function appendJoinedStr(e) {
    return (e._type === "TemplateStr" ? "t" : "f") + Sk.misceval.objectRepr(new Sk.builtin.str(buildFtStringBody(e.values)));
}

function appendAstExpr(e, level) {
    switch (e._type) {
        case "BoolOp": {
            const and = e.op._type === "And";
            const priority = and ? PR_AND : PR_OR;
            return parenthesize(e.values.map(value => appendAstExpr(value, priority + 1)).join(and ? " and " : " or "), level, priority);
        }
        case "BinOp": {
            const [op, priority] = binaryOps[e.op._type];
            const rightAssociative = e.op._type === "Pow";
            return parenthesize(appendAstExpr(e.left, priority + Number(rightAssociative)) + op +
                appendAstExpr(e.right, priority + Number(!rightAssociative)), level, priority);
        }
        case "UnaryOp": {
            const priority = e.op._type === "Not" ? PR_NOT : PR_FACTOR;
            const op = { Invert: "~", Not: "not ", UAdd: "+", USub: "-" }[e.op._type];
            return parenthesize(op + appendAstExpr(e.operand, priority), level, priority);
        }
        case "Lambda":
            return parenthesize((e.args.args.length + e.args.posonlyargs.length ? "lambda " : "lambda") +
                appendAstArgs(e.args) + ": " + appendAstExpr(e.body, PR_TEST), level, PR_TEST);
        case "IfExp":
            return parenthesize(appendAstExpr(e.body, PR_TEST + 1) + " if " + appendAstExpr(e.test, PR_TEST + 1) +
                " else " + appendAstExpr(e.orelse, PR_TEST), level, PR_TEST);
        case "Dict":
            return "{" + e.values.map((value, i) => e.keys[i] ? appendAstExpr(e.keys[i], PR_TEST) + ": " + appendAstExpr(value, PR_TEST)
                : "**" + appendAstExpr(value, PR_EXPR)).join(", ") + "}";
        case "List": return "[" + e.elts.map(value => appendAstExpr(value, PR_TEST)).join(", ") + "]";
        case "Set": return "{" + e.elts.map(value => appendAstExpr(value, PR_TEST)).join(", ") + "}";
        case "Tuple":
            return !e.elts.length ? "()" : parenthesize(e.elts.map(value => appendAstExpr(value, PR_TEST)).join(", ") +
                (e.elts.length === 1 ? "," : ""), level, PR_TUPLE);
        case "GeneratorExp": case "ListComp": case "SetComp": case "DictComp": {
            const [open, close] = e._type === "GeneratorExp" ? ["(", ")"] : e._type === "ListComp" ? ["[", "]"] : ["{", "}"];
            const element = e._type === "DictComp" ? appendAstExpr(e.key, PR_TEST) + ": " + appendAstExpr(e.value, PR_TEST)
                : appendAstExpr(e.elt, PR_TEST);
            return open + element + appendAstComprehensions(e.generators) + close;
        }
        case "Compare":
            return parenthesize(appendAstExpr(e.left, PR_CMP + 1) + e.comparators.map((value, i) =>
                comparisonOps[e.ops[i]._type] + appendAstExpr(value, PR_CMP + 1)).join(""), level, PR_CMP);
        case "Call": {
            const func = appendAstExpr(e.func, PR_ATOM);
            if (e.args.length === 1 && !e.keywords.length && e.args[0]._type === "GeneratorExp") {
                return func + appendAstExpr(e.args[0], PR_TEST);
            }
            const args = e.args.map(value => appendAstExpr(value, PR_TEST));
            args.push(...e.keywords.map(kw => (kw.arg === null ? "**" : kw.arg + "=") + appendAstExpr(kw.value, PR_TEST)));
            return func + "(" + args.join(", ") + ")";
        }
        case "Constant": return appendAstConstant(e);
        case "JoinedStr": case "TemplateStr": return appendJoinedStr(e);
        case "FormattedValue": case "Interpolation": return appendInterpolation(e);
        case "Name": return e.id;
        case "Attribute":
            return appendAstExpr(e.value, PR_ATOM) + (e.value._type === "Constant" && e.value.value.type === "int" ? " ." : ".") + e.attr;
        case "Subscript": return appendAstExpr(e.value, PR_ATOM) + "[" + appendAstExpr(e.slice, PR_TUPLE) + "]";
        case "Starred": return "*" + appendAstExpr(e.value, PR_EXPR);
        case "Slice": return (e.lower ? appendAstExpr(e.lower, PR_TEST) : "") + ":" +
            (e.upper ? appendAstExpr(e.upper, PR_TEST) : "") + (e.step ? ":" + appendAstExpr(e.step, PR_TEST) : "");
        case "Yield": return e.value ? "(yield " + appendAstExpr(e.value, PR_TEST) + ")" : "(yield)";
        case "YieldFrom": return "(yield from " + appendAstExpr(e.value, PR_TEST) + ")";
        case "Await": return parenthesize("await " + appendAstExpr(e.value, PR_ATOM), level, PR_AWAIT);
        case "NamedExpr": return parenthesize(appendAstExpr(e.target, PR_ATOM) + " := " + appendAstExpr(e.value, PR_ATOM), level, PR_TUPLE);
        default: throw new Sk.builtin.SystemError("unknown annotation expression kind: " + e._type);
    }
}

module.exports.exprAsUnicode = e => appendAstExpr(e, PR_TEST);
