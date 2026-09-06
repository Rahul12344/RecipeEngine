"""
Regression test for a real bug found by actually running the ingestion
pipeline end to end: BaseRetriever._worker did a bare `await self._queue.get()`,
which blocks forever once the queue is empty. That meant a worker could
never become "done", so scrape()'s `all(w.done() for w in workers)`
termination check could never be satisfied -- scrape() would hang forever
instead of finishing once there was nothing left to crawl (e.g. every page
came back blocked/empty, or the whole site was exhausted).

This mocks only BaseRetriever._fetch_html (the actual network call); the
real crawl/queue/worker/termination logic all runs unmodified.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from data_pipeline.meta_info.source_metadata import SourceMetadata
from data_pipeline.retriever.recipe_source_retrievers import BaseRetriever


class _FakeSourceMetadata(SourceMetadata):
    def __init__(self, hostname: str):
        self._hostname = hostname

    @property
    def name(self) -> str:
        return "fake_source"

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def recipe_identifier(self) -> str:
        return "/recipe/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/recipe/"}


async def _collect(async_iter, timeout: float):
    """Drain an async generator, failing the test (via TimeoutError) if it
    doesn't finish on its own within `timeout` seconds -- this is exactly
    the hang the underlying bug caused."""
    results = []

    async def _drain():
        async for item in async_iter:
            results.append(item)

    await asyncio.wait_for(_drain(), timeout=timeout)
    return results


class BaseRetrieverTerminationTest(unittest.IsolatedAsyncioTestCase):
    async def test_scrape_terminates_when_every_fetch_is_blocked(self):
        """Every page 403s (empty html, no links) -- the crawl has nothing
        to do after the very first fetch and must still terminate."""
        retriever = BaseRetriever(max_concurrent=5, delay_range=(0.0, 0.0))
        source = _FakeSourceMetadata("https://example.test")

        with patch.object(BaseRetriever, "_fetch_html", new=AsyncMock(return_value="")):
            results = await _collect(retriever.scrape(source), timeout=10.0)

        self.assertEqual(results, [])

    async def test_scrape_terminates_after_exhausting_a_small_link_graph(self):
        """A seed page links to one recipe page with no further links --
        the crawl must terminate once that small graph is exhausted, not
        hang waiting for more work that will never arrive."""
        pages = {
            "https://example.test": '<a href="/recipe/1">A recipe</a>',
            "https://example.test/recipe/1": "<p>no further links here</p>",
        }

        async def fake_fetch_html(self, url, session):
            return pages.get(url, "")

        retriever = BaseRetriever(max_concurrent=5, delay_range=(0.0, 0.0))
        source = _FakeSourceMetadata("https://example.test")

        with patch.object(BaseRetriever, "_fetch_html", new=fake_fetch_html):
            results = await _collect(retriever.scrape(source), timeout=10.0)

        self.assertEqual([r.url for r in results], ["https://example.test/recipe/1"])


if __name__ == "__main__":
    unittest.main()
