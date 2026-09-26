/* Implementation of the Python token module */

var $builtinmodule = function (name) {
    return modernTokenModule();
};

// Generated from CPython v3.14.3 Lib/token.py (PSF license).
function modernTokenModule() {
    const names = [
        "ENDMARKER", "NAME", "NUMBER", "STRING", "NEWLINE", "INDENT", "DEDENT",
        "LPAR", "RPAR", "LSQB", "RSQB", "COLON", "COMMA", "SEMI",
        "PLUS", "MINUS", "STAR", "SLASH", "VBAR", "AMPER", "LESS",
        "GREATER", "EQUAL", "DOT", "PERCENT", "LBRACE", "RBRACE", "EQEQUAL",
        "NOTEQUAL", "LESSEQUAL", "GREATEREQUAL", "TILDE", "CIRCUMFLEX", "LEFTSHIFT", "RIGHTSHIFT",
        "DOUBLESTAR", "PLUSEQUAL", "MINEQUAL", "STAREQUAL", "SLASHEQUAL", "PERCENTEQUAL", "AMPEREQUAL",
        "VBAREQUAL", "CIRCUMFLEXEQUAL", "LEFTSHIFTEQUAL", "RIGHTSHIFTEQUAL", "DOUBLESTAREQUAL", "DOUBLESLASH", "DOUBLESLASHEQUAL",
        "AT", "ATEQUAL", "RARROW", "ELLIPSIS", "COLONEQUAL", "EXCLAMATION", "OP",
        "TYPE_IGNORE", "TYPE_COMMENT", "SOFT_KEYWORD", "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", "TSTRING_START",
        "TSTRING_MIDDLE", "TSTRING_END", "COMMENT", "NL", "ERRORTOKEN", "ENCODING",
    ];
    const exact = {
        "!": 54,
        "!=": 28,
        "%": 24,
        "%=": 40,
        "&": 19,
        "&=": 41,
        "(": 7,
        ")": 8,
        "*": 16,
        "**": 35,
        "**=": 46,
        "*=": 38,
        "+": 14,
        "+=": 36,
        ",": 12,
        "-": 15,
        "-=": 37,
        "->": 51,
        ".": 23,
        "...": 52,
        "/": 17,
        "//": 47,
        "//=": 48,
        "/=": 39,
        ":": 11,
        ":=": 53,
        ";": 13,
        "<": 20,
        "<<": 33,
        "<<=": 44,
        "<=": 29,
        "=": 22,
        "==": 27,
        ">": 21,
        ">=": 30,
        ">>": 34,
        ">>=": 45,
        "@": 49,
        "@=": 50,
        "[": 9,
        "]": 10,
        "^": 32,
        "^=": 43,
        "{": 25,
        "|": 18,
        "|=": 42,
        "}": 26,
        "~": 31
    };
    const mod = {};
    const pairs = [];
    names.push("N_TOKENS");
    names.forEach((name, value) => {
        mod[name] = new Sk.builtin.int_(value);
        pairs.push(mod[name], new Sk.builtin.str(name));
    });
    mod.NT_OFFSET = new Sk.builtin.int_(256);
    pairs.push(mod.NT_OFFSET, new Sk.builtin.str("NT_OFFSET"));
    mod.tok_name = new Sk.builtin.dict(pairs);
    mod.EXACT_TOKEN_TYPES = Sk.ffi.remapToPy(exact);
    mod.ISTERMINAL = new Sk.builtin.func((value) => Sk.ffi.remapToPy(Sk.ffi.remapToJs(value) < 256));
    mod.ISNONTERMINAL = new Sk.builtin.func((value) => Sk.ffi.remapToPy(Sk.ffi.remapToJs(value) >= 256));
    mod.ISEOF = new Sk.builtin.func((value) => Sk.ffi.remapToPy(Sk.ffi.remapToJs(value) === 0));
    mod.__all__ = new Sk.builtin.list(Object.keys(mod).map((name) => new Sk.builtin.str(name)));
    return mod;
}
