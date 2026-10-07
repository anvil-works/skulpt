/* Flags for def-use information */

var DEF_GLOBAL = 1;
/* global stmt */
var DEF_LOCAL = 2;
/* assignment in code block */
var DEF_PARAM = 2 << 1;
/* formal parameter */
var USE = 2 << 2;
/* name is used */
var DEF_STAR = 2 << 3;
/* parameter is star arg */
var DEF_DOUBLESTAR = 2 << 4;
/* parameter is star-star arg */
var DEF_INTUPLE = 2 << 5;
/* name defined in tuple in parameters */
var DEF_FREE = 2 << 6;
/* name used but not defined in nested block */
var DEF_FREE_GLOBAL = 2 << 7;
/* free variable is actually implicit global */
var DEF_FREE_CLASS = 2 << 8;
/* free variable from class's method */
var DEF_IMPORT = 2 << 9;
/* assignment occurred via import */
var DEF_NONLOCAL = 2 << 10;
/* nonlocal stmt */
var DEF_ANNOT = 2 << 11;
/* this name is annotated */
var DEF_COMP_ITER = 1 << 16;
/* comprehension iteration target; above the encoded scope bits */
var DEF_TYPE_PARAM = 1 << 17;

var DEF_BOUND = (DEF_LOCAL | DEF_PARAM | DEF_IMPORT);

/* GLOBAL_EXPLICIT and GLOBAL_IMPLICIT are used internally by the symbol
 table.  GLOBAL is returned from PyST_GetScope() for either of them.
 It is stored in ste_symbols at bits 13-15, above DEF_ANNOT at bit 12.
 */
var SCOPE_OFF = 13;
var SCOPE_MASK = 7;

var LOCAL = 1;
var GLOBAL_EXPLICIT = 2;
var GLOBAL_IMPLICIT = 3;
var FREE = 4;
var CELL = 5;

/* The following three names are used for the ste_unoptimized bit field */
var OPT_IMPORT_STAR = 1;
var OPT_EXEC = 2;
var OPT_BARE_EXEC = 4;
var OPT_TOPLEVEL = 8;
/* top-level names, including eval and exec */

var GENERATOR = 2;
var GENERATOR_EXPRESSION = 2;

var ModuleBlock = "module";
var FunctionBlock = "function";
var ClassBlock = "class";

var SYMTAB_CONSTS = {
    DEF_GLOBAL: DEF_GLOBAL,
    DEF_LOCAL: DEF_LOCAL,
    DEF_TYPE_PARAM: DEF_TYPE_PARAM,
    DEF_PARAM: DEF_PARAM,
    USE: USE,
    DEF_STAR: DEF_STAR,
    DEF_DOUBLESTAR: DEF_DOUBLESTAR,
    DEF_INTUPLE: DEF_INTUPLE,
    DEF_FREE: DEF_FREE,
    DEF_FREE_GLOBAL: DEF_FREE_GLOBAL,
    DEF_FREE_CLASS: DEF_FREE_CLASS,
    DEF_IMPORT: DEF_IMPORT,
    DEF_BOUND: DEF_BOUND,
    SCOPE_OFF: SCOPE_OFF,
    SCOPE_MASK: SCOPE_MASK,
    LOCAL: LOCAL,
    GLOBAL_EXPLICIT: GLOBAL_EXPLICIT,
    GLOBAL_IMPLICIT: GLOBAL_IMPLICIT,
    FREE: FREE,
    CELL: CELL,
    OPT_IMPORT_STAR: OPT_IMPORT_STAR,
    OPT_EXEC: OPT_EXEC,
    OPT_BARE_EXEC: OPT_BARE_EXEC,
    OPT_TOPLEVEL: OPT_TOPLEVEL,
    GENERATOR: GENERATOR,
    GENERATOR_EXPRESSION: GENERATOR_EXPRESSION,
    ModuleBlock: ModuleBlock,
    FunctionBlock: FunctionBlock,
    ClassBlock: ClassBlock
};

Sk.exportSymbol("Sk.SYMTAB_CONSTS", SYMTAB_CONSTS);

/**
 * @constructor
 * @param {string} name
 * @param {number} flags
 * @param {Array.<SymbolTableScope>} namespaces
 */
function Symbol_ (name, flags, namespaces) {
    this.__name = name;
    this.__flags = flags;
    this.__scope = (flags >> SCOPE_OFF) & SCOPE_MASK;
    this.__namespaces = namespaces || [];
}
Symbol_.prototype.get_name = function () {
    return this.__name;
};
Symbol_.prototype.is_referenced = function () {
    return !!(this.__flags & USE);
};
Symbol_.prototype.is_parameter = function () {
    return !!(this.__flags & DEF_PARAM);
};
Symbol_.prototype.is_global = function () {
    return this.__scope === GLOBAL_IMPLICIT || this.__scope == GLOBAL_EXPLICIT;
};
Symbol_.prototype.is_declared_global = function () {
    return this.__scope == GLOBAL_EXPLICIT;
};
Symbol_.prototype.is_local = function () {
    return !!(this.__flags & DEF_BOUND);
};
Symbol_.prototype.is_free = function () {
    return this.__scope == FREE;
};
Symbol_.prototype.is_imported = function () {
    return !!(this.__flags & DEF_IMPORT);
};
Symbol_.prototype.is_assigned = function () {
    return !!(this.__flags & DEF_LOCAL);
};
Symbol_.prototype.is_namespace = function () {
    return this.__namespaces && this.__namespaces.length > 0;
};
Symbol_.prototype.get_namespaces = function () {
    return this.__namespaces;
};

var astScopeCounter = 0;

/**
 * @constructor
 * @param {SymbolTable} table
 * @param {string} name
 * @param {string} type
 * @param {number} lineno
 */
function SymbolTableScope (table, name, type, ast, lineno) {
    this.symFlags = {};
    this.name = name;
    this.varnames = [];
    this.children = [];
    this.blockType = type;
    this.ast = ast;

    this.isNested = false;
    this.hasFree = false;
    this.childHasFree = false;  // true if child block has free vars including free refs to globals
    this.hasCells = false;  // true if this scope has cell variables (locals accessed by nested functions)
    this.generator = false;
    this.inConditionalBlock = false;
    this.varargs = false;
    this.varkeywords = false;
    this.returnsValue = false;

    this.lineno = lineno;

    this.table = table;

    this.isMethod = !!(table.cur && table.cur.blockType === ClassBlock && type === FunctionBlock && ast._type !== "Annotation");
    if (table.cur && (table.cur.isNested || table.cur.blockType === FunctionBlock)) {
        this.isNested = true;
    }

    ast.scopeId = astScopeCounter++;
    table.stss[ast.scopeId] = this;

    // cache of Symbols for returning to other parts of code
    this.symbols = {};
}
SymbolTableScope.prototype.get_type = function () {
    return this.blockType;
};
SymbolTableScope.prototype.get_name = function () {
    return this.name;
};
SymbolTableScope.prototype.get_lineno = function () {
    return this.lineno;
};
SymbolTableScope.prototype.is_nested = function () {
    return this.isNested;
};
SymbolTableScope.prototype.has_children = function () {
    return this.children.length > 0;
};
SymbolTableScope.prototype.get_identifiers = function () {
    return this._identsMatching(function () {
        return true;
    });
};
SymbolTableScope.prototype.lookup = function (name) {
    var namespaces;
    var flags;
    var sym;
    if (!this.symbols.hasOwnProperty(name)) {
        flags = this.symFlags[name];
        namespaces = this.__check_children(name);
        sym = this.symbols[name] = new Symbol_(name, flags, namespaces);
    }
    else {
        sym = this.symbols[name];
    }
    return sym;
};
SymbolTableScope.prototype.__check_children = function (name) {
    //print("  check_children:", name);
    var child;
    var i;
    var ret = [];
    for (i = 0; i < this.children.length; ++i) {
        child = this.children[i];
        if (child.name === name) {
            ret.push(child);
        }
    }
    return ret;
};

