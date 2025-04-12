import sys
import json
from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
import jmespath
import re

API_KEY = "YOUR_SCRAPINGBEE_API_KEY"  # <-- Set your ScrapingBee API key here
BASE_URL = "https://tradezone.sg/shop"

if API_KEY == "YOUR_SCRAPINGBEE_API_KEY":
    print("[ERROR] Please set your ScrapingBee API key in the script.", file=sys.stderr)
    sys.exit(1)

client = ScrapingBeeClient(api_key=API_KEY)
page_urls = []

# First collect all product page URLs
for page_num in range(1, 21):  # For 20 pages
    print(f"[INFO] Fetching shop page {page_num}...")
    response = client.get(
        f"{BASE_URL}/page/{page_num}",
        params={
            'premium_proxy': True,
            'country_code': 'us',
            "block_resources": True,
            'device': 'desktop',
        }
    )
    if response.status_code != 200:
        print(f"[WARN] Failed to fetch page {page_num}: {response.status_code}", file=sys.stderr)
        continue

    soup = BeautifulSoup(response.content, 'html.parser')
    product_links = soup.select('li.product a.woocommerce-LoopProduct-link')
    print(f"[INFO] Found {len(product_links)} product links on page {page_num}")
    for link in product_links:
        page_urls.append(link['href'])

print(f"[INFO] Total product URLs collected: {len(page_urls)}")

# Then scrape each product page
def clean_html(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'header', 'footer', 'nav']):
        tag.decompose()
    for span in soup.find_all('span'):
        span.unwrap()
    text = soup.get_text(separator=' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

products_data = []
for idx, url in enumerate(page_urls):
    print(f"[INFO] Scraping product {idx+1}/{len(page_urls)}: {url}")
    response = client.get(
        url,
        params={'premium_proxy': True}
    )
    if response.status_code != 200:
        print(f"[WARN] Failed to fetch product page: {url} ({response.status_code})", file=sys.stderr)
        continue

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract JSON-LD product data if available
    json_ld = soup.find('script', {'type': 'application/ld+json'})
    if json_ld:
        try:
            product_data = json.loads(json_ld.string)
            cleaned_data = jmespath.search('{name: name, description: description, price: offers.price, url: url}', product_data)
            # Clean description if present
            if cleaned_data and 'description' in cleaned_data and cleaned_data['description']:
                cleaned_data['description'] = clean_html(cleaned_data['description'])
            products_data.append(cleaned_data)
            print(f"[INFO] Used JSON-LD for {url}")
            continue
        except Exception as e:
            print(f"[WARN] JSON-LD extraction failed for {url}: {e}")

    # Fallback to HTML parsing if JSON-LD not available
    product = {}
    product['url'] = url
    name_elem = soup.select_one('h1.product_title')
    product['name'] = name_elem.text.strip() if name_elem else ""
    desc_elems = soup.select('div.description p')
    raw_description = ' '.join([p.text.strip() for p in desc_elems])
    product['description'] = clean_html(raw_description) if raw_description else ""
    price_elem = soup.select_one('span.price')
    product['price'] = price_elem.text.strip() if price_elem else ""

    # Extract variations if available
    variations = []
    variation_elements = soup.select('table.variations tr')
    for element in variation_elements:
        label = element.select_one('label')
        name = label.text.strip() if label else ""
        options = [opt.text.strip() for opt in element.select('select option') if opt.get('value')]
        variations.append({'name': name, 'options': options})
    product['variations'] = variations

    products_data.append(product)
    print(f"[INFO] Used HTML fallback for {url}")

# Save to JSON
try:
    with open("woocommerce_products.json", "w") as f:
        json.dump(products_data, f, indent=4)
    print(f"[INFO] Saved {len(products_data)} products to woocommerce_products.json")
except Exception as e:
    print(f"[ERROR] Failed to save JSON: {e}", file=sys.stderr)