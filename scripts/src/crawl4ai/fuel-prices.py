import asyncio
import os
import csv
import pycountry
import argparse
import shutil
from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing
from crawl4ai import AsyncWebCrawler

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Crawl gasoline prices and save data.")
    parser.add_argument("--subfolder", type=str, help="Subfolder name inside scripts_output/crawl4ai", required=True)
    parser.add_argument("--clean", action="store_true", help="Clean the output folder before crawling")
    return parser.parse_args()

# Ensure output folder exists
def ensure_output_folder(base_folder: str, subfolder: str, clean: bool = False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_path = os.path.abspath(os.path.join(current_dir, "../../"))  # Go up two levels

    # Ensure base folder exists
    base_folder_path = os.path.join(output_base_path, base_folder)
    os.makedirs(base_folder_path, exist_ok=True)

    # Ensure subfolder exists inside the base folder
    output_path = os.path.join(base_folder_path, subfolder)
    if os.path.exists(output_path) and clean:
        shutil.rmtree(output_path)  # Clean the folder if the flag is set
    os.makedirs(output_path, exist_ok=True)

    print(f"Output folder ensured: {output_path}")
    return output_path

# Get ISO country codes
def get_country_codes(country_name):
    try:
        country = pycountry.countries.lookup(country_name)
        return country.alpha_2, country.alpha_3
    except LookupError:
        return "", ""

# Asynchronous scraping function
async def scrape_gasoline_prices(output_folder):
    # Initialize crawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler
        result = await crawler.arun(url="https://tradingeconomics.com/country-list/gasoline-prices?continent=world")

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(result.html, "html.parser")
        rows = soup.select('table tbody tr')

        # Extract the unit dynamically from the page
        unit_element = soup.find("span", class_="table-description")  # Adjust this selector if needed
        unit = unit_element.get_text(strip=True) if unit_element else "USD/Liter"  # Fallback if not found

        extracted_data = []

        # Extract data from the table
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                country = cells[0].get_text(strip=True)
                price = cells[1].get_text(strip=True)
                previous_price = cells[2].get_text(strip=True)
                reference = cells[3].get_text(strip=True)

                # Add ISO codes
                alpha2, alpha3 = get_country_codes(country)

                # Append extracted data dynamically with the actual unit
                extracted_data.append({
                    "Country": country,
                    "ALPHA2": alpha2,
                    "ALPHA3": alpha3,
                    "Price": price,
                    "PreviousPrice": previous_price,
                    "Reference": reference,
                    "Unit": unit  # Dynamically extracted unit
                })

        # Save data to CSV in the specified folder
        csv_file = os.path.join(output_folder, "gasoline_prices_crawl4ai.csv")
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["Country", "ALPHA2", "ALPHA3", "Price", "PreviousPrice", "Reference", "Unit"])
            writer.writeheader()
            for entry in extracted_data:
                writer.writerow(entry)

        print(f"Scraped data has been saved to {csv_file}")

# Main function to parse arguments and run scraping
if __name__ == "__main__":
    args = parse_args()

    base_folder = "scripts_output/crawl4ai"
    output_folder = ensure_output_folder(base_folder, args.subfolder, clean=args.clean)

    asyncio.run(scrape_gasoline_prices(output_folder))