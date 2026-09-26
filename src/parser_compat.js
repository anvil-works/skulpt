/* Compatibility for callers passing Sk.parse(...).cst straight to Sk.astFromParse.
 * The replacement frontend has no concrete syntax tree; cst is an opaque AST handle.
 */
Sk.parse = function (filename, source) {
    const parsed = Sk.parseCompilerModule(source, filename);
    const lines = source.split("\n");
    const columns = new Map();
    function legacyColumns(node) {
        if (Array.isArray(node)) {
            node.forEach(legacyColumns);
        } else if (node && node._fields) {
            if (node.lineno !== undefined && node.col_offset !== undefined) {
                const line = lines[node.lineno - 1];
                if (/[^\x00-\x7f]/.test(line)) {
                    let offsets = columns.get(node.lineno);
                    if (!offsets) {
                        offsets = [0];
                        let bytes = 0;
                        let units = 0;
                        for (const char of line) {
                            const cp = char.codePointAt(0);
                            bytes += cp < 0x80 ? 1 : cp < 0x800 ? 2 : cp < 0x10000 ? 3 : 4;
                            units += char.length;
                            offsets[bytes] = units;
                        }
                        columns.set(node.lineno, offsets);
                    }
                    node.col_offset = offsets[node.col_offset];
                }
            }
            for (let i = 1; i < node._fields.length; i += 2) {
                legacyColumns(node._fields[i](node));
            }
        }
    }
    legacyColumns(parsed.ast);
    return {cst: parsed.ast, flags: parsed.flags};
};

Sk.astFromParse = function (tree, filename, flags) {
    return tree;
};

Sk.exportSymbol("Sk.parse", Sk.parse);
Sk.exportSymbol("Sk.astFromParse", Sk.astFromParse);
