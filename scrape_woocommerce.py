import sys
import json
import requests

# WooCommerce API credentials and endpoint
WC_API_URL = "https://tradezone.sg/wp-json/wc/v3/products"
CONSUMER_KEY = "ck_9c3e0a271969ea56a3d294e54537ec1e7518c92e"
CONSUMER_SECRET = "cs_c13ac8aa41322b22a5d25fcb5f422982acec5a53"

def fetch_all_products():
    products = []
    per_page = 100  # WooCommerce max per_page is usually 100
    page = 1

    print("[INFO] Starting product fetch from WooCommerce API...")

    while True:
        print(f"[INFO] Fetching page {page}...")
        response = requests.get(
            WC_API_URL,
            auth=(CONSUMER_KEY, CONSUMER_SECRET),
            params={"per_page": per_page, "page": page}
        )
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch page {page}: {response.status_code} {response.text}", file=sys.stderr)
            break

        page_products = response.json()
        if not page_products:
            print(f"[INFO] No more products found on page {page}.")
            break

        print(f"[INFO] Retrieved {len(page_products)} products from page {page}.")
        products.extend(page_products)
        page += 1

    print(f"[INFO] Total products fetched: {len(products)}")
    return products

def main():
    try:
        products = fetch_all_products()
        with open("woocommerce_products.json", "w") as f:
            json.dump(products, f, indent=4)
        print(f"[INFO] Saved {len(products)} products to woocommerce_products.json")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()