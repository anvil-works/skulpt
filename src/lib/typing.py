"""Compiler-created typing objects; further typing APIs remain unimplemented."""
from _typing import TypeAliasType, TypeVar, NoDefault, ParamSpec, ParamSpecArgs, ParamSpecKwargs, TypeVarTuple, Unpack, _UnpackGenericAlias
from types import GenericAlias, UnionType
Union = UnionType

def get_args(tp):
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias)):
        return tp.__args__
    return ()

def get_origin(tp):
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias, ParamSpecArgs, ParamSpecKwargs)):
        return tp.__origin__
    return None

# Helpers invoked by native parameters, following CPython Lib/typing.py.
def _type_check(arg, message):
    if arg is None:
        return type(None)
    if isinstance(arg, str):
        raise NotImplementedError("string type arguments require ForwardRef support")
    if type(arg) is tuple:
        raise TypeError(message + " Got " + repr(arg) + ".")
    return arg

def _is_param_expr(arg):
    return arg is ... or isinstance(arg, (tuple, list, ParamSpec))

def _unpack_args(*args):
    newargs = []
    for arg in args:
        subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
        if subargs is not None and not (subargs and subargs[-1] is ...):
            newargs.extend(subargs)
        else:
            newargs.append(arg)
    return newargs


def _typevartuple_prepare_subst(self, alias, args):
    params = alias.__parameters__
    typevartuple_index = params.index(self)
    for param in params[typevartuple_index + 1:]:
        if isinstance(param, TypeVarTuple):
            raise TypeError(f"More than one TypeVarTuple parameter in {alias}")

    alen = len(args)
    plen = len(params)
    left = typevartuple_index
    right = plen - typevartuple_index - 1
    var_tuple_index = None
    fillarg = None
    for k, arg in enumerate(args):
        if not isinstance(arg, type):
            subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
            if subargs and len(subargs) == 2 and subargs[-1] is ...:
                if var_tuple_index is not None:
                    raise TypeError("More than one unpacked arbitrary-length tuple argument")
                var_tuple_index = k
                fillarg = subargs[0]
    if var_tuple_index is not None:
        left = min(left, var_tuple_index)
        right = min(right, alen - var_tuple_index - 1)
    elif left + right > alen:
        raise TypeError(f"Too few arguments for {alias};"
                        f" actual {alen}, expected at least {plen-1}")
    if left == alen - right and self.has_default():
        replacement = _unpack_args(self.__default__)
    else:
        replacement = args[left: alen - right]

    return (
        *args[:left],
        *([fillarg]*(typevartuple_index - left)),
        replacement,
        *([fillarg]*(plen - right - left - typevartuple_index - 1)),
        *args[alen - right:],
    )


def _paramspec_subst(self, arg):
    if isinstance(arg, (list, tuple)):
        arg = tuple(_type_check(a, "Expected a type.") for a in arg)
    elif not _is_param_expr(arg):
        raise TypeError(f"Expected a list of types, an ellipsis, "
                        f"ParamSpec, or Concatenate. Got {arg}")
    return arg


def _paramspec_prepare_subst(self, alias, args):
    params = alias.__parameters__
    i = params.index(self)
    if i == len(args) and self.has_default():
        args = (*args, self.__default__)
    if i >= len(args):
        raise TypeError(f"Too few arguments for {alias}")
    # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
    if len(params) == 1 and not _is_param_expr(args[0]):
        assert i == 0
        args = (args,)
    # Convert lists to tuples to help other libraries cache the results.
    elif isinstance(args[i], list):
        args = (*args[:i], tuple(args[i]), *args[i+1:])
    return args

