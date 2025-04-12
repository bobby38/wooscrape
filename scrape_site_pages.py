import sys
import json
import os
from urllib.parse import urljoin, urlparse
from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
from dotenv import load_dotenv

print("[DEBUG] Loading .env file...")
load_dotenv()
API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
if API_KEY:
    print(f"[DEBUG] SCRAPINGBEE_API_KEY loaded: {API_KEY[:4]}...{API_KEY[-4:]}")
else:
    print("[DEBUG] SCRAPINGBEE_API_KEY not found in environment.")
BASE_URL = "https://tradezone.sg"

if not API_KEY or API_KEY == "your_scrapingbee_api_key_here":
    print("[ERROR] Please set your SCRAPINGBEE_API_KEY in the .env file.", file=sys.stderr)
    sys.exit(1)

client = ScrapingBeeClient(api_key=API_KEY)

def is_internal_link(href, base_domain):
    if not href:
        return False
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc != base_domain:
        return False
    if parsed.scheme and parsed.scheme not in ["http", "https", ""]:
        return False
    return True

def get_main_nav_links(soup, base_url):
    # Try to find navigation links (header nav, menu, etc.)
    nav_links = set()
    # Common navigation containers
    nav_selectors = [
        "nav", "header", ".main-navigation", ".menu", ".site-navigation"
    ]
    for selector in nav_selectors:
        for nav in soup.select(selector):
            for a in nav.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("#"):
                    continue
                full_url = urljoin(base_url, href)
                nav_links.add(full_url)
    # Fallback: all <a> tags on the homepage
    if not nav_links:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#"):
                continue
            full_url = urljoin(base_url, href)
            nav_links.add(full_url)
    return list(nav_links)

def filter_unique_internal_links(links, base_domain):
    unique = set()
    for link in links:
        parsed = urlparse(link)
        if is_internal_link(link, base_domain):
            # Normalize: remove query, fragment
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            unique.add(clean_url)
    return list(unique)

def scrape_page(url):
    print(f"[INFO] Scraping page: {url}")
    response = client.get(
        url,
        params={
            'premium_proxy': True,
            'country_code': 'us',
            "block_resources": False,
            'device': 'desktop',
        }
    )
    if response.status_code != 200:
        print(f"[WARN] Failed to fetch {url}: {response.status_code}", file=sys.stderr)
        return None
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.title.string.strip() if soup.title else ""
    h1s = [h1.text.strip() for h1 in soup.find_all("h1")]
    h2s = [h2.text.strip() for h2 in soup.find_all("h2")]
    # Optionally, extract main text content
    paragraphs = [p.text.strip() for p in soup.find_all("p")]
    return {
        "url": url,
        "title": title,
        "h1": h1s,
        "h2": h2s,
        "paragraphs": paragraphs,
        "html": soup.prettify()
    }

def main():
    base_domain = urlparse(BASE_URL).netloc
    print(f"[INFO] Fetching homepage: {BASE_URL}")
    response = client.get(
        BASE_URL,
        params={
            'premium_proxy': True,
            'country_code': 'us',
            "block_resources": False,
            'device': 'desktop',
        }
    )
    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch homepage: {response.status_code}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(response.content, 'html.parser')
    nav_links = get_main_nav_links(soup, BASE_URL)
    unique_links = filter_unique_internal_links(nav_links, base_domain)
    print(f"[INFO] Found {len(unique_links)} unique internal links to scrape.")

    scraped_pages = []
    for url in unique_links:
        page_data = scrape_page(url)
        if page_data:
            scraped_pages.append(page_data)

    try:
        with open("site_pages.json", "w") as f:
            json.dump(scraped_pages, f, indent=4)
        print(f"[INFO] Saved {len(scraped_pages)} pages to site_pages.json")
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()