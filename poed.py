import json
import os
import re
import difflib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set

import tkinter as tk
from tkinter import ttk, messagebox

# Kaust, kus asuvad poodide JSON-failid
ANDMETE_KAUST = "data"


@dataclass
class Pood:
    # Ühe poe andmed
    nimi: str
    kaubad: Dict[str, float]  # normaliseeritud_nimi -> hind


def normaliseeri_tekst(tekst: str) -> str:
    # Muudab teksti väikesteks tähtedeks ja eemaldab liigsed tühikud
    return re.sub(r"\s+", " ", tekst.strip().lower())


def hind_tekstist_arvuks(hinna_tekst: str) -> float | None:
    # Võtab hinnatekstist numbri: "1,89 €" / "0.99 €" -> 1.89 / 0.99
    if hinna_tekst is None:
        return None

    puhastatud = str(hinna_tekst).strip().replace("\u00a0", " ")
    vaste = re.search(r"(\d+[.,]\d+)", puhastatud)

    if not vaste:
        return None

    return float(vaste.group(1).replace(",", "."))


def lae_poed() -> List[Pood]:
    #Loeb poodide andmed kaustast data/
    if not os.path.isdir(ANDMETE_KAUST):
        raise FileNotFoundError(f"Kausta '{ANDMETE_KAUST}' ei leitud.")

    poed: List[Pood] = []

    for faili_nimi in os.listdir(ANDMETE_KAUST):
        if not faili_nimi.lower().endswith(".json"):
            continue

        faili_tee = os.path.join(ANDMETE_KAUST, faili_nimi)
        with open(faili_tee, "r", encoding="utf-8") as f:
            sisu = json.load(f)

        # Loeme ainult list-formaadis faile
        if not isinstance(sisu, list):
            continue

        kaubad: Dict[str, float] = {}

        for rida in sisu:
            if not isinstance(rida, dict):
                continue

            toote_nimi = rida.get("nimi") or rida.get("name")
            hinna_tekst = rida.get("hind") or rida.get("price")

            if not toote_nimi:
                continue

            hind = hind_tekstist_arvuks(hinna_tekst)
            if hind is None:
                continue

            kaubad[normaliseeri_tekst(toote_nimi)] = hind

        if kaubad:
            poe_nimi = os.path.splitext(faili_nimi)[0]
            poed.append(Pood(nimi=poe_nimi, kaubad=kaubad))

    return poed


def leia_parim_vaste(otsitav: str, valikud: List[str]) -> str | None:
    # Leiab kõige sarnasema tootenime
    vasted = difflib.get_close_matches(otsitav, valikud, n=1, cutoff=0.6)
    return vasted[0] if vasted else None


def arvuta_poe_korv(
    pood: Pood,
    ostukorv: Dict[str, int]
) -> Tuple[float, List[str]]:
    # Arvutab ühe poe ostukorvi hinna ja puuduolevad tooted
    koguhind = 0.0
    puuduolevad: List[str] = []

    saadaolevad_tooted = list(pood.kaubad.keys())

    for toode_norm, kogus in ostukorv.items():
        if toode_norm in pood.kaubad:
            koguhind += pood.kaubad[toode_norm] * kogus
        else:
            vaste = leia_parim_vaste(toode_norm, saadaolevad_tooted)
            if vaste:
                koguhind += pood.kaubad[vaste] * kogus
            else:
                puuduolevad.append(toode_norm)

    return koguhind, puuduolevad


