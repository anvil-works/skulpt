# CPython 3.14 Lib/test/test_source_encoding.py at 18ef0f0cb52.
# Methods/assertions unchanged; only subTest infrastructure adapted.
import unittest

class MiscSourceEncodingTest(unittest.TestCase):
    def test_compilestring(self):
        # see #1882
        c = compile(b"\n# coding: utf-8\nu = '\xc3\xb3'\n", "dummy", "exec")
        d = {}
        exec(c, d)
        self.assertEqual(d['u'], '\xf3')

    def test_issue2301(self):
        try:
            compile(b"# coding: cp932\nprint '\x94\x4e'", "dummy", "exec")
        except SyntaxError as v:
            self.assertEqual(v.text.rstrip('\n'), "print '\u5e74'")
        else:
            self.fail()

    def test_issue4626(self):
        c = compile("# coding=latin-1\n\u00c6 = '\u00c6'", "dummy", "exec")
        d = {}
        exec(c, d)
        self.assertEqual(d['\xc6'], '\xc6')

    def test_issue3297(self):
        c = compile("a, b = '\U0001010F', '\\U0001010F'", "dummy", "exec")
        d = {}
        exec(c, d)
        self.assertEqual(d['a'], d['b'])
        self.assertEqual(len(d['a']), len(d['b']))
        self.assertEqual(ascii(d['a']), ascii(d['b']))

    def test_issue7820(self):
        # Ensure that check_bom() restores all bytes in the right order if
        # check_bom() fails in pydebug mode: a buffer starts with the first
        # byte of a valid BOM, but next bytes are different

        # one byte in common with the UTF-16-LE BOM
        self.assertRaises(SyntaxError, eval, b'\xff\x20')

        # one byte in common with the UTF-8 BOM
        self.assertRaises(SyntaxError, eval, b'\xef\x20')

        # two bytes in common with the UTF-8 BOM
        self.assertRaises(SyntaxError, eval, b'\xef\xbb\x20')

    def test_truncated_utf8_at_eof(self):
        # Regression test for https://issues.oss-fuzz.com/issues/451112368
        # Truncated multi-byte UTF-8 sequences at end of input caused an
        # out-of-bounds read in Parser/tokenizer/helpers.c:valid_utf8().
        truncated = [
            b'\xc2',              # 2-byte lead, missing 1 continuation
            b'\xdf',              # 2-byte lead, missing 1 continuation
            b'\xe0',              # 3-byte lead, missing 2 continuations
            b'\xe0\xa0',          # 3-byte lead, missing 1 continuation
            b'\xf0\x90',          # 4-byte lead, missing 2 continuations
            b'\xf0\x90\x80',      # 4-byte lead, missing 1 continuation
            b'\xf3',              # 4-byte lead, missing 3 (the oss-fuzz reproducer)
        ]
        for seq in truncated:
            if True:  # No subTest context in Skulpt unittest.
                self.assertRaises(SyntaxError, compile, seq, '<test>', 'exec')

    def test_error_message(self):
        compile(b'# -*- coding: iso-8859-15 -*-\n', 'dummy', 'exec')
        compile(b'\xef\xbb\xbf\n', 'dummy', 'exec')
        compile(b'\xef\xbb\xbf# -*- coding: utf-8 -*-\n', 'dummy', 'exec')
        with self.assertRaisesRegex(SyntaxError, 'fake'):
            compile(b'# -*- coding: fake -*-\n', 'dummy', 'exec')
        with self.assertRaisesRegex(SyntaxError, 'iso-8859-15'):
            compile(b'\xef\xbb\xbf# -*- coding: iso-8859-15 -*-\n',
                    'dummy', 'exec')
        with self.assertRaisesRegex(SyntaxError, 'BOM'):
            compile(b'\xef\xbb\xbf# -*- coding: iso-8859-15 -*-\n',
                    'dummy', 'exec')
        with self.assertRaisesRegex(SyntaxError, 'fake'):
            compile(b'\xef\xbb\xbf# -*- coding: fake -*-\n', 'dummy', 'exec')
        with self.assertRaisesRegex(SyntaxError, 'BOM'):
            compile(b'\xef\xbb\xbf# -*- coding: fake -*-\n', 'dummy', 'exec')

    def test_exec_valid_coding(self):
        d = {}
        exec(b'# coding: cp949\na = "\xaa\xa7"\n', d)
        self.assertEqual(d['a'], '\u3047')

    # CPython builtin_eval_impl / tokenizer BOM ordering regressions.
    def test_eval_whitespace_before_bom(self):
        self.assertEqual(eval(b' \t\xef\xbb\xbf1'), 1)
        self.assertRaises(SyntaxError, eval, b'\xef\xbb\xbf\xef\xbb\xbf1')

if __name__ == "__main__":
    unittest.main()
