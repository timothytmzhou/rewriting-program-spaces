from __future__ import annotations
from dataclasses import dataclass, replace

from core.grammar import *
from lexing.leaves import Token
from .typescript_grammar import IDLEAF
from .types import *


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
    # TODO: Get frozendict or some equivalent
    env: tuple[tuple[str, Type], ...] = ()

    @classmethod
    def from_dict(cls, dct: dict[str, Type]):
        return cls(tuple(dct.items()))

    def __contains__(self, obj):
        if isinstance(obj, str):
            return any(entry[0] == obj for entry in self.env)
        return obj in self.env

    def __getitem__(self, obj):
        if isinstance(obj, str):
            for pair in self.env:
                if pair[0] == obj:
                    return pair
            raise ValueError(f"No variable {obj} in env {self.env}")
        return self.env[obj]

    def add(self, bindings: tuple[tuple[str, Type], ...]) -> Environment:
        return Environment(self.env + bindings)

    def _get_typed(self, var: str, typ: Type) -> tuple[TreeGrammar, Type]:
        """
        Get the type of a variable, or empty if it doesn't exist.
        """
        if (var in self and contains(typ, self[var][1])):
            return (Constant(replace(IDLEAF, prefix=var, is_complete=True)),
                    self[var][1])
        else:
            return (EmptySet(), EmptyType())

    def get_terms_of_type(self, identifiers: Token, typ: Type) -> TreeGrammar:
        if identifiers.token_type == "id":
            if identifiers.is_complete:
                return self._get_typed(identifiers.prefix, typ)[0]
            return Union.of(
                {self._get_typed(var, typ)[0] for (var, _) in self.env
                 if var.startswith(identifiers.prefix)}
            )
        raise ValueError(f"Unknown identifiers type: {identifiers}")
