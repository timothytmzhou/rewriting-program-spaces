from core.grammar import Application, Unary, Binary, TreeGrammar
from dataclasses import dataclass


"""
Define abstract syntax as follows. Each constructor should be a frozen dataclass
that inherits from Application, and the fields should be of type TreeGrammar/Token.
"""
@dataclass(frozen=True)
class Num(Application):
    t: TreeGrammar


@dataclass(frozen=True)
class Add(Application):
    left: TreeGrammar
    right: TreeGrammar


"""
As shorthand, you can also write the above more concisely using the built-in 
Unary, and Binary classes as below.
"""
class Num(Unary): ...
class Add(Binary): ...
