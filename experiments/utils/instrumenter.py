from dataclasses import dataclass, field
from typing import Callable, TypeVar
from functools import wraps
import time

from experiments.utils.totaler import Totaler
from llm.realizability import RealizabilityChecker
from llm.run_llm import LanguageModelRunner


T = TypeVar('T')


@dataclass
class Instrumenter:
    prompt_num: int = 0
    run_num: int = 0
    timeouts: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )
    pass_constraint: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )
    pass_tests: Totaler[bool] = field(
        default_factory=lambda: Totaler()
    )
    timer: Totaler[Callable] = field(
        default_factory=lambda: Totaler()
    )

    def log_total_time(self, f: Callable[..., T]):
        @wraps(f)
        def wrapped(*args, **kwargs) -> T:
            start = time.time()
            result = f(*args, **kwargs)
            end = time.time()
            self.timer.incr(f, (end - start))
            return result
        return wrapped

    def __post_init__(self):
        # Set timers on important functions
        RealizabilityChecker.realizable = self.log_total_time(
            RealizabilityChecker.realizable
        )
        LanguageModelRunner.run = self.log_total_time(
            LanguageModelRunner.run
        )

    def set_indices(self, prompt_num, run_num):
        self.prompt_num = prompt_num
        self.run_num = run_num
        self.timer.set_indices(prompt_num, run_num)
        self.pass_constraint.set_indices(prompt_num, run_num)
        self.pass_tests.set_indices(prompt_num, run_num)
        self.timeouts.set_indices(prompt_num, run_num)

    def instrument(self, prog: str, passes_constraints: bool, timeout: bool):
        self.pass_constraint.incr(
            True,
            1.0 if passes_constraints else 0.0
        )

        # TODO: Check if tests passed
        self.pass_tests.incr(
            True,
            1.0
        )

        self.timeouts.incr(
            True,
            1.0 if timeout else 0.0
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
            + f"{self.timeouts.sum().first}/{self.timeouts.sum().second}\n"
        )

    def get_tot_times_this_run(self) -> str:
        out = ""
        keys = list(self.timer.dct.keys())
        for (pnum, rnum, f) in keys:
            if pnum == self.timer.curr_prompt_num and rnum == self.timer.curr_run_num:
                total = self.timer.sum(pnum=self.timer.get_prompt_num(),
                                       rnum=self.timer.get_run_num(),
                                       k=f)
                out += (
                    f"{f.__name__}:\n \t\ttot_time: {total.first:.4f} secs;"
                    + f"\tnum_calls: {total.second};"
                    + f"\tavg_time {total.avg():.4f} secs\n")

        return out

    def clear(self):
        # Restore timed functions
        RealizabilityChecker.realizable = RealizabilityChecker.realizable.__wrapped__
        LanguageModelRunner.run = LanguageModelRunner.run.__wrapped__

        # Clear totalers in case instrumenter is reused
        self.pass_constraint.clear()
        self.pass_tests.clear()
        self.timer.clear()
        self.timeouts.clear()
