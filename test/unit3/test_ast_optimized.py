# Complete CPython 3.14 test_ast methods at 18ef0f0cb52.
import ast
import textwrap
import unittest
from test_annotationlib import HarnessCase as BaseCase

class HarnessCase(BaseCase):
    def assertListEqual(self, first, second, msg=None):
        self.assertIsInstance(first, list)
        self.assertIsInstance(second, list)
        self.assertTrue(first == second, msg)

class ASTTests(HarnessCase):

    def test_optimization_levels__debug__(self):
        cases = [(-1, '__debug__'), (0, '__debug__'), (1, False), (2, False)]
        for (optval, expected) in cases:
            with self.subTest(optval=optval, expected=expected):
                res1 = ast.parse("__debug__", optimize=optval)
                res2 = ast.parse(ast.parse("__debug__"), optimize=optval)
                for res in [res1, res2]:
                    self.assertIsInstance(res.body[0], ast.Expr)
                    if isinstance(expected, bool):
                        self.assertIsInstance(res.body[0].value, ast.Constant)
                        self.assertEqual(res.body[0].value.value, expected)
                    else:
                        self.assertIsInstance(res.body[0].value, ast.Name)
                        self.assertEqual(res.body[0].value.id, expected)

    def test_docstring_optimization_single_node(self):
        # https://github.com/python/cpython/issues/137308
        class_example1 = textwrap.dedent('''
            class A:
                """Docstring"""
        ''')
        class_example2 = textwrap.dedent('''
            class A:
                """
                Docstring"""
        ''')
        def_example1 = textwrap.dedent('''
            def some():
                """Docstring"""
        ''')
        def_example2 = textwrap.dedent('''
            def some():
                """Docstring
                                       """
        ''')
        async_def_example1 = textwrap.dedent('''
            async def some():
                """Docstring"""
        ''')
        async_def_example2 = textwrap.dedent('''
            async def some():
                """
                Docstring
            """
        ''')
        for code in [
            class_example1,
            class_example2,
            def_example1,
            def_example2,
            async_def_example1,
            async_def_example2,
        ]:
            for opt_level in [0, 1, 2]:
                with self.subTest(code=code, opt_level=opt_level):
                    mod = ast.parse(code, optimize=opt_level)
                    self.assertEqual(len(mod.body[0].body), 1)
                    if opt_level == 2:
                        pass_stmt = mod.body[0].body[0]
                        self.assertIsInstance(pass_stmt, ast.Pass)
                        self.assertEqual(
                            vars(pass_stmt),
                            {
                                'lineno': 3,
                                'col_offset': 4,
                                'end_lineno': 3,
                                'end_col_offset': 8,
                            },
                        )
                    else:
                        self.assertIsInstance(mod.body[0].body[0], ast.Expr)
                        self.assertIsInstance(
                            mod.body[0].body[0].value,
                            ast.Constant,
                        )

                    compile(code, "a", "exec")
                    compile(code, "a", "exec", optimize=opt_level)
                    compile(mod, "a", "exec")
                    compile(mod, "a", "exec", optimize=opt_level)

    def test_docstring_optimization_multiple_nodes(self):
        # https://github.com/python/cpython/issues/137308
        class_example = textwrap.dedent(
            """
            class A:
                '''
                Docstring
                '''
                x = 1
            """
        )

        def_example = textwrap.dedent(
            """
            def some():
                '''
                Docstring

            '''
                x = 1
            """
        )

        async_def_example = textwrap.dedent(
            """
            async def some():

                '''Docstring

            '''
                x = 1
            """
        )

        for code in [
            class_example,
            def_example,
            async_def_example,
        ]:
            for opt_level in [0, 1, 2]:
                with self.subTest(code=code, opt_level=opt_level):
                    mod = ast.parse(code, optimize=opt_level)
                    if opt_level == 2:
                        self.assertNotIsInstance(
                            mod.body[0].body[0],
                            (ast.Pass, ast.Expr),
                        )
                    else:
                        self.assertIsInstance(mod.body[0].body[0], ast.Expr)
                        self.assertIsInstance(
                            mod.body[0].body[0].value,
                            ast.Constant,
                        )

                    compile(code, "a", "exec")
                    compile(code, "a", "exec", optimize=opt_level)
                    compile(mod, "a", "exec")
                    compile(mod, "a", "exec", optimize=opt_level)

    def test_compare_basics(self):
        self.assertTrue(ast.compare(ast.parse("x = 10"), ast.parse("x = 10")))
        self.assertFalse(ast.compare(ast.parse("x = 10"), ast.parse("")))
        self.assertFalse(ast.compare(ast.parse("x = 10"), ast.parse("x")))
        self.assertFalse(
            ast.compare(ast.parse("x = 10;y = 20"), ast.parse("class C:pass"))
        )

    def test_compare_modified_ast(self):
        # The ast API is a bit underspecified. The objects are mutable,
        # and even _fields and _attributes are mutable. The compare() does
        # some simple things to accommodate mutability.
        a = ast.parse("m * x + b", mode="eval")
        b = ast.parse("m * x + b", mode="eval")
        self.assertTrue(ast.compare(a, b))

        a._fields = a._fields + ("spam",)
        a.spam = "Spam"
        self.assertNotEqual(a._fields, b._fields)
        self.assertFalse(ast.compare(a, b))
        self.assertFalse(ast.compare(b, a))

        b._fields = a._fields
        b.spam = a.spam
        self.assertTrue(ast.compare(a, b))
        self.assertTrue(ast.compare(b, a))

        b._attributes = b._attributes + ("eggs",)
        b.eggs = "eggs"
        self.assertNotEqual(a._attributes, b._attributes)
        self.assertFalse(ast.compare(a, b, compare_attributes=True))
        self.assertFalse(ast.compare(b, a, compare_attributes=True))

        a._attributes = b._attributes
        a.eggs = b.eggs
        self.assertTrue(ast.compare(a, b, compare_attributes=True))
        self.assertTrue(ast.compare(b, a, compare_attributes=True))

    def test_compare_literals(self):
        constants = (
            -20,
            20,
            20.0,
            1,
            1.0,
            True,
            0,
            False,
            frozenset(),
            tuple(),
            "ABCD",
            "abcd",
            "中文字",
            1e1000,
            -1e1000,
        )
        for next_index, constant in enumerate(constants[:-1], 1):
            next_constant = constants[next_index]
            with self.subTest(literal=constant, next_literal=next_constant):
                self.assertTrue(
                    ast.compare(ast.Constant(constant), ast.Constant(constant))
                )
                self.assertFalse(
                    ast.compare(
                        ast.Constant(constant), ast.Constant(next_constant)
                    )
                )

        same_looking_literal_cases = [
            {1, 1.0, True, 1 + 0j},
            {0, 0.0, False, 0 + 0j},
        ]
        for same_looking_literals in same_looking_literal_cases:
            for literal in same_looking_literals:
                for same_looking_literal in same_looking_literals - {literal}:
                    self.assertFalse(
                        ast.compare(
                            ast.Constant(literal),
                            ast.Constant(same_looking_literal),
                        )
                    )

    def test_compare_fieldless(self):
        self.assertTrue(ast.compare(ast.Add(), ast.Add()))
        self.assertFalse(ast.compare(ast.Sub(), ast.Add()))

        # test that missing runtime fields is handled in ast.compare()
        a1, a2 = ast.Name('a'), ast.Name('a')
        self.assertTrue(ast.compare(a1, a2))
        self.assertTrue(ast.compare(a1, a2))
        del a1.id
        self.assertFalse(ast.compare(a1, a2))
        del a2.id
        self.assertTrue(ast.compare(a1, a2))

    def test_compare_attributes_option(self):
        def parse(a, b):
            return ast.parse(a), ast.parse(b)

        a, b = parse("2 + 2", "2+2")
        self.assertTrue(ast.compare(a, b))
        self.assertTrue(ast.compare(a, b, compare_attributes=False))
        self.assertFalse(ast.compare(a, b, compare_attributes=True))

    def test_compare_attributes_option_missing_attribute(self):
        # test that missing runtime attributes is handled in ast.compare()
        a1, a2 = ast.Name('a', lineno=1), ast.Name('a', lineno=1)
        self.assertTrue(ast.compare(a1, a2))
        self.assertTrue(ast.compare(a1, a2, compare_attributes=True))
        del a1.lineno
        self.assertFalse(ast.compare(a1, a2, compare_attributes=True))
        del a2.lineno
        self.assertTrue(ast.compare(a1, a2, compare_attributes=True))

