# Run Crawl4Ai Locally

Form `scripts/src/crawl4ai` folder `pip install -r requirements.txt` and `playwright install`

# How To Setup Crawl4Ai

You might need to do `playwright install-deps` in a container (if it's not part of Dockerfile)
After all done try `python crawl4ai/3-crawl-fast.py`

# Scripts

`python3 3-crawl-fast.py --website "https://proalab.com/sitemap.xml" --subfolder "proalab" --clean`

`python3 3-crawl-fast.py --website "https://help.mywayroute.com/sitemap-pages.xml" --subfolder "myway_route_planner" --clean`
`python3 3-crawl-fast.py --website "https://www.mywayroute.com/sitemap.xml" --subfolder "myway_route_planner"`

`python fuel-prices.py --subfolder "fuel_prices" --clean`