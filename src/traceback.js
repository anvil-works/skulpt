// Python/traceback.c: traceback nodes retain their frame and the raise location.
Sk.builtin.frame = Sk.abstr.buildNativeClass("frame", {
    constructor: function frame(state) { this.$state = state; },
    slots: {
        tp$new() { throw new Sk.builtin.TypeError("cannot create 'frame' instances"); },
    },
    getsets: {
        f_code: { $get() { return this.$state.getCode(); } },
        f_lineno: {
            $get() { return new Sk.builtin.int_(this.$state.getLine()); },
            $set() { throw new Sk.builtin.NotImplementedError("frame line jumps require tracing support"); },
        },
        f_globals: { $get() { return Sk.misceval.namespaceDict(this.$state.getGlobals()); } },
        f_builtins: { $get() { return this.$state.getBuiltins(); } },
        f_back: {
            $get() {
                const previous = this.$state.getBack();
                return previous ? Sk.builtin.getFrame(previous) : Sk.builtin.none.none$;
            },
        },
        f_locals: { $get() { throw new Sk.builtin.NotImplementedError("frame locals proxies are not yet supported"); } },
        f_lasti: { $get() { throw new Sk.builtin.NotImplementedError("JavaScript code has no bytecode offsets"); } },
    },
    flags: { sk$acceptable_as_base_class: false },
});

Sk.builtin.getFrame = function (state) {
    return state.$pyFrame || (state.$pyFrame = new Sk.builtin.frame(state));
};

Sk.builtin.traceback = Sk.abstr.buildNativeClass("traceback", {
    constructor: function traceback(next, frame, lasti, lineno) {
        this.$next = next;
        this.$frame = frame;
        this.$lasti = lasti;
        this.$lineno = lineno;
    },
    slots: {
        tp$new(args, kwargs) {
            const [next, frame, lasti, lineno] = Sk.abstr.copyKeywordsToNamedArgs(
                "traceback", ["tb_next", "tb_frame", "tb_lasti", "tb_lineno"], args, kwargs);
            Sk.abstr.checkArgsLen("traceback", [next, frame, lasti, lineno].filter(value => value !== undefined), 4, 4);
            if (next !== Sk.builtin.none.none$ && !(next instanceof Sk.builtin.traceback)) {
                throw new Sk.builtin.TypeError("traceback() argument 'tb_next' must be traceback or None");
            }
            if (!(frame instanceof Sk.builtin.frame)) {
                throw new Sk.builtin.TypeError("traceback() argument 'tb_frame' must be frame, not " + Sk.abstr.typeName(frame));
            }
            return new Sk.builtin.traceback(next, frame, tracebackInt(lasti), tracebackInt(lineno));
        },
    },
    getsets: {
        tb_next: {
            $get() { return this.$next; },
            $set(next) {
                if (next === undefined) {throw new Sk.builtin.TypeError("can't delete tb_next attribute");}
                if (next !== Sk.builtin.none.none$ && !(next instanceof Sk.builtin.traceback)) {
                    throw new Sk.builtin.TypeError("expected traceback object, got '" + Sk.abstr.typeName(next) + "'");
                }
                for (let current = next; current instanceof Sk.builtin.traceback; current = current.$next) {
                    if (current === this) {throw new Sk.builtin.ValueError("traceback loop detected");}
                }
                this.$next = next;
            },
        },
        tb_frame: { $get() { return this.$frame; } },
        tb_lineno: {
            $get() {
                if (this.$lineno < 0) {throw new Sk.builtin.NotImplementedError("resolving traceback lines requires bytecode offsets");}
                return new Sk.builtin.int_(this.$lineno);
            },
        },
        tb_lasti: {
            $get() {
                if (this.$lasti === undefined) {throw new Sk.builtin.NotImplementedError("JavaScript code has no bytecode offsets");}
                return new Sk.builtin.int_(this.$lasti);
            },
        },
    },
    flags: { sk$acceptable_as_base_class: false },
});

function tracebackInt(value) {
    const result = Sk.misceval.asIndexSized(value, Sk.builtin.OverflowError);
    if (result < -2147483648 || result > 2147483647) {
        throw new Sk.builtin.OverflowError("Python int too large to convert to C int");
    }
    return result;
}

Sk.builtin.addTraceback = function (error, state, lineno, colno, filename) {
    // RERAISE keeps the current traceback; caller frames prepend their call site.
    // Compiler cleanup can catch the same propagation more than once per frame.
    const frame = Sk.builtin.getFrame(state);
    if (error.$tracebackFrame === frame) {return;}
    error.$tracebackFrame = frame;
    if (lineno === undefined) {lineno = state.getLine();}
    error.$traceback = new Sk.builtin.traceback(error.$traceback || Sk.builtin.none.none$, frame, undefined, lineno);
    // Retain the existing JavaScript error rendering contract without sharing a
    // mutable array between an original exception group and derived subgroups.
    error.traceback = error.traceback.concat([{lineno: lineno, colno: colno, filename: filename}]);
};
