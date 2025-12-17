import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# 1. Setup Selenium for background execution
chrome_options = Options()
chrome_options.add_argument("--headless") 
driver = webdriver.Chrome(options=chrome_options)

def get_coop_products(pages=1):
    all_products = []
    
    for page in range(1, pages + 1):
        # Using the standard ecoop URL for general products
        url = f"https://vandra.ecoop.ee/et/tooted?page={page}"
        print(f"Scraping Coop page {page}...")
        
        try:
            driver.get(url)
            time.sleep(1)  # Wait for Angular to render the dynamic content
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            cards = soup.find_all('app-product-card')
            
            # If no cards are found, we might have reached the end or been blocked
            if not cards:
                print(f"No products found on page {page}. Stopping.")
                break

            for card in cards:
                name_tag = card.find("p", class_="product-name")
                integer_tag = card.find("div", class_="integer")
                decimal_tag = card.find("div", class_="decimal")
                
                if name_tag and integer_tag and decimal_tag:
                    name = name_tag.get_text(strip=True)
                    # Clean the decimal part (remove the '€' symbol and spaces)
                    cents = decimal_tag.get_text(strip=True).replace('€', '').strip()
                    price = f"{integer_tag.get_text(strip=True)}.{cents} €"
                    
                    all_products.append({
                        "name": name,
                        "price": price
                    })
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
                
    return all_products

# --- EXECUTION ---
# Set the number of pages you want to scrape
PAGE_COUNT = 50 

products = get_coop_products(pages=PAGE_COUNT)

# 2. Export to JSON file
file_name = "coop_products.json"
with open(file_name, 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\nSuccessfully scraped {len(products)} products.")
print(f"Data saved to {file_name}")

# Close the browser
driver.quit()
