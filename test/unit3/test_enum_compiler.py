# Selected complete CPython 3.14 test_enum.py methods and fixture.
import unittest
import enum
from enum import Enum, IntEnum, StrEnum, Flag, auto

class _EnumTests:
    values = None
    def setUp(self):
        if self.__class__.__name__[-5:] == 'Class':
            class BaseEnum(self.enum_type):
                @enum.property
                def first(self):
                    return '%s is first!' % self.name
            class MainEnum(BaseEnum):
                first = auto()
                second = auto()
                third = auto()
                if issubclass(self.enum_type, Flag):
                    dupe = 3
                else:
                    dupe = third
            self.MainEnum = MainEnum
            #
            class NewStrEnum(self.enum_type):
                def __str__(self):
                    return self.name.upper()
                first = auto()
            self.NewStrEnum = NewStrEnum
            #
            class NewFormatEnum(self.enum_type):
                def __format__(self, spec):
                    return self.name.upper()
                first = auto()
            self.NewFormatEnum = NewFormatEnum
            #
            class NewStrFormatEnum(self.enum_type):
                def __str__(self):
                    return self.name.title()
                def __format__(self, spec):
                    return ''.join(reversed(self.name))
                first = auto()
            self.NewStrFormatEnum = NewStrFormatEnum
            #
            class NewBaseEnum(self.enum_type):
                def __str__(self):
                    return self.name.title()
                def __format__(self, spec):
                    return ''.join(reversed(self.name))
            self.NewBaseEnum = NewBaseEnum
            class NewSubEnum(NewBaseEnum):
                first = auto()
            self.NewSubEnum = NewSubEnum
            #
            class LazyGNV(self.enum_type):
                def _generate_next_value_(name, start, last, values):
                    pass
            self.LazyGNV = LazyGNV
            #
            class BusyGNV(self.enum_type):
                @staticmethod
                def _generate_next_value_(name, start, last, values):
                    pass
            self.BusyGNV = BusyGNV
            #
            self.is_flag = False
            self.names = ['first', 'second', 'third']
            if issubclass(MainEnum, StrEnum):
                self.values = self.names
            elif MainEnum._member_type_ is str:
                self.values = ['1', '2', '3']
            elif issubclass(self.enum_type, Flag):
                self.values = [1, 2, 4]
                self.is_flag = True
                self.dupe2 = MainEnum(5)
            else:
                self.values = self.values or [1, 2, 3]
            #
            if not getattr(self, 'source_values', False):
                self.source_values = self.values
        elif self.__class__.__name__[-8:] == 'Function':
            @enum.property
            def first(self):
                return '%s is first!' % self.name
            BaseEnum = self.enum_type('BaseEnum', {'first':first})
            #
            first = auto()
            second = auto()
            third = auto()
            if issubclass(self.enum_type, Flag):
                dupe = 3
            else:
                dupe = third
            self.MainEnum = MainEnum = BaseEnum('MainEnum', dict(first=first, second=second, third=third, dupe=dupe))
            #
            def __str__(self):
                return self.name.upper()
            first = auto()
            self.NewStrEnum = self.enum_type('NewStrEnum', (('first',first),('__str__',__str__)))
            #
            def __format__(self, spec):
                return self.name.upper()
            first = auto()
            self.NewFormatEnum = self.enum_type('NewFormatEnum', [('first',first),('__format__',__format__)])
            #
            def __str__(self):
                return self.name.title()
            def __format__(self, spec):
                return ''.join(reversed(self.name))
            first = auto()
            self.NewStrFormatEnum = self.enum_type('NewStrFormatEnum', dict(first=first, __format__=__format__, __str__=__str__))
            #
            def __str__(self):
                return self.name.title()
            def __format__(self, spec):
                return ''.join(reversed(self.name))
            self.NewBaseEnum = self.enum_type('NewBaseEnum', dict(__format__=__format__, __str__=__str__))
            self.NewSubEnum = self.NewBaseEnum('NewSubEnum', 'first')
            #
            def _generate_next_value_(name, start, last, values):
                pass
            self.LazyGNV = self.enum_type('LazyGNV', {'_generate_next_value_':_generate_next_value_})
            #
            @staticmethod
            def _generate_next_value_(name, start, last, values):
                pass
            self.BusyGNV = self.enum_type('BusyGNV', {'_generate_next_value_':_generate_next_value_})
            #
            self.is_flag = False
            self.names = ['first', 'second', 'third']
            if issubclass(MainEnum, StrEnum):
                self.values = self.names
            elif MainEnum._member_type_ is str:
                self.values = ['1', '2', '3']
            elif issubclass(self.enum_type, Flag):
                self.values = [1, 2, 4]
                self.is_flag = True
                self.dupe2 = MainEnum(5)
            else:
                self.values = self.values or [1, 2, 3]
            #
            if not getattr(self, 'source_values', False):
                self.source_values = self.values
        else:
            raise ValueError('unknown enum style: %r' % self.__class__.__name__)


    def test_basics(self):
        TE = self.MainEnum
        if self.is_flag:
            self.assertEqual(repr(TE), "<flag 'MainEnum'>")
            self.assertEqual(str(TE), "<flag 'MainEnum'>")
            self.assertEqual(format(TE), "<flag 'MainEnum'>")
            self.assertTrue(TE(5) is self.dupe2)
            self.assertTrue(7 in TE)
        else:
            self.assertEqual(repr(TE), "<enum 'MainEnum'>")
            self.assertEqual(str(TE), "<enum 'MainEnum'>")
            self.assertEqual(format(TE), "<enum 'MainEnum'>")
        self.assertEqual(list(TE), [TE.first, TE.second, TE.third])
        self.assertEqual(
                [m.name for m in TE],
                self.names,
                )
        self.assertEqual(
                [m.value for m in TE],
                self.values,
                )
        self.assertEqual(
                [m.first for m in TE],
                ['first is first!', 'second is first!', 'third is first!']
                )
        for member, name in zip(TE, self.names, strict=True):
            self.assertIs(TE[name], member)
        for member, value in zip(TE, self.values, strict=True):
            self.assertIs(TE(value), member)
        if issubclass(TE, StrEnum):
            self.assertTrue(TE.dupe is TE('third') is TE['dupe'])
        elif TE._member_type_ is str:
            self.assertTrue(TE.dupe is TE('3') is TE['dupe'])
        elif issubclass(TE, Flag):
            self.assertTrue(TE.dupe is TE(3) is TE['dupe'])
        else:
            self.assertTrue(TE.dupe is TE(self.values[2]) is TE['dupe'])


    def test_bool_is_true(self):
        class Empty(self.enum_type):
            pass
        self.assertTrue(Empty)
        #
        self.assertTrue(self.MainEnum)
        for member in self.MainEnum:
            self.assertTrue(member)


    def test_changing_member_fails(self):
        MainEnum = self.MainEnum
        with self.assertRaises(AttributeError):
            self.MainEnum.second = 'really first'


    def test_enum_in_enum_out(self):
        Main = self.MainEnum
        self.assertIs(Main(Main.first), Main.first)


    def test_gnv_is_static(self):
        lazy = self.LazyGNV
        busy = self.BusyGNV
        self.assertTrue(type(lazy.__dict__['_generate_next_value_']) is staticmethod)
        self.assertTrue(type(busy.__dict__['_generate_next_value_']) is staticmethod)


    def test_hash(self):
        MainEnum = self.MainEnum
        mapping = {}
        mapping[MainEnum.first] = '1225'
        mapping[MainEnum.second] = '0315'
        mapping[MainEnum.third] = '0704'
        self.assertEqual(mapping[MainEnum.second], '0315')


class TestPlainEnumClass(_EnumTests, unittest.TestCase):
    enum_type = Enum

class TestIntEnumClass(_EnumTests, unittest.TestCase):
    enum_type = IntEnum

if __name__ == '__main__': unittest.main()
