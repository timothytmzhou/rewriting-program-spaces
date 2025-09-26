from __future__ import annotations
from dataclasses import dataclass, replace
import regex as re

from core.grammar import TreeGrammar, EmptySet, Union
from core.lexing.token import Token
from .types import *

# Token template for ID tokens.
# TODO: Get this directly from lark.
IDLEAF = Token(
    "ID",
    re.compile(
        "(?!(true|false|number|string|boolean|return|function|let|if|else|typescript)$)"
        + "([a-zA-Z][a-zA-Z0-9_]*)|(Math\\.[a-zA-Z0-9_]+)"  # Math library hack
    )
)


@dataclass(frozen=True)
class FrozenDict:
    # TODO: Is there no better implementation?
    env: tuple[tuple[str, Type, bool], ...] = ()  # (name, type, is_mutable)

    @classmethod
    def from_dict(cls, dct: dict[str, Type]):
        return cls(tuple((a, b, True) for a, b in dct.items()))

    def __contains__(self, obj):
        if isinstance(obj, str):
            return any(entry[0] == obj for entry in self.env)
        return obj in self.env

    def __getitem__(self, obj):
        if isinstance(obj, str):
            for triple in self.env:
                if triple[0] == obj:
                    return triple
            raise ValueError(f"No variable {obj} in env {self.env}")
        return self.env[obj]

    def add(self, bindings: tuple[tuple[str, Type, bool], ...]) -> FrozenDict:
        return FrozenDict(bindings + self.env)


DEFAULT_NUMBER_METHODS = FrozenDict.from_dict({
    "toString": FuncType.of(VOIDTYPE, STRINGTYPE),
    "toExponential": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "toFixed": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "toPrecision": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "toLocaleString": FuncType.of(ProdType.of(STRINGTYPE), STRINGTYPE),
})

DEFAULT_STRING_METHODS = FrozenDict.from_dict({
    "charAt": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "concat": FuncType.of(ProdType.of(STRINGTYPE, extensible=True), STRINGTYPE),
    "indexOf": FuncType.of(ProdType.of(STRINGTYPE, extensible=True), STRINGTYPE),
    "charCodeAt": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "codePointAt": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "includes": FuncType.of(ProdType.of(STRINGTYPE), BOOLEANTYPE),
    "endswith": FuncType.of(ProdType.of(STRINGTYPE), BOOLEANTYPE),
    "lastIndexOf": FuncType.of(ProdType.of(STRINGTYPE, extensible=True), STRINGTYPE),
    "localeCompare": FuncType.of(ProdType.of(STRINGTYPE, extensible=True), STRINGTYPE),
    "normalize": FuncType.of(ProdType.of(STRINGTYPE), STRINGTYPE),
    "padEnd": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), STRINGTYPE),
    "padStart": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), STRINGTYPE),
    "repeat": FuncType.of(ProdType.of(NUMBERTYPE), STRINGTYPE),
    "replace": FuncType.of(ProdType.of(STRINGTYPE, STRINGTYPE), STRINGTYPE),
    "replaceAll": FuncType.of(ProdType.of(STRINGTYPE, STRINGTYPE), STRINGTYPE),
    "slice": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), STRINGTYPE),
    # "split": FuncType.of(ProdType.of(STRINGTYPE), STRINGTYPE),
    "startsWith": FuncType.of(ProdType.of(STRINGTYPE, extensible=True), BOOLEANTYPE),
    "substring": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), STRINGTYPE),
    "toUpperCase": FuncType.of(VOIDTYPE, STRINGTYPE),
    "toLowerCase": FuncType.of(VOIDTYPE, STRINGTYPE),
    "trim": FuncType.of(VOIDTYPE, STRINGTYPE),
    "trimStart": FuncType.of(VOIDTYPE, STRINGTYPE),
    "trimEnd": FuncType.of(VOIDTYPE, STRINGTYPE),
})


@dataclass(frozen=True)
class Environment:
    """
    Represents a set of environments, maps from variables to types.
    An EnvironmentSet assigns (sets of) types to variables and either
     (i) contains all environments with other variables assigned arbitrarily
     or (ii) does not contain any environments with additional variables.
    envs is a map from variable names to sets of types they could inhabit.
    isextendible indicates whether the EnvironmentSet is of kind i or kind ii.
    Note that the type EnvironmentSet defines a lattice.
    """
    env: FrozenDict = FrozenDict()
    # number_methods: FrozenDict = DEFAULT_NUMBER_METHODS  # e.g., 5.toString()
    # string_methods: FrozenDict = DEFAULT_STRING_METHODS

    @classmethod
    def from_dict(cls, dct: dict[str, Type]):
        return cls(FrozenDict.from_dict(dct))

    def __contains__(self, obj):
        return obj in self.env

    def add(self, bindings: tuple[tuple[str, Type, bool], ...]) -> Environment:
        return Environment(self.env.add(bindings))

    def _get_typed(self, var: str, typ: Type, is_mutable: Optional[bool] = None
                   ) -> tuple[TreeGrammar, Type]:
        """
        Get the type of a variable, or empty if it doesn't exist.
        """
        if (
            var in self.env
            and self.env[var][1] in typ
            and (is_mutable is None or self.env[var][2] == is_mutable)
        ):
            return (replace(IDLEAF, prefix=var, is_complete=True),
                    self.env[var][1])
        return (EmptySet(), EmptyType())

    def get_terms_of_type(self, identifiers: Token, typ: Type,
                          is_mutable: Optional[bool] = None) -> TreeGrammar:
        if identifiers.token_type == "ID":
            if identifiers.is_complete:
                return self._get_typed(identifiers.prefix, typ, is_mutable)[0]
            return Union.of(
                {self._get_typed(var, typ, is_mutable)[0]
                    for (var, _, _) in self.env.env
                    if var.startswith(identifiers.prefix)}
            )

        raise ValueError(f"Unknown identifiers type: {identifiers}")