class Rakendus(tk.Tk):
    def __init__(self):
        super().__init__()
        # Akna põhiandmed
        self.title("Odavaim ostukorv")
        self.geometry("920x560")
        self.minsize(880, 520)

        # Laeme poed sisse (JSON-failidest)
        try:
            self.poed = lae_poed()
        except Exception as viga:
            messagebox.showerror("Viga", str(viga))
            self.destroy()
            return

        # Ostukorv: { toode_norm : kogus }
        self.ostukorv: Dict[str, int] = {}

        # Kõik tooted kõigist poodidest (autocomplete jaoks)
        self.koik_tooted: List[str] = sorted(self._kogu_koik_tooted())

        # UI muutujad (Entry + kogus)
        self.kogus_muuttuja = tk.IntVar(value=1)
        self.toode_muuttuja = tk.StringVar()

        # Ehitame kasutajaliidese
        self._ehita_ui()

    def _kogu_koik_tooted(self) -> Set[str]:
        # Koondab kõik toodete võtmed kõikidest poodidest
        koik: Set[str] = set()
        for pood in self.poed:
            koik.update(pood.kaubad.keys())
        return koik

    def _ehita_ui(self):
        # Tkinteri stii
        stiil = ttk.Style()
        if "clam" in stiil.theme_names():
            stiil.theme_use("clam")
        stiil.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        stiil.configure("TButton", font=("Segoe UI", 10))
        stiil.configure("TLabel", font=("Segoe UI", 10))

        # Peamine konteiner
        juur = ttk.Frame(self, padding=16)
        juur.pack(fill="both", expand=True)

        ttk.Label(juur, text="Odavaima poe leidja", style="Title.TLabel").pack(anchor="w")

        # Kahe veeruga paigutus
        sisu = ttk.Frame(juur)
        sisu.pack(fill="both", expand=True, pady=(12, 0))

        # Vasak paneel: lisamine
        vasak = ttk.LabelFrame(sisu, text="Lisa toode", padding=12)
        vasak.pack(side="left", fill="both", expand=True)

        ttk.Label(vasak, text="Toote nimi").pack(anchor="w")

        self.sisestus = ttk.Entry(vasak, textvariable=self.toode_muuttuja)
        self.sisestus.pack(fill="x", pady=(6, 4))
        self.sisestus.focus_set()

        # Autocomplete list
        self.soovituste_kast = tk.Listbox(vasak, height=6)
        self.soovituste_kast.pack(fill="x")
        self.soovituste_kast.pack_forget()

        # Kirjutamine -> uuenda soovitusi
        self.toode_muuttuja.trace_add("write", lambda *_: self._uuenda_soovitusi())

        # Soovituste valimine hiire/Enteriga
        self.soovituste_kast.bind("<ButtonRelease-1>", lambda _e: self._vali_soovitus())
        self.soovituste_kast.bind("<Return>", lambda _e: self._vali_soovitus())
        self.sisestus.bind("<Down>", lambda _e: self._fookus_soovitustele())
        self.sisestus.bind("<Escape>", lambda _e: self._peida_soovitused())
        self.soovituste_kast.bind("<Escape>", lambda _e: self._peida_soovitused())

        # Enter: vali esimene soovitus ja lisa ostukorvi
        self.sisestus.bind("<Return>", self._enter_sisestuses)
        # Ctrl+F: vii fookus sisestusse
        self.bind_all("<Control-f>", lambda _e: (self.sisestus.focus_set(), "break"))

        # Koguse rida (+ / -)
        koguse_rida = ttk.Frame(vasak)
        koguse_rida.pack(fill="x", pady=(10, 10))

        ttk.Label(koguse_rida, text="Kogus").pack(side="left")
        ttk.Button(koguse_rida, text="−", width=3, command=self._kogus_miinus).pack(side="left", padx=(10, 6))
        ttk.Label(koguse_rida, textvariable=self.kogus_muuttuja, width=4, anchor="center").pack(side="left")
        ttk.Button(koguse_rida, text="+", width=3, command=self._kogus_pluss).pack(side="left", padx=(6, 0))

        ttk.Button(vasak, text="Lisa ostukorvi", command=self.lisa_ostukorvi).pack(fill="x")

        ttk.Separator(vasak).pack(fill="x", pady=12)

        ttk.Button(vasak, text="Arvuta odavaim pood", command=self.arvuta).pack(fill="x")

        # Tulemuse sildid
        self.parim_silt = ttk.Label(vasak, text="", font=("Segoe UI", 11, "bold"))
        self.parim_silt.pack(anchor="w", pady=(12, 6))

        self.puudu_silt = ttk.Label(vasak, text="", wraplength=380, justify="left")
        self.puudu_silt.pack(anchor="w")

        # Parem paneel: ostukorv
        parem = ttk.LabelFrame(sisu, text="Ostukorv", padding=12)
        parem.pack(side="right", fill="both", expand=True, padx=(14, 0))

        veerud = ("Toode", "Kogus")
        self.tabel = ttk.Treeview(parem, columns=veerud, show="headings", height=16)
        self.tabel.heading("Toode", text="Toode")
        self.tabel.heading("Kogus", text="Kogus")
        self.tabel.column("Toode", width=360, anchor="w")
        self.tabel.column("Kogus", width=80, anchor="center")
        self.tabel.pack(fill="both", expand=True)

        # Ostukorvi nupud
        nupurea = ttk.Frame(parem)
        nupurea.pack(fill="x", pady=(10, 0))
        ttk.Button(nupurea, text="Eemalda valitu", command=self.eemalda_valitu).pack(side="left")
        ttk.Button(nupurea, text="Tühjenda ostukorv", command=self.tyhjenda_ostukorv).pack(side="left", padx=(8, 0))

        # Jalus: laetud poed
        poed_rida = ", ".join(p.nimi for p in self.poed)
        ttk.Label(juur, text=f"Laetud poed: {poed_rida}").pack(anchor="w", pady=(12, 0))

    def _uuenda_soovitusi(self):
        # Uuendab autocomplete soovitusi sisestuse põhjal
        otsing = normaliseeri_tekst(self.toode_muuttuja.get())
        if not otsing:
            self._peida_soovitused()
            return

        vasted = [t for t in self.koik_tooted if otsing in t][:12]
        if not vasted:
            self._peida_soovitused()
            return

        self.soovituste_kast.delete(0, tk.END)
        for v in vasted:
            self.soovituste_kast.insert(tk.END, v)

        if not self.soovituste_kast.winfo_ismapped():
            self.soovituste_kast.pack(fill="x", pady=(0, 6))

        self.soovituste_kast.selection_clear(0, tk.END)
        self.soovituste_kast.selection_set(0)
        self.soovituste_kast.activate(0)

    def _enter_sisestuses(self, _e):
        # Enter: kui on soovitusi, vali esimene ja lisa ostukorvi
        if self.soovituste_kast.winfo_ismapped() and self.soovituste_kast.size() > 0:
            self.soovituste_kast.selection_clear(0, tk.END)
            self.soovituste_kast.selection_set(0)
            self.soovituste_kast.activate(0)
            self._vali_soovitus()
            self.lisa_ostukorvi()
            return
        self.lisa_ostukorvi()

    def _peida_soovitused(self):
        # Peidab autocomplete kasti
        if self.soovituste_kast.winfo_ismapped():
            self.soovituste_kast.pack_forget()

    def _fookus_soovitustele(self):
        # Viib fookuse soovituste listile
        if self.soovituste_kast.winfo_ismapped() and self.soovituste_kast.size() > 0:
            self.soovituste_kast.focus_set()
            self.soovituste_kast.selection_clear(0, tk.END)
            self.soovituste_kast.selection_set(0)
            self.soovituste_kast.activate(0)

    def _vali_soovitus(self):
        # Paneb valitud soovituse sisestuskasti
        valik = self.soovituste_kast.curselection()
        if not valik:
            return
        soovitus = self.soovituste_kast.get(valik[0])
        self.toode_muuttuja.set(soovitus)
        self._peida_soovitused()
        self.sisestus.focus_set()
        self.sisestus.icursor(tk.END)

    def _kogus_pluss(self):
        # Suurendab kogust
        self.kogus_muuttuja.set(self.kogus_muuttuja.get() + 1)

    def _kogus_miinus(self):
        # Vähendab kogust (min 1)
        self.kogus_muuttuja.set(max(1, self.kogus_muuttuja.get() - 1))

    def lisa_ostukorvi(self):
        # Lisab sisestatud toote ostukorvi
        toote_nimi = self.toode_muuttuja.get().strip()
        kogus = int(self.kogus_muuttuja.get())

        if not toote_nimi:
            messagebox.showwarning("Hoiatus", "Sisesta toote nimi.")
            return

        voti = normaliseeri_tekst(toote_nimi)
        self.ostukorv[voti] = self.ostukorv.get(voti, 0) + kogus

        self.toode_muuttuja.set("")
        self.kogus_muuttuja.set(1)
        self._peida_soovitused()
        self._uuenda_ostukorvi_vaadet()

    def _uuenda_ostukorvi_vaadet(self):
        # Värskendab ostukorvi tabelit
        self.tabel.delete(*self.tabel.get_children())
        for toode_norm, kogus in sorted(self.ostukorv.items()):
            self.tabel.insert("", "end", values=(toode_norm, kogus))

    def eemalda_valitu(self):
        # Eemaldab tabelist valitud tooted ostukorvist
        valitud = self.tabel.selection()
        if not valitud:
            return
        for iid in valitud:
            toode_norm = self.tabel.item(iid, "values")[0]
            self.ostukorv.pop(toode_norm, None)
        self._uuenda_ostukorvi_vaadet()

    def tyhjenda_ostukorv(self):
        # Tühjendab ostukorvi ja tulemused
        self.ostukorv.clear()
        self._uuenda_ostukorvi_vaadet()
        self.parim_silt.config(text="")
        self.puudu_silt.config(text="")
        self._peida_soovitused()

    def arvuta(self):
        # Leiab odavaima poe selle ostukorvi jaoks
        if not self.ostukorv:
            messagebox.showwarning("Hoiatus", "Ostukorv on tühi.")
            return

        tulemused = []
        for pood in self.poed:
            koguhind, puudu = arvuta_poe_korv(pood, self.ostukorv)
            tulemused.append((pood.nimi, koguhind, puudu))

        tulemused.sort(key=lambda x: (len(x[2]) > 0, x[1]))
        parim_nimi, parim_hind, parim_puudu = tulemused[0]

        ilus_poe_nimi = parim_nimi.replace("_products", "").capitalize()

        if len(parim_puudu) == 0:
            self.parim_silt.config(
            text=f"Odavaim pood: {ilus_poe_nimi} — {parim_hind:.2f} €")
            self.puudu_silt.config(
                text="Puuduolevaid tooteid selles poes ei ole.")
        else:
            self.parim_silt.config(
                text=f"Odavaim pood: {ilus_poe_nimi} — {parim_hind:.2f} €")
            self.puudu_silt.config(
                text="Selles poes ei ole: " + ", ".join(parim_puudu))


if __name__ == "__main__":
    Rakendus().mainloop()
