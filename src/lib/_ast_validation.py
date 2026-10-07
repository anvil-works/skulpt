# Python-2.0 license. Procedural validation follows CPython 3.14 Python/ast.c.
from _ast import *


def _positions(node):
    if not hasattr(node, 'lineno'): return
    line, column = node.lineno, node.col_offset
    end_line = node.end_lineno if node.end_lineno is not None else line
    end_column = node.end_col_offset if node.end_col_offset is not None else column
    if line > end_line:
        raise ValueError(f'AST node line range ({line}, {end_line}) is not valid')
    if (line < 0 and end_line != line) or (column < 0 and end_column != column):
        raise ValueError(f'AST node column range ({column}, {end_column}) for line range ({line}, {end_line}) is not valid')
    if line == end_line and column > end_column:
        raise ValueError(f'line {line}, column {column}-{end_column} is not a valid range')


def _name(name):
    if name in ('None', 'True', 'False'):
        raise ValueError(f"identifier field can't represent '{name}' constant")


def _nonempty(seq, field, owner):
    if not seq: raise ValueError(f'empty {field} on {owner}')


def _exprs(nodes, context=Load, null_ok=False):
    for node in nodes:
        if node is None:
            if null_ok: continue
            raise ValueError('None disallowed in expression list')
        _expr(node, context)


def _arguments(args):
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        _positions(arg)
        if arg.annotation is not None: _expr(arg.annotation)
    for arg in (args.vararg, args.kwarg):
        if arg is not None and arg.annotation is not None: _expr(arg.annotation)
    if len(args.defaults) > len(args.posonlyargs) + len(args.args):
        raise ValueError('more positional defaults than args on arguments')
    if len(args.kw_defaults) != len(args.kwonlyargs):
        raise ValueError('length of kwonlyargs is not the same as kw_defaults on arguments')
    _exprs(args.defaults)
    _exprs(args.kw_defaults, null_ok=True)


def _comprehension(generators):
    if not generators: raise ValueError('comprehension with no generators')
    for comp in generators:
        _expr(comp.target, Store)
        _expr(comp.iter)
        _exprs(comp.ifs)


def _keywords(keywords):
    for keyword in keywords: _expr(keyword.value)


def _expr(node, context=Load):
    _positions(node)
    if isinstance(node, Name): _name(node.id)
    if isinstance(node, (Attribute, Subscript, Starred, Name, List, Tuple)):
        if not isinstance(node.ctx, context):
            raise ValueError(f'expression must have {context.__name__} context but has {type(node.ctx).__name__} instead')
    elif context is not Load:
        raise ValueError(f"expression which can't be assigned to in {context.__name__} context")
    if isinstance(node, BoolOp):
        if len(node.values) < 2: raise ValueError('BoolOp with less than 2 values')
        _exprs(node.values)
    elif isinstance(node, BinOp):
        _expr(node.left); _expr(node.right)
    elif isinstance(node, UnaryOp): _expr(node.operand)
    elif isinstance(node, Lambda):
        _arguments(node.args); _expr(node.body)
    elif isinstance(node, IfExp):
        _expr(node.test); _expr(node.body); _expr(node.orelse)
    elif isinstance(node, Dict):
        if len(node.keys) != len(node.values): raise ValueError("Dict doesn't have the same number of keys as values")
        _exprs(node.keys, null_ok=True); _exprs(node.values)
    elif isinstance(node, Set): _exprs(node.elts)
    elif isinstance(node, (ListComp, SetComp, GeneratorExp)):
        _comprehension(node.generators); _expr(node.elt)
    elif isinstance(node, DictComp):
        _comprehension(node.generators); _expr(node.key); _expr(node.value)
    elif isinstance(node, Yield):
        if node.value is not None: _expr(node.value)
    elif isinstance(node, (YieldFrom, Await)): _expr(node.value)
    elif isinstance(node, Compare):
        if not node.comparators: raise ValueError('Compare with no comparators')
        if len(node.comparators) != len(node.ops): raise ValueError('Compare has a different number of comparators and operands')
        _exprs(node.comparators); _expr(node.left)
    elif isinstance(node, Call):
        _expr(node.func); _exprs(node.args); _keywords(node.keywords)
    elif isinstance(node, (JoinedStr, TemplateStr)): _exprs(node.values)
    elif isinstance(node, (FormattedValue, Interpolation)):
        _expr(node.value)
        if node.format_spec is not None: _expr(node.format_spec)
    elif isinstance(node, Attribute): _expr(node.value)
    elif isinstance(node, Subscript):
        _expr(node.slice); _expr(node.value)
    elif isinstance(node, Starred): _expr(node.value, context)
    elif isinstance(node, Slice):
        for part in (node.lower, node.upper, node.step):
            if part is not None: _expr(part)
    elif isinstance(node, (List, Tuple)): _exprs(node.elts, context)
    elif isinstance(node, NamedExpr):
        if not isinstance(node.target, Name): raise TypeError('NamedExpr target must be a Name')
        _expr(node.value)


