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
from urllib.parse import urljoin, urlparse, parse_qs, unquote  # <- extended import
import aiofiles
import argparse
import shutil  # For folder cleanup


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Crawl websites with Crawl4AI.")
    parser.add_argument("--website", type=str, help="URL of the website to crawl", required=True)
    parser.add_argument("--subfolder", type=str, help="Subfolder name inside scripts_output/crawl4ai", required=True)
    parser.add_argument("--clean", action="store_true", help="Clean the output folder before crawling")
    return parser.parse_args()


def clean_folder(folder_path: str):
    """Delete all files and subfolders in the specified folder."""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symlink
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print(f"Cleaned folder: {folder_path}")
    else:
        print(f"Folder does not exist: {folder_path}")


def ensure_output_folder(base_folder: str, subfolder: str, clean: bool = False):
    """Ensure both the base folder and subfolder exist inside the output path."""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get current script directory
    output_base_path = os.path.abspath(os.path.join(current_dir, "../../"))  # Move two levels up

    # Ensure base folder exists
    base_folder_path = os.path.join(output_base_path, base_folder)
    os.makedirs(base_folder_path, exist_ok=True)

    # Ensure subfolder exists inside base folder
    output_path = os.path.join(base_folder_path, subfolder)
    if os.path.exists(output_path) and clean:
        clean_folder(output_path)  # Clean the folder if the flag is set

    os.makedirs(output_path, exist_ok=True)
    print(f"Output folder ensured: {output_path}")
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


# Global dictionary to store hashes of saved images
saved_images_hashes = {}


async def download_image(session, img_url, output_folder, page_url):
    """Download and save an image only if its hash does not already exist."""
    try:
        # Parse the URL to extract the base filename and query parameters
        parsed_url = urlparse(img_url)
        base_name = os.path.basename(parsed_url.path)

        # Extract the extension or default to .jpg
        extension = os.path.splitext(base_name)[1]
        if not extension:
            # Try to infer from query parameters
            if "format" in parse_qs(parsed_url.query):
                extension = f".{parse_qs(parsed_url.query)['format'][0]}"
            else:
                extension = ".jpg"  # Default fallback

        # Build a unique filename using page context
        page_context = urlparse(page_url).path.replace("/", "_").strip("_")
        query_hash = hashlib.md5(parsed_url.query.encode()).hexdigest() if parsed_url.query else "noquery"
        filename = f"{parsed_url.netloc.replace('https', '').replace('http', '').replace(':', '_').replace('/', '_')}_{page_context}_{base_name}_{query_hash}{extension}"
        filename = os.path.join(output_folder, filename)

        # Download the image
        async with session.get(img_url) as response:
            if response.status == 200:
                content = await response.read()

                # Calculate the hash of the image content
                content_hash = hashlib.md5(content).hexdigest()

                # Check if the image hash already exists
                if content_hash in saved_images_hashes:
                    print(f"Duplicate image found: {img_url} -> Skipping download")
                    return saved_images_hashes[content_hash]  # Return existing filename

                # Save the image and add the hash to the dictionary
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(content)
                saved_images_hashes[content_hash] = filename  # Map hash to filename
                print(f"Image saved: {filename}")
                return filename
            else:
                print(f"Failed to download image {img_url}: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"Error downloading image {img_url}: {e}")
        return None


# --- smarter file downloader for .xlsx/.xls/.csv (handles query, headers) ---
async def download_file(session, file_url, files_folder, page_url):
    try:
        os.makedirs(files_folder, exist_ok=True)

        parsed = urlparse(file_url)
        base_name = os.path.basename(parsed.path) or "file"
        base_name = unquote(base_name)

        # guess extension from path
        ext = os.path.splitext(base_name)[1].lower()

        async with session.get(file_url) as resp:
            if resp.status != 200:
                print(f"Failed to download file {file_url}: HTTP {resp.status}")
                return None

            # try to get filename from Content-Disposition
            cd = resp.headers.get("Content-Disposition", "")
            if "filename" in cd:
                # Try RFC 5987 filename* first, then regular filename
                m = re.search(r"filename\*=(?:UTF-8''|utf-8''|)([^;]+)", cd, re.IGNORECASE) \
                    or re.search(r'filename="?([^";]+)"?', cd)
                if m:
                    base_name = unquote(m.group(1).strip())
                    # Remove leftover utf-8'' prefix if still present
                    base_name = base_name.lstrip("utf-8''").lstrip("UTF-8''")
                    ext = os.path.splitext(base_name)[1].lower() or ext

            # if still no extension, infer from content-type
            if not ext:
                ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if ct == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    ext = ".xlsx"
                elif ct in ("application/vnd.ms-excel", "application/octet-stream"):
                    ext = ".xls"
                elif ct in ("text/csv", "application/csv"):
                    ext = ".csv"
                else:
                    ext = ".bin"

            # ensure filename has extension
            if not base_name.lower().endswith(ext):
                base_name = f"{base_name}{ext}"

            save_path = os.path.join(files_folder, base_name)
            content = await resp.read()

        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)
        print(f"File saved: {save_path}")
        return save_path
    except Exception as e:
        print(f"Error downloading file {file_url}: {e}")
        return None
# --- END ---


async def crawl_parallel(urls: List[str], subfolder: str, max_concurrent: int = 3, clean: bool = False):
    print("\n=== Parallel Crawling with Image Saving ===")

    base_folder = "scripts_output/crawl4ai"
    output_folder = ensure_output_folder(base_folder, subfolder, clean=clean)
    image_folder = os.path.join(output_folder, "images")
    os.makedirs(image_folder, exist_ok=True)
    files_folder = os.path.join(output_folder, "files")
    os.makedirs(files_folder, exist_ok=True)

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
                            raw_file.write(result.markdown.raw_markdown)
                        print(f"Markdown saved: {raw_filename}")

                        # Parse the markdown content
                        markdown_content = result.markdown.raw_markdown
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

                        # --- extract file links by path extension (ignore query) ---
                        raw_links = re.findall(r"\[.*?\]\(([^)]+)\)", markdown_content)
                        file_links = []
                        for link in raw_links:
                            abs_link = urljoin(url, link)
                            p = urlparse(abs_link)
                            ext = os.path.splitext(p.path)[1].lower()
                            if ext in (".xlsx", ".xls", ".csv"):
                                file_links.append(abs_link)
                        if file_links:
                            print(f"Found files in {url}: {file_links}")
                        # --- END ---

                        print(f"Extracted image URLs from {url}: {image_urls}")

                        # Download images
                        for img_url in image_urls:
                            await download_image(session, img_url, image_folder, url)

                        # Download files
                        for file_url in file_links:
                            await download_file(session, file_url, files_folder, url)

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


async def main(sitemap_url: str, subfolder: str, clean: bool):
    print("Fetching URLs from sitemap...")
    urls = await fetch_sitemap_urls(sitemap_url)

    if not urls:
        print("No URLs found in the sitemap.")
        return

    print(f"Found {len(urls)} URLs in the sitemap.")
    await crawl_parallel(urls, subfolder, max_concurrent=5, clean=clean)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.website, args.subfolder, args.clean))