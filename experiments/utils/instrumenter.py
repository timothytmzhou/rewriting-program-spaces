from dataclasses import dataclass, field
from experiments.utils.totaler import GLB_Timer, Totaler
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import LanguageModelRunner


@dataclass
class Instrumenter:
    checker: RealizabilityChecker
    prompt_num: int = 0
    run_num: int = 0
    pass_constraint: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )
    pass_tests: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )

    def set_indices(self, prompt_num, run_num):
        self.prompt_num = prompt_num
        self.run_num = run_num
        GLB_Timer.set_indices(prompt_num, run_num)
        self.pass_constraint.set_indices(prompt_num, run_num)
        self.pass_tests.set_indices(prompt_num, run_num)

    def instrument(self, prog: str):
        # Check if checker constraints passed (don't time this call!)
        passes_constraints = self.checker.realizable.__wrapped__(
            self.checker, prog, final=True
        )

        self.pass_constraint.incr(
            True,
            1.0 if passes_constraints else 0.0
        )

        # TODO: Check if tests passed
        self.pass_tests.incr(
            True,
            1.0
        )

    def table_row(self) -> str:
        return (
            f"{self.pass_constraint.sum().first}/{self.pass_constraint.sum().second}"
            + "\t\t\t\t\t\t\t\t"
            + f"{self.pass_tests.sum().first}/{self.pass_tests.sum().second}"
            + "\t\t\t\t\t\t\t\t"
            + f"{GLB_Timer.avg(k=LanguageModelRunner.run.__wrapped__):.4f}"
            + "\t\t\t\t\t\t\t\t"
            + f"{GLB_Timer.avg(k=RealizabilityChecker.realizable.__wrapped__):.4f}\n"
        )

    def clear(self):
        GLB_Timer.clear()
