/* Compatibility for callers passing Sk.parse(...).cst straight to Sk.astFromParse.
 * The replacement frontend has no concrete syntax tree; cst is an opaque AST handle.
 */
Sk.parse = function (filename, source) {
    const parsed = Sk.parseCompilerModule(source, filename);
    return {cst: parsed.ast, flags: parsed.flags};
};

Sk.astFromParse = function (tree, filename, flags) {
    return tree;
};

Sk.exportSymbol("Sk.parse", Sk.parse);
Sk.exportSymbol("Sk.astFromParse", Sk.astFromParse);
