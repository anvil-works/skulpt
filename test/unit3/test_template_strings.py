# CPython 3.14 template tests at 18ef0f0cb52.
import unittest
from string.templatelib import Template, Interpolation, convert

class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False
class HarnessCase(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertRaisesRegex(self, exception, regex):
        # Skulpt re uses JavaScript regexes, which require literal braces escaped.
        return super().assertRaisesRegex(exception, regex.replace("{", r"\{").replace("}", r"\}"))

# Upstream assertions unchanged.
class TStringBaseCase:
    def assertInterpolationEqual(self, i, exp):
        """Test Interpolation equality.

        The *i* argument must be an Interpolation instance.

        The *exp* argument must be a tuple of the form
        (value, expression, conversion, format_spec) where the final three
        items may be omitted and are assumed to be '', None and '' respectively.
        """
        if len(exp) == 4:
            actual = (i.value, i.expression, i.conversion, i.format_spec)
            self.assertEqual(actual, exp)
        elif len(exp) == 3:
            self.assertEqual((i.value, i.expression, i.conversion), exp)
            self.assertEqual(i.format_spec, "")
        elif len(exp) == 2:
            self.assertEqual((i.value, i.expression), exp)
            self.assertEqual(i.conversion, None)
            self.assertEqual(i.format_spec, "")
        elif len(exp) == 1:
            self.assertEqual((i.value,), exp)
            self.assertEqual(i.expression, "")
            self.assertEqual(i.conversion, None)
            self.assertEqual(i.format_spec, "")

    def assertTStringEqual(self, t, strings, interpolations):
        """Test template string literal equality.

        The *strings* argument must be a tuple of strings equal to *t.strings*.

        The *interpolations* argument must be a sequence of tuples which are
        compared against *t.interpolations*. Each tuple must match the form
        described in the `assertInterpolationEqual` method.
        """
        self.assertEqual(t.strings, strings)
        self.assertEqual(len(t.interpolations), len(interpolations))

        for i, exp in zip(t.interpolations, interpolations, strict=True):
            self.assertInterpolationEqual(i, exp)

# Equivalent test helper until compiler match support: preserve the same formatting.
def fstring(template):
    parts = []
    for item in template:
        if isinstance(item, str):
            parts.append(item)
        else:
            parts.append(format(convert(item.value, item.conversion), item.format_spec))
    return ''.join(parts)

class TestTemplate(HarnessCase, TStringBaseCase):
    def test_common(self):
        self.assertEqual(type(t'').__name__, 'Template')
        self.assertEqual(type(t'').__qualname__, 'Template')
        self.assertEqual(type(t'').__module__, 'string.templatelib')

        a = 'a'
        i = t'{a}'.interpolations[0]
        self.assertEqual(type(i).__name__, 'Interpolation')
        self.assertEqual(type(i).__qualname__, 'Interpolation')
        self.assertEqual(type(i).__module__, 'string.templatelib')
    def test_final_types(self):
        with self.assertRaisesRegex(TypeError, 'is not an acceptable base type'):
            class Sub(Template): ...

        with self.assertRaisesRegex(TypeError, 'is not an acceptable base type'):
            class Sub(Interpolation): ...
    def test_basic_creation(self):
        # Simple t-string creation
        t = t'Hello, world'
        self.assertIsInstance(t, Template)
        self.assertTStringEqual(t, ('Hello, world',), ())
        self.assertEqual(fstring(t), 'Hello, world')

        # Empty t-string
        t = t''
        self.assertTStringEqual(t, ('',), ())
        self.assertEqual(fstring(t), '')

        # Multi-line t-string
        t = t"""Hello,
world"""
        self.assertEqual(t.strings, ('Hello,\nworld',))
        self.assertEqual(len(t.interpolations), 0)
        self.assertEqual(fstring(t), 'Hello,\nworld')
    def test_interpolation_creation(self):
        i = Interpolation('Maria', 'name', 'a', 'fmt')
        self.assertInterpolationEqual(i, ('Maria', 'name', 'a', 'fmt'))

        i = Interpolation('Maria', 'name', 'a')
        self.assertInterpolationEqual(i, ('Maria', 'name', 'a'))

        i = Interpolation('Maria', 'name')
        self.assertInterpolationEqual(i, ('Maria', 'name'))

        i = Interpolation('Maria')
        self.assertInterpolationEqual(i, ('Maria',))
    def test_creation_interleaving(self):
        # Should add strings on either side
        t = Template(Interpolation('Maria', 'name', None, ''))
        self.assertTStringEqual(t, ('', ''), [('Maria', 'name')])
        self.assertEqual(fstring(t), 'Maria')

        # Should prepend empty string
        t = Template(Interpolation('Maria', 'name', None, ''), ' is my name')
        self.assertTStringEqual(t, ('', ' is my name'), [('Maria', 'name')])
        self.assertEqual(fstring(t), 'Maria is my name')

        # Should append empty string
        t = Template('Hello, ', Interpolation('Maria', 'name', None, ''))
        self.assertTStringEqual(t, ('Hello, ', ''), [('Maria', 'name')])
        self.assertEqual(fstring(t), 'Hello, Maria')

        # Should concatenate strings
        t = Template('Hello', ', ', Interpolation('Maria', 'name', None, ''),
                     '!')
        self.assertTStringEqual(t, ('Hello, ', '!'), [('Maria', 'name')])
        self.assertEqual(fstring(t), 'Hello, Maria!')

        # Should add strings on either side and in between
        t = Template(Interpolation('Maria', 'name', None, ''),
                     Interpolation('Python', 'language', None, ''))
        self.assertTStringEqual(
            t, ('', '', ''), [('Maria', 'name'), ('Python', 'language')]
        )
        self.assertEqual(fstring(t), 'MariaPython')
    def test_template_values(self):
        t = t'Hello, world'
        self.assertEqual(t.values, ())

        name = "Lys"
        t = t'Hello, {name}'
        self.assertEqual(t.values, ("Lys",))

        country = "GR"
        age = 0
        t = t'Hello, {name}, {age} from {country}'
        self.assertEqual(t.values, ("Lys", 0, "GR"))

class TemplateIterTests(HarnessCase):
    def test_final(self):
        TemplateIter = type(iter(t''))
        with self.assertRaisesRegex(TypeError, 'is not an acceptable base type'):
            class Sub(TemplateIter): ...
    def test_iter(self):
        x = 1
        res = list(iter(t'abc {x} yz'))

        self.assertEqual(res[0], 'abc ')
        self.assertIsInstance(res[1], Interpolation)
        self.assertEqual(res[1].value, 1)
        self.assertEqual(res[1].expression, 'x')
        self.assertEqual(res[1].conversion, None)
        self.assertEqual(res[1].format_spec, '')
        self.assertEqual(res[2], ' yz')
    def test_exhausted(self):
        # See https://github.com/python/cpython/issues/134119.
        template_iter = iter(t"{1}")
        self.assertIsInstance(next(template_iter), Interpolation)
        self.assertRaises(StopIteration, next, template_iter)
        self.assertRaises(StopIteration, next, template_iter)

class TestFunctions(HarnessCase):
    def test_convert(self):
        from fractions import Fraction

        for obj in ('Café', None, 3.14, Fraction(1, 2)):
            with self.subTest(f'{obj=}'):
                self.assertEqual(convert(obj, None), obj)
                self.assertEqual(convert(obj, 's'), str(obj))
                self.assertEqual(convert(obj, 'r'), repr(obj))
                self.assertEqual(convert(obj, 'a'), ascii(obj))

                # Invalid conversion specifier
                with self.assertRaises(ValueError):
                    convert(obj, 'z')
                with self.assertRaises(ValueError):
                    convert(obj, 1)
                with self.assertRaises(ValueError):
                    convert(obj, object())

class TestTString(HarnessCase, TStringBaseCase):
    def test_string_representation(self):
        # Test __repr__
        t = t"Hello"
        self.assertEqual(repr(t), "Template(strings=('Hello',), interpolations=())")

        name = "Python"
        t = t"Hello, {name}"
        self.assertEqual(repr(t),
            "Template(strings=('Hello, ', ''), "
            "interpolations=(Interpolation('Python', 'name', None, ''),))"
        )
    def test_interpolation_basics(self):
        # Test basic interpolation
        name = "Python"
        t = t"Hello, {name}"
        self.assertTStringEqual(t, ("Hello, ", ""), [(name, "name")])
        self.assertEqual(fstring(t), "Hello, Python")

        # Multiple interpolations
        first = "Python"
        last = "Developer"
        t = t"{first} {last}"
        self.assertTStringEqual(
            t, ("", " ", ""), [(first, 'first'), (last, 'last')]
        )
        self.assertEqual(fstring(t), "Python Developer")

        # Interpolation with expressions
        a = 10
        b = 20
        t = t"Sum: {a + b}"
        self.assertTStringEqual(t, ("Sum: ", ""), [(a + b, "a + b")])
        self.assertEqual(fstring(t), "Sum: 30")

        # Interpolation with function
        def square(x):
            return x * x
        t = t"Square: {square(5)}"
        self.assertTStringEqual(
            t, ("Square: ", ""), [(square(5), "square(5)")]
        )
        self.assertEqual(fstring(t), "Square: 25")

        # Test attribute access in expressions
        class Person:
            def __init__(self, name):
                self.name = name

            def upper(self):
                return self.name.upper()

        person = Person("Alice")
        t = t"Name: {person.name}"
        self.assertTStringEqual(
            t, ("Name: ", ""), [(person.name, "person.name")]
        )
        self.assertEqual(fstring(t), "Name: Alice")

        # Test method calls
        t = t"Name: {person.upper()}"
        self.assertTStringEqual(
            t, ("Name: ", ""), [(person.upper(), "person.upper()")]
        )
        self.assertEqual(fstring(t), "Name: ALICE")

        # Test dictionary access
        data = {"name": "Bob", "age": 30}
        t = t"Name: {data['name']}, Age: {data['age']}"
        self.assertTStringEqual(
            t, ("Name: ", ", Age: ", ""),
            [(data["name"], "data['name']"), (data["age"], "data['age']")],
        )
        self.assertEqual(fstring(t), "Name: Bob, Age: 30")
    def test_format_specifiers(self):
        # Test basic format specifiers
        value = 3.14159
        t = t"Pi: {value:.2f}"
        self.assertTStringEqual(
            t, ("Pi: ", ""), [(value, "value", None, ".2f")]
        )
        self.assertEqual(fstring(t), "Pi: 3.14")

        a = 3
        b = 4
        t = t"{a!=b:>10}"
        self.assertTStringEqual(
            t, ("", ""), [(a != b, "a!=b", None, ">10")]
        )
        self.assertEqual(fstring(t), "         1")
    def test_conversions(self):
        # Test !s conversion (str)
        obj = object()
        t = t"Object: {obj!s}"
        self.assertTStringEqual(t, ("Object: ", ""), [(obj, "obj", "s")])
        self.assertEqual(fstring(t), f"Object: {str(obj)}")

        # Test !r conversion (repr)
        t = t"Data: {obj!r}"
        self.assertTStringEqual(t, ("Data: ", ""), [(obj, "obj", "r")])
        self.assertEqual(fstring(t), f"Data: {repr(obj)}")

        # Test !a conversion (ascii)
        text = "Café"
        t = t"ASCII: {text!a}"
        self.assertTStringEqual(t, ("ASCII: ", ""), [(text, "text", "a")])
        self.assertEqual(fstring(t), f"ASCII: {ascii(text)}")

        # Test !z conversion (error)
        num = 1
        with self.assertRaises(SyntaxError):
            eval("t'{num!z}'")
    def test_debug_specifier(self):
        # Test debug specifier
        value = 42
        t = t"Value: {value=}"
        self.assertTStringEqual(
            t, ("Value: value=", ""), [(value, "value", "r")]
        )
        self.assertEqual(fstring(t), "Value: value=42")

        # Test debug specifier with format (conversion default to !r)
        t = t"Value: {value=:.2f}"
        self.assertTStringEqual(
            t, ("Value: value=", ""), [(value, "value", None, ".2f")]
        )
        self.assertEqual(fstring(t), "Value: value=42.00")

        # Test debug specifier with conversion
        t = t"Value: {value=!s}"
        self.assertTStringEqual(
            t, ("Value: value=", ""), [(value, "value", "s")]
        )

        # Test white space in debug specifier
        t = t"Value: {value = }"
        self.assertTStringEqual(
            t, ("Value: value = ", ""), [(value, "value ", "r")]
        )
        self.assertEqual(fstring(t), "Value: value = 42")

        # Explicit line continuations after the debug marker are part of
        # the debug text, not the interpolation expression.
        for template, strings, interpolation, rendered in (
            (
                t"""Value: {value =\
}""",
                ("Value: value =\\\n", ""),
                (value, "value ", "r"),
                "Value: value =\\\n42",
            ),
            (
                t"""Value: {value =\
!r}""",
                ("Value: value =\\\n", ""),
                (value, "value ", "r"),
                "Value: value =\\\n42",
            ),
            (
                t"""Value: {value =\
:04}""",
                ("Value: value =\\\n", ""),
                (value, "value ", None, "04"),
                "Value: value =\\\n0042",
            ),
            (
                t"""Value: {value =\
\
}""",
                ("Value: value =\\\n\\\n", ""),
                (value, "value ", "r"),
                "Value: value =\\\n\\\n42",
            ),
        ):
            with self.subTest(template=template):
                self.assertTStringEqual(template, strings, [interpolation])
                self.assertEqual(fstring(template), rendered)
    def test_interpolation_expression_whitespace(self):
        x = 42
        for template, expected in (
            (t"{x}", "x"),
            (t"{x }", "x "),
            (t"{ x}", " x"),
            (t"{ x }", " x "),
            (t"{  x  }", "  x  "),
            (t"""{
  x
}""", "\n  x\n"),
            (t"{ x !r}", " x "),
            (t"{ x :.2f}", " x "),
            (t"{ x = }", " x "),
            (t"{ x = !r}", " x "),
            (t"{ x = :.2f}", " x "),
            (t"{x == 42 = }", "x == 42 "),
        ):
            with self.subTest(template=template):
                self.assertEqual(
                    template.interpolations[0].expression,
                    expected,
                )
    def test_raw_tstrings(self):
        path = r"C:\Users"
        t = rt"{path}\Documents"
        self.assertTStringEqual(t, ("", r"\Documents"), [(path, "path")])
        self.assertEqual(fstring(t), r"C:\Users\Documents")

        # Test alternative prefix
        t = tr"{path}\Documents"
        self.assertTStringEqual(t, ("", r"\Documents"), [(path, "path")])
    def test_template_concatenation(self):
        # Test template + template
        t1 = t"Hello, "
        t2 = t"world"
        combined = t1 + t2
        self.assertTStringEqual(combined, ("Hello, world",), ())
        self.assertEqual(fstring(combined), "Hello, world")

        # Test template + string
        t1 = t"Hello"
        expected_msg = 'can only concatenate string.templatelib.Template ' \
            '\\(not "str"\\) to string.templatelib.Template'
        with self.assertRaisesRegex(TypeError, expected_msg):
            t1 + ", world"

        # Test template + template with interpolation
        name = "Python"
        t1 = t"Hello, "
        t2 = t"{name}"
        combined = t1 + t2
        self.assertTStringEqual(combined, ("Hello, ", ""), [(name, "name")])
        self.assertEqual(fstring(combined), "Hello, Python")

        # Test string + template
        expected_msg = 'can only concatenate str ' \
            '\\(not "string.templatelib.Template"\\) to str'
        with self.assertRaisesRegex(TypeError, expected_msg):
            "Hello, " + t"{name}"
    def test_nested_templates(self):
        # Test a template inside another template expression
        name = "Python"
        inner = t"{name}"
        t = t"Language: {inner}"

        t_interp = t.interpolations[0]
        self.assertEqual(t.strings, ("Language: ", ""))
        self.assertEqual(t_interp.value.strings, ("", ""))
        self.assertEqual(t_interp.value.interpolations[0].value, name)
        self.assertEqual(t_interp.value.interpolations[0].expression, "name")
        self.assertEqual(t_interp.value.interpolations[0].conversion, None)
        self.assertEqual(t_interp.value.interpolations[0].format_spec, "")
        self.assertEqual(t_interp.expression, "inner")
        self.assertEqual(t_interp.conversion, None)
        self.assertEqual(t_interp.format_spec, "")
    def test_syntax_errors(self):
        for case, err in (
            ("t'", "unterminated t-string literal"),
            ("t'''", "unterminated triple-quoted t-string literal"),
            ("t''''", "unterminated triple-quoted t-string literal"),
            ("t'{", "'{' was never closed"),
            ("t'{'", "t-string: expecting '}'"),
            ("t'{a'", "t-string: expecting '}'"),
            ("t'}'", "t-string: single '}' is not allowed"),
            ("t'{}'", "t-string: valid expression required before '}'"),
            ("t'{=x}'", "t-string: valid expression required before '='"),
            ("t'{!x}'", "t-string: valid expression required before '!'"),
            ("t'{:x}'", "t-string: valid expression required before ':'"),
            ("t'{x;y}'", "t-string: expecting '=', or '!', or ':', or '}'"),
            ("t'{x=y}'", "t-string: expecting '!', or ':', or '}'"),
            ("t'{x!s!}'", "t-string: expecting ':' or '}'"),
            ("t'{x!s:'", "t-string: expecting '}', or format specs"),
            ("t'{x!}'", "t-string: missing conversion character"),
            ("t'{x=!}'", "t-string: missing conversion character"),
            ("t'{x!z}'", "t-string: invalid conversion character 'z': "
                         "expected 's', 'r', or 'a'"),
            ("t'{lambda:1}'", "t-string: lambda expressions are not allowed "
                              "without parentheses"),
            ("t'{x:{;}}'", "t-string: expecting a valid expression after '{'"),
            ("t'{1:d\n}'", "t-string: newlines are not allowed in format specifiers")
        ):
            with self.subTest(case), self.assertRaisesRegex(SyntaxError, err):
                eval(case)
    def test_runtime_errors(self):
        # Test missing variables
        with self.assertRaises(NameError):
            eval("t'Hello, {name}'")
    def test_literal_concatenation(self):
        # Test concatenation of t-string literals
        t = t"Hello, " t"world"
        self.assertTStringEqual(t, ("Hello, world",), ())
        self.assertEqual(fstring(t), "Hello, world")

        # Test concatenation with interpolation
        name = "Python"
        t = t"Hello, " t"{name}"
        self.assertTStringEqual(t, ("Hello, ", ""), [(name, "name")])
        self.assertEqual(fstring(t), "Hello, Python")

        # Test disallowed mix of t-string and string/f-string (incl. bytes)
        what = 't'
        expected_msg = 'cannot mix t-string literals with string or bytes literals'
        for case in (
            "t'{what}-string literal' 'str literal'",
            "t'{what}-string literal' u'unicode literal'",
            "t'{what}-string literal' f'f-string literal'",
            "t'{what}-string literal' r'raw string literal'",
            "t'{what}-string literal' rf'raw f-string literal'",
            "t'{what}-string literal' b'bytes literal'",
            "t'{what}-string literal' br'raw bytes literal'",
            "'str literal' t'{what}-string literal'",
            "u'unicode literal' t'{what}-string literal'",
            "f'f-string literal' t'{what}-string literal'",
            "r'raw string literal' t'{what}-string literal'",
            "rf'raw f-string literal' t'{what}-string literal'",
            "b'bytes literal' t'{what}-string literal'",
            "br'raw bytes literal' t'{what}-string literal'",
        ):
            with self.subTest(case):
                with self.assertRaisesRegex(SyntaxError, expected_msg):
                    eval(case)
    def test_triple_quoted(self):
        # Test triple-quoted t-strings
        t = t"""
        Hello,
        world
        """
        self.assertTStringEqual(
            t, ("\n        Hello,\n        world\n        ",), ()
        )
        self.assertEqual(fstring(t), "\n        Hello,\n        world\n        ")

        # Test triple-quoted with interpolation
        name = "Python"
        t = t"""
        Hello,
        {name}
        """
        self.assertTStringEqual(
            t, ("\n        Hello,\n        ", "\n        "), [(name, "name")]
        )
        self.assertEqual(fstring(t), "\n        Hello,\n        Python\n        ")


class TemplateCompilerRegression(HarnessCase, TStringBaseCase):
    def test_evaluation_and_suspended_values(self):
        calls = []
        class Value:
            def __format__(self, spec):
                raise AssertionError('template creation must not format values')
            def __repr__(self):
                raise AssertionError('template creation must not convert values')
        value = Value()
        def item():
            calls.append('value')
            return value
        def spec():
            calls.append('spec')
            return 4
        template = t'{item()!r:{spec()}}'
        self.assertEqual(calls, ['value', 'spec'])
        interpolation = template.interpolations[0]
        self.assertIs(interpolation.value, value)
        self.assertEqual(interpolation.conversion, 'r')
        self.assertEqual(interpolation.format_spec, '4')

        def generator():
            return t'{(yield "value")}:{(yield "second")}:{3:{(yield "width")}}'
        g = generator()
        self.assertEqual(next(g), 'value')
        self.assertEqual(g.send(value), 'second')
        self.assertEqual(g.send(2), 'width')
        try:
            g.send(4)
        except StopIteration as exc:
            template = exc.value
        self.assertEqual(template.values, (value, 2, 3))
        self.assertEqual(template.interpolations[2].format_spec, '4')

    def test_native_constructor_validation_and_reduction(self):
        for field in ('expression', 'conversion', 'format_spec'):
            with self.assertRaises(TypeError):
                Interpolation(1, **{field: 2})
        with self.assertRaises(ValueError):
            Interpolation(1, conversion='z')
        with self.assertRaises(TypeError):
            Template(1)
        with self.assertRaises(TypeError):
            Template(strings=('a',))
        interpolation = Interpolation(1, 'x', 'r', '04')
        for field in ('value', 'expression', 'conversion', 'format_spec'):
            with self.assertRaises(AttributeError):
                setattr(interpolation, field, None)
        template = Template('a', interpolation, 'b')
        for field in ('strings', 'interpolations', 'values'):
            with self.assertRaises(AttributeError):
                setattr(template, field, ())
        rebuild, args = template.__reduce__()
        self.assertTStringEqual(rebuild(*args), ('a', 'b'), [(1, 'x', 'r', '04')])
        rebuild, args = interpolation.__reduce__()
        self.assertInterpolationEqual(rebuild(*args), (1, 'x', 'r', '04'))
        for cls in (Template, Interpolation):
            alias = cls[int]
            self.assertIs(alias.__origin__, cls)
            self.assertEqual(alias.__args__, (int,))

# This upstream unparse round-trip needs the parser's dev.8 metadata fixes.
from test_ast_unparse import ASTTestCase

class TemplateUnparseCases(ASTTestCase):
    def test_tstrings(self):
        self.check_ast_roundtrip("t'foo'")
        self.check_ast_roundtrip("t'foo {bar}'")
        self.check_ast_roundtrip("t'foo {bar!s:.2f}'")
        self.check_ast_roundtrip("t'{a +    b}'")
        self.check_ast_roundtrip("t'{a +    b:x}'")
        self.check_ast_roundtrip("t'{a +    b!s}'")
        self.check_ast_roundtrip("t'{ {a}}'")
        self.check_ast_roundtrip("t'{ {a}=}'")
        self.check_ast_roundtrip("t'{{a}}'")
        self.check_ast_roundtrip("t''")
        self.check_ast_roundtrip('t""')
        self.check_ast_roundtrip("t'{(lambda x: x)}'")
        self.check_ast_roundtrip("t'{t'{x}'}'")
        self.check_ast_roundtrip(
            r"""t'''{(
                1,  # Force lexer metadata reconstruction.
                "\"#")}'''"""
        )
        self.check_ast_roundtrip(
            r'''t"""Value: {value =\
}"""'''
        )

class TemplateASTCompilation(TStringBaseCase, HarnessCase):
    def test_missing_expression_metadata(self):
        import ast
        tree = ast.fix_missing_locations(ast.Expression(ast.TemplateStr([
            ast.Interpolation(ast.BinOp(ast.Name('x'), ast.Add(), ast.Constant(1)),
                              str=None, conversion=-1)])))
        result = eval(compile(tree, '<template>', 'eval'), {'x': 2})
        self.assertTStringEqual(result, ('', ''), [(3, None)])
        tree.body.values[0].str = 'x+1'
        result = eval(compile(tree, '<template>', 'eval'), {'x': 2})
        self.assertTStringEqual(result, ('', ''), [(3, 'x+1')])
        self.assertIs(compile(tree, '<copy>', 'eval', ast.PyCF_ONLY_AST).body.values[0].str, tree.body.values[0].str)

    def test_invalid_conversion(self):
        import ast
        for value, container in ((ast.Interpolation(ast.Constant(1), 'x', 255), ast.TemplateStr),
                                 (ast.FormattedValue(ast.Constant(1), 255), ast.JoinedStr)):
            tree = ast.fix_missing_locations(ast.Expression(container([value])))
            with self.assertRaisesRegex(SystemError, 'Unrecognized conversion character 255'):
                compile(tree, '<conversion>', 'eval')

if __name__ == '__main__': unittest.main()
