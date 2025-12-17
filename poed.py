import json
import os
import re
import difflib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set

import tkinter as tk
from tkinter import ttk, messagebox

DATA_DIR = "data"


@dataclass
class Store:
    name: str
    items: Dict[str, float]  # normalized_name -> price


def normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def parse_price_to_float(price_text: str) -> float | None:
    """
    Võtab hinnast numbri: "1,89 €" / "0.99 €" -> 1.89 / 0.99
    """
    if price_text is None:
        return None
    t = str(price_text).strip().replace("\u00a0", " ")
    m = re.search(r"(\d+[.,]\d+)", t)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def load_stores() -> List[Store]:
    """
    LOEB AINULT sinu praegust formaati:
    [
      {"nimi": "...", "hind": "1,89 €"},
      ...
    ]
    (Lubab ka "name"/"price", kui mõnes failis on inglise võtmed.)
    Poe nimi võetakse faili nimest.
    """
    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(f"Kausta '{DATA_DIR}' ei leitud.")

    stores: List[Store] = []

    for fn in os.listdir(DATA_DIR):
        if not fn.lower().endswith(".json"):
            continue

        path = os.path.join(DATA_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            # Me loeme AINULT list-formaati; muu jätame vahele.
            continue

        items: Dict[str, float] = {}
        for row in raw:
            if not isinstance(row, dict):
                continue

            name = row.get("nimi") or row.get("name")
            price_text = row.get("hind") or row.get("price")

            if not name:
                continue

            price = parse_price_to_float(price_text)
            if price is None:
                continue

            items[normalize(name)] = price

        if items:
            store_name = os.path.splitext(fn)[0]
            stores.append(Store(name=store_name, items=items))

    if not stores:
        raise ValueError(
            "Ei leidnud ühtegi sobivat poe faili. "
            "Ootan, et data/*.json oleks list kujul: "
            "[{'nimi':..., 'hind':...}, ...]"
        )

    return stores


def best_match(name_norm: str, choices: List[str]) -> str | None:
    m = difflib.get_close_matches(name_norm, choices, n=1, cutoff=0.6)
    return m[0] if m else None


def calculate_for_store(store: Store, basket: Dict[str, int]) -> Tuple[float, List[str]]:
    total = 0.0
    missing: List[str] = []
    keys = list(store.items.keys())

    for item_norm, qty in basket.items():
        if item_norm in store.items:
            total += store.items[item_norm] * qty
        else:
            match = best_match(item_norm, keys)
            if match:
                total += store.items[match] * qty
            else:
                missing.append(item_norm)

    return total, missing


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Odavaim ostukorv")
        self.geometry("920x560")
        self.minsize(880, 520)

        try:
            self.stores = load_stores()
        except Exception as e:
            messagebox.showerror("Viga", str(e))
            self.destroy()
            return

        self.basket: Dict[str, int] = {}
        self.all_products: List[str] = sorted(self._collect_all_products())

        self.qty_var = tk.IntVar(value=1)
        self.item_var = tk.StringVar()

        self._build_ui()

    def _collect_all_products(self) -> Set[str]:
        s: Set[str] = set()
        for st in self.stores:
            s.update(st.items.keys())
        return s

    def _build_ui(self):
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10))

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Odavaima poe leidja", style="Title.TLabel").pack(anchor="w")

        main = ttk.Frame(root)
        main.pack(fill="both", expand=True, pady=(12, 0))

        left = ttk.LabelFrame(main, text="Lisa toode", padding=12)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Toote nimi").pack(anchor="w")

        self.entry = ttk.Entry(left, textvariable=self.item_var)
        self.entry.pack(fill="x", pady=(6, 4))
        self.entry.focus_set()

        self.suggest_box = tk.Listbox(left, height=6)
        self.suggest_box.pack(fill="x")
        self.suggest_box.pack_forget()

        self.item_var.trace_add("write", lambda *_: self._update_suggestions())

        self.suggest_box.bind("<ButtonRelease-1>", lambda _e: self._pick_suggestion())
        self.suggest_box.bind("<Return>", lambda _e: self._pick_suggestion())
        self.entry.bind("<Down>", lambda _e: self._focus_suggestions())
        self.entry.bind("<Escape>", lambda _e: self._hide_suggestions())
        self.suggest_box.bind("<Escape>", lambda _e: self._hide_suggestions())

        self.entry.bind("<Return>", self._on_enter_in_entry)
        self.bind_all("<Control-f>", lambda _e: (self.entry.focus_set(), "break"))

        qty_row = ttk.Frame(left)
        qty_row.pack(fill="x", pady=(10, 10))

        ttk.Label(qty_row, text="Kogus").pack(side="left")
        ttk.Button(qty_row, text="−", width=3, command=self._qty_minus).pack(side="left", padx=(10, 6))
        ttk.Label(qty_row, textvariable=self.qty_var, width=4, anchor="center").pack(side="left")
        ttk.Button(qty_row, text="+", width=3, command=self._qty_plus).pack(side="left", padx=(6, 0))

        ttk.Button(left, text="Lisa ostukorvi", command=self.add_to_basket).pack(fill="x")

        ttk.Separator(left).pack(fill="x", pady=12)

        ttk.Button(left, text="Arvuta odavaim pood", command=self.calculate).pack(fill="x")

        self.best_lbl = ttk.Label(left, text="", font=("Segoe UI", 11, "bold"))
        self.best_lbl.pack(anchor="w", pady=(12, 6))

        self.missing_lbl = ttk.Label(left, text="", wraplength=380, justify="left")
        self.missing_lbl.pack(anchor="w")

        right = ttk.LabelFrame(main, text="Ostukorv", padding=12)
        right.pack(side="right", fill="both", expand=True, padx=(14, 0))

        cols = ("Toode", "Kogus")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=16)
        self.tree.heading("Toode", text="Toode")
        self.tree.heading("Kogus", text="Kogus")
        self.tree.column("Toode", width=360, anchor="w")
        self.tree.column("Kogus", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_row = ttk.Frame(right)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Eemalda valitu", command=self.remove_selected).pack(side="left")
        ttk.Button(btn_row, text="Tühjenda ostukorv", command=self.clear_basket).pack(side="left", padx=(8, 0))

        stores_line = ", ".join(s.name for s in self.stores)
        ttk.Label(root, text=f"Laetud poed: {stores_line}").pack(anchor="w", pady=(12, 0))

    def _update_suggestions(self):
        typed = normalize(self.item_var.get())
        if not typed:
            self._hide_suggestions()
            return

        matches = [p for p in self.all_products if typed in p][:12]
        if not matches:
            self._hide_suggestions()
            return

        self.suggest_box.delete(0, tk.END)
        for m in matches:
            self.suggest_box.insert(tk.END, m)

        if not self.suggest_box.winfo_ismapped():
            self.suggest_box.pack(fill="x", pady=(0, 6))

        self.suggest_box.selection_clear(0, tk.END)
        self.suggest_box.selection_set(0)
        self.suggest_box.activate(0)

    def _on_enter_in_entry(self, _e):
        if self.suggest_box.winfo_ismapped() and self.suggest_box.size() > 0:
            self.suggest_box.selection_clear(0, tk.END)
            self.suggest_box.selection_set(0)
            self.suggest_box.activate(0)
            self._pick_suggestion()
            self.add_to_basket()
            return
        self.add_to_basket()

    def _hide_suggestions(self):
        if self.suggest_box.winfo_ismapped():
            self.suggest_box.pack_forget()

    def _focus_suggestions(self):
        if self.suggest_box.winfo_ismapped() and self.suggest_box.size() > 0:
            self.suggest_box.focus_set()
            self.suggest_box.selection_clear(0, tk.END)
            self.suggest_box.selection_set(0)
            self.suggest_box.activate(0)

    def _pick_suggestion(self):
        sel = self.suggest_box.curselection()
        if not sel:
            return
        value = self.suggest_box.get(sel[0])
        self.item_var.set(value)
        self._hide_suggestions()
        self.entry.focus_set()
        self.entry.icursor(tk.END)

    def _qty_plus(self):
        self.qty_var.set(self.qty_var.get() + 1)

    def _qty_minus(self):
        self.qty_var.set(max(1, self.qty_var.get() - 1))

    def add_to_basket(self):
        name = self.item_var.get().strip()
        qty = int(self.qty_var.get())

        if not name:
            messagebox.showwarning("Hoiatus", "Sisesta toote nimi.")
            return

        key = normalize(name)
        self.basket[key] = self.basket.get(key, 0) + qty

        self.item_var.set("")
        self.qty_var.set(1)
        self._hide_suggestions()
        self._refresh_basket_view()

    def _refresh_basket_view(self):
        self.tree.delete(*self.tree.get_children())
        for item_norm, qty in sorted(self.basket.items()):
            self.tree.insert("", "end", values=(item_norm, qty))

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            item_norm = self.tree.item(iid, "values")[0]
            self.basket.pop(item_norm, None)
        self._refresh_basket_view()

    def clear_basket(self):
        self.basket.clear()
        self._refresh_basket_view()
        self.best_lbl.config(text="")
        self.missing_lbl.config(text="")
        self._hide_suggestions()

    def calculate(self):
        if not self.basket:
            messagebox.showwarning("Hoiatus", "Ostukorv on tühi.")
            return

        results = []
        for s in self.stores:
            total, missing = calculate_for_store(s, self.basket)
            results.append((s.name, total, missing))

        results.sort(key=lambda x: (len(x[2]) > 0, x[1]))
        best_name, best_total, best_missing = results[0]

        if len(best_missing) == 0:
            self.best_lbl.config(text=f"✅ Odavaim pood: {best_name} — {best_total:.2f} €")
            self.missing_lbl.config(text="Puuduolevaid tooteid selles poes ei ole.")
        else:
            self.best_lbl.config(text=f"⚠️ Odavaim (osalise korviga): {best_name} — {best_total:.2f} €")
            self.missing_lbl.config(text="Selles poes ei ole: " + ", ".join(best_missing))


if __name__ == "__main__":
    App().mainloop()
