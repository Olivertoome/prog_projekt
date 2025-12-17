import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# 1. Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless") # Runs in background
driver = webdriver.Chrome(options=chrome_options)

def get_prisma_products(scroll_batches=10):
    all_products = []
    
    try:
        url = "https://www.prismamarket.ee/tooted"
        driver.get(url)
        print("Loading Prisma...")
        time.sleep(2) # Initial wait for the page to load
        
        # 2. Infinite Scroll logic
        # Prisma loads more content as you scroll. 
        # Increase 'scroll_batches' to get more items.
        for i in range(scroll_batches):
            print(f"Scrolling batch {i+1}...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) # Give the site time to load the next set of items
        
        # 3. Parse the fully rendered HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_cards = soup.find_all('article', attrs={'data-test-id': 'product-card'})
        
        print(f"Parsing {len(product_cards)} products...")

        for card in product_cards:
            name_tag = card.find("div", attrs={"data-test-id": "product-card__productName"})
            price_tag = card.find("span", attrs={"data-test-id": "display-price"})
            
            if name_tag and price_tag:
                # Get the title from the inner span for the cleanest name
                name = name_tag.get_text(strip=True)
                price = price_tag.get_text(strip=True)
                
                all_products.append({
                    "nimi": name,
                    "hind": price,
                })
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
        
    return all_products

# --- EXECUTION ---
# Increase batches to get more products (each batch is roughly 15-20 items)
SCROLL_COUNT = 15 

products = get_prisma_products(scroll_batches=SCROLL_COUNT)

# 4. Export to JSON file
file_name = "prisma_products.json"
with open(file_name, 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\nDone! Successfully saved {len(products)} products to {file_name}")
