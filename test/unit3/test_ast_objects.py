# CPython 3.14 Lib/test/test_ast/test_ast.py at 18ef0f0cb52.
# Complete upstream methods; unsupported helpers/optimizations follow separately.
import ast
import unittest
from textwrap import dedent
from test_type_parameters import SubTest

class ASTObjects(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_AST_objects(self):
        x = ast.AST()
        self.assertEqual(x._fields, ())
        x.foobar = 42
        self.assertEqual(x.foobar, 42)
        self.assertEqual(x.__dict__["foobar"], 42)

        with self.assertRaises(AttributeError):
            x.vararg

        with self.assertRaises(TypeError):
            # "ast.AST constructor takes 0 positional arguments"
            ast.AST(2)

    def test_dump(self):
        node = ast.parse('spam(eggs, "and cheese")')
        self.assertEqual(ast.dump(node),
            "Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load()), "
            "args=[Name(id='eggs', ctx=Load()), Constant(value='and cheese')]))])"
        )
        self.assertEqual(ast.dump(node, annotate_fields=False),
            "Module([Expr(Call(Name('spam', Load()), [Name('eggs', Load()), "
            "Constant('and cheese')]))])"
        )
        self.assertEqual(ast.dump(node, include_attributes=True),
            "Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load(), "
            "lineno=1, col_offset=0, end_lineno=1, end_col_offset=4), "
            "args=[Name(id='eggs', ctx=Load(), lineno=1, col_offset=5, "
            "end_lineno=1, end_col_offset=9), Constant(value='and cheese', "
            "lineno=1, col_offset=11, end_lineno=1, end_col_offset=23)], "
            "lineno=1, col_offset=0, end_lineno=1, end_col_offset=24), "
            "lineno=1, col_offset=0, end_lineno=1, end_col_offset=24)])"
        )

    def test_dump_indent(self):
        node = ast.parse('spam(eggs, "and cheese")')
        self.assertEqual(ast.dump(node, indent=3), """\
Module(
   body=[
      Expr(
         value=Call(
            func=Name(id='spam', ctx=Load()),
            args=[
               Name(id='eggs', ctx=Load()),
               Constant(value='and cheese')]))])""")
        self.assertEqual(ast.dump(node, annotate_fields=False, indent='\t'), """\
Module(
\t[
\t\tExpr(
\t\t\tCall(
\t\t\t\tName('spam', Load()),
\t\t\t\t[
\t\t\t\t\tName('eggs', Load()),
\t\t\t\t\tConstant('and cheese')]))])""")
        self.assertEqual(ast.dump(node, include_attributes=True, indent=3), """\
Module(
   body=[
      Expr(
         value=Call(
            func=Name(
               id='spam',
               ctx=Load(),
               lineno=1,
               col_offset=0,
               end_lineno=1,
               end_col_offset=4),
            args=[
               Name(
                  id='eggs',
                  ctx=Load(),
                  lineno=1,
                  col_offset=5,
                  end_lineno=1,
                  end_col_offset=9),
               Constant(
                  value='and cheese',
                  lineno=1,
                  col_offset=11,
                  end_lineno=1,
                  end_col_offset=23)],
            lineno=1,
            col_offset=0,
            end_lineno=1,
            end_col_offset=24),
         lineno=1,
         col_offset=0,
         end_lineno=1,
         end_col_offset=24)])""")

    def test_dump_show_empty(self):
        def check_node(node, empty, full, **kwargs):
            with self.subTest(show_empty=False):
                self.assertEqual(
                    ast.dump(node, show_empty=False, **kwargs),
                    empty,
                )
            with self.subTest(show_empty=True):
                self.assertEqual(
                    ast.dump(node, show_empty=True, **kwargs),
                    full,
                )

        def check_text(code, empty, full, **kwargs):
            check_node(ast.parse(code), empty, full, **kwargs)

        check_node(
            ast.arguments(),
            empty="arguments()",
            full="arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])",
        )

        check_node(
            # Corner case: there are no real `Name` instances with `id=''`:
            ast.Name(id='', ctx=ast.Load()),
            empty="Name(id='', ctx=Load())",
            full="Name(id='', ctx=Load())",
        )

        check_node(
            ast.MatchSingleton(value=None),
            empty="MatchSingleton(value=None)",
            full="MatchSingleton(value=None)",
        )

        check_node(
            ast.MatchSingleton(value=[]),
            empty="MatchSingleton(value=[])",
            full="MatchSingleton(value=[])",
        )

        check_node(
            ast.Constant(value=None),
            empty="Constant(value=None)",
            full="Constant(value=None)",
        )

        check_node(
            ast.Constant(value=[]),
            empty="Constant(value=[])",
            full="Constant(value=[])",
        )

        check_node(
            ast.Constant(value=''),
            empty="Constant(value='')",
            full="Constant(value='')",
        )

        check_node(
            ast.Interpolation(value=ast.Constant(42), str=None, conversion=-1),
            empty="Interpolation(value=Constant(value=42), str=None, conversion=-1)",
            full="Interpolation(value=Constant(value=42), str=None, conversion=-1)",
        )

        check_node(
            ast.Interpolation(value=ast.Constant(42), str=[], conversion=-1),
            empty="Interpolation(value=Constant(value=42), str=[], conversion=-1)",
            full="Interpolation(value=Constant(value=42), str=[], conversion=-1)",
        )

        check_text(
            "def a(b: int = 0, *, c): ...",
            empty="Module(body=[FunctionDef(name='a', args=arguments(args=[arg(arg='b', annotation=Name(id='int', ctx=Load()))], kwonlyargs=[arg(arg='c')], kw_defaults=[None], defaults=[Constant(value=0)]), body=[Expr(value=Constant(value=Ellipsis))])])",
            full="Module(body=[FunctionDef(name='a', args=arguments(posonlyargs=[], args=[arg(arg='b', annotation=Name(id='int', ctx=Load()))], kwonlyargs=[arg(arg='c')], kw_defaults=[None], defaults=[Constant(value=0)]), body=[Expr(value=Constant(value=Ellipsis))], decorator_list=[], type_params=[])], type_ignores=[])",
        )

        check_text(
            "def a(b: int = 0, *, c): ...",
            empty="Module(body=[FunctionDef(name='a', args=arguments(args=[arg(arg='b', annotation=Name(id='int', ctx=Load(), lineno=1, col_offset=9, end_lineno=1, end_col_offset=12), lineno=1, col_offset=6, end_lineno=1, end_col_offset=12)], kwonlyargs=[arg(arg='c', lineno=1, col_offset=21, end_lineno=1, end_col_offset=22)], kw_defaults=[None], defaults=[Constant(value=0, lineno=1, col_offset=15, end_lineno=1, end_col_offset=16)]), body=[Expr(value=Constant(value=Ellipsis, lineno=1, col_offset=25, end_lineno=1, end_col_offset=28), lineno=1, col_offset=25, end_lineno=1, end_col_offset=28)], lineno=1, col_offset=0, end_lineno=1, end_col_offset=28)])",
            full="Module(body=[FunctionDef(name='a', args=arguments(posonlyargs=[], args=[arg(arg='b', annotation=Name(id='int', ctx=Load(), lineno=1, col_offset=9, end_lineno=1, end_col_offset=12), lineno=1, col_offset=6, end_lineno=1, end_col_offset=12)], kwonlyargs=[arg(arg='c', lineno=1, col_offset=21, end_lineno=1, end_col_offset=22)], kw_defaults=[None], defaults=[Constant(value=0, lineno=1, col_offset=15, end_lineno=1, end_col_offset=16)]), body=[Expr(value=Constant(value=Ellipsis, lineno=1, col_offset=25, end_lineno=1, end_col_offset=28), lineno=1, col_offset=25, end_lineno=1, end_col_offset=28)], decorator_list=[], type_params=[], lineno=1, col_offset=0, end_lineno=1, end_col_offset=28)], type_ignores=[])",
            include_attributes=True,
        )

        check_text(
            'spam(eggs, "and cheese")',
            empty="Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load()), args=[Name(id='eggs', ctx=Load()), Constant(value='and cheese')]))])",
            full="Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load()), args=[Name(id='eggs', ctx=Load()), Constant(value='and cheese')], keywords=[]))], type_ignores=[])",
        )

        check_text(
            'spam(eggs, text="and cheese")',
            empty="Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load()), args=[Name(id='eggs', ctx=Load())], keywords=[keyword(arg='text', value=Constant(value='and cheese'))]))])",
            full="Module(body=[Expr(value=Call(func=Name(id='spam', ctx=Load()), args=[Name(id='eggs', ctx=Load())], keywords=[keyword(arg='text', value=Constant(value='and cheese'))]))], type_ignores=[])",
        )

        check_text(
            "import _ast as ast; from module import sub",
            empty="Module(body=[Import(names=[alias(name='_ast', asname='ast')]), ImportFrom(module='module', names=[alias(name='sub')], level=0)])",
            full="Module(body=[Import(names=[alias(name='_ast', asname='ast')]), ImportFrom(module='module', names=[alias(name='sub')], level=0)], type_ignores=[])",
        )

    def test_copy_location(self):
        src = ast.parse('1 + 1', mode='eval')
        src.body.right = ast.copy_location(ast.Constant(2), src.body.right)
        self.assertEqual(ast.dump(src, include_attributes=True),
            'Expression(body=BinOp(left=Constant(value=1, lineno=1, col_offset=0, '
            'end_lineno=1, end_col_offset=1), op=Add(), right=Constant(value=2, '
            'lineno=1, col_offset=4, end_lineno=1, end_col_offset=5), lineno=1, '
            'col_offset=0, end_lineno=1, end_col_offset=5))'
        )
        func = ast.Name('spam', ast.Load())
        src = ast.Call(col_offset=1, lineno=1, end_lineno=1, end_col_offset=1, func=func)
        new = ast.copy_location(src, ast.Call(col_offset=None, lineno=None, func=func))
        self.assertIsNone(new.end_lineno)
        self.assertIsNone(new.end_col_offset)
        self.assertEqual(new.lineno, 1)
        self.assertEqual(new.col_offset, 1)

    def test_fix_missing_locations(self):
        src = ast.parse('write("spam")')
        src.body.append(ast.Expr(ast.Call(ast.Name('spam', ast.Load()),
                                          [ast.Constant('eggs')], [])))
        self.assertEqual(src, ast.fix_missing_locations(src))
        self.maxDiff = None
        self.assertEqual(ast.dump(src, include_attributes=True),
            "Module(body=[Expr(value=Call(func=Name(id='write', ctx=Load(), "
            "lineno=1, col_offset=0, end_lineno=1, end_col_offset=5), "
            "args=[Constant(value='spam', lineno=1, col_offset=6, end_lineno=1, "
            "end_col_offset=12)], lineno=1, col_offset=0, end_lineno=1, "
            "end_col_offset=13), lineno=1, col_offset=0, end_lineno=1, "
            "end_col_offset=13), Expr(value=Call(func=Name(id='spam', ctx=Load(), "
            "lineno=1, col_offset=0, end_lineno=1, end_col_offset=0), "
            "args=[Constant(value='eggs', lineno=1, col_offset=0, end_lineno=1, "
            "end_col_offset=0)], lineno=1, col_offset=0, end_lineno=1, "
            "end_col_offset=0), lineno=1, col_offset=0, end_lineno=1, end_col_offset=0)])"
        )

    def test_increment_lineno(self):
        src = ast.parse('1 + 1', mode='eval')
        self.assertEqual(ast.increment_lineno(src, n=3), src)
        self.assertEqual(ast.dump(src, include_attributes=True),
            'Expression(body=BinOp(left=Constant(value=1, lineno=4, col_offset=0, '
            'end_lineno=4, end_col_offset=1), op=Add(), right=Constant(value=1, '
            'lineno=4, col_offset=4, end_lineno=4, end_col_offset=5), lineno=4, '
            'col_offset=0, end_lineno=4, end_col_offset=5))'
        )
        # issue10869: do not increment lineno of root twice
        src = ast.parse('1 + 1', mode='eval')
        self.assertEqual(ast.increment_lineno(src.body, n=3), src.body)
        self.assertEqual(ast.dump(src, include_attributes=True),
            'Expression(body=BinOp(left=Constant(value=1, lineno=4, col_offset=0, '
            'end_lineno=4, end_col_offset=1), op=Add(), right=Constant(value=1, '
            'lineno=4, col_offset=4, end_lineno=4, end_col_offset=5), lineno=4, '
            'col_offset=0, end_lineno=4, end_col_offset=5))'
        )
        src = ast.Call(
            func=ast.Name("test", ast.Load()), args=[], keywords=[], lineno=1
        )
        self.assertEqual(ast.increment_lineno(src).lineno, 2)
        self.assertIsNone(ast.increment_lineno(src).end_lineno)

    def test_iter_fields(self):
        node = ast.parse('foo()', mode='eval')
        d = dict(ast.iter_fields(node.body))
        self.assertEqual(d.pop('func').id, 'foo')
        self.assertEqual(d, {'keywords': [], 'args': []})

    def test_iter_child_nodes(self):
        node = ast.parse("spam(23, 42, eggs='leek')", mode='eval')
        self.assertEqual(len(list(ast.iter_child_nodes(node.body))), 4)
        iterator = ast.iter_child_nodes(node.body)
        self.assertEqual(next(iterator).id, 'spam')
        self.assertEqual(next(iterator).value, 23)
        self.assertEqual(next(iterator).value, 42)
        self.assertEqual(ast.dump(next(iterator)),
            "keyword(arg='eggs', value=Constant(value='leek'))"
        )

    def test_literal_eval(self):
        self.assertEqual(ast.literal_eval('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(ast.literal_eval('{"foo": 42}'), {"foo": 42})
        self.assertEqual(ast.literal_eval('(True, False, None)'), (True, False, None))
        self.assertEqual(ast.literal_eval('{1, 2, 3}'), {1, 2, 3})
        self.assertEqual(ast.literal_eval('b"hi"'), b"hi")
        self.assertEqual(ast.literal_eval('set()'), set())
        self.assertRaises(ValueError, ast.literal_eval, 'foo()')
        self.assertEqual(ast.literal_eval('6'), 6)
        self.assertEqual(ast.literal_eval('+6'), 6)
        self.assertEqual(ast.literal_eval('-6'), -6)
        self.assertEqual(ast.literal_eval('3.25'), 3.25)
        self.assertEqual(ast.literal_eval('+3.25'), 3.25)
        self.assertEqual(ast.literal_eval('-3.25'), -3.25)
        self.assertEqual(repr(ast.literal_eval('-0.0')), '-0.0')
        self.assertRaises(ValueError, ast.literal_eval, '++6')
        self.assertRaises(ValueError, ast.literal_eval, '+True')
        self.assertRaises(ValueError, ast.literal_eval, '2+3')

    def test_literal_eval_complex(self):
        # Issue #4907
        self.assertEqual(ast.literal_eval('6j'), 6j)
        self.assertEqual(ast.literal_eval('-6j'), -6j)
        self.assertEqual(ast.literal_eval('6.75j'), 6.75j)
        self.assertEqual(ast.literal_eval('-6.75j'), -6.75j)
        self.assertEqual(ast.literal_eval('3+6j'), 3+6j)
        self.assertEqual(ast.literal_eval('-3+6j'), -3+6j)
        self.assertEqual(ast.literal_eval('3-6j'), 3-6j)
        self.assertEqual(ast.literal_eval('-3-6j'), -3-6j)
        self.assertEqual(ast.literal_eval('3.25+6.75j'), 3.25+6.75j)
        self.assertEqual(ast.literal_eval('-3.25+6.75j'), -3.25+6.75j)
        self.assertEqual(ast.literal_eval('3.25-6.75j'), 3.25-6.75j)
        self.assertEqual(ast.literal_eval('-3.25-6.75j'), -3.25-6.75j)
        self.assertEqual(ast.literal_eval('(3+6j)'), 3+6j)
        self.assertRaises(ValueError, ast.literal_eval, '-6j+3')
        self.assertRaises(ValueError, ast.literal_eval, '-6j+3j')
        self.assertRaises(ValueError, ast.literal_eval, '3+-6j')
        self.assertRaises(ValueError, ast.literal_eval, '3+(0+6j)')
        self.assertRaises(ValueError, ast.literal_eval, '-(3+6j)')

    def test_literal_eval_malformed_dict_nodes(self):
        malformed = ast.Dict(keys=[ast.Constant(1), ast.Constant(2)], values=[ast.Constant(3)])
        self.assertRaises(ValueError, ast.literal_eval, malformed)
        malformed = ast.Dict(keys=[ast.Constant(1)], values=[ast.Constant(2), ast.Constant(3)])
        self.assertRaises(ValueError, ast.literal_eval, malformed)

    def test_literal_eval_trailing_ws(self):
        self.assertEqual(ast.literal_eval("    -1"), -1)
        self.assertEqual(ast.literal_eval("\t\t-1"), -1)
        self.assertEqual(ast.literal_eval(" \t -1"), -1)
        self.assertRaises(IndentationError, ast.literal_eval, "\n -1")

    def test_literal_eval_malformed_lineno(self):
        msg = r'malformed node or string on line 3:'
        with self.assertRaisesRegex(ValueError, msg):
            ast.literal_eval("{'a': 1,\n'b':2,\n'c':++3,\n'd':4}")

        node = ast.UnaryOp(
            ast.UAdd(), ast.UnaryOp(ast.UAdd(), ast.Constant(6)))
        self.assertIsNone(getattr(node, 'lineno', None))
        msg = r'malformed node or string:'
        with self.assertRaisesRegex(ValueError, msg):
            ast.literal_eval(node)

    def test_parser_constants_and_modern_fields(self):
        tree = compile("x = 123456789123456789123456789\ny = 2j\nz = b'hi'\n", '<ast>', 'exec', ast.PyCF_ONLY_AST)
        self.assertEqual(tree.body[0].value.value, 123456789123456789123456789)
        self.assertEqual(tree.body[1].value.value, 2j)
        self.assertEqual(tree.body[2].value.value, b'hi')
        tree = ast.parse('def f[T](x: T): pass')
        self.assertEqual(tree.body[0].type_params[0].name, 'T')
        self.assertIsInstance(tree.body[0].args.args[0].annotation, ast.Name)
        self.assertEqual(ast.Name._field_types['id'], str)
        self.assertEqual(ast.Name.__match_args__, ('id', 'ctx'))

if __name__ == '__main__': unittest.main()
