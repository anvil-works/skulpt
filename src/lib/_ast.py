# CPython 3.14 Parser/Python.asdl at 18ef0f0cb52; Python-2.0 license.
# Public classes share ast's namespace, as in CPython's generated backend.
from _ast_native import _parse_tree, _register_type, _compile_tree, _int_field, _list_size, _list_item
PyCF_ONLY_AST = 0x400
PyCF_TYPE_COMMENTS = 0x1000
PyCF_ALLOW_TOP_LEVEL_AWAIT = 0x2000
PyCF_OPTIMIZED_AST = 0x8000

class AST:
    _fields = ()
    _attributes = ()
    def __init__(self, *args, **kwargs):
        fields = self._fields
        if len(args) > len(fields):
            raise TypeError(f"{type(self).__name__} constructor takes at most {len(fields)} positional arguments")
        for name, value in zip(fields, args):
            if name in kwargs:
                raise TypeError(f"{type(self).__name__} got multiple values for argument {name!r}")
            setattr(self, name, value)
        for name in fields[len(args):]:
            if name not in kwargs and getattr(self._field_types.get(name), '__origin__', None) is list:
                setattr(self, name, [])
            elif name not in kwargs and self._field_types.get(name) is expr_context:
                setattr(self, name, _AST_SINGLETONS['Load'])
        for name, value in kwargs.items():
            setattr(self, name, value)
    def __repr__(self):
        return _repr_ast(self, 3, set())


# Python/Python-ast.c: ast_repr_max_depth and ast_repr_list.
def _repr_ast(node, depth, seen):
    name = type(node).__name__
    if depth <= 0 or id(node) in seen:
        return f"{name}(...)"
    seen.add(id(node))
    try:
        values = []
        for field in type(node)._fields:
            value = getattr(node, field)
            if isinstance(value, (list, tuple)):
                items = value if len(value) <= 2 else (value[0], ..., value[-1])
                parts = [_repr_ast(item, depth - 1, seen) if isinstance(item, AST)
                         else '...' if item is ... and len(value) > 2 else repr(item)
                         for item in items]
                start, end = ('[', ']') if isinstance(value, list) else ('(', ')')
                text = start + ', '.join(parts) + end
            elif isinstance(value, AST):
                text = _repr_ast(value, depth - 1, seen)
            else:
                text = repr(value)
            values.append(f"{field}={text}")
        return f"{name}({', '.join(values)})"
    finally:
        seen.remove(id(node))

AST.__module__ = 'ast'
AST._field_types = {}