SymbolTableScope.prototype._identsMatching = function (f) {
    var k;
    var ret = [];
    for (k in this.symFlags) {
        if (this.symFlags.hasOwnProperty(k)) {
            if (f(this.symFlags[k])) {
                ret.push(k);
            }
        }
    }
    ret.sort();
    return ret;
};
SymbolTableScope.prototype.get_parameters = function () {
    Sk.asserts.assert(this.get_type() == "function", "get_parameters only valid for function scopes");
    if (!this._funcParams) {
        this._funcParams = this._identsMatching(function (x) {
            return x & DEF_PARAM;
        });
    }
    return this._funcParams;
};
SymbolTableScope.prototype.get_locals = function () {
    Sk.asserts.assert(this.get_type() == "function", "get_locals only valid for function scopes");
    if (!this._funcLocals) {
        this._funcLocals = this._identsMatching(function (x) {
            return x & DEF_BOUND;
        });
    }
    return this._funcLocals;
};
SymbolTableScope.prototype.get_globals = function () {
    Sk.asserts.assert(this.get_type() == "function", "get_globals only valid for function scopes");
    if (!this._funcGlobals) {
        this._funcGlobals = this._identsMatching(function (x) {
            var masked = (x >> SCOPE_OFF) & SCOPE_MASK;
            return masked == GLOBAL_IMPLICIT || masked == GLOBAL_EXPLICIT;
        });
    }
    return this._funcGlobals;
};
SymbolTableScope.prototype.get_frees = function () {
    Sk.asserts.assert(this.get_type() == "function", "get_frees only valid for function scopes");
    if (!this._funcFrees) {
        this._funcFrees = this._identsMatching(function (x) {
            var masked = (x >> SCOPE_OFF) & SCOPE_MASK;
            return masked == FREE;
        });
    }
    return this._funcFrees;
};
SymbolTableScope.prototype.get_methods = function () {
    var i;
    var all;
    Sk.asserts.assert(this.get_type() == "class", "get_methods only valid for class scopes");
    if (!this._classMethods) {
        // todo; uniq?
        all = [];
        for (i = 0; i < this.children.length; ++i) {
            all.push(this.children[i].name);
        }
        all.sort();
        this._classMethods = all;
    }
    return this._classMethods;
};
SymbolTableScope.prototype.getScope = function (name) {
    //print("getScope");
    //for (var k in this.symFlags) print(k);
    var v = this.symFlags[name];
    if (v === undefined) {
        return 0;
    }
    return (v >> SCOPE_OFF) & SCOPE_MASK;
};

/**
 * @constructor
 * @param {string} filename
 */
function SymbolTable (filename, flags) {
    this.flags = flags || 0;
    this.filename = filename;
    this.cur = null;
    this.top = null;
    this.stack = [];
    this.global = null; // points at top level module symFlags
    this.curClass = null; // current class or null
    this.tmpname = 0;

    // mapping from ast nodes to their scope if they have one. we add an
    // id to the ast node when a scope is created for it, and store it in
    // here for the compiler to lookup later.
    this.stss = {};
}
SymbolTable.prototype.getStsForAst = function (ast) {
    var v;
    Sk.asserts.assert(ast.scopeId !== undefined, "ast wasn't added to st?");
    v = this.stss[ast.scopeId];
    Sk.asserts.assert(v !== undefined, "unknown sym tab entry");
    return v;
};

SymbolTable.prototype.SEQStmt = function (nodes) {
    var val;
    var i;
    var len;
    if (nodes !== null) {
        Sk.asserts.assert(Sk.isArrayLike(nodes), "SEQ: nodes isn't array? got " + nodes.toString());
        len = nodes.length;
        for (i = 0; i < len; ++i) {
            val = nodes[i];
            if (val) {
                this.visitStmt(val);
            }
        }
    }
};

SymbolTable.prototype.SEQExpr = function (nodes) {
    var val;
    var i;
    var len;
    if (nodes !== null) {
        Sk.asserts.assert(Sk.isArrayLike(nodes), "SEQ: nodes isn't array? got " + nodes.toString());
        len = nodes.length;
        for (i = 0; i < len; ++i) {
            val = nodes[i];
            if (val) {
                this.visitExpr(val);
            }
        }
    }
};

SymbolTable.prototype.enterBlock = function (name, blockType, ast, lineno) {
    var prev;
    name = Sk.fixReserved(name);
    //print("enterBlock:", name);
    prev = null;
    if (this.cur) {
        prev = this.cur;
        this.stack.push(this.cur);
    }
    this.cur = new SymbolTableScope(this, name, blockType, ast, lineno);
    this.cur.compIterExpr = prev ? prev.compIterExpr : 0;
    if (name === "top") {
        this.global = this.cur.symFlags;
    }
    if (prev) {
        //print("    adding", this.cur.name, "to", prev.name);
        prev.children.push(this.cur);
    }
};

SymbolTable.prototype.exitBlock = function () {
    //print("exitBlock");
    this.cur = null;
    if (this.stack.length > 0) {
        this.cur = this.stack.pop();
    }
};

SymbolTable.prototype.visitParams = function (args, toplevel) {
    var arg;
    var i;
    for (i = 0; i < args.length; ++i) {
        arg = args[i];
        if (arg._type === "arg") {
            // TODO arguments are more complicated in Python 3...
            this.addDef(arg.arg, DEF_PARAM, arg.lineno);
        }
        else {
            // Tuple isn't supported
            throw new Sk.builtin.SyntaxError("invalid expression in parameter list", this.filename);
        }
    }
};

