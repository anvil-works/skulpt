import unittest


class ExceptionNotesRegression(unittest.TestCase):
    def test_notes_descriptors_and_native_append(self):
        class Notes(list):
            def append(self, note):
                raise AssertionError('native append must bypass Python overrides')
        class Note(str):
            pass
        class Error(Exception):
            @property
            def __notes__(self):
                return self.storage
            @__notes__.setter
            def __notes__(self, value):
                self.storage = value
        error = Error()
        note = Note('first')
        self.assertIsNone(error.add_note(note))
        self.assertIs(error.storage[0], note)
        error.storage = Notes()
        error.add_note('second')
        self.assertEqual(error.storage, ['second'])
        class Broken(Exception):
            @property
            def __notes__(self):
                raise ValueError('getter')
        with self.assertRaisesRegex(ValueError, 'getter'):
            Broken().add_note('note')
        class ReadOnly(Exception):
            @property
            def __notes__(self):
                raise AttributeError('absent')
        with self.assertRaises(AttributeError):
            ReadOnly().add_note('note')
        error = Exception()
        with self.assertRaises(TypeError):
            error.__cause__ = 1
        with self.assertRaises(TypeError):
            del error.__cause__
        self.assertFalse(error.__suppress_context__)
        cause = ValueError()
        error.__cause__ = cause
        self.assertIs(error.__cause__, cause)
        self.assertTrue(error.__suppress_context__)

if __name__ == "__main__": unittest.main()