class ASTOptimizationTests(HarnessCase):
    def wrap_expr(self, expr):
        return ast.Module(body=[ast.Expr(value=expr)])

    def wrap_statement(self, statement):
        return ast.Module(body=[statement])

    def assert_ast(self, code, non_optimized_target, optimized_target):
        non_optimized_tree = ast.parse(code, optimize=-1)
        optimized_tree = ast.parse(code, optimize=1)

        # Is a non-optimized tree equal to a non-optimized target?
        self.assertTrue(
            ast.compare(non_optimized_tree, non_optimized_target),
            f"{ast.dump(non_optimized_target)} must equal "
            f"{ast.dump(non_optimized_tree)}",
        )

        # Is a optimized tree equal to a non-optimized target?
        self.assertFalse(
            ast.compare(optimized_tree, non_optimized_target),
            f"{ast.dump(non_optimized_target)} must not equal "
            f"{ast.dump(non_optimized_tree)}"
        )

        # Is a optimized tree is equal to an optimized target?
        self.assertTrue(
            ast.compare(optimized_tree,  optimized_target),
            f"{ast.dump(optimized_target)} must equal "
            f"{ast.dump(optimized_tree)}",
        )

    def test_folding_format(self):
        code = "'%s' % (a,)"

        non_optimized_target = self.wrap_expr(
            ast.BinOp(
                left=ast.Constant(value="%s"),
                op=ast.Mod(),
                right=ast.Tuple(elts=[ast.Name(id='a')]))
        )
        optimized_target = self.wrap_expr(
            ast.JoinedStr(
                values=[
                    ast.FormattedValue(value=ast.Name(id='a'), conversion=115)
                ]
            )
        )

        self.assert_ast(code, non_optimized_target, optimized_target)

    def test_folding_match_case_allowed_expressions(self):
        def get_match_case_values(node):
            result = []
            if isinstance(node, ast.Constant):
                result.append(node.value)
            elif isinstance(node, ast.MatchValue):
                result.extend(get_match_case_values(node.value))
            elif isinstance(node, ast.MatchMapping):
                for key in node.keys:
                    result.extend(get_match_case_values(key))
            elif isinstance(node, ast.MatchSequence):
                for pat in node.patterns:
                    result.extend(get_match_case_values(pat))
            else:
                self.fail(f"Unexpected node {node}")
            return result

        tests = [
            ("-0", [0]),
            ("-0.1", [-0.1]),
            ("-0j", [complex(0, 0)]),
            ("-0.1j", [complex(0, -0.1)]),
            ("1 + 2j", [complex(1, 2)]),
            ("1 - 2j", [complex(1, -2)]),
            ("1.1 + 2.1j", [complex(1.1, 2.1)]),
            ("1.1 - 2.1j", [complex(1.1, -2.1)]),
            ("-0 + 1j", [complex(0, 1)]),
            ("-0 - 1j", [complex(0, -1)]),
            ("-0.1 + 1.1j", [complex(-0.1, 1.1)]),
            ("-0.1 - 1.1j", [complex(-0.1, -1.1)]),
            ("{-0: 0}", [0]),
            ("{-0.1: 0}", [-0.1]),
            ("{-0j: 0}", [complex(0, 0)]),
            ("{-0.1j: 0}", [complex(0, -0.1)]),
            ("{1 + 2j: 0}", [complex(1, 2)]),
            ("{1 - 2j: 0}", [complex(1, -2)]),
            ("{1.1 + 2.1j: 0}", [complex(1.1, 2.1)]),
            ("{1.1 - 2.1j: 0}", [complex(1.1, -2.1)]),
            ("{-0 + 1j: 0}", [complex(0, 1)]),
            ("{-0 - 1j: 0}", [complex(0, -1)]),
            ("{-0.1 + 1.1j: 0}", [complex(-0.1, 1.1)]),
            ("{-0.1 - 1.1j: 0}", [complex(-0.1, -1.1)]),
            ("{-0: 0, 0 + 1j: 0, 0.1 + 1j: 0}", [0, complex(0, 1), complex(0.1, 1)]),
            ("[-0, -0.1, -0j, -0.1j]", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("[[[[-0, -0.1, -0j, -0.1j]]]]", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("[[-0, -0.1], -0j, -0.1j]", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("[[-0, -0.1], [-0j, -0.1j]]", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("(-0, -0.1, -0j, -0.1j)", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("((((-0, -0.1, -0j, -0.1j))))", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("((-0, -0.1), -0j, -0.1j)", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
            ("((-0, -0.1), (-0j, -0.1j))", [0, -0.1, complex(0, 0), complex(0, -0.1)]),
        ]
        for match_expr, constants in tests:
            with self.subTest(match_expr):
                src = f"match 0:\n\t case {match_expr}: pass"
                tree = ast.parse(src, optimize=1)
                match_stmt = tree.body[0]
                case = match_stmt.cases[0]
                values = get_match_case_values(case.pattern)
                self.assertListEqual(constants, values)

    def test_match_case_not_folded_in_unoptimized_ast(self):
        src = textwrap.dedent("""
            match a:
                case 1+2j:
                    pass
            """)

        unfolded = "MatchValue(value=BinOp(left=Constant(value=1), op=Add(), right=Constant(value=2j))"
        folded = "MatchValue(value=Constant(value=(1+2j)))"
        for optval in (0, 1, 2):
            self.assertIn(folded if optval else unfolded, ast.dump(ast.parse(src, optimize=optval)))


class OptimizedASTRegressions(HarnessCase):
    # CPython-checked ASTs also protect generated format-node source locations.
    def test_format_limits_and_locations(self):
        cases = [("'a%%b%s' % (x,)",
          "Module(body=[Expr(value=JoinedStr(values=[Constant(value='a%b', lineno=-1, col_offset=-1, "
          "end_lineno=-1, end_col_offset=-1), FormattedValue(value=Name(id='x', ctx=Load(), lineno=1, "
          'col_offset=12, end_lineno=1, end_col_offset=13), conversion=115, lineno=1, col_offset=12, '
          'end_lineno=1, end_col_offset=13)], lineno=1, col_offset=0, end_lineno=1, end_col_offset=15), '
          'lineno=1, col_offset=0, end_lineno=1, end_col_offset=15)])'),
         ("'%+09.2r' % (x,)",
          "Module(body=[Expr(value=JoinedStr(values=[FormattedValue(value=Name(id='x', ctx=Load(), "
          'lineno=1, col_offset=13, end_lineno=1, end_col_offset=14), conversion=114, '
          "format_spec=Constant(value='>9.2', lineno=-1, col_offset=-1, end_lineno=-1, end_col_offset=-1), "
          'lineno=1, col_offset=13, end_lineno=1, end_col_offset=14)], lineno=1, col_offset=0, '
          'end_lineno=1, end_col_offset=16), lineno=1, col_offset=0, end_lineno=1, end_col_offset=16)])'),
         ("'%-2.s' % (x,)",
          "Module(body=[Expr(value=JoinedStr(values=[FormattedValue(value=Name(id='x', ctx=Load(), "
          'lineno=1, col_offset=11, end_lineno=1, end_col_offset=12), conversion=115, '
          "format_spec=Constant(value='2.0', lineno=-1, col_offset=-1, end_lineno=-1, end_col_offset=-1), "
          'lineno=1, col_offset=11, end_lineno=1, end_col_offset=12)], lineno=1, col_offset=0, '
          'end_lineno=1, end_col_offset=14), lineno=1, col_offset=0, end_lineno=1, end_col_offset=14)])'),
         ("'%99s' % (x,)",
          "Module(body=[Expr(value=JoinedStr(values=[FormattedValue(value=Name(id='x', ctx=Load(), "
          'lineno=1, col_offset=10, end_lineno=1, end_col_offset=11), conversion=115, '
          "format_spec=Constant(value='>99', lineno=-1, col_offset=-1, end_lineno=-1, end_col_offset=-1), "
          'lineno=1, col_offset=10, end_lineno=1, end_col_offset=11)], lineno=1, col_offset=0, '
          'end_lineno=1, end_col_offset=13), lineno=1, col_offset=0, end_lineno=1, end_col_offset=13)])'),
         ("'%100s' % (x,)",
          "Module(body=[Expr(value=BinOp(left=Constant(value='%100s', lineno=1, col_offset=0, "
          "end_lineno=1, end_col_offset=7), op=Mod(), right=Tuple(elts=[Name(id='x', ctx=Load(), lineno=1, "
          'col_offset=11, end_lineno=1, end_col_offset=12)], ctx=Load(), lineno=1, col_offset=10, '
          'end_lineno=1, end_col_offset=14), lineno=1, col_offset=0, end_lineno=1, end_col_offset=14), '
          'lineno=1, col_offset=0, end_lineno=1, end_col_offset=14)])'),
         ("'%s' % (*x,)",
          "Module(body=[Expr(value=BinOp(left=Constant(value='%s', lineno=1, col_offset=0, end_lineno=1, "
          "end_col_offset=4), op=Mod(), right=Tuple(elts=[Starred(value=Name(id='x', ctx=Load(), lineno=1, "
          'col_offset=9, end_lineno=1, end_col_offset=10), ctx=Load(), lineno=1, col_offset=8, '
          'end_lineno=1, end_col_offset=10)], ctx=Load(), lineno=1, col_offset=7, end_lineno=1, '
          'end_col_offset=12), lineno=1, col_offset=0, end_lineno=1, end_col_offset=12), lineno=1, '
          'col_offset=0, end_lineno=1, end_col_offset=12)])'),
         ("'%s%s' % (x,)",
          "Module(body=[Expr(value=BinOp(left=Constant(value='%s%s', lineno=1, col_offset=0, end_lineno=1, "
          "end_col_offset=6), op=Mod(), right=Tuple(elts=[Name(id='x', ctx=Load(), lineno=1, "
          'col_offset=10, end_lineno=1, end_col_offset=11)], ctx=Load(), lineno=1, col_offset=9, '
          'end_lineno=1, end_col_offset=13), lineno=1, col_offset=0, end_lineno=1, end_col_offset=13), '
          'lineno=1, col_offset=0, end_lineno=1, end_col_offset=13)])'),
         ("'%%' % ()",
          "Module(body=[Expr(value=JoinedStr(values=[Constant(value='%', lineno=-1, col_offset=-1, "
          'end_lineno=-1, end_col_offset=-1)], lineno=1, col_offset=0, end_lineno=1, end_col_offset=9), '
          'lineno=1, col_offset=0, end_lineno=1, end_col_offset=9)])'),
         ("'%d' % (x,)",
          "Module(body=[Expr(value=BinOp(left=Constant(value='%d', lineno=1, col_offset=0, end_lineno=1, "
          "end_col_offset=4), op=Mod(), right=Tuple(elts=[Name(id='x', ctx=Load(), lineno=1, col_offset=8, "
          'end_lineno=1, end_col_offset=9)], ctx=Load(), lineno=1, col_offset=7, end_lineno=1, '
          'end_col_offset=11), lineno=1, col_offset=0, end_lineno=1, end_col_offset=11), lineno=1, '
          'col_offset=0, end_lineno=1, end_col_offset=11)])')]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(ast.dump(ast.parse(source, optimize=1), include_attributes=True), expected)

    def test_flags_snapshots_and_future_annotations(self):
        original = ast.parse('__debug__; 1 + 2; -1')
        snapshot = ast.dump(original, include_attributes=True)
        optimized = compile(original, '?', 'exec', ast.PyCF_ONLY_AST | ast.PyCF_OPTIMIZED_AST, optimize=0)
        self.assertIs(optimized.body[0].value.value, True)
        self.assertIsInstance(optimized.body[1].value, ast.BinOp)
        self.assertIsInstance(optimized.body[2].value, ast.UnaryOp)
        self.assertEqual(ast.dump(original, include_attributes=True), snapshot)
        source = 'from __future__ import annotations\ndef f(x: __debug__ = __debug__) -> __debug__: pass\ny: __debug__ = __debug__'
        tree = ast.parse(source, optimize=1)
        func, variable = tree.body[1:]
        self.assertIsInstance(func.args.args[0].annotation, ast.Name)
        self.assertIsInstance(func.returns, ast.Name)
        self.assertIsInstance(variable.annotation, ast.Name)
        self.assertIs(func.args.defaults[0].value, False)
        self.assertIs(variable.value.value, False)
        tree = compile('x: __debug__', '?', 'exec', ast.PyCF_ONLY_AST | ast.PyCF_OPTIMIZED_AST | 0x1000000, optimize=1)
        self.assertIsInstance(tree.body[0].annotation, ast.Name)
        self.assertIsInstance(ast.parse('__debug__', mode='eval', optimize=1).body, ast.Constant)
        self.assertIsInstance(ast.parse('__debug__', mode='single', optimize=1).body[0].value, ast.Constant)

if __name__ == '__main__':
    unittest.main()
