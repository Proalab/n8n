# https://crawl4ai.com/mkdocs/advanced/multi-url-crawling/

import asyncio
import os
import aiohttp
import hashlib
import re
import psutil
from xml.etree import ElementTree as ET
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import aiofiles
import argparse

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Crawl websites with Crawl4AI.")
    parser.add_argument("--website", type=str, help="URL of the website to crawl", required=True)
    return parser.parse_args()

def ensure_output_folder(folder_name: str):
    """Ensure the output folder exists, two levels up from the script's location."""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get current script directory
    output_base_path = os.path.abspath(os.path.join(current_dir, "../../"))  # Move two levels up
    output_path = os.path.join(output_base_path, folder_name)  # Append the folder name

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
                if url.text:
                    urls.append(url.text.strip())

            return urls

from urllib.parse import urlparse, parse_qs

async def download_image(session, img_url, output_folder, page_url):
    """Download and save an image with a proper filename."""
    try:
        # Parse the URL to extract the base filename
        parsed_url = urlparse(img_url)
        query_params = parse_qs(parsed_url.query)
        base_name = os.path.basename(parsed_url.path)

        # Determine the correct file extension
        extension = os.path.splitext(base_name)[1] or ".jpg"  # Default to .jpg if no extension
        if not extension.startswith("."):
            extension = f".{extension}"

        # Add query parameters to differentiate images if needed
        unique_name = hashlib.md5((img_url + page_url).encode()).hexdigest() + extension

        # Final file path
        filename = os.path.join(output_folder, unique_name)

        async with session.get(img_url) as response:
            if response.status == 200:
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(await response.read())
                print(f"Image saved: {filename}")
            else:
                print(f"Failed to download image {img_url}: HTTP {response.status}")
    except Exception as e:
        print(f"Error downloading image {img_url}: {e}")

async def crawl_parallel(urls: List[str], max_concurrent: int = 3):
    print("\n=== Parallel Crawling with Image Saving ===")

    output_folder = ensure_output_folder("scripts_output/crawl4ai")
    image_folder = os.path.join(output_folder, "images")
    os.makedirs(image_folder, exist_ok=True)

    peak_memory = 0
    process = psutil.Process(os.getpid())
    success_count = 0
    fail_count = 0

    def log_memory(prefix: str = ""):
        nonlocal peak_memory
        current_mem = process.memory_info().rss
        if current_mem > peak_memory:
            peak_memory = current_mem
        print(f"{prefix} Current Memory: {current_mem // (1024 * 1024)} MB, Peak: {peak_memory // (1024 * 1024)} MB")

    browser_config = BrowserConfig(headless=True, extra_args=["--disable-gpu", "--no-sandbox"])
    crawl_config = CrawlerRunConfig(markdown_generator=DefaultMarkdownGenerator())

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(urls), max_concurrent):
                batch = urls[i:i + max_concurrent]
                tasks = [crawler.arun(url=url, config=crawl_config, session_id=f"parallel_session_{i + j}") for j, url in enumerate(batch)]

                log_memory(prefix=f"Before batch {i // max_concurrent + 1}: ")

                results = await asyncio.gather(*tasks, return_exceptions=True)

                log_memory(prefix=f"After batch {i // max_concurrent + 1}: ")

                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        print(f"Error crawling {url}: {result}")
                        fail_count += 1
                        continue
                    elif result.success:
                        success_count += 1
                        # Save raw markdown
                        raw_filename = os.path.join(output_folder, f"{re.sub(r'^https?://', '', url).replace('/', '_')}.md")
                        with open(raw_filename, "w", encoding="utf-8") as raw_file:
                            raw_file.write(result.markdown_v2.raw_markdown)
                        print(f"Markdown saved: {raw_filename}")

                        # Parse the markdown content
                        markdown_content = result.markdown_v2.raw_markdown
                        soup = BeautifulSoup(markdown_content, "html.parser")

                        # Extract image URLs from <img> tags
                        image_urls = []
                        for img in soup.find_all("img"):
                            src = img.get("src") or img.get("data-src")
                            if src:
                                image_urls.append(urljoin(url, src))

                        # Extract image URLs from markdown syntax (![...](...))
                        markdown_images = re.findall(r"!\[.*?\]\((.*?)\)", markdown_content)
                        image_urls.extend(urljoin(url, img_url) for img_url in markdown_images)

                        print(f"Extracted image URLs from {url}: {image_urls}")

                        # Download images
                        for img_url in image_urls:
                            await download_image(session, img_url, image_folder, url)
                    else:
                        fail_count += 1
                        print(f"Failed to crawl {url}")

        print("\nSummary:")
        print(f"  - Successfully crawled: {success_count}")
        print(f"  - Failed: {fail_count}")
    finally:
        print("\nClosing crawler...")
        await crawler.close()
        log_memory(prefix="Final: ")
        print(f"\nPeak memory usage (MB): {peak_memory // (1024 * 1024)}")

async def main(sitemap_url: str):
    print("Fetching URLs from sitemap...")
    urls = await fetch_sitemap_urls(sitemap_url)

    if not urls:
        print("No URLs found in the sitemap.")
        return

    print(f"Found {len(urls)} URLs in the sitemap.")
    await crawl_parallel(urls, max_concurrent=5)

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.website))
