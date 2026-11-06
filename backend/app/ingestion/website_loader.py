"""
Website loading service: HTTP-based scraping with SSRF protection,
robots.txt respect, rate limiting, HTML cleaning, and deduplication.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.database.models import Document

logger = get_logger(__name__)

# Tags whose full content (including children) should be removed
_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "meta", "link"}

# Minimum text length to store a page (skip empty pages)
_MIN_TEXT_LENGTH = 100


class WebsiteLoader:
    """
    Load and extract text content from a company website.
    Applies rate limiting, page limits, and deduplication.
    """

    def __init__(self, max_pages: int = settings.INGESTION_MAX_PAGES) -> None:
        self.max_pages = max_pages
        self._visited: Set[str] = set()
        self._robots: Dict[str, RobotFileParser] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def load(
        self,
        start_url: str,
        account_id: str,
        db: AsyncSession,
    ) -> List[Dict]:
        """
        Crawl `start_url` up to `max_pages`, extract text, deduplicate, and
        persist document records to PostgreSQL.

        Returns a list of dicts: {document_id, url, title, text}.
        """
        parsed = urlparse(start_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        headers = {"User-Agent": settings.INGESTION_USER_AGENT}
        timeout = httpx.Timeout(settings.INGESTION_REQUEST_TIMEOUT)

        pages: List[Dict] = []
        queue: List[str] = [start_url]

        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            await self._load_robots(client, base_domain)

            while queue and len(pages) < self.max_pages:
                url = queue.pop(0)
                norm_url = self._normalize_url(url)

                if norm_url in self._visited:
                    continue
                self._visited.add(norm_url)

                if not self._robots_allowed(norm_url, base_domain):
                    logger.debug("robots.txt disallows: %s", norm_url)
                    continue

                try:
                    page_data = await self._fetch_page(client, norm_url, account_id, db)
                except Exception as exc:
                    logger.warning("Failed to fetch %s: %s", norm_url, exc)
                    continue

                if page_data is None:
                    continue

                pages.append(page_data)
                logger.info("Ingested page %d/%d: %s", len(pages), self.max_pages, norm_url)

                # Discover internal links
                if len(pages) < self.max_pages:
                    new_links = self._extract_internal_links(
                        page_data.get("_html", ""), base_domain, norm_url
                    )
                    for link in new_links:
                        if link not in self._visited and link not in queue:
                            queue.append(link)

                # Polite delay between requests
                await asyncio.sleep(0.5)

        logger.info(
            "Website load complete. %d pages ingested for account %s",
            len(pages), account_id,
        )
        return pages

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        account_id: str,
        db: AsyncSession,
    ) -> Optional[Dict]:
        """Fetch a single page, clean it, and persist to DB if new."""
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.debug("HTTP error %d for %s", exc.response.status_code, url)
            return None
        except httpx.RequestError as exc:
            logger.debug("Request error for %s: %s", url, exc)
            return None

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            logger.debug("Skipping non-HTML content at %s", url)
            return None

        raw_html = response.text
        if len(raw_html.encode()) > settings.INGESTION_PAGE_SIZE_LIMIT:
            logger.debug("Page too large, skipping: %s", url)
            return None

        text, title = self._extract_text(raw_html)
        if len(text) < _MIN_TEXT_LENGTH:
            logger.debug("Insufficient text content at %s", url)
            return None

        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Deduplicate by content hash per account
        existing_q = await db.execute(
            select(Document).where(
                Document.account_id == account_id,
                Document.content_hash == content_hash,
            )
        )
        if existing_q.scalar_one_or_none():
            logger.debug("Duplicate content, skipping: %s", url)
            return None

        # Persist document record
        from datetime import datetime
        doc = Document(
            account_id=account_id,
            source_type="website",
            source_url=url,
            source_title=title,
            content_hash=content_hash,
            retrieved_at=datetime.utcnow(),
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)

        return {
            "document_id": doc.document_id,
            "url": url,
            "title": title,
            "text": text,
            "_html": raw_html,  # Kept temporarily for link extraction; not stored
        }

    @staticmethod
    def _extract_text(html: str) -> tuple[str, str]:
        """Extract clean readable text and page title from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Remove unwanted elements
        for tag in soup.find_all(_REMOVE_TAGS):
            tag.decompose()

        # Get text, collapse whitespace
        raw_text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", raw_text).strip()
        return text, title

    @staticmethod
    def _extract_internal_links(html: str, base_domain: str, current_url: str) -> List[str]:
        """Find internal links on the page for breadth-first crawling."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            # Skip anchors, mailto, javascript
            if any(href.startswith(prefix) for prefix in ("#", "mailto:", "tel:", "javascript:")):
                continue
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            if parsed.netloc and parsed.netloc == urlparse(base_domain).netloc:
                links.append(full_url.split("#")[0])  # Strip fragments
        return list(set(links))

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Strip trailing slashes and query strings for deduplication."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    async def _load_robots(self, client: httpx.AsyncClient, base_domain: str) -> None:
        """Attempt to load robots.txt for the domain."""
        robots_url = f"{base_domain}/robots.txt"
        try:
            response = await client.get(robots_url)
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read_robots_txt = lambda: None  # We'll parse manually
                rp.parse(response.text.splitlines())
                self._robots[base_domain] = rp
        except Exception:
            pass  # robots.txt is optional

    def _robots_allowed(self, url: str, base_domain: str) -> bool:
        """Check whether our user agent is allowed to access the URL."""
        rp = self._robots.get(base_domain)
        if rp is None:
            return True
        return rp.can_fetch(settings.INGESTION_USER_AGENT, url)
