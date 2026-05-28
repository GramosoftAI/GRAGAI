import logging
import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from ....core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ScraperService:
    """
    Unified scraper service with Gcrawl primary and BeautifulSoup fallback.
    
    STRATEGY:
    1. Try Gcrawl API (JS-rendering, high success, multi-page support)
    2. Fallback to BeautifulSoup (Resilient local extraction)
    """

    @staticmethod
    async def extract_website_content(
        url: str, 
        crawl_type: str = "single", 
        proxy_mode: str = "basic"
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for website extraction.
        
        Args:
            url: Target URL
            crawl_type: "single" or "all"
            proxy_mode: "basic", "stealth", or "enhanced"
            
        Returns:
            List of normalized document dicts
        """
        # URL Normalization: Remove trailing slashes which can confuse some crawlers
        url = url.rstrip("/")
        
        if not settings.gcrawl_enabled:
            logger.info("Gcrawl is disabled. Using BeautifulSoup fallback.")
            return await ScraperService.extract_with_beautifulsoup(url)

        try:
            # 1. Try Gcrawl API
            response_data = await ScraperService.call_gcrawl_api(url, crawl_type, proxy_mode)
            
            if response_data and response_data.get("data"):
                logger.info(f" Gcrawl success for {url}")
                return ScraperService.normalize_gcrawl_response(response_data)
            
            logger.warning(f"Gcrawl returned empty data for {url}. Falling back.")

        except Exception as e:
            logger.warning(f"Gcrawl failed for {url}: {str(e)}. Falling back.")

        # 2. Fallback -> BeautifulSoup
        return await ScraperService.extract_with_beautifulsoup(url)

    @staticmethod
    async def call_gcrawl_api(url: str, crawl_type: str, proxy_mode: str) -> Optional[Dict[str, Any]]:
        """
        Call the Gcrawl Scrape API with retries.
        
        API: POST https://gcrawl.gramopro.ai/scrape
        Body: { "url": "...", "type": "single|all", "proxymode": "basic|stealth|enhanced" }
        """
        payload = {
            "url": url,
            "type": crawl_type,
            "proxymode": proxy_mode
        }
        
        base_url = getattr(settings, "crawler_api_url", "https://gcrawlai.com").rstrip("/") + "/scrape"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=settings.gcrawl_timeout) as client:
            for attempt in range(settings.gcrawl_retry + 1):
                try:
                    response = await client.post(base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    return response.json()
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    if attempt < settings.gcrawl_retry:
                        logger.warning(f"Gcrawl attempt {attempt + 1} failed: {e}. Retrying...")
                        await asyncio.sleep(1)
                    else:
                        raise e
        return None

    @staticmethod
    def normalize_gcrawl_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize Gcrawl response to existing document schema.
        
        CRITICAL: Ensures compatibility with the chunking and embedding pipeline.
        """
        documents = []
        data = response.get("data", [])
        
        # Gcrawl might return a single dict or a list
        if isinstance(data, dict):
            data = [data]
            
        for page in data:
            # Extract content from Gcrawl structure
            # Prioritize markdown then text content
            content = page.get("markdown") or page.get("text") or ""
            if not content.strip():
                continue
                
            documents.append({
                "content": content,
                "source": page.get("url"),
                "metadata": {
                    "title": page.get("title", "Untitled Page"),
                    "description": page.get("description"),
                    "crawl_id": response.get("crawl_id")
                }
            })
            
        return documents

    @staticmethod
    async def extract_with_beautifulsoup(url: str) -> List[Dict[str, Any]]:
        """
        Fallback extraction using BeautifulSoup.
        Standard resilient scraping for non-JS heavy sites.
        """
        try:
            logger.info(f" BeautifulSoup extraction for: {url}")
            async with httpx.AsyncClient(timeout=15.0) as client:
                headers = {"User-Agent": "GraphMind/1.0.0"}
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Basic cleaning: remove noise elements
                for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    s.decompose()
                
                # Get title
                title_tag = soup.find("title")
                title = title_tag.get_text() if title_tag else "Untitled Page"
                
                # Get text content with basic structure preservation
                text_content = "\n".join([
                    l.strip() 
                    for l in soup.get_text(separator="\n").splitlines() 
                    if l.strip()
                ])
                
                if not text_content:
                    logger.warning(f"BS4 produced empty content for {url}")
                    return []
                    
                return [{
                    "content": text_content,
                    "source": url,
                    "metadata": {
                        "title": title.strip()
                    }
                }]
                
        except Exception as e:
            logger.error(f"BeautifulSoup fallback also failed: {e}")
            return []
