/* Parse source into the modern AST using the configured Python compatibility mode. */

const { parseExpression, parseModule, parseFunctionType, scan, UnicodeNameDatabaseRequired } = require("@anvil-works/skulpt-parser/dist-core/index.js");
Sk["$scanSource"] = scan;
let resolveUnicodeName;

/**
 * Parse a module into plain AST nodes with UTF-8 byte columns.
 * Uses Sk.configure's Python mode and raises Skulpt syntax errors.
 * @param {string} source
 * @param {string} filename
 */
function parseSource(source, filename, mode) {
    try {
        const parse = mode === "eval" ? parseExpression : mode === "func_type" ? parseFunctionType : parseModule;
        return parse(source, {
            filename,
            pythonVersion: Sk.__future__.python3 ? 3 : 2,
            asyncAwaitAsIdentifiers: !Sk.__future__.python3,
            printFunction: Sk.__future__.print_function,
            resolveUnicodeName,
        });
    } catch (error) {
        if (error instanceof UnicodeNameDatabaseRequired) {
            resolveUnicodeName = require("@anvil-works/skulpt-parser/dist-core/unicode-names.js").unicodeName;
            return parseSource(source, filename, mode);
        }
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
}

Sk.parseModule = function (source, filename) {
    return parseSource(source, filename, "exec");
};
Sk.parseExpression = function (source, filename) {
    return parseSource(source, filename, "eval");
};
Sk.exportSymbol("Sk.parseModule", Sk.parseModule);
Sk.exportSymbol("Sk.parseExpression", Sk.parseExpression);
Sk.parseFunctionType = function (source, filename) {
    return parseSource(source, filename, "func_type");
};
Sk.exportSymbol("Sk.parseFunctionType", Sk.parseFunctionType);

// The parser currently exports module/expression entry points. Apply the
// interactive single_input boundary to its module AST and lexical newlines.
Sk.parseInteractive = function (source, filename) {
    const ast = Sk.parseModule(source, filename);
    if (ast.body.length === 0) {
        throw new Sk.builtin.SyntaxError("invalid syntax", filename);
    }
    const compound = Array.isArray(ast.body[0].body) || ast.body[0]._type === "Match";
    let indent = 0;
    let firstNewline;
    let lastNewline;
    let lastNewlineIndent = 0;
    for (const token of scan(source, { filename, pythonVersion: Sk.__future__.python3 ? 3 : 2, extraTokens: false })) {
        if (token.type === "INDENT") indent++;
        if (token.type === "DEDENT") indent--;
        if (token.type === "NEWLINE") {
            firstNewline = firstNewline || token;
            lastNewline = token;
            lastNewlineIndent = indent;
        }
    }
    const multiple = compound ? ast.body.length !== 1
        : ast.body.some(stmt => stmt.lineno > firstNewline.start[0]);
    if (multiple) {
        throw new Sk.builtin.SyntaxError("multiple statements found while compiling a single statement", filename);
    }
    // A simple suite following a compound header requires an actual newline;
    // an indented suite may end at EOF with the parser's implied dedent.
    if (compound && lastNewlineIndent === 0 && !/[\r\n]$/.test(lastNewline.line)) {
        throw new Sk.builtin.SyntaxError("invalid syntax", filename);
    }
    return { _type: "Interactive", body: ast.body };
};
Sk.exportSymbol("Sk.parseInteractive", Sk.parseInteractive);
