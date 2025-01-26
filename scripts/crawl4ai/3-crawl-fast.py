# https://crawl4ai.com/mkdocs/advanced/multi-url-crawling/

import asyncio
import os
import aiohttp
import re
import psutil
from xml.etree import ElementTree as ET
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from datetime import datetime

def ensure_output_folder(folder_name: str):
    """Ensure the output folder exists, relative to the script's location."""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get current script directory
    output_path = os.path.join(current_dir, folder_name)  # Create full path
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created folder: {output_path}")
    return output_path

async def fetch_sitemap_urls(sitemap_url: str) -> List[str]:
    """Fetch and parse URLs from a sitemap XML."""
    async with aiohttp.ClientSession() as session:
        async with session.get(sitemap_url) as response:
            if response.status != 200:
                print(f"Failed to fetch sitemap: {response.status}")
                return []

            sitemap_content = await response.text()
            root = ET.fromstring(sitemap_content)

            urls = []
            for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                if url.text:  # Ensure there's text in the <loc> element
                    urls.append(url.text.strip())  # Strip whitespace or newlines

            return urls

async def crawl_parallel(urls: List[str], max_concurrent: int = 3):
    print("\n=== Parallel Crawling with Crawl4AI Native Filtering ===")

    # Dynamically set the output folder based on the script's location
    output_folder = ensure_output_folder("markdown_output")

    peak_memory = 0
    process = psutil.Process(os.getpid())

    def log_memory(prefix: str = ""):
        nonlocal peak_memory
        current_mem = process.memory_info().rss  # in bytes
        if current_mem > peak_memory:
            peak_memory = current_mem
        print(f"{prefix} Current Memory: {current_mem // (1024 * 1024)} MB, Peak: {peak_memory // (1024 * 1024)} MB")

    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(),  # Use Crawl4AI native filtering
    )

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        success_count = 0
        fail_count = 0
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            tasks = []

            for j, url in enumerate(batch):
                session_id = f"parallel_session_{i + j}"
                task = crawler.arun(url=url, config=crawl_config, session_id=session_id)
                tasks.append(task)

            log_memory(prefix=f"Before batch {i // max_concurrent + 1}: ")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            log_memory(prefix=f"After batch {i // max_concurrent + 1}: ")

            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    print(f"Error crawling {url}: {result}")
                    fail_count += 1
                elif result.success:
                    success_count += 1

                    # Save raw markdown
                    raw_filename = os.path.join(
                        output_folder, f"{re.sub(r'^https?://', '', url).replace('/', '_')}.md"
                    )
                    with open(raw_filename, "w", encoding="utf-8") as raw_file:
                        raw_file.write(result.markdown_v2.raw_markdown)
                else:
                    fail_count += 1

        print(f"\nSummary:")
        print(f"  - Successfully crawled: {success_count}")
        print(f"  - Failed: {fail_count}")

    finally:
        print("\nClosing crawler...")
        await crawler.close()
        log_memory(prefix="Final: ")
        print(f"\nPeak memory usage (MB): {peak_memory // (1024 * 1024)}")

async def main():
    # sitemap_url = "https://mywayroute.com/sitemap.xml"
    sitemap_url = "https://help.mywayroute.com/sitemap-pages.xml" 
    print("Fetching URLs from sitemap...")
    urls = await fetch_sitemap_urls(sitemap_url)

    if not urls:
        print("No URLs found in the sitemap.")
        return

    print(f"Found {len(urls)} URLs in the sitemap.")
    await crawl_parallel(urls, max_concurrent=5)

if __name__ == "__main__":
    asyncio.run(main())