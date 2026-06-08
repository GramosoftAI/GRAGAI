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
        crawl_type: str = "all", 
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
            
            if response_data and response_data.get("status") == "queued" and response_data.get("crawl_id"):
                crawl_id = response_data.get("crawl_id")
                logger.info(f" Gcrawl queued task {crawl_id} for {url}. Polling for results...")
                response_data = await ScraperService.poll_gcrawl_data(crawl_id)
            
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
        Call the Gcrawl Scrape API with retries and advanced payload.
        """
        # Read from settings
        crawler_api_key = getattr(settings, "crawler_api_key", None)
        crawler_mode = getattr(settings, "crawler_mode", crawl_type)
        enable_md = getattr(settings, "crawler_enable_md", True)
        
        is_all = (crawler_mode == "all")

        payload = {
            "url": url,
            "crawl": {
                "max_pages": 1000 if is_all else 1,
                "same_domain_only": True,
                "include_subdomains": False
            },
            "proxy": {
                "geo": proxy_mode if proxy_mode in ["us", "eu", "as"] else "string"
            },
            "markdown": {
                "enabled": enable_md,
                "clean": True
            },
            "html": {
                "enabled": True,
                "clean": True,
                "remove_external_links": False,
                "relative_to_absolute_links": True,
                "remove_data_images": False,
                "ignore_tags": []
            },
            "screenshot": {
                "enabled": False, # Disabled by default to save bandwidth, unless requested
                "full_page": False,
                "format": "png",
                "quality": 90,
                "js_render": False,
                "render_timeout": 30000,
                "auto_scroll": True,
                "scroll_delay": 500,
                "max_scrolls": 2
            },
            "seo": {
                "enabled": True
            },
            "images": {
                "enabled": True
            }
        }
        
        base_url = getattr(
            settings,
            "crawler_api_url",
            "https://gcrawlai.com/gc/api/v1"
        ).rstrip("/") + "/crawl"
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if crawler_api_key:
            headers["X-API-Key"] = crawler_api_key

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
    async def poll_gcrawl_data(crawl_id: str, timeout_seconds: int = 60) -> Optional[Dict[str, Any]]:
        """
        Poll the Gcrawl data endpoint until status is 'success' or timeout is reached.
        """
        crawler_api_key = getattr(settings, "crawler_api_key", None)
        base_url = getattr(
            settings,
            "crawler_api_url",
            "https://gcrawlai.com/gc/api/v1"
        ).rstrip("/")
        
        poll_url = f"{base_url}/crawler/data/{crawl_id}"
        
        headers = {
            "accept": "application/json"
        }
        if crawler_api_key:
            headers["X-API-Key"] = crawler_api_key
            
        start_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                    logger.warning(f"Gcrawl polling timed out after {timeout_seconds}s for task {crawl_id}")
                    return None
                    
                try:
                    response = await client.get(poll_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    status = data.get("status")
                    if status == "success":
                        logger.info(f"Gcrawl polling success for task {crawl_id}")
                        return data
                    elif status in ["failed", "error"]:
                        logger.error(f"Gcrawl task {crawl_id} failed: {data}")
                        return None
                        
                    # If still queued/processing, wait and poll again
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"Error while polling Gcrawl task {crawl_id}: {e}")
                    await asyncio.sleep(3)

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
