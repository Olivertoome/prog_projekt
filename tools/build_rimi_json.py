import re
import json
import time
import requests
from xml.etree import ElementTree as ET

SITEMAP_URL = "https://www.rimi.ee/epood/sitemaps/products/siteMap_rimiEeSite_Product_en_2.xml"
OUT_JSON = "data/rimi.json"
MAX_PRODUCTS = 200
SLEEP_SEC = 0.6

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "et-EE,et;q=0.9,en;q=0.8",
}

def norm_name(s: str) -> str:
    return s.strip().lower().replace(" ", "")

def get_product_urls_from_sitemap(url: str) -> list[str]:
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()

    content_type = (r.headers.get("Content-Type") or "").lower()
    text = r.text.strip()

    # Kui see pole XML (või tuleb HTML), siis ütleme kohe välja alguse
    if not text.startswith("<"):
        raise RuntimeError("Sitemap vastus ei näe välja nagu XML/HTML (tühi või bin).")

    if "xml" not in content_type and not text.lstrip().startswith("<?xml"):
        # Tõenäoliselt HTML blokk/Cloudflare
        preview = text[:300].replace("\n", " ")
        raise RuntimeError(
            "Sitemap ei tagastanud XML-i. "
            f"Content-Type: {content_type}. Algus: {preview}"
        )

    try:
        root = ET.fromstring(text)
    except Exception as e:
        preview = text[:300].replace("\n", " ")
        raise RuntimeError(f"XML parse ebaõnnestus: {e}. Algus: {preview}")

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [loc.text for loc in root.findall(".//sm:url/sm:loc", ns)]
    return [u for u in locs if u]

def extract_name_price(html: str) -> tuple[str | None, float | None]:
    m = re.search(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None, None

    try:
        data = json.loads(m.group(1).strip())
    except Exception:
        return None, None

    candidates = data if isinstance(data, list) else [data]
    for obj in candidates:
        if isinstance(obj, dict) and str(obj.get("@type", "")).lower() == "product":
            name = obj.get("name")
            offers = obj.get("offers") or {}
            price = offers.get("price")
            try:
                return name, float(price)
            except Exception:
                return name, None

    return None, None

def main():
    urls = get_product_urls_from_sitemap(SITEMAP_URL)[:MAX_PRODUCTS]
    items = {}

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        r = requests.get(url, timeout=30, headers=HEADERS)
        if r.status_code != 200:
            continue

        name, price = extract_name_price(r.text)
        if name and price is not None:
            items[norm_name(name)] = price

        time.sleep(SLEEP_SEC)

    out = {"store": "Rimi", "items": items}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Valmis: {OUT_JSON} (tooteid: {len(items)})")

if __name__ == "__main__":
    main()
