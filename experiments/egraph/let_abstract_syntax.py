from dataclasses import dataclass
from core.grammar import Application, TreeGrammar, Atom, Unary, Binary
from core.lexing.token import Token


@dataclass(frozen=True)
class Let(Application):
    var: Token
    binding: TreeGrammar
    expr: TreeGrammar


class Var(Atom): ...


class Num(Atom): ...


class Neg(Unary): ...


class App(Binary): ...


class Add(Binary): ...


class Sub(Binary): ...


class Mul(Binary): ...


class Div(Binary): ...


constructors: list[type[Application]] = [Let, Var, Num, Neg, App, Add, Sub, Mul, Div]
