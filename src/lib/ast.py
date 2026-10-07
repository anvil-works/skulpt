"""CPython 3.14 AST objects and traversal helpers.

Schema: Parser/Python.asdl at 18ef0f0cb52. Helpers: Lib/ast.py at that revision.
Source parsing uses Skulpt's configured parser. Statement unparsing, optimized
ASTs and type-comment parsing are implemented in subsequent compiler layers.
"""
from _ast import *
from _ast import _parse_ast

def parse(source, filename='<unknown>', mode='exec', *, type_comments=False, feature_version=None, optimize=-1):
    if feature_version is not None:
        raise NotImplementedError('versioned AST grammars are not yet supported')
    flags = PyCF_ONLY_AST
    if type_comments: flags |= PyCF_TYPE_COMMENTS
    if optimize > 0: flags |= PyCF_OPTIMIZED_AST
    return compile(source, filename, mode, flags, optimize=optimize)


def literal_eval(node_or_string):
    """
    Evaluate an expression node or a string containing only a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, bytes, numbers, tuples, lists, dicts,
    sets, booleans, and None.

    Caution: A complex expression can overflow the C stack and cause a crash.
    """
    if isinstance(node_or_string, str):
        node_or_string = parse(node_or_string.lstrip(" \t"), mode='eval')
    if isinstance(node_or_string, Expression):
        node_or_string = node_or_string.body
    def _raise_malformed_node(node):
        msg = "malformed node or string"
        if lno := getattr(node, 'lineno', None):
            msg += f' on line {lno}'
        raise ValueError(msg + f': {node!r}')
    def _convert_num(node):
        if not isinstance(node, Constant) or type(node.value) not in (int, float, complex):
            _raise_malformed_node(node)
        return node.value
    def _convert_signed_num(node):
        if isinstance(node, UnaryOp) and isinstance(node.op, (UAdd, USub)):
            operand = _convert_num(node.operand)
            if isinstance(node.op, UAdd):
                return + operand
            else:
                return - operand
        return _convert_num(node)
    def _convert(node):
        if isinstance(node, Constant):
            return node.value
        elif isinstance(node, Tuple):
            return tuple(map(_convert, node.elts))
        elif isinstance(node, List):
            return list(map(_convert, node.elts))
        elif isinstance(node, Set):
            return set(map(_convert, node.elts))
        elif (isinstance(node, Call) and isinstance(node.func, Name) and
              node.func.id == 'set' and node.args == node.keywords == []):
            return set()
        elif isinstance(node, Dict):
            if len(node.keys) != len(node.values):
                _raise_malformed_node(node)
            return dict(zip(map(_convert, node.keys),
                            map(_convert, node.values)))
        elif isinstance(node, BinOp) and isinstance(node.op, (Add, Sub)):
            left = _convert_signed_num(node.left)
            right = _convert_num(node.right)
            if isinstance(left, (int, float)) and isinstance(right, complex):
                if isinstance(node.op, Add):
                    return left + right
                else:
                    return left - right
        return _convert_signed_num(node)
    return _convert(node_or_string)


def dump(
    node, annotate_fields=True, include_attributes=False,
    *,
    indent=None, show_empty=False,
):
    """
    Return a formatted dump of the tree in node.  This is mainly useful for
    debugging purposes.  If annotate_fields is true (by default),
    the returned string will show the names and the values for fields.
    If annotate_fields is false, the result string will be more compact by
    omitting unambiguous field names.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    include_attributes can be set to true.  If indent is a non-negative
    integer or string, then the tree will be pretty-printed with that indent
    level. None (the default) selects the single line representation.
    If show_empty is False, then empty lists and fields that are None
    will be omitted from the output for better readability.
    """
    def _format(node, level=0):
        if indent is not None:
            level += 1
            prefix = '\n' + indent * level
            sep = ',\n' + indent * level
        else:
            prefix = ''
            sep = ', '
        if isinstance(node, AST):
            cls = type(node)
            args = []
            args_buffer = []
            allsimple = True
            keywords = annotate_fields
            for name in node._fields:
                try:
                    value = getattr(node, name)
                except AttributeError:
                    keywords = True
                    continue
                if value is None and getattr(cls, name, ...) is None:
                    keywords = True
                    continue
                if not show_empty:
                    if value == []:
                        field_type = cls._field_types.get(name, object)
                        if getattr(field_type, '__origin__', ...) is list:
                            if not keywords:
                                args_buffer.append(repr(value))
                            continue
                    if not keywords:
                        args.extend(args_buffer)
                        args_buffer = []
                value, simple = _format(value, level)
                allsimple = allsimple and simple
                if keywords:
                    args.append('%s=%s' % (name, value))
                else:
                    args.append(value)
            if include_attributes and node._attributes:
                for name in node._attributes:
                    try:
                        value = getattr(node, name)
                    except AttributeError:
                        continue
                    if value is None and getattr(cls, name, ...) is None:
                        continue
                    value, simple = _format(value, level)
                    allsimple = allsimple and simple
                    args.append('%s=%s' % (name, value))
            if allsimple and len(args) <= 3:
                return '%s(%s)' % (node.__class__.__name__, ', '.join(args)), not args
            return '%s(%s%s)' % (node.__class__.__name__, prefix, sep.join(args)), False
        elif isinstance(node, list):
            if not node:
                return '[]', True
            return '[%s%s]' % (prefix, sep.join(_format(x, level)[0] for x in node)), False
        return repr(node), True

    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    if indent is not None and not isinstance(indent, str):
        indent = ' ' * indent
    return _format(node)[0]