// symtable_visit_annotation: variable annotations share one annotation block.
// Function-local and future annotations validate syntax without outer captures.
SymbolTable.prototype.visitAnnotation = function (annotation, statement) {
    const parent = this.cur;
    const namespace = [ClassBlock, ModuleBlock].includes(parent.blockType);
    if (statement && namespace) {
        statement.conditionalAnnotation = parent.blockType === ModuleBlock || parent.inConditionalBlock;
        if (statement.conditionalAnnotation) parent.hasConditionalAnnotations = true;
    }
    const deferred = Sk.__future__.python3 && !(this.flags & 0x1000000) && statement && namespace;
    if (deferred) {
        if (statement.simple) {
            const annotations = parent.deferredVariableAnnotations || (parent.deferredVariableAnnotations = []);
            statement.conditionalAnnotationIndex = statement.conditionalAnnotation ? (parent.nextAnnotationIndex || 0) : -1;
            if (statement.conditionalAnnotation) parent.nextAnnotationIndex = statement.conditionalAnnotationIndex + 1;
            annotations.push({ statement, index: statement.conditionalAnnotationIndex });
        }
        if (!parent.variableAnnotationScope) {
            const key = { _type: "Annotation", variableAnnotations: true,
                lineno: parent.ast.lineno || (parent.ast.body[0] && parent.ast.body[0].lineno) || 1,
                args: { posonlyargs: [{ _type: "arg", arg: "$annotationFormat", annotation: null }], args: [],
                    defaults: [], kwonlyargs: [], kw_defaults: [], vararg: null, kwarg: null } };
            parent.variableAnnotationScope = key;
            this.enterBlock("__annotate__", FunctionBlock, key, annotation.lineno);
            this.cur.annotationScope = true;
            if (parent.blockType === ClassBlock) {
                this.cur.classScope = parent;
                this.cur.hasFree = true;
                parent.needsClassdict = true;
                this.addDef("__classdict__", USE, annotation.lineno);
            }
            this.visitArguments(key.args, annotation.lineno);
        } else {
            this.stack.push(parent);
            this.cur = this.getStsForAst(parent.variableAnnotationScope);
        }
        if (statement.simple && statement.conditionalAnnotation) this.addDef("__conditional_annotations__", USE, annotation.lineno);
        this.visitExpr(annotation);
        this.exitBlock();
        return;
    }
    this.enterBlock("__annotate__", FunctionBlock, {}, annotation.lineno);
    this.cur.annotationScope = true;
    this.visitExpr(annotation);
    this.exitBlock();
    this.cur.children.pop();
};

// symtable_enter_type_param_block and symtable_visit_type_param: parameter
// bindings enclose the function/alias, with separate lazy bound/default blocks.
SymbolTable.prototype.visitTypeParameters = function (owner) {
    const name = owner._type === "TypeAlias" ? owner.name.id : owner.name;
    const args = { posonlyargs: [], args: [], defaults: [], kwonlyargs: [], kw_defaults: [], vararg: null, kwarg: null };
    if (owner.args && owner.args.defaults.length) args.posonlyargs.push({ _type: "arg", arg: "$typeDefaults", annotation: null });
    if (owner.args && owner.args.kw_defaults.some(e => e)) args.posonlyargs.push({ _type: "arg", arg: "$typeKwdefaults", annotation: null });
    const key = owner.typeParamScope = { _type: "TypeParameters", args, lineno: owner.lineno };
    const classScope = this.cur.blockType === ClassBlock ? this.cur : this.cur.classScope;
    this.enterBlock("<generic parameters of " + name + ">", FunctionBlock, key, owner.lineno);
    this.cur.annotationScope = true;
    this.cur.annotationKind = "generic";
    this.cur.isMethod = false;
    if (classScope) {
        this.cur.classScope = classScope;
        classScope.needsClassdict = true;
        this.addDef("__classdict__", USE, owner.lineno);
    }
    this.visitArguments(args, owner.lineno);
    const names = new Set();
    let seenDefault = false;
    for (const param of owner.type_params) {
        const mangled = Sk.mangleName(this.curClass, param.name).v;
        if (names.has(mangled)) throw new Sk.builtin.SyntaxError("duplicate type parameter '" + param.name + "'", this.filename, param.lineno);
        names.add(mangled);
        if (param.name === "__classdict__") throw new Sk.builtin.SyntaxError("reserved name '__classdict__' cannot be used for type parameter", this.filename, param.lineno);
        this.addDef(param.name, DEF_LOCAL | DEF_TYPE_PARAM, param.lineno);
        if (param.bound) param.boundScope = this.visitTypeVariable(param, param.bound, param.bound._type === "Tuple" ? "a TypeVar constraint" : "a TypeVar bound");
        if (param.default_value) {
            seenDefault = true;
            param.defaultScope = this.visitTypeVariable(param, param.default_value, "a " + param._type + " default");
        } else if (seenDefault) {
            throw new Sk.builtin.SyntaxError("non-default type parameter '" + param.name + "' follows default type parameter", this.filename, param.lineno);
        }
    }
};

SymbolTable.prototype.visitTypeVariable = function (param, expression, kind) {
    const key = { _type: "TypeVariable", lineno: param.lineno,
        args: { posonlyargs: [{ _type: "arg", arg: "$typeFormat", annotation: null }], args: [],
            defaults: [{ _type: "Constant", value: { type: "int", value: 1 } }], kwonlyargs: [], kw_defaults: [], vararg: null, kwarg: null } };
    const classScope = this.cur.classScope;
    this.enterBlock(param.name, FunctionBlock, key, param.lineno);
    this.cur.annotationScope = true;
    this.cur.annotationKind = kind;
    this.cur.isMethod = false;
    if (classScope) {
        this.cur.classScope = classScope;
        classScope.needsClassdict = true;
        this.addDef("__classdict__", USE, param.lineno);
    }
    this.visitArguments(key.args, param.lineno);
    this.visitExpr(expression);
    this.exitBlock();
    return key;
};

SymbolTable.prototype.visitAnnotations = function (a, returns, owner) {
    const annotations = a.args.concat(a.posonlyargs, a.vararg ? [a.vararg] : [], a.kwonlyargs, a.kwarg ? [a.kwarg] : []).filter(arg => arg.annotation);
    if (Sk.__future__.python3 && annotations.length + Number(!!returns)) {
        const key = { _type: "Annotation", owner, lineno: owner.lineno,
            args: { posonlyargs: [{ _type: "arg", arg: "$annotationFormat", annotation: null }], args: [],
                defaults: [], kwonlyargs: [], kw_defaults: [], vararg: null, kwarg: null } };
        a.annotationScope = key;
        const classScope = this.cur.blockType === ClassBlock ? this.cur : this.cur.classScope;
        this.enterBlock("__annotate__", FunctionBlock, key, owner.lineno);
        this.cur.annotationScope = true;
        if (classScope && !(this.flags & 0x1000000)) {
            this.cur.classScope = classScope;
            this.cur.hasFree = true;
            classScope.needsClassdict = true;
            this.addDef("__classdict__", USE, owner.lineno);
        }
        this.visitArguments(key.args, owner.lineno);
        for (const arg of annotations) this.visitExpr(arg.annotation);
        if (returns) this.visitExpr(returns);
        const scope = this.cur;
        this.exitBlock();
        if (this.flags & 0x1000000) {
            this.cur.children.pop();
            // Stringization emits no nested expression code or closure.
            scope.children = [];
            this.analyzeBlock(scope, null, {}, {});
        }
        return;
    }
    if (a.posonlyargs) {
        this.visitArgAnnotations(a.posonlyargs);
    }
    if (a.args) {
        this.visitArgAnnotations(a.args);
    }
    if (a.vararg && a.vararg.annotation) {
        this.visitAnnotation(a.vararg.annotation);
    }
    if (a.kwarg && a.kwarg.annotation) {
        this.visitAnnotation(a.kwarg.annotation);
    }
    if (a.kwonlyargs) {
        this.visitArgAnnotations(a.kwonlyargs);
    }
    if (returns) {
        this.visitAnnotation(returns);
    }
};