# ASDL data is shared by public field metadata and AST conversion/validation.
_AST_SCHEMA = {'mod': ('AST', [], ()),
 'Module': ('mod', [('body', 'stmt', '*'), ('type_ignores', 'type_ignore', '*')], ()),
 'Interactive': ('mod', [('body', 'stmt', '*')], ()),
 'Expression': ('mod', [('body', 'expr', '')], ()),
 'FunctionType': ('mod', [('argtypes', 'expr', '*'), ('returns', 'expr', '')], ()),
 'stmt': ('AST', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'FunctionDef': ('stmt',
                 [('name', 'identifier', ''),
                  ('args', 'arguments', ''),
                  ('body', 'stmt', '*'),
                  ('decorator_list', 'expr', '*'),
                  ('returns', 'expr', '?'),
                  ('type_comment', 'string', '?'),
                  ('type_params', 'type_param', '*')],
                 ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'AsyncFunctionDef': ('stmt',
                      [('name', 'identifier', ''),
                       ('args', 'arguments', ''),
                       ('body', 'stmt', '*'),
                       ('decorator_list', 'expr', '*'),
                       ('returns', 'expr', '?'),
                       ('type_comment', 'string', '?'),
                       ('type_params', 'type_param', '*')],
                      ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'ClassDef': ('stmt',
              [('name', 'identifier', ''),
               ('bases', 'expr', '*'),
               ('keywords', 'keyword', '*'),
               ('body', 'stmt', '*'),
               ('decorator_list', 'expr', '*'),
               ('type_params', 'type_param', '*')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Return': ('stmt',
            [('value', 'expr', '?')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Delete': ('stmt',
            [('targets', 'expr', '*')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Assign': ('stmt',
            [('targets', 'expr', '*'), ('value', 'expr', ''), ('type_comment', 'string', '?')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'TypeAlias': ('stmt',
               [('name', 'expr', ''), ('type_params', 'type_param', '*'), ('value', 'expr', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'AugAssign': ('stmt',
               [('target', 'expr', ''), ('op', 'operator', ''), ('value', 'expr', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'AnnAssign': ('stmt',
               [('target', 'expr', ''),
                ('annotation', 'expr', ''),
                ('value', 'expr', '?'),
                ('simple', 'int', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'For': ('stmt',
         [('target', 'expr', ''),
          ('iter', 'expr', ''),
          ('body', 'stmt', '*'),
          ('orelse', 'stmt', '*'),
          ('type_comment', 'string', '?')],
         ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'AsyncFor': ('stmt',
              [('target', 'expr', ''),
               ('iter', 'expr', ''),
               ('body', 'stmt', '*'),
               ('orelse', 'stmt', '*'),
               ('type_comment', 'string', '?')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'While': ('stmt',
           [('test', 'expr', ''), ('body', 'stmt', '*'), ('orelse', 'stmt', '*')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'If': ('stmt',
        [('test', 'expr', ''), ('body', 'stmt', '*'), ('orelse', 'stmt', '*')],
        ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'With': ('stmt',
          [('items', 'withitem', '*'), ('body', 'stmt', '*'), ('type_comment', 'string', '?')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'AsyncWith': ('stmt',
               [('items', 'withitem', '*'), ('body', 'stmt', '*'), ('type_comment', 'string', '?')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Match': ('stmt',
           [('subject', 'expr', ''), ('cases', 'match_case', '*')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Raise': ('stmt',
           [('exc', 'expr', '?'), ('cause', 'expr', '?')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Try': ('stmt',
         [('body', 'stmt', '*'),
          ('handlers', 'excepthandler', '*'),
          ('orelse', 'stmt', '*'),
          ('finalbody', 'stmt', '*')],
         ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'TryStar': ('stmt',
             [('body', 'stmt', '*'),
              ('handlers', 'excepthandler', '*'),
              ('orelse', 'stmt', '*'),
              ('finalbody', 'stmt', '*')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Assert': ('stmt',
            [('test', 'expr', ''), ('msg', 'expr', '?')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Import': ('stmt',
            [('names', 'alias', '*')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'ImportFrom': ('stmt',
                [('module', 'identifier', '?'), ('names', 'alias', '*'), ('level', 'int', '?')],
                ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Global': ('stmt',
            [('names', 'identifier', '*')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Nonlocal': ('stmt',
              [('names', 'identifier', '*')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Expr': ('stmt',
          [('value', 'expr', '')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Pass': ('stmt', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Break': ('stmt', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Continue': ('stmt', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'expr': ('AST', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'BoolOp': ('expr',
            [('op', 'boolop', ''), ('values', 'expr', '*')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'NamedExpr': ('expr',
               [('target', 'expr', ''), ('value', 'expr', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'BinOp': ('expr',
           [('left', 'expr', ''), ('op', 'operator', ''), ('right', 'expr', '')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'UnaryOp': ('expr',
             [('op', 'unaryop', ''), ('operand', 'expr', '')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Lambda': ('expr',
            [('args', 'arguments', ''), ('body', 'expr', '')],
            ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'IfExp': ('expr',
           [('test', 'expr', ''), ('body', 'expr', ''), ('orelse', 'expr', '')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Dict': ('expr',
          [('keys', 'expr', '?*'), ('values', 'expr', '*')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Set': ('expr', [('elts', 'expr', '*')], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'ListComp': ('expr',
              [('elt', 'expr', ''), ('generators', 'comprehension', '*')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'SetComp': ('expr',
             [('elt', 'expr', ''), ('generators', 'comprehension', '*')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'DictComp': ('expr',
              [('key', 'expr', ''), ('value', 'expr', ''), ('generators', 'comprehension', '*')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'GeneratorExp': ('expr',
                  [('elt', 'expr', ''), ('generators', 'comprehension', '*')],
                  ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Await': ('expr',
           [('value', 'expr', '')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Yield': ('expr',
           [('value', 'expr', '?')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'YieldFrom': ('expr',
               [('value', 'expr', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Compare': ('expr',
             [('left', 'expr', ''), ('ops', 'cmpop', '*'), ('comparators', 'expr', '*')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Call': ('expr',
          [('func', 'expr', ''), ('args', 'expr', '*'), ('keywords', 'keyword', '*')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'FormattedValue': ('expr',
                    [('value', 'expr', ''),
                     ('conversion', 'int', ''),
                     ('format_spec', 'expr', '?')],
                    ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Interpolation': ('expr',
                   [('value', 'expr', ''),
                    ('str', 'constant', ''),
                    ('conversion', 'int', ''),
                    ('format_spec', 'expr', '?')],
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'JoinedStr': ('expr',
               [('values', 'expr', '*')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'TemplateStr': ('expr',
                 [('values', 'expr', '*')],
                 ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Constant': ('expr',
              [('value', 'constant', ''), ('kind', 'string', '?')],
              ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Attribute': ('expr',
               [('value', 'expr', ''), ('attr', 'identifier', ''), ('ctx', 'expr_context', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Subscript': ('expr',
               [('value', 'expr', ''), ('slice', 'expr', ''), ('ctx', 'expr_context', '')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Starred': ('expr',
             [('value', 'expr', ''), ('ctx', 'expr_context', '')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Name': ('expr',
          [('id', 'identifier', ''), ('ctx', 'expr_context', '')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'List': ('expr',
          [('elts', 'expr', '*'), ('ctx', 'expr_context', '')],
          ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Tuple': ('expr',
           [('elts', 'expr', '*'), ('ctx', 'expr_context', '')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'Slice': ('expr',
           [('lower', 'expr', '?'), ('upper', 'expr', '?'), ('step', 'expr', '?')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'expr_context': ('AST', [], ()),
 'Load': ('expr_context', [], ()),
 'Store': ('expr_context', [], ()),
 'Del': ('expr_context', [], ()),
 'boolop': ('AST', [], ()),
 'And': ('boolop', [], ()),
 'Or': ('boolop', [], ()),
 'operator': ('AST', [], ()),
 'Add': ('operator', [], ()),
 'Sub': ('operator', [], ()),
 'Mult': ('operator', [], ()),
 'MatMult': ('operator', [], ()),
 'Div': ('operator', [], ()),
 'Mod': ('operator', [], ()),
 'Pow': ('operator', [], ()),
 'LShift': ('operator', [], ()),
 'RShift': ('operator', [], ()),
 'BitOr': ('operator', [], ()),
 'BitXor': ('operator', [], ()),
 'BitAnd': ('operator', [], ()),
 'FloorDiv': ('operator', [], ()),
 'unaryop': ('AST', [], ()),
 'Invert': ('unaryop', [], ()),
 'Not': ('unaryop', [], ()),
 'UAdd': ('unaryop', [], ()),
 'USub': ('unaryop', [], ()),
 'cmpop': ('AST', [], ()),
 'Eq': ('cmpop', [], ()),
 'NotEq': ('cmpop', [], ()),
 'Lt': ('cmpop', [], ()),
 'LtE': ('cmpop', [], ()),
 'Gt': ('cmpop', [], ()),
 'GtE': ('cmpop', [], ()),
 'Is': ('cmpop', [], ()),
 'IsNot': ('cmpop', [], ()),
 'In': ('cmpop', [], ()),
 'NotIn': ('cmpop', [], ()),
 'comprehension': ('AST',
                   [('target', 'expr', ''),
                    ('iter', 'expr', ''),
                    ('ifs', 'expr', '*'),
                    ('is_async', 'int', '')],
                   ()),
 'excepthandler': ('AST', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'ExceptHandler': ('excepthandler',
                   [('type', 'expr', '?'), ('name', 'identifier', '?'), ('body', 'stmt', '*')],
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'arguments': ('AST',
               [('posonlyargs', 'arg', '*'),
                ('args', 'arg', '*'),
                ('vararg', 'arg', '?'),
                ('kwonlyargs', 'arg', '*'),
                ('kw_defaults', 'expr', '?*'),
                ('kwarg', 'arg', '?'),
                ('defaults', 'expr', '*')],
               ()),
 'arg': ('AST',
         [('arg', 'identifier', ''), ('annotation', 'expr', '?'), ('type_comment', 'string', '?')],
         ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'keyword': ('AST',
             [('arg', 'identifier', '?'), ('value', 'expr', '')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'alias': ('AST',
           [('name', 'identifier', ''), ('asname', 'identifier', '?')],
           ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'withitem': ('AST', [('context_expr', 'expr', ''), ('optional_vars', 'expr', '?')], ()),
 'match_case': ('AST',
                [('pattern', 'pattern', ''), ('guard', 'expr', '?'), ('body', 'stmt', '*')],
                ()),
 'pattern': ('AST', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchValue': ('pattern',
                [('value', 'expr', '')],
                ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchSingleton': ('pattern',
                    [('value', 'constant', '')],
                    ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchSequence': ('pattern',
                   [('patterns', 'pattern', '*')],
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchMapping': ('pattern',
                  [('keys', 'expr', '*'),
                   ('patterns', 'pattern', '*'),
                   ('rest', 'identifier', '?')],
                  ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchClass': ('pattern',
                [('cls', 'expr', ''),
                 ('patterns', 'pattern', '*'),
                 ('kwd_attrs', 'identifier', '*'),
                 ('kwd_patterns', 'pattern', '*')],
                ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchStar': ('pattern',
               [('name', 'identifier', '?')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchAs': ('pattern',
             [('pattern', 'pattern', '?'), ('name', 'identifier', '?')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'MatchOr': ('pattern',
             [('patterns', 'pattern', '*')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'type_ignore': ('AST', [], ()),
 'TypeIgnore': ('type_ignore', [('lineno', 'int', ''), ('tag', 'string', '')], ()),
 'type_param': ('AST', [], ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'TypeVar': ('type_param',
             [('name', 'identifier', ''), ('bound', 'expr', '?'), ('default_value', 'expr', '?')],
             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'ParamSpec': ('type_param',
               [('name', 'identifier', ''), ('default_value', 'expr', '?')],
               ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')),
 'TypeVarTuple': ('type_param',
                  [('name', 'identifier', ''), ('default_value', 'expr', '?')],
                  ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'))}

for _name, (_base, _fields, _attrs) in _AST_SCHEMA.items():
    _names = tuple(field[0] for field in _fields)
    _namespace = {'__module__': 'ast', '_fields': _names, '__match_args__': _names,
                  '_attributes': _attrs}
    _namespace.update({name: None for name, _, mods in _fields if mods.endswith('?')})
    _namespace.update({name: None for name in _attrs if name.startswith('end_')})
    globals()[_name] = type(_name, (globals()[_base],), _namespace)

for _name, (_, _fields, _) in _AST_SCHEMA.items():
    _types = {}
    for _field, _type, _mods in _fields:
        _dtype = {'identifier': str, 'string': str, 'int': int, 'constant': object}.get(_type)
        if _dtype is None: _dtype = globals()[_type]
        for _mod in _mods:
            _dtype = list[_dtype] if _mod == '*' else _dtype | None
        _types[_field] = _dtype
    globals()[_name]._field_types = _types

# CPython parser-produced operator/context nodes and default Load contexts share
# singleton objects. Explicit operator constructors still allocate new objects.
_AST_SINGLETONS = {name: globals()[name]() for name, (base, _, _) in _AST_SCHEMA.items()
                   if base in ('expr_context', 'boolop', 'operator', 'unaryop', 'cmpop')}

def _from_parser(value):
    if isinstance(value, list):
        return [_from_parser(item) for item in value]
    if isinstance(value, dict) and 'py_value' in value:
        return value['py_value']
    if isinstance(value, dict) and '_type' in value:
        if value['_type'] in _AST_SINGLETONS:
            return _AST_SINGLETONS[value['_type']]
        cls = globals()[value['_type']]
        return cls(**{name: _from_parser(item) for name, item in value.items() if name != '_type'})
    return value

def _parse_ast(source, filename, mode):
    return _from_parser(_parse_tree(source, filename, mode))



# Python/Python-ast.c: conversion from public objects into ASDL nodes.
def _constant_to_parser(value):
    if value is None: return {'type': 'none', 'py_value': value}
    if value is ...: return {'type': 'ellipsis', 'py_value': value}
    kind = {int: 'int', float: 'float', complex: 'complex', bool: 'bool',
            str: 'str', bytes: 'bytes', tuple: 'tuple', frozenset: 'frozenset'}.get(type(value))
    if kind is None:
        raise TypeError(f'got an invalid type in Constant: {type(value).__name__}')
    if kind == 'int': return {'type': kind, 'value': str(value), 'py_value': value}
    if kind == 'complex': return {'type': kind, 'real': value.real, 'imag': value.imag, 'py_value': value}
    original = value
    if kind == 'bytes': value = list(value)
    elif kind in ('tuple', 'frozenset'): value = [_constant_to_parser(item) for item in value]
    return {'type': kind, 'value': value, 'py_value': original}


def _to_parser(node):
    for cls in type(node).__mro__:
        name = cls.__name__
        if cls is globals().get(name) and name in _AST_SCHEMA:
            base, fields, attributes = _AST_SCHEMA[name]
            if base == 'AST' and not fields:
                raise TypeError(f'expected some sort of {name}, but got {node!r}')
            break
    else:
        raise TypeError(f'expected some sort of AST node, but got {node!r}')
    result = {'_type': name}

    def convert(value, type_name, mods, field):
        if mods.endswith('*'):
            if not isinstance(value, list):
                raise TypeError(f'{name} field "{field}" must be a list, not a {type(value).__name__}')
            length = _list_size(value)
            result = []
            for index in range(length):
                item = _list_item(value, index)
                result.append(None if item is None and type_name in ('stmt', 'expr')
                              else convert(item, type_name, mods[:-1], field))
                if _list_size(value) != length:
                    raise RuntimeError(f'{name} field "{field}" changed size during iteration')
            return result
        if mods.endswith('?'):
            if value is None: return None
            return convert(value, type_name, mods[:-1], field)
        if type_name == 'constant': return _constant_to_parser(value)
        if type_name in ('identifier', 'string'):
            if not isinstance(value, str):
                raise TypeError(f'AST identifier must be of type str')
            return value
        if type_name == 'int': return _int_field(value)
        if not isinstance(value, globals()[type_name]):
            raise TypeError(f'expected some sort of {type_name}, but got {value!r}')
        return _to_parser(value)

    for field, type_name, mods in fields:
        try: value = getattr(node, field)
        except AttributeError:
            raise TypeError(f'required field "{field}" missing from {name}') from None
        if value is None and not mods and type_name not in ('constant', 'int', 'identifier', 'string'):
            raise ValueError(f"field '{field}' is required for {name}")
        result[field] = convert(value, type_name, mods, field)
    for attribute in attributes:
        try: value = getattr(node, attribute)
        except AttributeError:
            if not attribute.startswith('end_'):
                owner = name if base == 'AST' else base
                raise TypeError(f'required field "{attribute}" missing from {owner}') from None
            value = None
        # Optional end positions default to the corresponding start positions.
        if value is None and attribute.startswith('end_'):
            result[attribute] = result[attribute[4:]]
        else:
            result[attribute] = convert(value, 'int', '', attribute)
    return result


_register_type(AST)

def _compile_ast(tree, filename, mode, flags, optimize):
    if mode not in ('exec', 'eval', 'single'):
        raise ValueError("compile() mode must be 'exec', 'eval' or 'single'")
    expected = {'exec': Module, 'eval': Expression, 'single': Interactive}[mode]
    if not isinstance(tree, expected):
        raise TypeError(f'expected {expected.__name__} node, got {type(tree).__name__}')
    converted = _to_parser(tree)
    snapshot = _from_parser(converted)
    if flags & PyCF_ONLY_AST: return snapshot
    from _ast_validation import _validate
    _validate(snapshot)
    return _compile_tree(converted, filename, mode, flags, optimize)

