import json
import time

# Selenium avab päris veebilehe (nagu brauseris)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# BeautifulSoup aitab HTML-koodi „lugeda“
from bs4 import BeautifulSoup


# 1. Brauseri seadistamine (Chrome töötab taustal)

# Loob Chrome’i seadete objekti
brauseri_seaded = Options()

# --headless tähendab, et Chrome ei avane nähtava aknana
# Programm töötab „taustal“
brauseri_seaded.add_argument("--headless")

# Käivitame Chrome’i Seleniumi kaudu
brauser = webdriver.Chrome(options=brauseri_seaded)


# 2. Funktsioon, mis loeb Prisma tooted veebilehelt

def loe_prisma_tooted(kerimise_kordi=10):
    koik_tooted = []

    try:
        url = "https://www.prismamarket.ee/tooted"

        # Avame lehe brauseris
        brauser.get(url)
        print("Laen Prisma veebilehte...")

        # Ootame natuke, et leht jõuaks ära laadida
        time.sleep(2)

        # 3. Lehe allapoole kerimine
        # Prisma laeb uusi tooteid alles siis, kui alla kerida.
        for i in range(kerimise_kordi):
            print(f"Kerimine {i + 1}/{kerimise_kordi}")
            brauser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)  # ootame, et uued tooted ilmuksid

        # 4. HTML-i lugemine BeautifulSoupiga
        # Võtame kogu lehe HTML-koodi
        soup = BeautifulSoup(brauser.page_source, "html.parser")

        # Iga toode on Prisma lehel <article> elemendis
        toote_kaardid = soup.find_all(
            "article", attrs={"data-test-id": "product-card"}
        )

        print(f"Leidsin {len(toote_kaardid)} toodet")

        # 5. Iga toote nime ja hinna lugemine
        for kaart in toote_kaardid:
            nimi_element = kaart.find(
                "div", attrs={"data-test-id": "product-card__productName"}
            )

            hind_element = kaart.find(
                "span", attrs={"data-test-id": "display-price"}
            )

            # Kui mõlemad on olemas, loeme andmed välja
            if nimi_element and hind_element:
                nimi = nimi_element.get_text(strip=True)
                hind = hind_element.get_text(strip=True)

                # Lisame toote listi
                koik_tooted.append({
                    "nimi": nimi,
                    "hind": hind
                })

    except Exception as viga:
        print(f"Tekkis viga: {viga}")

    finally:
        brauser.quit()

    return koik_tooted

# 6. Programmi käivitamine

# Mitu korda lehte alla kerime
KERIMISTE_ARV = 15

# Kutsume funktsiooni välja
tooted = loe_prisma_tooted(kerimise_kordi=KERIMISTE_ARV)


# 7. Andmete salvestamine JSON-faili
faili_nimi = "prisma_products.json"

with open(faili_nimi, "w", encoding="utf-8") as f:
    json.dump(tooted, f, ensure_ascii=False, indent=4)

print(f"\nValmis! Salvestasin {len(tooted)} toodet faili {faili_nimi}")