SymbolTable.prototype.visitArgAnnotations = function (args) {
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        if (arg.annotation) {
            this.visitAnnotation(arg.annotation);
        }
    }
};

SymbolTable.prototype.visitArguments = function (a, lineno) {
    this.visitParams(a.posonlyargs, true);
    if (a.args) {
        this.visitParams(a.args, true);
    }
    if (a.kwonlyargs) {
        this.visitParams(a.kwonlyargs, true);
    }
    if (a.vararg) {
        this.addDef(a.vararg.arg, DEF_PARAM, lineno);
        this.cur.varargs = true;
    }
    if (a.kwarg) {
        this.addDef(a.kwarg.arg, DEF_PARAM, lineno);
        this.cur.varkeywords = true;
    }
};

SymbolTable.prototype.newTmpname = function (lineno) {
    this.addDef(new Sk.builtin.str("_[" + (++this.tmpname) + "]"), DEF_LOCAL, lineno);
};

SymbolTable.prototype.addDef = function (name, flag, lineno, scope) {
    // Validation precedes optimization, including skipped suites and asserts.
    if ((typeof name === "string" ? name : name.v) === "__debug__" && (flag & (DEF_LOCAL | DEF_PARAM | DEF_IMPORT))) {
        throw new Sk.builtin.SyntaxError("cannot assign to __debug__", this.filename, lineno);
    }
    scope = scope || this.cur;
    var fromGlobal;
    var val;
    var mangled = Sk.mangleName(this.curClass, name).v;
    mangled = Sk.fixReserved(mangled);
    val = scope.symFlags[mangled];
    if (val !== undefined) {
        if ((flag & DEF_PARAM) && (val & DEF_PARAM)) {
            throw new Sk.builtin.SyntaxError("duplicate argument '" + name + "' in function definition", this.filename, lineno);
        }
        val |= flag;
    }
    else {
        val = flag;
    }
    if (scope.compIterTarget && (flag & DEF_LOCAL)) {
        if (val & (DEF_GLOBAL | DEF_NONLOCAL)) {
            throw new Sk.builtin.SyntaxError("comprehension inner loop cannot rebind assignment expression target '" + name + "'", this.filename, lineno);
        }
        val |= DEF_COMP_ITER;
    }
    scope.symFlags[mangled] = val;
    if (flag & DEF_PARAM) {
        scope.varnames.push(mangled);
    }
    else if (flag & DEF_GLOBAL) {
        val = flag;
        fromGlobal = this.global[mangled];
        if (fromGlobal !== undefined) {
            val |= fromGlobal;
        }
        this.global[mangled] = val;
    }
};

SymbolTable.prototype.visitSlice = function (s) {
    if (s._type === "Slice") {
        if (s.lower) this.visitExpr(s.lower);
        if (s.upper) this.visitExpr(s.upper);
        if (s.step) this.visitExpr(s.step);
    } else if (s._type === "Tuple") {
        s.elts.forEach(elt => this.visitSlice(elt));
    } else {
        this.visitExpr(s);
    }
};

SymbolTable.prototype.visitKeywords = function (keywords) {
    const seen = new Set();
    for (const keyword of keywords) {
        if (keyword.arg !== null) {
            if (seen.has(keyword.arg)) throw new Sk.builtin.SyntaxError("keyword argument repeated: " + keyword.arg, this.filename, keyword.value.lineno);
            seen.add(keyword.arg);
        }
        this.visitExpr(keyword.value);
    }
};

