# Complete CPython 3.14 function-type methods at 18ef0f0cb52.
import ast
import unittest
from test_annotationlib import HarnessCase

class FunctionTypeTests(HarnessCase):

    def test_func_type_input(self):

        def parse_func_type_input(source):
            return ast.parse(source, "<unknown>", "func_type")

        # Some checks below will crash if the returned structure is wrong
        tree = parse_func_type_input("() -> int")
        self.assertEqual(tree.argtypes, [])
        self.assertEqual(tree.returns.id, "int")

        tree = parse_func_type_input("(int) -> List[str]")
        self.assertEqual(len(tree.argtypes), 1)
        arg = tree.argtypes[0]
        self.assertEqual(arg.id, "int")
        self.assertEqual(tree.returns.value.id, "List")
        self.assertEqual(tree.returns.slice.id, "str")

        tree = parse_func_type_input("(int, *str, **Any) -> float")
        self.assertEqual(tree.argtypes[0].id, "int")
        self.assertEqual(tree.argtypes[1].id, "str")
        self.assertEqual(tree.argtypes[2].id, "Any")
        self.assertEqual(tree.returns.id, "float")

        tree = parse_func_type_input("(*int) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        tree = parse_func_type_input("(**int) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        tree = parse_func_type_input("(*int, **str) -> None")
        self.assertEqual(tree.argtypes[0].id, "int")
        self.assertEqual(tree.argtypes[1].id, "str")

        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(int, *str, *Any) -> float")

        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(int, **str, Any) -> float")

        with self.assertRaises(SyntaxError):
            tree = parse_func_type_input("(**int, **str) -> float")

    def test_parse_ast_func_type(self):
        # see gh-156689
        tree = ast.parse('(int, str) -> bool', mode='func_type')
        self.assertEqual(ast.dump(ast.parse(tree, mode='func_type')),
                         ast.dump(tree))
        self.assertRaises(TypeError, ast.parse, ast.Constant(42),
                          mode='func_type')
        self.assertRaises(TypeError, ast.parse, tree, mode='exec')

    # CPython-checked public compiler boundary: FunctionType is AST-only.
    def test_function_type_flags_and_edited_validation(self):
        source = '(int, __debug__) -> list[str]'
        with self.assertRaisesRegex(ValueError, "requires flag PyCF_ONLY_AST"):
            compile(source, '<type>', 'func_type')
        original = ast.parse(source, mode='func_type')
        before = ast.dump(original, include_attributes=True)
        for source_or_ast in (source, original):
            for optimize in (0, 1, 2):
                result = compile(source_or_ast, '<type>', 'func_type', ast.PyCF_OPTIMIZED_AST, optimize=optimize)
                self.assertIsInstance(result, ast.FunctionType)
                self.assertIsInstance(result.argtypes[1], ast.Name)
                self.assertTrue(ast.compare(original, result, compare_attributes=True))
        self.assertEqual(ast.dump(original, include_attributes=True), before)
        invalid = ast.fix_missing_locations(ast.FunctionType(
            argtypes=[ast.Name('x', ast.Store())], returns=ast.Name('y', ast.Load())))
        with self.assertRaises(ValueError):
            compile(invalid, '<type>', 'func_type', ast.PyCF_ONLY_AST)
        with self.assertRaises(TypeError):
            ast.parse(original, mode='eval')

if __name__ == '__main__':
    unittest.main()
