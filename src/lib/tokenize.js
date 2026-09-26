/* Implementation of the python tokenize module */

function legacyTokenizeModule(name) {
    var mod = {};

    mod.tokenize = new Sk.builtin.func(function(readline) {
        Sk.builtin.pyCheckArgsLen("tokenize", 1, 1);
        Sk.builtin.checkFunction(readline);

        // We construct a list of all tokens, since we can't yield from
        // within the tokenizer function as it currently exists. This may
        // be inefficient for tokenizing large files
        const tokens = [];
        function receiveToken(token) {
            tokens.push(
                new Sk.builtin.tuple([
                    Sk.ffi.remapToPy(token.type),
                    Sk.ffi.remapToPy(token.string),
                    new Sk.builtin.tuple([Sk.ffi.remapToPy(token.start[0]), Sk.ffi.remapToPy(token.start[1])]),
                    new Sk.builtin.tuple([Sk.ffi.remapToPy(token.end[0]), Sk.ffi.remapToPy(token.end[1])]),
                    Sk.ffi.remapToPy(token.line)
                ])
            );
        }

        function jsReadline() {
            const line = Sk.misceval.callsimArray(readline);
            return Sk.ffi.remapToJs(line);
        }

        Sk._tokenize("<stdin>", jsReadline, "UTF-8", receiveToken);

        return new Sk.builtin.list(tokens);
    });

    return mod;
};