SymbolTable.prototype.visitStmt = function (s) {
    var cur;
    var name;
    var i;
    var nameslen;
    var tmp;
    var e_name;
    Sk.asserts.assert(s !== undefined, "visitStmt called with undefined");
    const parent = this.cur;
    const inConditional = parent.inConditionalBlock;
    if (["If", "While", "For", "AsyncFor", "With", "AsyncWith", "Try", "TryStar", "Match"].includes(s._type)) {
        parent.inConditionalBlock = true;
    }
    switch (s._type) {
        case "FunctionDef":
            if (s.type_params.length && !Sk.__future__.python3) throw new Sk.builtin.SyntaxError("invalid syntax", this.filename, s.lineno);
            this.addDef(s.name, DEF_LOCAL, s.lineno);
            if (s.args.defaults) {
                this.SEQExpr(s.args.defaults);
                this.SEQExpr(s.args.kw_defaults);
            }
            if (s.decorator_list) {
                this.SEQExpr(s.decorator_list);
            }
            if (s.type_params.length) this.visitTypeParameters(s);
            this.visitAnnotations(s.args, s.returns, s);
            this.enterBlock(s.name, FunctionBlock, s, s.lineno);
            this.cur.isMethod = parent.blockType === ClassBlock && !s.type_params.length;
            this.visitArguments(s.args, s.lineno);
            this.SEQStmt(s.body);
            this.exitBlock();
            if (s.type_params.length) this.exitBlock();
            break;
        case "ClassDef":
            if (s.type_params.length) throw new Sk.builtin.SyntaxError("Type parameters are not supported by the Skulpt compiler", this.filename, s.lineno);
            this.addDef(s.name, DEF_LOCAL, s.lineno);
            this.SEQExpr(s.bases);
            this.visitKeywords(s.keywords);
            if (s.decorator_list) {
                this.SEQExpr(s.decorator_list);
            }
            this.enterBlock(s.name, ClassBlock, s, s.lineno);
            tmp = this.curClass;
            this.curClass = s.name;
            this.SEQStmt(s.body);
            this.exitBlock();
            break;
        case "Return":
            if (s.value) {
                this.visitExpr(s.value);
                this.cur.returnsValue = true;
            }
            break;
        case "TypeAlias": {
            if (!Sk.__future__.python3) throw new Sk.builtin.SyntaxError("invalid syntax", this.filename, s.lineno);
            this.visitExpr(s.name);
            if (s.type_params.length) this.visitTypeParameters(s);
            s.args = { posonlyargs: [{ _type: "arg", arg: "$aliasFormat", annotation: null }], args: [],
                defaults: [{ _type: "Constant", value: { type: "int", value: 1 } }], kwonlyargs: [], kw_defaults: [], vararg: null, kwarg: null };
            const classScope = this.cur.blockType === ClassBlock ? this.cur : this.cur.classScope;
            this.enterBlock(s.name.id, FunctionBlock, s, s.lineno);
            this.cur.annotationScope = true;
            this.cur.annotationKind = "type alias";
            this.cur.isMethod = false;
            if (classScope) {
                this.cur.classScope = classScope;
                this.cur.hasFree = true;
                classScope.needsClassdict = true;
                this.addDef("__classdict__", USE, s.lineno);
            }
            this.visitArguments(s.args, s.lineno);
            this.visitExpr(s.value);
            this.exitBlock();
            if (s.type_params.length) this.exitBlock();
            break;
        }
        case "Delete":
            this.SEQExpr(s.targets);
            break;
        case "Assign":
            this.SEQExpr(s.targets);
            this.visitExpr(s.value);
            break;
        case "AnnAssign":
            if (s.target._type == "Name") {
                e_name = s.target;
                name = Sk.mangleName(this.curClass, e_name.id).v;
                name = Sk.fixReserved(name);
                cur = this.cur.symFlags[name];
                if ((cur & (DEF_GLOBAL | DEF_NONLOCAL) )
                    && (this.global != this.cur.symFlags) // TODO
                    && (s.simple)) {
                    throw new Sk.builtin.SyntaxError("annotated name '"+ name +"' can't be global", this.filename, s.lineno);
                }
                if (s.simple) {
                    this.addDef(new Sk.builtin.str(name), DEF_ANNOT | DEF_LOCAL, s.lineno);
                } else if (s.value) {
                    this.addDef(new Sk.builtin.str(name), DEF_LOCAL, s.lineno);
                }
            } else {
                this.visitExpr(s.target);
            }
            this.visitAnnotation(s.annotation, s);
            if (s.value) {
                this.visitExpr(s.value);
            }
            break;
        case "AugAssign":
            this.visitExpr(s.target);
            this.visitExpr(s.value);
            break;
        case "Print":
            if (s.dest) {
                this.visitExpr(s.dest);
            }
            this.SEQExpr(s.values);
            break;
        case "For":
            this.visitExpr(s.target);
            this.visitExpr(s.iter);
            this.SEQStmt(s.body);
            if (s.orelse) {
                this.SEQStmt(s.orelse);
            }
            break;
        case "While":
            this.visitExpr(s.test);
            this.SEQStmt(s.body);
            if (s.orelse) {
                this.SEQStmt(s.orelse);
            }
            break;
        case "If":
            this.visitExpr(s.test);
            this.SEQStmt(s.body);
            if (s.orelse) {
                this.SEQStmt(s.orelse);
            }
            break;
        case "LegacyRaise":
        case "Raise":
            if (s.exc) {
                this.visitExpr(s.exc);
                // Our hacked AST supports both Python 2 (inst, tback)
                // and Python 3 (cause) versions of the Raise statement
                if (s.inst) {
                    this.visitExpr(s.inst);
                    if (s.tback) {
                        this.visitExpr(s.tback);
                    }
                }
                if (s.cause) {
                    this.visitExpr(s.cause);
                }
            }
            break;
        case "Assert":
            this.visitExpr(s.test);
            if (s.msg) {
                this.visitExpr(s.msg);
            }
            break;
        case "Import":
        case "ImportFrom":
            this.visitAlias(s.names, s.lineno);
            break;
        case "Global":
            nameslen = s.names.length;
            for (i = 0; i < nameslen; ++i) {
                name = Sk.mangleName(this.curClass, s.names[i]).v;
                name = Sk.fixReserved(name);
                cur = this.cur.symFlags[name];
                if (cur & (DEF_LOCAL | USE)) {
                    if (cur & DEF_LOCAL) {
                        throw new Sk.builtin.SyntaxError("name '" + name + "' is assigned to before global declaration", this.filename, s.lineno);
                    }
                    else {
                        throw new Sk.builtin.SyntaxError("name '" + name + "' is used prior to global declaration", this.filename, s.lineno);
                    }
                }
                this.addDef(new Sk.builtin.str(name), DEF_GLOBAL, s.lineno);
            }
            break;
        case "Nonlocal":
            nameslen = s.names.length;
            for (i = 0; i < nameslen; ++i) {
                name = Sk.mangleName(this.curClass, s.names[i]).v;
                name = Sk.fixReserved(name);
                cur = this.cur.symFlags[name];
                if (cur & (DEF_PARAM | DEF_LOCAL | USE | DEF_ANNOT)) {
                    if (cur & DEF_PARAM) {
                        throw new Sk.builtin.SyntaxError(
                            "name '" + name + "' is parameter and nonlocal",
                            this.filename,
                            s.lineno
                        );
                    } else if (cur & USE) {
                        throw new Sk.builtin.SyntaxError(
                            "name '" + name + "' is used prior to nonlocal declaration",
                            this.filename,
                            s.lineno
                        );
                    } else if (cur & DEF_ANNOT) {
                        throw new Sk.builtin.SyntaxError(
                            "annotated name '" + name + "' can't be nonlocal",
                            this.filename,
                            s.lineno
                        );
                    } else {
                        // DEF_LOCAL
                        throw new Sk.builtin.SyntaxError(
                            "name '" + name + "' is assigned to before nonlocal declaration",
                            this.filename,
                            s.lineno
                        );
                    }
                }
                this.addDef(new Sk.builtin.str(name), DEF_NONLOCAL, s.lineno);
            }
            break;
        case "Expr":
            if (s.value._type === "Name" && s.value.id === "debugger") break;
            this.visitExpr(s.value);
            break;
        case "Pass":
        case "Break":
        case "Continue":
        case "Debugger":
            // nothing
            break;
        case "With":
            VISIT_SEQ(this.visit_withitem.bind(this), s.items);
            VISIT_SEQ(this.visitStmt.bind(this), s.body);
            break;

        case "TryStar":
        case "Try":
            if (s._type === "TryStar" && !Sk.__future__.python3) throw new Sk.builtin.SyntaxError("invalid syntax", this.filename, s.lineno);
            this.SEQStmt(s.body);
            this.visitExcepthandlers(s.handlers)
            this.SEQStmt(s.orelse);
            this.SEQStmt(s.finalbody);
            break;

        default:
            throw new Sk.builtin.SyntaxError(s._type + " is not supported by the Skulpt compiler", this.filename, s.lineno);
    }
    parent.inConditionalBlock = inConditional;
};

SymbolTable.prototype.visit_withitem = function(item) {
    this.visitExpr(item.context_expr);
    if (item.optional_vars) {
        this.visitExpr(item.optional_vars);
    }
}


function VISIT_SEQ(visitFunc, seq) {
    var i;
    for (i = 0; i < seq.length; i++) {
        var elt = seq[i];
        visitFunc(elt)
    }
}

