# Python-2.0 license. CPython 3.14 test_ast ASTValidatorTests pattern fixture.
import ast
import unittest
from contextlib import nullcontext

class PatternASTValidationTests(unittest.TestCase):
    def subTest(self, *args, **kwargs): return nullcontext()

    constant_1 = ast.Constant(1)


    pattern_1 = ast.MatchValue(constant_1)


    constant_x = ast.Constant('x')


    pattern_x = ast.MatchValue(constant_x)


    constant_true = ast.Constant(True)


    pattern_true = ast.MatchSingleton(True)


    name_carter = ast.Name('carter', ast.Load())


    _MATCH_PATTERNS = [
        ast.MatchValue(
            ast.Attribute(
                ast.Attribute(
                    ast.Name('x', ast.Store()),
                    'y', ast.Load()
                ),
                'z', ast.Load()
            )
        ),
        ast.MatchValue(
            ast.Attribute(
                ast.Attribute(
                    ast.Name('x', ast.Load()),
                    'y', ast.Store()
                ),
                'z', ast.Load()
            )
        ),
        ast.MatchValue(
            ast.Constant(...)
        ),
        ast.MatchValue(
            ast.Constant(True)
        ),
        ast.MatchValue(
            ast.Constant((1,2,3))
        ),
        ast.MatchSingleton('string'),
        ast.MatchSequence([
          ast.MatchSingleton('string')
        ]),
        ast.MatchSequence(
            [
                ast.MatchSequence(
                    [
                        ast.MatchSingleton('string')
                    ]
                )
            ]
        ),
        ast.MatchMapping(
            [constant_1, constant_true],
            [pattern_x]
        ),
        ast.MatchMapping(
            [constant_true, constant_1],
            [pattern_x, pattern_1],
            rest='True'
        ),
        ast.MatchMapping(
            [constant_true, ast.Starred(ast.Name('lol', ast.Load()), ast.Load())],
            [pattern_x, pattern_1],
            rest='legit'
        ),
        ast.MatchClass(
            ast.Attribute(
                ast.Attribute(
                    constant_x,
                    'y', ast.Load()),
                'z', ast.Load()),
            patterns=[], kwd_attrs=[], kwd_patterns=[]
        ),
        ast.MatchClass(
            name_carter,
            patterns=[],
            kwd_attrs=['True'],
            kwd_patterns=[pattern_1]
        ),
        ast.MatchClass(
            name_carter,
            patterns=[],
            kwd_attrs=[],
            kwd_patterns=[pattern_1]
        ),
        ast.MatchClass(
            name_carter,
            patterns=[ast.MatchSingleton('string')],
            kwd_attrs=[],
            kwd_patterns=[]
        ),
        ast.MatchClass(
            name_carter,
            patterns=[ast.MatchStar()],
            kwd_attrs=[],
            kwd_patterns=[]
        ),
        ast.MatchClass(
            name_carter,
            patterns=[],
            kwd_attrs=[],
            kwd_patterns=[ast.MatchStar()]
        ),
        ast.MatchClass(
            constant_true,  # invalid name
            patterns=[],
            kwd_attrs=['True'],
            kwd_patterns=[pattern_1]
        ),
        ast.MatchSequence(
            [
                ast.MatchStar("True")
            ]
        ),
        ast.MatchAs(
            name='False'
        ),
        ast.MatchOr(
            []
        ),
        ast.MatchOr(
            [pattern_1]
        ),
        ast.MatchOr(
            [pattern_1, pattern_x, ast.MatchSingleton('xxx')]
        ),
        ast.MatchAs(name="_"),
        ast.MatchStar(name="x"),
        ast.MatchSequence([ast.MatchStar("_")]),
        ast.MatchMapping([], [], rest="_"),
    ]


    def test_match_validation_pattern(self):
        name_x = ast.Name('x', ast.Load())
        for pattern in self._MATCH_PATTERNS:
            with self.subTest(ast.dump(pattern, indent=4)):
                node = ast.Match(
                    subject=name_x,
                    cases = [
                        ast.match_case(
                            pattern=pattern,
                            body = [ast.Pass()]
                        )
                    ]
                )
                node = ast.fix_missing_locations(node)
                module = ast.Module([node], [])
                with self.assertRaises(ValueError):
                    compile(module, "<test>", "exec")



if __name__ == "__main__":
    unittest.main()
