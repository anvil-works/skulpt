"""Public AST preprocessing, following Python/ast_preprocess.c in CPython 3.14.

Numeric constant folding belongs to CPython's flowgraph optimizer; optimized
ASTs retain those expressions. This pass operates on the compiler's snapshot.
"""
import ast


def _make_const(node, value):
    return ast.copy_location(ast.Constant(value=value), node)


def _fold_const_match_patterns(node):
    try:
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant):
                return _make_const(node, -node.operand.value)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            if isinstance(node.right, ast.Constant):
                node.left = _fold_const_match_patterns(node.left)
                if isinstance(node.left, ast.Constant):
                    value = (node.left.value + node.right.value if isinstance(node.op, ast.Add)
                             else node.left.value - node.right.value)
                    return _make_const(node, value)
    except (TypeError, ValueError, OverflowError):
        # CPython's make_const clears failed folds, leaving the original node.
        pass
    return node


def _format_const(value):
    return ast.Constant(value=value, lineno=-1, col_offset=-1,
                        end_lineno=-1, end_col_offset=-1)


def _optimize_format(node):
    """CPython's parse_literal, simple_format_arg_parse and optimize_format."""
    if not (isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str) and isinstance(node.right, ast.Tuple)):
        return node
    if any(isinstance(elt, ast.Starred) for elt in node.right.elts):
        return node
    fmt = node.left.value
    values = []
    pos = count = 0
    while True:
        literal = ''
        while pos < len(fmt):
            if fmt[pos] != '%':
                literal += fmt[pos]
                pos += 1
            elif fmt[pos:pos + 2] == '%%':
                literal += '%'
                pos += 2
            else:
                break
        if literal:
            values.append(_format_const(literal))
        if pos == len(fmt):
            break
        if count == len(node.right.elts):
            return node
        pos += 1
        left_justify = False
        while pos < len(fmt) and fmt[pos] in '-+ #0':
            left_justify |= fmt[pos] == '-'
            pos += 1
        start = pos
        while pos < len(fmt) and '0' <= fmt[pos] <= '9':
            pos += 1
        if pos - start >= 3:
            return node
        width = int(fmt[start:pos]) if pos > start else -1
        precision = -1
        if pos < len(fmt) and fmt[pos] == '.':
            pos += 1
            start = pos
            while pos < len(fmt) and '0' <= fmt[pos] <= '9':
                pos += 1
            if pos - start >= 3:
                return node
            precision = int(fmt[start:pos]) if pos > start else 0
        if pos == len(fmt) or fmt[pos] not in 'sra':
            return node
        spec = '>' if not left_justify and width > 0 else ''
        if width >= 0:
            spec += str(width)
        if precision >= 0:
            spec += '.' + str(precision)
        arg = node.right.elts[count]
        value = ast.FormattedValue(value=arg, conversion=ord(fmt[pos]),
                                   format_spec=_format_const(spec) if spec else None)
        values.append(ast.copy_location(value, arg))
        pos += 1
        count += 1
    if count != len(node.right.elts):
        return node
    return ast.copy_location(ast.JoinedStr(values=values), node)


class _Preprocessor(ast.NodeTransformer):
    def __init__(self, optimize, future_annotations, syntax_check_only):
        self.optimize = optimize
        self.syntax_check_only = syntax_check_only
        self.future_annotations = future_annotations

    def _astfold_body(self, body):
        def is_docstring():
            return (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str))
        docstring = is_docstring()
        if docstring and self.optimize >= 2:
            if len(body) == 1:
                stmt = body[0]
                body[0] = ast.Pass(lineno=stmt.lineno, col_offset=stmt.col_offset,
                                   end_lineno=stmt.lineno, end_col_offset=stmt.col_offset + 4)
            else:
                del body[0]
            docstring = False
        body[:] = [self.visit(stmt) for stmt in body]
        if not docstring and is_docstring():
            stmt = body[0]
            stmt.value = ast.copy_location(ast.JoinedStr(values=[stmt.value]), stmt)
        return body

    def generic_visit(self, node):
        # Only module/function/class bodies treat their first string as a docstring.
        doc_body = isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for field, value in ast.iter_fields(node):
            if self.future_annotations and field in ('annotation', 'returns'):
                continue
            if doc_body and field == 'body':
                self._astfold_body(value)
            elif isinstance(value, list):
                value[:] = [self.visit(item) if isinstance(item, ast.AST) else item for item in value]
            elif isinstance(value, ast.AST):
                setattr(node, field, self.visit(value))
        return node

    def visit_FunctionType(self, node):
        return node

    def visit_Name(self, node):
        if not self.syntax_check_only and isinstance(node.ctx, ast.Load) and node.id == '__debug__':
            return _make_const(node, not self.optimize)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        return node if self.syntax_check_only else _optimize_format(node)

    def visit_MatchValue(self, node):
        if not self.syntax_check_only:
            node.value = _fold_const_match_patterns(node.value)
        return node

    def visit_MatchMapping(self, node):
        if not self.syntax_check_only:
            node.keys = [_fold_const_match_patterns(key) for key in node.keys]
        node.patterns = [self.visit(pattern) for pattern in node.patterns]
        return node


def _preprocess(tree, flags, optimize):
    future_annotations = bool(flags & 0x1000000)
    if isinstance(tree, (ast.Module, ast.Interactive)):
        for index, stmt in enumerate(tree.body):
            if isinstance(stmt, ast.ImportFrom) and stmt.module == '__future__' and stmt.level == 0:
                future_annotations |= any(name.name == 'annotations' for name in stmt.names)
            elif not (index == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                      and isinstance(stmt.value.value, str)):
                break
    return _Preprocessor(optimize, future_annotations, not (flags & 0x8000)).visit(tree)