SymbolTable.prototype.visitExpr = function (e) {
    var i;
    Sk.asserts.assert(e !== undefined, "visitExpr called with undefined");
    if (this.cur.annotationScope && ["Yield", "YieldFrom", "Await", "NamedExpr"].includes(e._type)) {
        const name = { Yield: "yield expression", YieldFrom: "yield expression", Await: "await expression", NamedExpr: "named expression" }[e._type];
        throw new Sk.builtin.SyntaxError(name + " cannot be used within " + (this.cur.annotationKind === "type alias" ? "a type alias" : this.cur.annotationKind || "an annotation"), this.filename, e.lineno);
    }
    // console.log("  e: ", e._type);
    switch (e._type) {
        case "NamedExpr":
            this.visitNamedExpr(e);
            break;
        case "BoolOp":
            this.SEQExpr(e.values);
            break;
        case "BinOp":
            this.visitExpr(e.left);
            this.visitExpr(e.right);
            break;
        case "UnaryOp":
            this.visitExpr(e.operand);
            break;
        case "Lambda":
            if (e.args.defaults) {
                this.SEQExpr(e.args.defaults);
                this.SEQExpr(e.args.kw_defaults);
            }
            this.enterBlock("lambda", FunctionBlock, e, e.lineno);
            this.visitArguments(e.args, e.lineno);
            this.visitExpr(e.body);
            this.exitBlock();
            break;
        case "IfExp":
            this.visitExpr(e.test);
            this.visitExpr(e.body);
            this.visitExpr(e.orelse);
            break;
        case "Dict":
            this.SEQExpr(e.keys);
            this.SEQExpr(e.values);
            break;
        case "DictComp":
            this.visitComprehensionScope(e, "dictcomp", e.value, e.key);
            break;
        case "SetComp":
            this.visitComprehensionScope(e, "setcomp", e.elt);
            break;
        case "ListComp":
            if (Sk.__future__.python3) {
                this.visitComprehensionScope(e, "listcomp", e.elt);
            } else {
                this.newTmpname(e.lineno);
                this.visitExpr(e.elt);
                this.visitComprehension(e.generators, 0);
            }
            break;
        case "GeneratorExp":
            this.visitGenexp(e);
            break;
        case "YieldFrom":
        case "Yield":
            if (this.cur.comprehension) {
                throw new Sk.builtin.SyntaxError("'yield' inside " + this.cur.comprehension, this.filename, e.lineno);
            }
            if (e.value) {
                this.visitExpr(e.value);
            }
            this.cur.generator = true;
            if (this.cur.returnsValue && !Sk.__future__.python3) {
                throw new Sk.builtin.SyntaxError("'return' with argument inside generator", this.filename);
            }
            break;
        case "Compare":
            this.visitExpr(e.left);
            this.SEQExpr(e.comparators);
            break;
        case "Call":
            this.visitExpr(e.func);
            if (e.args) {
                for (let a of e.args) {
                    if (a._type === "Starred") {
                        this.visitExpr(a.value);
                    } else {
                        this.visitExpr(a);
                    }
                }
            }
            this.visitKeywords(e.keywords);
            break;
        case "Constant":
            break;
        case "TemplateStr":
            if (!(this.flags & 0x1000000)) throw new Sk.builtin.SyntaxError("TemplateStr is not supported by the Skulpt compiler", this.filename, e.lineno);
        case "JoinedStr":
            for (let s of e.values) {
                this.visitExpr(s);
            }
            break;
        case "Interpolation":
        case "FormattedValue":
            this.visitExpr(e.value);
            if (e.format_spec) {
                this.visitExpr(e.format_spec);
            }
            break;
        case "Attribute":
            if (e.attr === "__debug__" && e.ctx._type !== "Load") {
                throw new Sk.builtin.SyntaxError("cannot " + (e.ctx._type === "Del" ? "delete" : "assign to") + " __debug__", this.filename, e.lineno);
            }
            this.visitExpr(e.value);
            break;
        case "Subscript":
            this.visitExpr(e.value);
            this.visitSlice(e.slice);
            break;
        case "Name":
            if (e.id === "__debug__" && e.ctx._type === "Del") {
                throw new Sk.builtin.SyntaxError("cannot delete __debug__", this.filename, e.lineno);
            }
            this.addDef(e.id, e.ctx._type === "Load" ? USE : DEF_LOCAL, e.lineno);
            if (e.ctx._type === "Load" && this.cur.blockType === FunctionBlock && e.id === "super") {
                this.addDef("__class__", USE, e.lineno);
            }
            break;
        case "NameConstant":
            break;
        case "List":
        case "Tuple":
        case "Set":
            this.SEQExpr(e.elts);
            break;
        case "Starred":
            this.visitExpr(e.value);
            break;
        case "Ellipsis":
            break;
        default:
            throw new Sk.builtin.SyntaxError(e._type + " is not supported by the Skulpt compiler", this.filename, e.lineno);
    }
};

SymbolTable.prototype.visitComprehension = function (lcs, startAt) {
    if (lcs.some(lc => lc.is_async)) throw new Sk.builtin.SyntaxError("Async comprehensions are not supported by the Skulpt compiler", this.filename);
    var lc;
    var i;
    var len = lcs.length;
    for (i = startAt; i < len; ++i) {
        lc = lcs[i];
        this.cur.compIterTarget = true;
        this.visitExpr(lc.target);
        this.cur.compIterTarget = false;
        this.cur.compIterExpr++;
        this.visitExpr(lc.iter);
        this.cur.compIterExpr--;
        this.SEQExpr(lc.ifs);
    }
};

SymbolTable.prototype.visitAlias = function (names, lineno) {
    /* Compute store_name, the name actually bound by the import
     operation.  It is diferent than a->name when a->name is a
     dotted package name (e.g. spam.eggs)
     */
    var dot;
    var storename;
    var name;
    var a;
    var i;
    for (i = 0; i < names.length; ++i) {
        a = names[i];
        name = a.asname === null ? a.name : a.asname;
        storename = name;
        dot = name.indexOf(".");
        if (dot !== -1) {
            storename = name.substr(0, dot);
        }
        if (name !== "*") {
            this.addDef(new Sk.builtin.str(storename), DEF_IMPORT, lineno);
        }
        else {
            if (this.cur.blockType !== ModuleBlock) {
                throw new Sk.builtin.SyntaxError("import * only allowed at module level", this.filename);
            }
        }
    }
};

SymbolTable.prototype.visitGenexp = function (e) {
    this.visitComprehensionScope(e, "genexpr", e.elt);
};