// CPython v3.14.3 Lib/tokenize.py contracts, adapted to the shared JS scanner.
var $builtinmodule = function (name) {
    const scan = Sk["$scanSource"];
    // The stdlib can be shared with a runtime that still uses the old tokenizer.
    if (!scan) {
        return legacyTokenizeModule(name);
    }
    return Sk.misceval.chain(
        Sk.importModule("token", false, true),
        (token) => Sk.misceval.chain(Sk.importModule("collections", false, true), (collections) => {
            const mod = Object.fromEntries(token.$d.__all__.v.map((key) => [key.v, token.$d[key.v]]));
            const pyStr = (s) => new Sk.builtin.str(s);
            const tupleType = Sk.misceval.callsimArray(collections.$d.namedtuple, [
                pyStr("TokenInfo"), pyStr("type string start end line")
            ]);
            const TokenInfo = Sk.abstr.buildNativeClass("tokenize.TokenInfo", {
                base: tupleType,
                constructor: function TokenInfo() {},
                slots: {
                    $r() {
                        const fields = ["type", "string", "start", "end", "line"];
                        const values = this.v.map((value) => Sk.misceval.objectRepr(value));
                        values[0] += " (" + mod.tok_name.mp$subscript(this.v[0]).v + ")";
                        return pyStr("TokenInfo(" + fields.map((field, i) => field + "=" + values[i]).join(", ") + ")");
                    }
                },
                getsets: {
                    exact_type: {
                        $get() {
                            if (this.v[0].v === mod.OP.v) {
                                return mod.EXACT_TOKEN_TYPES.mp$lookup(this.v[1]) || this.v[0];
                            }
                            return this.v[0];
                        }
                    }
                },
                proto: {__module__: pyStr("tokenize")}
            });
            mod.TokenInfo = TokenInfo;
            const TokenError = Sk.abstr.buildNativeClass("tokenize.TokenError", {
                base: Sk.builtin.Exception,
                constructor: function TokenError(message, position) {
                    Sk.builtin.Exception.call(this, message);
                    if (position !== undefined) {
                        this.args = new Sk.builtin.tuple([pyStr(message), new Sk.builtin.tuple(position.map((x) => new Sk.builtin.int_(x)))]);
                    }
                }
            });
            mod.TokenError = TokenError;
            function info(type, string, start, end, line) {
                return Sk.misceval.callsimArray(TokenInfo, [
                    mod[type], pyStr(string),
                    new Sk.builtin.tuple(start.map((x) => new Sk.builtin.int_(x))),
                    new Sk.builtin.tuple(end.map((x) => new Sk.builtin.int_(x))), pyStr(line)
                ]);
            }
            function read(readline) {
                try {
                    return Sk.misceval.callsimArray(readline);
                } catch (error) {
                    if (error instanceof Sk.builtin.StopIteration) return null;
                    throw error;
                }
            }
            function *tokens(readline, withEncoding, python2) {
                // scan takes a complete string. Buffer source, but emit tokens lazily.
                const lines = [];
                let bytes;
                while (true) {
                    const value = read(readline);
                    if (value === null) break;
                    const isBytes = value instanceof Sk.builtin.bytes;
                    if (!(value instanceof Sk.builtin.str) && !isBytes) {
                        throw new Sk.builtin.TypeError("readline must return str or bytes");
                    }
                    if (!withEncoding && isBytes) {
                        throw new Sk.builtin.TypeError("generate_tokens requires a str readline");
                    }
                    if (bytes === undefined) bytes = isBytes;
                    if (bytes !== isBytes) throw new Sk.builtin.TypeError("readline cannot mix str and bytes");
                    if (value.v.length === 0) break;
                    lines.push(value.v);
                }
                let source;
                if (bytes) {
                    // Restrict byte input to UTF-8 until broader codecs are needed.
                    const decoder = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true});
                    try {
                        source = lines.map((line) => decoder.decode(line)).join("");
                        if (source.charCodeAt(0) === 0xfeff) source = source.slice(1);
                    } catch (error) {
                        throw new Sk.builtin.SyntaxError("invalid or missing encoding declaration");
                    }
                    const first = source.split("\n", 2);
                    const cookie = /^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)/;
                    for (let i = 0; i < first.length; i++) {
                        const match = cookie.exec(first[i]);
                        if (match) {
                            const encoding = match[1].toLowerCase().replace(/_/g, "-");
                            if (encoding !== "utf-8" && encoding !== "utf8" && !encoding.startsWith("utf-8-")) {
                                throw new Sk.builtin.SyntaxError("tokenize currently supports only UTF-8 byte input");
                            }
                            break;
                        }
                        if (i === 0 && !/^[ \t\f]*(?:#|\r?$)/.test(first[i])) break;
                    }
                } else {
                    source = lines.join("");
                }
                lines.length = 0;
                if (withEncoding) yield info("ENCODING", bytes === false ? "UTF-8" : "utf-8", [0, 0], [0, 0], "");
                try {
                    for (const token of scan(source, {extraTokens: true, python2Compat: python2})) {
                        yield info(token.type, token.string, token.start, token.end, token.line);
                    }
                } catch (error) {
                    if (error.name === "SyntaxError") {
                        const message = error.message.includes("unterminated triple-quoted string literal")
                            ? "EOF in multi-line string" : error.message;
                        throw new TokenError(message, [error.lineno, error.offset]);
                    }
                    if (error.name === "IndentationError" || error.name === "TabError") {
                        const converted = new Sk.builtin[error.name](error.message, "<string>", error.lineno);
                        converted.$msg = pyStr(error.message);
                        converted.$filename = pyStr("<string>");
                        converted.$lineno = new Sk.builtin.int_(error.lineno);
                        converted.$offset = new Sk.builtin.int_(error.offset);
                        converted.$text = error.text == null ? Sk.builtin.none.none$ : pyStr(error.text);
                        throw converted;
                    }
                    throw error;
                }
            }
            const TokenIterator = Sk.abstr.buildIteratorClass("tokenize.TokenIterator", {
                constructor: function TokenIterator(iterator) { this.iterator = iterator; },
                iternext() {
                    const next = this.iterator.next();
                    return next.done ? undefined : next.value;
                }
            });
            for (const name of ["tokenize", "generate_tokens"]) {
                mod[name] = new Sk.builtin.func(function (readline) {
                    Sk.builtin.pyCheckArgsLen(name, arguments.length, 1, 1);
                    Sk.builtin.checkFunction(readline);
                    return new TokenIterator(tokens(readline, name === "tokenize", !Sk.__future__.python3));
                });
            }
            mod.__all__ = new Sk.builtin.list([
                ...token.$d.__all__.v,
                ...["TokenInfo", "TokenError", "tokenize", "generate_tokens"].map(pyStr)
            ]);
            return mod;
        })
    );
};
