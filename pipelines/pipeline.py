from __future__ import annotations


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