def copy_location(new_node, old_node):
    """
    Copy source location (`lineno`, `col_offset`, `end_lineno`, and `end_col_offset`
    attributes) from *old_node* to *new_node* if possible, and return *new_node*.
    """
    for attr in 'lineno', 'col_offset', 'end_lineno', 'end_col_offset':
        if attr in old_node._attributes and attr in new_node._attributes:
            value = getattr(old_node, attr, None)
            # end_lineno and end_col_offset are optional attributes, and they
            # should be copied whether the value is None or not.
            if value is not None or (
                hasattr(old_node, attr) and attr.startswith("end_")
            ):
                setattr(new_node, attr, value)
    return new_node


def fix_missing_locations(node):
    """
    When you compile a node tree with compile(), the compiler expects lineno and
    col_offset attributes for every node that supports them.  This is rather
    tedious to fill in for generated nodes, so this helper adds these attributes
    recursively where not already set, by setting them to the values of the
    parent node.  It works recursively starting at *node*.
    """
    def _fix(node, lineno, col_offset, end_lineno, end_col_offset):
        if 'lineno' in node._attributes:
            if not hasattr(node, 'lineno'):
                node.lineno = lineno
            else:
                lineno = node.lineno
        if 'end_lineno' in node._attributes:
            if getattr(node, 'end_lineno', None) is None:
                node.end_lineno = end_lineno
            else:
                end_lineno = node.end_lineno
        if 'col_offset' in node._attributes:
            if not hasattr(node, 'col_offset'):
                node.col_offset = col_offset
            else:
                col_offset = node.col_offset
        if 'end_col_offset' in node._attributes:
            if getattr(node, 'end_col_offset', None) is None:
                node.end_col_offset = end_col_offset
            else:
                end_col_offset = node.end_col_offset
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset, end_lineno, end_col_offset)
    _fix(node, 1, 0, 1, 0)
    return node


def increment_lineno(node, n=1):
    """
    Increment the line number and end line number of each node in the tree
    starting at *node* by *n*. This is useful to "move code" to a different
    location in a file.
    """
    for child in walk(node):
        # TypeIgnore is a special case where lineno is not an attribute
        # but rather a field of the node itself.
        if isinstance(child, TypeIgnore):
            child.lineno = getattr(child, 'lineno', 0) + n
            continue

        if 'lineno' in child._attributes:
            child.lineno = getattr(child, 'lineno', 0) + n
        if (
            "end_lineno" in child._attributes
            and (end_lineno := getattr(child, "end_lineno", 0)) is not None
        ):
            child.end_lineno = end_lineno + n
    return node


def iter_fields(node):
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node):
    """
    Yield all direct child nodes of *node*, that is, all fields that are nodes
    and all items of fields that are lists of nodes.
    """
    for name, field in iter_fields(node):
        if isinstance(field, AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, AST):
                    yield item


def walk(node):
    """
    Recursively yield all descendant nodes in the tree starting at *node*
    (including *node* itself), in no specified order.  This is useful if you
    only want to modify nodes in place and don't care about the context.
    """
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node


class NodeVisitor(object):
    """
    A node visitor base class that walks the abstract syntax tree and calls a
    visitor function for every node found.  This function may return a value
    which is forwarded by the `visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `visit` method.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item)
            elif isinstance(value, AST):
                self.visit(value)


class NodeTransformer(NodeVisitor):
    """
    A :class:`NodeVisitor` subclass that walks the abstract syntax tree and
    allows modification of nodes.

    The `NodeTransformer` will walk the AST and use the return value of the
    visitor methods to replace or remove the old node.  If the return value of
    the visitor method is ``None``, the node will be removed from its location,
    otherwise it is replaced with the return value.  The return value may be the
    original node in which case no replacement takes place.

    Here is an example transformer that rewrites all occurrences of name lookups
    (``foo``) to ``data['foo']``::

       class RewriteName(NodeTransformer):

           def visit_Name(self, node):
               return Subscript(
                   value=Name(id='data', ctx=Load()),
                   slice=Constant(value=node.id),
                   ctx=node.ctx
               )

    Keep in mind that if the node you're operating on has child nodes you must
    either transform the child nodes yourself or call the :meth:`generic_visit`
    method for the node first.

    For nodes that were part of a collection of statements (that applies to all
    statement nodes), the visitor may also return a list of nodes rather than
    just a single node.

    Usually you use the transformer like this::

       node = YourTransformer().visit(node)
    """

    def generic_visit(self, node):
        for field, old_value in iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node



def unparse(ast_obj):
    global _Unparser
    try:
        unparser = _Unparser()
    except NameError:
        from _ast_unparse import Unparser as _Unparser
        unparser = _Unparser()
    return unparser.visit(ast_obj)

