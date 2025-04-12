import streamlit as st
import requests
from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
import jmespath
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

def clean_html(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'header', 'footer', 'nav']):
        tag.decompose()
    for span in soup.find_all('span'):
        span.unwrap()
    text = soup.get_text(separator=' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def scrape_woocommerce_api(base_url, consumer_key, consumer_secret):
    st.info("Fetching products from WooCommerce API...")
    products = []
    per_page = 100
    page = 1
    api_url = f"{base_url.rstrip('/')}/wp-json/wc/v3/products"
    while True:
        resp = requests.get(
            api_url,
            auth=(consumer_key, consumer_secret),
            params={"per_page": per_page, "page": page}
        )
        if resp.status_code != 200:
            st.error(f"API error: {resp.status_code} {resp.text}")
            break
        page_products = resp.json()
        if not page_products:
            break
        products.extend(page_products)
        page += 1
    st.success(f"Fetched {len(products)} products.")
    return products

def scrape_html(base_url, api_key, max_pages=5):
    st.info("Scraping product data from HTML using ScrapingBee...")
    client = ScrapingBeeClient(api_key=api_key)
    page_urls = []
    for page_num in range(1, max_pages+1):
        st.write(f"Fetching shop page {page_num}...")
        resp = client.get(
            f"{base_url.rstrip('/')}/page/{page_num}",
            params={
                'premium_proxy': True,
                'country_code': 'us',
                "block_resources": True,
                'device': 'desktop',
            }
        )
        if resp.status_code != 200:
            st.warning(f"Failed to fetch page {page_num}: {resp.status_code}")
            continue
        soup = BeautifulSoup(resp.content, 'html.parser')
        product_links = soup.select('li.product a.woocommerce-LoopProduct-link')
        for link in product_links:
            page_urls.append(link['href'])
    st.write(f"Collected {len(page_urls)} product URLs.")

    products_data = []
    for idx, url in enumerate(page_urls):
        st.write(f"Scraping product {idx+1}/{len(page_urls)}: {url}")
        resp = client.get(
            url,
            params={'premium_proxy': True}
        )
        if resp.status_code != 200:
            st.warning(f"Failed to fetch product page: {url} ({resp.status_code})")
            continue
        soup = BeautifulSoup(resp.content, 'html.parser')
        # JSON-LD
        json_ld = soup.find('script', {'type': 'application/ld+json'})
        if json_ld:
            try:
                product_data = json.loads(json_ld.string)
                cleaned_data = jmespath.search('{name: name, description: description, price: offers.price, url: url}', product_data)
                if cleaned_data and 'description' in cleaned_data and cleaned_data['description']:
                    cleaned_data['description'] = clean_html(cleaned_data['description'])
                products_data.append(cleaned_data)
                continue
            except Exception as e:
                st.warning(f"JSON-LD extraction failed for {url}: {e}")
        # Fallback
        product = {}
        product['url'] = url
        name_elem = soup.select_one('h1.product_title')
        product['name'] = name_elem.text.strip() if name_elem else ""
        desc_elems = soup.select('div.description p')
        raw_description = ' '.join([p.text.strip() for p in desc_elems])
        product['description'] = clean_html(raw_description) if raw_description else ""
        price_elem = soup.select_one('span.price')
        product['price'] = price_elem.text.strip() if price_elem else ""
        # Variations
        variations = []
        variation_elements = soup.select('table.variations tr')
        for element in variation_elements:
            label = element.select_one('label')
            name = label.text.strip() if label else ""
            options = [opt.text.strip() for opt in element.select('select option') if opt.get('value')]
            variations.append({'name': name, 'options': options})
        product['variations'] = variations
        products_data.append(product)
    st.success(f"Scraped {len(products_data)} products.")
    return products_data

st.write("App Loaded - Test")

st.title("WooCommerce Product Scraper")

mode = st.radio("Select scraping mode:", ("WooCommerce API", "HTML (ScrapingBee)", "Crawl4AI", "Scrapy", "BeautifulSoup (Direct)"))
st.write(f"[DEBUG] Selected mode: '{mode}'")

if mode == "WooCommerce API":
    base_url = st.text_input("WooCommerce Site URL (e.g. https://tradezone.sg)", value=os.getenv("WOOCOMMERCE_URL", ""))
    consumer_key = st.text_input("Consumer Key", value=os.getenv("WOOCOMMERCE_CONSUMER_KEY", ""))
    consumer_secret = st.text_input("Consumer Secret", type="password", value=os.getenv("WOOCOMMERCE_CONSUMER_SECRET", ""))
    if st.button("Scrape Products"):
        if not base_url or not consumer_key or not consumer_secret:
            st.error("Please provide all required fields.")
        else:
            products = scrape_woocommerce_api(base_url, consumer_key, consumer_secret)
            st.write(products)
            st.download_button("Download JSON", json.dumps(products, indent=4), file_name="woocommerce_products.json")
elif mode == "HTML (ScrapingBee)":
    base_url = st.text_input("Shop URL (e.g. https://tradezone.sg/shop)", value=os.getenv("WOOCOMMERCE_URL", ""))
    api_key = st.text_input("ScrapingBee API Key", type="password", value=os.getenv("SCRAPINGBEE_API_KEY", ""))
    max_pages = st.number_input("Number of shop pages to scrape", min_value=1, max_value=50, value=5)
    if st.button("Scrape Products"):
        if not base_url or not api_key:
            st.error("Please provide all required fields.")
        else:
            products = scrape_html(base_url, api_key, max_pages)
            st.write(products)
            st.download_button("Download JSON", json.dumps(products, indent=4), file_name="woocommerce_products.json")
elif mode == "Crawl4AI":
    st.info("Crawl any URL using Crawl4AI API")
    crawl4ai_url = st.text_input("Target URL to crawl (e.g. https://tradezone.sg/)")
    crawl4ai_token = st.text_input("CRAWL4AI_API_TOKEN", type="password", value=os.getenv("CRAWL4AI_API_TOKEN", ""))
    crawl4ai_api_base = st.text_input("Crawl4AI API Base (e.g. https://crawl.getrezult.com)", value=os.getenv("CRAWL4AI_API_BASE", "https://crawl.getrezult.com"))
    if st.button("Start Crawl"):
        if not crawl4ai_url or not crawl4ai_token or not crawl4ai_api_base:
            st.error("Please provide all required fields.")
        else:
            # Start crawl
            headers = {"Authorization": f"Bearer {crawl4ai_token}", "Content-Type": "application/json"}
            start_resp = requests.post(
                f"{crawl4ai_api_base.rstrip('/')}/crawl",
                headers=headers,
                json={"urls": [crawl4ai_url]}
            )
            if start_resp.status_code != 200:
                st.error(f"Failed to start crawl: {start_resp.status_code} {start_resp.text}")
            else:
                task = start_resp.json()
                st.write("Crawl4AI start response:", task)
                # Try to extract task id from various possible locations
                task_id = task.get("id") or task.get("task_id") or task.get("task", {}).get("id")
                st.write(f"Extracted task_id: {task_id}")
                st.write(f"Started crawl, task id: {task_id}")
                # Poll for result
                import time
                import time
                result = None
                time.sleep(5)  # Wait longer before first poll
                for i in range(30):
                    poll_url = f"{crawl4ai_api_base.rstrip('/')}/task/{task_id}"
                    st.write(f"Polling URL: {poll_url}")
                    poll_resp = requests.get(
                        poll_url,
                        headers=headers
                    )
                    if poll_resp.status_code == 200:
                        data = poll_resp.json()
                        status = data.get("status", "unknown")
                        st.write(f"Task status: {status} (try {i+1}/30)")
                        if status in ["finished", "done", "completed"]:
                            result = data
                            break
                    else:
                        st.warning(f"Polling failed: {poll_resp.status_code} at {poll_url}")
                    time.sleep(2)
                if result:
                    st.success("Crawl finished!")
                    st.write(result)
                    st.download_button("Download JSON", json.dumps(result, indent=4), file_name="crawl4ai_result.json")
                else:
                    st.error("Crawl did not finish in time. Try again later or check the Crawl4AI dashboard.")

elif mode == "Scrapy":
    import tempfile
    import os
    import subprocess

    st.info("Crawl any URL using Scrapy (single page demo)")
    scrapy_url = st.text_input("Target URL to crawl (e.g. https://tradezone.sg/)")
    if st.button("Start Scrapy Crawl"):
        if not scrapy_url:
            st.error("Please provide a target URL.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                spider_path = os.path.join(tmpdir, "simple_spider.py")
                output_path = os.path.join(tmpdir, "scrapy_output.json")
                # Write a simple spider that extracts all text and links from the page
                spider_code = f'''
import scrapy
import json

class SimpleSpider(scrapy.Spider):
    name = "simplespider"
    start_urls = ["{scrapy_url}"]

    custom_settings = {{
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }}

    def parse(self, response):
        self.logger.info(f"Response status: {{response.status}}")
        self.logger.info(f"Response body sample: {{response.text[:500]}}")
        if response.status != 200 or not response.text.strip():
            yield {{
                "error": "No content or non-200 response",
                "status": response.status,
                "url": response.url,
                "body_sample": response.text[:500]
            }}
            return
        yield {{
            "url": response.url,
            "title": response.css("title::text").get(),
            "h1": response.css("h1::text").getall(),
            "h2": response.css("h2::text").getall(),
            "links": response.css("a::attr(href)").getall(),
            "text": " ".join(response.css("body *::text").getall())
        }}
'''

elif mode == "BeautifulSoup (Direct)":
    st.write("[DEBUG] Entered BeautifulSoup (Direct) block")
    st.info("Scrape a page using requests + BeautifulSoup (no API, no JS)")
    bs_url = st.text_input("Target URL to scrape", value=os.getenv("WOOCOMMERCE_URL", ""))
    if st.button("Scrape with BeautifulSoup"):
        if not bs_url:
            st.error("Please provide a target URL.")
        else:
            st.write(f"[DEBUG] Scraping URL: {bs_url}")
            try:
                resp = requests.get(bs_url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(resp.content, "html.parser")
                data = {
                    "url": bs_url,
                    "status": resp.status_code,
                    "title": soup.title.string.strip() if soup.title else "",
                    "h1": [h1.text.strip() for h1 in soup.find_all("h1")],
                    "h2": [h2.text.strip() for h2 in soup.find_all("h2")],
                    "links": [a.get("href") for a in soup.find_all("a", href=True)],
                    "text": " ".join(soup.stripped_strings)[:10000]
                }
                st.success("Scraped page with BeautifulSoup.")
                st.json(data)
                st.download_button("Download JSON", json.dumps(data, indent=4), file_name="bs4_result.json")
            except Exception as e:
                st.error(f"Error scraping with BeautifulSoup: {e}")
            with open(spider_path, "w") as f:
                f.write(spider_code)
            st.code(spider_code, language="python")
            # Run scrapy as a subprocess
            cmd = [
                "scrapy", "runspider", spider_path,
                "-O", f"{output_path}:json"
            ]
            st.write(f"Running: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir, timeout=60)
                st.write("Scrapy stdout:", result.stdout)
                st.write("Scrapy stderr:", result.stderr)
                if os.path.exists(output_path):
                    with open(output_path, "r") as f:
                        data = json.load(f)
                    st.success(f"Scrapy crawl finished. {len(data)} items scraped.")
                    st.write(data)
                    st.download_button("Download JSON", json.dumps(data, indent=4), file_name="scrapy_result.json")
                else:
                    st.error("Scrapy did not produce output. Check logs above.")
            except Exception as e:
                st.error(f"Error running Scrapy: {e}")
                st.error("Crawl did not finish in time. Try again later or check the Crawl4AI dashboard.")