// CPython symtable_handle_namedexpr / symtable_extend_namedexpr_scope.
// A comprehension assignment binds in the nearest enclosing function/module,
// while iteration variables and iterable expressions have stricter rules.
SymbolTable.prototype.visitNamedExpr = function (e) {
    if (this.cur.compIterExpr) {
        throw new Sk.builtin.SyntaxError("assignment expression cannot be used in a comprehension iterable expression", this.filename, e.lineno);
    }
    if (this.cur.comprehension) {
        const name = e.target.id;
        const mangled = Sk.fixReserved(Sk.mangleName(this.curClass, name).v);
        for (const scope of [this.cur].concat(this.stack.slice().reverse())) {
            if (scope.annotationKind === "type alias") {
                throw new Sk.builtin.SyntaxError("assignment expression within a comprehension cannot be used in a type alias", this.filename, e.lineno);
            }
            if (scope.annotationKind === "generic" || ["a TypeVar", "a TypeVarTuple", "a ParamSpec"].some(kind => (scope.annotationKind || "").startsWith(kind))) {
                throw new Sk.builtin.SyntaxError("assignment expression within a comprehension cannot be used " +
                    (scope.annotationKind === "generic" ? "within the definition of a generic" : "in " + (scope.annotationKind.startsWith("a ParamSpec") ? "a ParamSpec default" : scope.annotationKind.startsWith("a TypeVarTuple") ? "a TypeVarTuple default" : "a TypeVar bound")), this.filename, e.lineno);
            }
            if (scope.annotationScope) continue;
            const flags = scope.symFlags[mangled] || 0;
            if (scope.comprehension) {
                if ((flags & DEF_COMP_ITER) && (flags & DEF_LOCAL)) {
                    throw new Sk.builtin.SyntaxError("assignment expression cannot rebind comprehension iteration variable '" + name + "'", this.filename, e.lineno);
                }
                continue;
            }
            if (scope.blockType === FunctionBlock) {
                this.addDef(name, flags & DEF_GLOBAL ? DEF_GLOBAL : DEF_NONLOCAL, e.lineno);
                this.addDef(name, DEF_LOCAL, e.lineno, scope);
                break;
            }
            if (scope.blockType === ModuleBlock) {
                this.addDef(name, DEF_GLOBAL, e.lineno);
                this.addDef(name, DEF_GLOBAL, e.lineno, scope);
                break;
            }
            if (scope.blockType === ClassBlock) {
                throw new Sk.builtin.SyntaxError("assignment expression within a comprehension cannot be used in a class body", this.filename, e.lineno);
            }
        }
    }
    this.visitExpr(e.value);
    this.visitExpr(e.target);
};

// CPython symtable_handle_comprehension evaluates only the outer iterable in
// the enclosing scope. The rest belongs to a separate logical function block,
// even when the compiler later inlines a list/set/dict comprehension.
SymbolTable.prototype.visitComprehensionScope = function (e, name, value, key) {
    var outermost = e.generators[0];
    this.cur.compIterExpr++;
    this.visitExpr(outermost.iter);
    this.cur.compIterExpr--;
    this.enterBlock(name, FunctionBlock, e, e.lineno);
    this.cur.comprehension = name;
    this.cur.generator = name === "genexpr";
    this.addDef(new Sk.builtin.str(".0"), DEF_PARAM, e.lineno);
    this.cur.compIterTarget = true;
    this.visitExpr(outermost.target);
    this.cur.compIterTarget = false;
    this.SEQExpr(outermost.ifs);
    this.visitComprehension(e.generators, 1);
    if (key) {
        this.visitExpr(key);
    }
    this.visitExpr(value);
    this.exitBlock();
};

SymbolTable.prototype.visitExcepthandlers = function (handlers) {
    var i, eh;
    for (i = 0; eh = handlers[i]; ++i) {
        if (eh.type) {
            this.visitExpr(eh.type);
        }
        if (eh.name) {
            this.addDef(eh.name, DEF_LOCAL, eh.lineno);
        } else if (eh.target) {
            this.visitExpr(eh.target);
        }
        this.SEQStmt(eh.body);
    }
};

function _dictUpdate (a, b) {
    var kb;
    for (kb in b) {
        a[kb] = b[kb];
    }
}

SymbolTable.prototype.analyzeBlock = function (ste, bound, free, global) {
    var c;
    var i;
    var childlen;
    var allfree;
    var flags;
    var name;
    var local = {};
    var scope = {};
    var newglobal = {};
    var newbound = {};
    var newfree = {};

    if (ste.blockType == ClassBlock) {
        _dictUpdate(newglobal, global);
        if (bound) {
            _dictUpdate(newbound, bound);
        }
        newbound.__class__ = null;
        newbound.__classdict__ = null;
        if (ste.hasConditionalAnnotations) newbound.__conditional_annotations__ = null;
    }

    for (name in ste.symFlags) {
        flags = ste.symFlags[name];
        this.analyzeName(ste, scope, name, flags, bound, local, free, global);
    }

    if (ste.blockType !== ClassBlock) {
        if (bound) {
            _dictUpdate(newbound, bound);
        }
        if (ste.blockType === FunctionBlock) {
            _dictUpdate(newbound, local);
        }
        _dictUpdate(newglobal, global);
    }

    allfree = {};
    childlen = ste.children.length;
    for (i = 0; i < childlen; ++i) {
        c = ste.children[i];
        this.analyzeChildBlock(c, newbound, newfree, newglobal, allfree);
        if (c.hasFree || c.childHasFree) {
            ste.childHasFree = true;
        }
    }

    _dictUpdate(newfree, allfree);
    if (ste.blockType === FunctionBlock) {
        this.analyzeCells(ste, scope, newfree);
    }
    if (ste.blockType === ClassBlock && newfree.__class__ !== undefined) {
        delete newfree.__class__;
        ste.needsClassClosure = true;
    }
    if (ste.blockType === ClassBlock && newfree.__classdict__ !== undefined) {
        delete newfree.__classdict__;
        ste.needsClassdict = true;
    }
    if (ste.blockType === ClassBlock && ste.hasConditionalAnnotations) delete newfree.__conditional_annotations__;
    this.updateSymbols(ste, ste.symFlags, scope, bound, newfree, ste.blockType === ClassBlock);

    _dictUpdate(free, newfree);
};

SymbolTable.prototype.analyzeChildBlock = function (entry, bound, free, global, childFree) {
    var tempGlobal;
    var tempFree;
    var tempBound = {};
    _dictUpdate(tempBound, bound);
    tempFree = {};
    _dictUpdate(tempFree, free);
    tempGlobal = {};
    _dictUpdate(tempGlobal, global);

    this.analyzeBlock(entry, tempBound, tempFree, tempGlobal);
    _dictUpdate(childFree, tempFree);
};

SymbolTable.prototype.analyzeCells = function (ste, scope, free) {
    var flags;
    var name;
    for (name in scope) {
        flags = scope[name];
        if (flags !== LOCAL) {
            continue;
        }
        if (free[name] === undefined) {
            continue;
        }
        scope[name] = CELL;
        delete free[name];
        ste.hasCells = true;
    }
};

/**
 * store scope info back into the st symbols dict. symbols is modified,
 * others are not.
 */
SymbolTable.prototype.updateSymbols = function (ste, symbols, scope, bound, free, classflag) {
    var i;
    var o;
    var freeValue;
    var w;
    var flags;
    var name;
    for (name in symbols) {
        flags = symbols[name];
        w = scope[name];
        flags |= w << SCOPE_OFF;
        symbols[name] = flags;
    }

    freeValue = FREE << SCOPE_OFF;
    for (name in free) {
        o = symbols[name];
        if (o !== undefined) {
            // it could be a free variable in a method of the class that has
            // the same name as a local or global in the class scope
            if (classflag && (o & (DEF_BOUND | DEF_GLOBAL))) {
                i = o | DEF_FREE_CLASS;
                symbols[name] = i;
            }
            // else it's not free, probably a cell
            continue;
        }
        if (bound[name] === undefined) {
            continue;
        }
        symbols[name] = freeValue;
        // This scope needs to pass through this free variable to children.
        // In CPython, the compiler scans ste_symbols for FREE scope to build co_freevars.
        // Skulpt's compiler uses hasFree as a shortcut, so we set it here.
        // Class bodies already relay their enclosing cells through $free.
        if (!classflag) {
            ste.hasFree = true;
        }
    }
};

