from urllib.parse import urljoin
import ssl
import random
import logging
from typing import List, Set, Iterable, AsyncIterator, Iterator
from collections.abc import AsyncGenerator
from dataclasses import dataclass
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from data_pipeline.meta_info.source_metadata import AllRecipesSourceMetadata, SourceMetadata, FoodDotComSourceMetadata

# TODO: Rethink logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_USER_AGENTS = 'User-Agent'
_MOZILLA_USER_AGENT = "Mozilla/5.0"



@dataclass
class RawRecipeData:
    """Data class for raw recipe data retrieved from a source"""
    html: str
    source: str
    url: str


class BaseRetriever:
    """
    Retrieves raw HTML.
    Only handles retrieval - extraction logic is handled by transformers.
    """

    def __init__(self, max_concurrent=20, delay_range=(0.00,0.01)):
        self._max_concurrent = max_concurrent
        self._delay_range = delay_range
        self._visited_urls: Set[str] = set()  # URLs that have been processed
        self._queued_urls: Set[str] = set()    # URLs that are in the queue (to prevent duplicates)
        self._visited_urls_lock = asyncio.Lock()
        self._queue: asyncio.LifoQueue[tuple[str, SourceMetadata]] = asyncio.LifoQueue()
        self._headers = {
            _USER_AGENTS: _MOZILLA_USER_AGENT
        }

    async def scrape(self, source_metadata: SourceMetadata) -> AsyncIterator[RawRecipeData]:
        """Async generator yielding RawRecipeData in real-time."""
        async with self._visited_urls_lock:
            self._visited_urls.clear()
            self._queued_urls.clear()
            self._queued_urls.add(source_metadata.hostname)

        await self._queue.put((source_metadata.hostname, source_metadata))
        output_queue: asyncio.Queue[RawRecipeData] = asyncio.Queue()
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self._worker(session, semaphore, output_queue))
                       for _ in range(self._max_concurrent)]

            while True:
                if all(w.done() for w in workers) and self._queue.empty() and output_queue.empty():
                    break
                try:
                    data = await asyncio.wait_for(output_queue.get(), timeout=1.0)
                    yield data
                    output_queue.task_done()
                except asyncio.TimeoutError:
                    continue

            for w in workers:
                w.cancel()

    async def fetch(self, url: str, source_metadata: SourceMetadata) -> Iterable[RawRecipeData]:
        """Fetch HTML content asynchronously."""
        async with aiohttp.ClientSession() as session:
            html = await self._fetch_html(url, session)
            yield RawRecipeData(html=html, source=source_metadata.name, url=url)

    async def _fetch_html(self, url: str, session: aiohttp.ClientSession) -> str:
        """Fetch HTML content asynchronously."""
        async with session.get(url, headers=self._headers) as resp:
            if resp.status == 200:
                return await resp.text()
            return ""

    async def _worker(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, output_queue: asyncio.Queue):
        """Worker coroutine fetching pages and yielding RawRecipeData."""
        while True:
            url, source_metadata = await self._queue.get()

            async with self._visited_urls_lock:
                if url in self._visited_urls:
                    self._queue.task_done()
                    continue

                self._visited_urls.add(url)
                self._queued_urls.discard(url)

            async with semaphore:
                try:
                    html = await self._fetch_html(url, session)
                    if html:
                        if self._is_recipe_page(url, source_metadata):
                            await output_queue.put(RawRecipeData(html=html, source=source_metadata.name, url=url))

                        new_links = await self._parse_links(html, source_metadata)
                        async with self._visited_urls_lock:
                            for link in new_links:
                                if link not in self._visited_urls and link not in self._queued_urls:
                                    self._queued_urls.add(link)
                                    await self._queue.put((link, source_metadata))
                    await asyncio.sleep(random.uniform(*self._delay_range))
                except Exception as e:
                    logger.error(f"Error fetching {url}: {e}")

            self._queue.task_done()

    async def _parse_links(self, html: str, source_metadata: SourceMetadata) -> List[str]:
        """Parse HTML off the async loop to get recipe links."""
        soup = await asyncio.to_thread(BeautifulSoup, html, "html.parser")
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(pattern in href for pattern in source_metadata.recipe_link_pattern):
                full_url = urljoin(source_metadata.hostname, href)
                links.append(full_url)
        return links

    def _is_recipe_page(self, url: str, source_metadata: SourceMetadata) -> bool:
        return source_metadata.recipe_identifier in url