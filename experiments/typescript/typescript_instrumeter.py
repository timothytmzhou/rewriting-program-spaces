from dataclasses import dataclass
from typing import Callable

from typescript.compile_typescript import compile_typescript
from utils.instrumenter import *


@dataclass
class TypescriptInstrumeter(Instrumenter):
    compile: Callable[[str], bool] = compile_typescript
    pass_compiler: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )

    def instrument(self, prog: str):
        super().instrument(prog)
        self.pass_compiler.incr(
            True,
            1.0 if self.compile(prog) else 0.0
        )

    def table_row(self) -> str:
        return (
            f"{self.pass_constraint.sum().first}/{self.pass_constraint.sum().second}"
            + "\t\t\t\t\t\t\t\t"
            + f"{self.pass_tests.sum().first}/{self.pass_tests.sum().second}"
            + "\t\t\t\t\t\t\t\t"
            + f"{self.timer.avg(k=LanguageModelRunner.run.__wrapped__):.4f}"
            + "\t\t\t\t\t\t\t\t"
            + f"{self.timer.avg(k=RealizabilityChecker.realizable.__wrapped__):.4f}"
            + "\t\t\t\t\t\t\t\t"
            + f"{self.pass_compiler.sum().first}/{self.pass_compiler.sum().second}\n"
        )