SymbolTable.prototype.analyzeName = function (ste, dict, name, flags, bound, local, free, global) {
    if (flags & DEF_GLOBAL) {
        if (flags & DEF_NONLOCAL) {
            throw new Sk.builtin.SyntaxError("name '" + name + "' is nonlocal and global", this.filename, ste.lineno);
        }
        if (flags & DEF_PARAM) {
            throw new Sk.builtin.SyntaxError("name '" + name + "' is local and global", this.filename, ste.lineno);
        }
        dict[name] = GLOBAL_EXPLICIT;
        global[name] = null;
        if (bound && bound[name] !== undefined) {
            delete bound[name];
        }
        return;
    }
    if (flags & DEF_NONLOCAL) {
        if (!bound) {
            throw new Sk.builtin.SyntaxError(
                "nonlocal declaration not allowed at module level",
                this.filename,
                ste.lineno
            );
        }
        if (bound[name] === undefined) {
            throw new Sk.builtin.SyntaxError("no binding for nonlocal '" + name + "' found", this.filename, ste.lineno);
        }
        if (bound[name] === "type parameter") {
            throw new Sk.builtin.SyntaxError("nonlocal binding not allowed for type parameter '" + name + "'", this.filename, ste.lineno);
        }
        dict[name] = FREE;
        ste.hasFree = true;
        free[name] = null;
        return;
    }
    if (flags & DEF_BOUND) {
        dict[name] = LOCAL;
        local[name] = flags & DEF_TYPE_PARAM ? "type parameter" : null;
        delete global[name];
        return;
    }

    // analyze_name: class annotation scopes use class/globals for a class-bound
    // name, even if an enclosing function binds the same name.
    if (ste.classScope) {
        const classFlags = ste.classScope.symFlags[name] || 0;
        if (classFlags & DEF_GLOBAL) {
            dict[name] = GLOBAL_EXPLICIT;
            return;
        }
        if (classFlags & DEF_BOUND && !(classFlags & DEF_NONLOCAL)) {
            dict[name] = GLOBAL_IMPLICIT;
            return;
        }
    }

    if (bound && bound[name] !== undefined) {
        dict[name] = FREE;
        ste.hasFree = true;
        free[name] = null;
    }
    else if (global && global[name] !== undefined) {
        dict[name] = GLOBAL_IMPLICIT;
    }
    else {
        if (ste.isNested) {
            ste.hasFree = true;
        }
        dict[name] = GLOBAL_IMPLICIT;
    }
};

SymbolTable.prototype.analyze = function () {
    var free = {};
    var global = {};
    this.analyzeBlock(this.top, null, free, global);
};

/**
 * @param {Object} ast
 * @param {string} filename
 */
Sk.symboltable = function (ast, filename, flags) {
    var i;
    var ret = new SymbolTable(filename, flags);

    ret.enterBlock("top", ModuleBlock, ast, 0);
    ret.top = ret.cur;

    //print(Sk.astDump(ast));
    // CPython symtable_visit_mod distinguishes module suites from expressions.
    if (ast._type === "Expression") {
        ret.visitExpr(ast.body);
    } else {
        for (i = 0; i < ast.body.length; ++i) {
            ret.visitStmt(ast.body[i]);
        }
    }

    ret.exitBlock();

    ret.analyze();

    return ret;
};

Sk.dumpSymtab = function (st) {
    var pyBoolStr = function (b) {
        return b ? "True" : "False";
    }
    var pyList = function (l) {
        var i;
        var ret = [];
        for (i = 0; i < l.length; ++i) {
            ret.push(new Sk.builtin.str(l[i])["$r"]().v);
        }
        return "[" + ret.join(", ") + "]";
    };
    var getIdents = function (obj, indent) {
        var ns;
        var j;
        var sub;
        var nsslen;
        var nss;
        var info;
        var i;
        var objidentslen;
        var objidents;
        var ret;
        if (indent === undefined) {
            indent = "";
        }
        ret = "";
        ret += indent + "Sym_type: " + obj.get_type() + "\n";
        ret += indent + "Sym_name: " + obj.get_name() + "\n";
        ret += indent + "Sym_lineno: " + obj.get_lineno() + "\n";
        ret += indent + "Sym_nested: " + pyBoolStr(obj.is_nested()) + "\n";
        ret += indent + "Sym_haschildren: " + pyBoolStr(obj.has_children()) + "\n";
        if (obj.get_type() === "class") {
            ret += indent + "Class_methods: " + pyList(obj.get_methods()) + "\n";
        }
        else if (obj.get_type() === "function") {
            ret += indent + "Func_params: " + pyList(obj.get_parameters()) + "\n";
            ret += indent + "Func_locals: " + pyList(obj.get_locals()) + "\n";
            ret += indent + "Func_globals: " + pyList(obj.get_globals()) + "\n";
            ret += indent + "Func_frees: " + pyList(obj.get_frees()) + "\n";
        }
        ret += indent + "-- Identifiers --\n";
        objidents = obj.get_identifiers();
        objidentslen = objidents.length;
        for (i = 0; i < objidentslen; ++i) {
            info = obj.lookup(objidents[i]);
            ret += indent + "name: " + info.get_name() + "\n";
            ret += indent + "  is_referenced: " + pyBoolStr(info.is_referenced()) + "\n";
            ret += indent + "  is_imported: " + pyBoolStr(info.is_imported()) + "\n";
            ret += indent + "  is_parameter: " + pyBoolStr(info.is_parameter()) + "\n";
            ret += indent + "  is_global: " + pyBoolStr(info.is_global()) + "\n";
            ret += indent + "  is_declared_global: " + pyBoolStr(info.is_declared_global()) + "\n";
            ret += indent + "  is_local: " + pyBoolStr(info.is_local()) + "\n";
            ret += indent + "  is_free: " + pyBoolStr(info.is_free()) + "\n";
            ret += indent + "  is_assigned: " + pyBoolStr(info.is_assigned()) + "\n";
            ret += indent + "  is_namespace: " + pyBoolStr(info.is_namespace()) + "\n";
            nss = info.get_namespaces();
            nsslen = nss.length;
            ret += indent + "  namespaces: [\n";
            sub = [];
            for (j = 0; j < nsslen; ++j) {
                ns = nss[j];
                sub.push(getIdents(ns, indent + "    "));
            }
            ret += sub.join("\n");
            ret += indent + "  ]\n";
        }
        return ret;
    };
    return getIdents(st.top, "");
};

Sk.exportSymbol("Sk.symboltable", Sk.symboltable);
Sk.exportSymbol("Sk.dumpSymtab", Sk.dumpSymtab);
