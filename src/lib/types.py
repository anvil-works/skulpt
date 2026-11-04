"""
This file was modified from CPython.
Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015 Python Software Foundation; All Rights Reserved
"""
"""Define names for all type symbols known in the standard interpreter.
Types that are part of optional modules (e.g. array) are not listed.
"""
import sys

# Iterators in Python aren't a matter of type but of protocol.  A large
# and changing number of builtin types implement *some* flavor of
# iterator.  Don't check the type!  Use hasattr to check for both
# "__iter__" and "next" attributes instead.
MappingProxyType = type(type.__dict__)
WrapperDescriptorType = type(object.__init__)
MethodWrapperType = type(object().__str__)
MethodDescriptorType = type(str.join)
ClassMethodDescriptorType = type(dict.__dict__['fromkeys'])

NoneType = type(None)
TypeType = type
ObjectType = object
IntType = int
try:
    LongType = long
except: pass
FloatType = float
BooleanType = bool
try:
    ComplexType = complex
except NameError:
    pass
StringType = str

# StringTypes is already outdated.  Instead of writing "type(x) in
# types.StringTypes", you should use "isinstance(x, basestring)".  But
# we keep around for compatibility with Python 2.2.
try:
    UnicodeType = unicode
    StringTypes = (StringType, UnicodeType)
except NameError:
    StringTypes = (StringType,)

BufferType = buffer

TupleType = tuple
ListType = list
DictType = DictionaryType = dict

def _f(): pass
FunctionType = type(_f)
LambdaType = type(lambda: None)         # Same as FunctionType
CodeType = type(_f.__code__)
def _cell_factory():
    a = None
    def f():
        return a
    return f.__closure__[0]
CellType = type(_cell_factory())

def _g():
    yield 1
GeneratorType = type(_g())

class _C:
    def _m(self): pass
ClassType = type(_C)
UnboundMethodType = type(_C._m)         # Same as MethodType
_x = _C()
InstanceType = type(_x)
MethodType = type(_x._m)
BuiltinFunctionType = type(len)
BuiltinMethodType = type([].append)     # Same as BuiltinFunctionType

ModuleType = type(sys)
FileType = file
try:
    XRangeType = xrange
except NameError:
    pass

try:
    raise TypeError
except TypeError as _error:
    _tb = _error.__traceback__
    TracebackType = type(_tb)
    FrameType = type(_tb.tb_frame)
    del _tb

SliceType = slice
EllipsisType = type(Ellipsis)

# DictProxyType = type(TypeType.__dict__)
NotImplementedType = type(NotImplemented)

# For Jython, the following two types are identical
# GetSetDescriptorType = type(FunctionType.func_code)
# MemberDescriptorType = type(FunctionType.func_globals)

# Class construction helpers from CPython 3.14 at 18ef0f0cb52.
# Provide a PEP 3115 compliant mechanism for class creation
def new_class(name, bases=(), kwds=None, exec_body=None):
    """Create a class object dynamically using the appropriate metaclass."""
    resolved_bases = resolve_bases(bases)
    meta, ns, kwds = prepare_class(name, resolved_bases, kwds)
    if exec_body is not None:
        exec_body(ns)
    if resolved_bases is not bases:
        ns['__orig_bases__'] = bases
    return meta(name, resolved_bases, ns, **kwds)

def resolve_bases(bases):
    """Resolve MRO entries dynamically as specified by PEP 560."""
    new_bases = list(bases)
    updated = False
    shift = 0
    for i, base in enumerate(bases):
        if isinstance(base, type):
            continue
        if not hasattr(base, "__mro_entries__"):
            continue
        new_base = base.__mro_entries__(bases)
        updated = True
        if not isinstance(new_base, tuple):
            raise TypeError("__mro_entries__ must return a tuple")
        else:
            new_bases[i+shift:i+shift+1] = new_base
            shift += len(new_base) - 1
    if not updated:
        return bases
    return tuple(new_bases)

def prepare_class(name, bases=(), kwds=None):
    """Call the __prepare__ method of the appropriate metaclass.

    Returns (metaclass, namespace, kwds) as a 3-tuple

    *metaclass* is the appropriate metaclass
    *namespace* is the prepared class namespace
    *kwds* is an updated copy of the passed in kwds argument with any
    'metaclass' entry removed. If no kwds argument is passed in, this will
    be an empty dict.
    """
    if kwds is None:
        kwds = {}
    else:
        kwds = dict(kwds) # Don't alter the provided mapping
    if 'metaclass' in kwds:
        meta = kwds.pop('metaclass')
    else:
        if bases:
            meta = type(bases[0])
        else:
            meta = type
    if isinstance(meta, type):
        # when meta is a type, we first determine the most-derived metaclass
        # instead of invoking the initial candidate directly
        meta = _calculate_meta(meta, bases)
    if hasattr(meta, '__prepare__'):
        ns = meta.__prepare__(name, bases, **kwds)
    else:
        ns = {}
    return meta, ns, kwds

def _calculate_meta(meta, bases):
    """Calculate the most derived metaclass."""
    winner = meta
    for base in bases:
        base_meta = type(base)
        if issubclass(winner, base_meta):
            continue
        if issubclass(base_meta, winner):
            winner = base_meta
            continue
        # else:
        raise TypeError("metaclass conflict: "
                        "the metaclass of a derived class "
                        "must be a (non-strict) subclass "
                        "of the metaclasses of all its bases")
    return winner


def get_original_bases(cls, /):
    """Return the class's "original" bases prior to modification by `__mro_entries__`.

    Examples::

        from typing import TypeVar, Generic, NamedTuple, TypedDict

        T = TypeVar("T")
        class Foo(Generic[T]): ...
        class Bar(Foo[int], float): ...
        class Baz(list[str]): ...
        Eggs = NamedTuple("Eggs", [("a", int), ("b", str)])
        Spam = TypedDict("Spam", {"a": int, "b": str})

        assert get_original_bases(Bar) == (Foo[int], float)
        assert get_original_bases(Baz) == (list[str],)
        assert get_original_bases(Eggs) == (NamedTuple,)
        assert get_original_bases(Spam) == (TypedDict,)
        assert get_original_bases(int) == (object,)
    """
    try:
        return cls.__dict__.get("__orig_bases__", cls.__bases__)
    except AttributeError:
        raise TypeError(
            f"Expected an instance of type, not {type(cls).__name__!r}"
        ) from None


if sys.version_info[0] >= 3:
    UnionType = type(int | str)

del sys, _f, _g, _C, _x                           # Not for export
__all__ = list(n for n in globals() if n[:1] != '_')

GenericAlias = type(type[int])