// Template and Interpolation follow Objects/templateobject.c and
// Objects/interpolationobject.c. Values/conversion/specification remain separate:
// constructing a template never formats or converts an interpolation value.
Sk.builtin.Interpolation = Sk.abstr.buildNativeClass("string.templatelib.Interpolation", {
    constructor: function Interpolation(value, expression, conversion, formatSpec) {
        this.$value = value;
        this.$expression = expression;
        this.$conversion = conversion;
        this.$formatSpec = formatSpec;
    },
    slots: {
        tp$doc: "Interpolation object",
        tp$getattr: Sk.generic.getAttr,
        tp$new(args, kwargs) {
            const [value, expression, conversion, formatSpec] = Sk.abstr.copyKeywordsToNamedArgs(
                "Interpolation", ["value", "expression", "conversion", "format_spec"], args, kwargs,
                [Sk.builtin.str.$emptystr, Sk.builtin.none.none$, Sk.builtin.str.$emptystr]);
            if (!Sk.builtin.checkString(expression)) {
                throw new Sk.builtin.TypeError("Interpolation() argument 'expression' must be str, not " + Sk.abstr.typeName(expression));
            }
            if (!Sk.builtin.checkNone(conversion)) {
                if (!Sk.builtin.checkString(conversion)) {
                    throw new Sk.builtin.TypeError("Interpolation() argument 'conversion' must be str, not " + Sk.abstr.typeQualifiedName(conversion));
                }
                if (!["s", "a", "r"].includes(conversion.$jsstr())) {
                    throw new Sk.builtin.ValueError("Interpolation() argument 'conversion' must be one of 's', 'a' or 'r'");
                }
            }
            if (!Sk.builtin.checkString(formatSpec)) {
                throw new Sk.builtin.TypeError("Interpolation() argument 'format_spec' must be str, not " + Sk.abstr.typeName(formatSpec));
            }
            return new Sk.builtin.Interpolation(value, expression, conversion, formatSpec);
        },
        $r() {
            return new Sk.builtin.str("Interpolation(" + [this.$value, this.$expression, this.$conversion, this.$formatSpec].map(Sk.misceval.objectRepr).join(", ") + ")");
        },
    },
    getsets: {
        value: { $get() { return this.$value; } },
        expression: { $get() { return this.$expression; } },
        conversion: { $get() { return this.$conversion; } },
        format_spec: { $get() { return this.$formatSpec; } },
    },
    methods: {
        __reduce__: {
            $meth() {
                return new Sk.builtin.tuple([Sk.builtin.Interpolation,
                                             new Sk.builtin.tuple([this.$value, this.$expression, this.$conversion, this.$formatSpec])]);
            },
            $flags: { NoArgs: true },
        },
    },
    classmethods: {
        __class_getitem__: {
            $meth(item) { return new Sk.builtin.GenericAlias(this, item); },
            $flags: { OneArg: true },
        },
    },
    proto: { __match_args__: new Sk.builtin.tuple(["value", "expression", "conversion", "format_spec"].map(name => new Sk.builtin.str(name))) },
    flags: { sk$unacceptableBase: true },
});

function templateFromParts(parts) {
    const strings = [];
    const interpolations = [];
    let lastWasString = false;
    for (const part of parts) {
        if (Sk.builtin.checkString(part)) {
            if (lastWasString) {strings[strings.length - 1] = new Sk.builtin.str(strings[strings.length - 1].$jsstr() + part.$jsstr());} else {strings.push(part);}
            lastWasString = true;
        } else if (part instanceof Sk.builtin.Interpolation) {
            if (!lastWasString) {strings.push(Sk.builtin.str.$emptystr);}
            interpolations.push(part);
            lastWasString = false;
        } else {
            throw new Sk.builtin.TypeError("Template.__new__ *args need to be of type 'str' or 'Interpolation', got " + Sk.abstr.typeQualifiedName(part));
        }
    }
    if (!lastWasString) {strings.push(Sk.builtin.str.$emptystr);}
    return new Sk.builtin.Template(new Sk.builtin.tuple(strings), new Sk.builtin.tuple(interpolations));
}

Sk.builtin.Template = Sk.abstr.buildNativeClass("string.templatelib.Template", {
    constructor: function Template(strings, interpolations) {
        this.$strings = strings;
        this.$interpolations = interpolations;
    },
    slots: {
        tp$doc: "Template object",
        tp$getattr: Sk.generic.getAttr,
        tp$new(args, kwargs) {
            if (kwargs !== undefined) {throw new Sk.builtin.TypeError("Template.__new__ only accepts *args arguments");}
            return templateFromParts(args);
        },
        tp$iter() { return new Sk.builtin.TemplateIter(this); },
        tp$as_sequence_or_mapping: true,
        sq$concat(other) {
            if (!(other instanceof Sk.builtin.Template)) {
                throw new Sk.builtin.TypeError('can only concatenate string.templatelib.Template (not "' + Sk.abstr.typeQualifiedName(other) + '") to string.templatelib.Template');
            }
            const left = this.$strings.v;
            const right = other.$strings.v;
            const joined = new Sk.builtin.str(left[left.length - 1].$jsstr() + right[0].$jsstr());
            const strings = new Sk.builtin.tuple([...left.slice(0, -1), joined, ...right.slice(1)]);
            const interpolations = new Sk.builtin.tuple([...this.$interpolations.v, ...other.$interpolations.v]);
            return new Sk.builtin.Template(strings, interpolations);
        },
        $r() {
            return new Sk.builtin.str("Template(strings=" + Sk.misceval.objectRepr(this.$strings) +
                ", interpolations=" + Sk.misceval.objectRepr(this.$interpolations) + ")");
        },
    },
    methods: {
        __reduce__: {
            $meth() {
                const moduleName = new Sk.builtin.str("string.templatelib");
                return Sk.misceval.chain(Sk.importModule(moduleName.$jsstr(), false, true),
                                         () => Sk.abstr.gattr(Sk.sysmodules.mp$subscript(moduleName), new Sk.builtin.str("_template_unpickle"), true),
                                         rebuild => new Sk.builtin.tuple([rebuild, new Sk.builtin.tuple([this.$strings, this.$interpolations])]));
            },
            $flags: { NoArgs: true },
        },
    },
    classmethods: {
        __class_getitem__: {
            $meth(item) { return new Sk.builtin.GenericAlias(this, item); },
            $flags: { OneArg: true },
        },
    },
    getsets: {
        strings: { $get() { return this.$strings; } },
        interpolations: { $get() { return this.$interpolations; } },
        values: { $get() { return new Sk.builtin.tuple(this.$interpolations.v.map(item => item.$value)); } },
    },
    flags: { sk$unacceptableBase: true },
});

Sk.builtin.TemplateIter = Sk.abstr.buildIteratorClass("string.templatelib.TemplateIter", {
    constructor: function TemplateIter(template) {
        this.$template = template;
        this.$stringsIndex = 0;
        this.$interpolationsIndex = 0;
        this.$fromStrings = true;
    },
    iternext() {
        // templateiter_next alternates two independent tuple iterators.
        const template = this.$template;
        if (this.$fromStrings) {
            const value = template.$strings.v[this.$stringsIndex++];
            this.$fromStrings = false;
            if (value === undefined || value.$jsstr() !== "") {return value;}
        }
        this.$fromStrings = true;
        return template.$interpolations.v[this.$interpolationsIndex++];
    },
    flags: { sk$unacceptableBase: true },
});