def _type_params(params):
    for param in params:
        _positions(param); _name(param.name)
        if isinstance(param, TypeVar) and param.bound is not None: _expr(param.bound)
        if param.default_value is not None: _expr(param.default_value)


def _body(body, owner):
    _nonempty(body, 'body', owner)
    _stmts(body)


def _stmt(node):
    _positions(node)
    owner = type(node).__name__
    if isinstance(node, (FunctionDef, AsyncFunctionDef)):
        _body(node.body, owner); _name(node.name); _type_params(node.type_params)
        _arguments(node.args); _exprs(node.decorator_list)
        if node.returns is not None: _expr(node.returns)
    elif isinstance(node, ClassDef):
        _body(node.body, owner); _name(node.name); _type_params(node.type_params)
        _exprs(node.bases); _keywords(node.keywords); _exprs(node.decorator_list)
    elif isinstance(node, Return):
        if node.value is not None: _expr(node.value)
    elif isinstance(node, (Delete, Assign)):
        _nonempty(node.targets, 'targets', owner)
        _exprs(node.targets, Del if isinstance(node, Delete) else Store)
        if isinstance(node, Assign): _expr(node.value)
    elif isinstance(node, AugAssign):
        _expr(node.target, Store); _expr(node.value)
    elif isinstance(node, AnnAssign):
        if not isinstance(node.target, Name) and node.simple: raise TypeError('AnnAssign with simple non-Name target')
        _expr(node.target, Store)
        if node.value is not None: _expr(node.value)
        _expr(node.annotation)
    elif isinstance(node, TypeAlias):
        if not isinstance(node.name, Name): raise TypeError('TypeAlias with non-Name name')
        _expr(node.name, Store); _type_params(node.type_params); _expr(node.value)
    elif isinstance(node, (For, AsyncFor)):
        _expr(node.target, Store); _expr(node.iter); _body(node.body, owner); _stmts(node.orelse)
    elif isinstance(node, (While, If)):
        _expr(node.test); _body(node.body, owner); _stmts(node.orelse)
    elif isinstance(node, (With, AsyncWith)):
        _nonempty(node.items, 'items', owner)
        for item in node.items:
            _expr(item.context_expr)
            if item.optional_vars is not None: _expr(item.optional_vars, Store)
        _body(node.body, owner)
    elif isinstance(node, Match):
        raise NotImplementedError('edited pattern AST validation follows with pattern compilation')
    elif isinstance(node, Raise):
        if node.exc is not None:
            _expr(node.exc)
            if node.cause is not None: _expr(node.cause)
        elif node.cause is not None: raise ValueError('Raise with cause but no exception')
    elif isinstance(node, (Try, TryStar)):
        _body(node.body, owner)
        if not node.handlers and not node.finalbody: raise ValueError(f'{owner} has neither except handlers nor finalbody')
        if not node.handlers and node.orelse: raise ValueError(f'{owner} has orelse but no except handlers')
        for handler in node.handlers:
            if isinstance(node, Try): _positions(handler)
            if handler.type is not None: _expr(handler.type)
            if isinstance(node, Try) and handler.name is not None: _name(handler.name)
            _body(handler.body, 'ExceptHandler')
        _stmts(node.finalbody); _stmts(node.orelse)
    elif isinstance(node, Assert):
        _expr(node.test)
        if node.msg is not None: _expr(node.msg)
    elif isinstance(node, (Import, ImportFrom)):
        if isinstance(node, ImportFrom) and node.level is not None and node.level < 0: raise ValueError('Negative ImportFrom level')
        _nonempty(node.names, 'names', owner)
        for alias in node.names:
            _name(alias.name)
            if alias.asname is not None: _name(alias.asname)
    elif isinstance(node, (Global, Nonlocal)): _nonempty(node.names, 'names', owner)
    elif isinstance(node, Expr): _expr(node.value)


def _stmts(nodes):
    for node in nodes:
        if node is None: raise ValueError('None disallowed in statement list')
        _stmt(node)


def _validate(tree):
    if isinstance(tree, (Module, Interactive)): _stmts(tree.body)
    elif isinstance(tree, Expression): _expr(tree.body)
    else: raise TypeError('expected Module, Interactive or Expression AST')
