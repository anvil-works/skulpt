# CPython 3.14 Lib/test/test_codecs.py at 18ef0f0cb52.
# UnicodeEscapeTest encoding cases use the production str.encode API
# instead of codecs tuple results; the character inputs/expectations are unchanged.
import unittest

class UnicodeEscape(unittest.TestCase):
    def test_raw_encode(self):
        for b in range(32, 127):
            if b != b'\\'[0]:
                self.assertEqual(chr(b).encode('unicode_escape'), bytes([b]))


    def test_escape_encode(self):
        check = lambda value, expected: self.assertEqual(value.encode('unicode_escape'), expected)
        check('\t', br'\t')
        check('\n', br'\n')
        check('\r', br'\r')
        check('\\', br'\\')
        for b in range(32):
            if chr(b) not in '\t\n\r':
                check(chr(b), ('\\x%02x' % b).encode())
        for b in range(127, 256):
            check(chr(b), ('\\x%02x' % b).encode())
        check('\u20ac', br'\u20ac')
        check('\U0001d120', br'\U0001d120')


    def test_unused_error_handlers(self):
        for errors in ('strict', 'replace', 'backslashreplace', 'surrogatepass', 'bogus'):
            self.assertEqual('é'.encode('unicode_escape', errors), b'\\xe9')
        with self.assertRaises(TypeError): 'é'.encode('unicode_escape', 1)

if __name__ == '__main__': unittest.main()
