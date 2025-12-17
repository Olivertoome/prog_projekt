import json
import time

# Selenium avab päris veebilehe (nagu brauseris)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# BeautifulSoup aitab HTML-ist otsida vajalikke elemente
from bs4 import BeautifulSoup


# 1. Brauseri käivitamine taustal (headless)

# Loome Chrome’i seadete objekti
brauseri_seaded = Options()

# --headless tähendab, et Chrome ei avane nähtava aknana
# Programm töötab taustal
brauseri_seaded.add_argument("--headless")

# Käivitame Chrome’i Seleniumi abil
brauser = webdriver.Chrome(options=brauseri_seaded)


# 2. Funktsioon, mis loeb Coop e-poe tooted veebilehelt

def loe_coop_tooted(lehti=1):
    koik_tooted = []

    # Käime läbi mitu lehte
    for lehe_nr in range(1, lehti + 1):

        # Iga lehe aadress: ...page=1, ...page=2 jne
        url = f"https://vandra.ecoop.ee/et/tooted?page={lehe_nr}"
        print(f"Loen Coop lehte {lehe_nr}/{lehti} ...")

        try:
            # Avame lehe brauseris
            brauser.get(url)

            # Ootame natuke, et leht jõuaks ära laadida
            time.sleep(1)

            # Võtame HTML-i ja anname BeautifulSoupile lugemiseks
            soup = BeautifulSoup(brauser.page_source, "html.parser")

            # Coop lehel on tooted <app-product-card> elementides
            toote_kaardid = soup.find_all("app-product-card")

            # Kui lehel ei ole enam tooteid, siis lõpetame
            if not toote_kaardid:
                print(f"Lehel {lehe_nr} ei leitud tooteid. Lõpetan.")
                break


            # 3. Iga toote nime ja hinna lugemine
            for kaart in toote_kaardid:
                # Toote nimi asub <p class="product-name">
                nimi_element = kaart.find("p", class_="product-name")

                # Hind on jagatud täisarvuliseks ja komakohaks:
                # integer= "1" ja decimal= "99 €"
                euro_osa = kaart.find("div", class_="integer")
                senti_osa = kaart.find("div", class_="decimal")

                # Kui vajalikud osad on olemas, saame toote kokku panna
                if nimi_element and euro_osa and senti_osa:
                    nimi = nimi_element.get_text(strip=True)

                    # Eemaldame senti osa seest "€" märgi
                    sendid = senti_osa.get_text(strip=True).replace("€", "").strip()

                    # Teeme hinna teksti kujule "1.99 €"
                    hind = f"{euro_osa.get_text(strip=True)}.{sendid} €"

                    # Lisame listi
                    koik_tooted.append({
                        "nimi": nimi,
                        "hind": hind
                    })

        except Exception as viga:
            print(f"Tekkis viga lehel {lehe_nr}: {viga}")
            break

    return koik_tooted


# 4. Programmi käivitamine
# Mitu lehte tahame läbi käia
LEHTE_KOKKU = 50

# Loeme tooted
tooted = loe_coop_tooted(lehti=LEHTE_KOKKU)


# 5. Tulemuse salvestamine JSON-faili
faili_nimi = "coop_products.json"

with open(faili_nimi, "w", encoding="utf-8") as f:
    json.dump(tooted, f, ensure_ascii=False, indent=4)

print(f"\nValmis! Leidsin {len(tooted)} toodet.")
print(f"Andmed salvestatud faili: {faili_nimi}")

# Sulgeme brauseri
brauser.quit()
