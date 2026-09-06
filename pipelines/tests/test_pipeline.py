import unittest

from pipelines.pipeline import Pipeline, PipelineStep


class PipelineTest(unittest.TestCase):
    def test_chains_steps_in_order(self):
        pipeline = Pipeline(steps=[lambda x: x + 1, lambda x: x * 2])
        self.assertEqual(pipeline(3), 8)  # (3 + 1) * 2

    def test_empty_pipeline_returns_input_unchanged(self):
        pipeline = Pipeline(steps=[])
        self.assertEqual(pipeline("unchanged"), "unchanged")

    def test_plain_function_satisfies_pipeline_step_protocol(self):
        def step(x):
            return x

        self.assertIsInstance(step, PipelineStep)

    def test_callable_class_satisfies_pipeline_step_protocol(self):
        class Doubler:
            def __call__(self, step_input):
                return step_input * 2

        self.assertIsInstance(Doubler(), PipelineStep)


if __name__ == "__main__":
    unittest.main()
