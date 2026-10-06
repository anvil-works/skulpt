var $builtinmodule = function () {
    return {
        _type_repr: new Sk.builtin.func(function(value) { return new Sk.builtin.str(Sk.builtin.typingTypeRepr(value)); }),
        TypeAliasType: Sk.builtin.TypeAliasType,
        TypeVar: Sk.builtin.TypeVar,
        NoDefault: Sk.builtin.NoDefault,
        ParamSpec: Sk.builtin.ParamSpec,
        ParamSpecArgs: Sk.builtin.ParamSpecArgs,
        ParamSpecKwargs: Sk.builtin.ParamSpecKwargs,
        TypeVarTuple: Sk.builtin.TypeVarTuple,
        Unpack: Sk.builtin.Unpack,
        _UnpackGenericAlias: Sk.builtin.UnpackAlias,
    };
};
