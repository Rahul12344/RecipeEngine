from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PipelineStep(Protocol):
    """Anything callable with a single input and a single output.

    A `Pipeline` is just a sequence of these, run in order with each
    step's output feeding the next step's input. Being a `Protocol` means
    a plain function, a lambda, or any class implementing `__call__` all
    satisfy it structurally -- no base class required.
    """

    def __call__(self, step_input: Any) -> Any: ...


class Pipeline:
    def __init__(
        self,
        steps: list[PipelineStep]
    ):
        self._steps = steps

    def __call__(
        self,
        step_input: Any
    ) -> Any:
        for step in self._steps:
            step_input = step(step_input)
        return step_input
