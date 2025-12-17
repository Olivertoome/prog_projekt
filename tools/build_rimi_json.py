import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "et-EE,et;q=0.9,en;q=0.8",
}

def norm_key(s: str) -> str:
    return s.strip().lower().replace(" ", "")

def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def extract_next_data(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    return json.loads(tag.string)

def find_products_anywhere(obj):
    # Otsime rekursiivselt listidest/dictidest "products"/"product" sarnaseid struktuure.
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in ("products", "productsearch", "searchresults") and isinstance(v, (dict, list)):
                found += find_products_anywhere(v)
            else:
                found += find_products_anywhere(v)
    elif isinstance(obj, list):
        for x in obj:
            found += find_products_anywhere(x)
    return found

def extract_name_price_from_json(obj, out_items: dict):
    # See osa sõltub lehe sisemisest struktuurist.
    # Proovime leida dict'e, kus on name ja price.
    if isinstance(obj, dict):
        name = obj.get("name") or obj.get("title")
        price = obj.get("price") or obj.get("currentPrice") or obj.get("unitPrice")
        if isinstance(name, str) and isinstance(price, (int, float)):
            out_items[norm_key(name)] = float(price)

        for v in obj.values():
            extract_name_price_from_json(v, out_items)

    elif isinstance(obj, list):
        for x in obj:
            extract_name_price_from_json(x, out_items)

def build_rimi_json(max_pages=5, page_size=20, sleep_sec=0.6):
    items = {}
    for page in range(max_pages):
        url = f"https://www.rimi.ee/epood/ee/otsing?currentPage={page}&pageSize={page_size}&query=%3Arelevance"
        html = fetch_html(url)

        data = extract_next_data(html)
        if not data:
            raise RuntimeError("Ei leidnud __NEXT_DATA__ JSON-i. Vaata lehe Source, mis skript seal on.")

        extract_name_price_from_json(data, items)
        print(f"Leht {page+1}: kokku tooteid {len(items)}")
        time.sleep(sleep_sec)

    return {"store": "Rimi", "items": items}

if __name__ == "__main__":
    out = build_rimi_json(max_pages=10, page_size=20)
    with open("data/rimi.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Valmis: data/rimi.json")
