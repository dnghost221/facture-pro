"""
Module de gestion des stocks
Fenêtre dédiée : niveaux de stock, alertes, historique des mouvements, ajustements.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db

# ─── Couleurs & polices (cohérentes avec le reste du projet) ──────────────────
COLORS = {
    "bg_main":      "#f8fafc",
    "bg_card":      "#ffffff",
    "primary":      "#1a56db",
    "primary_dark": "#0d3d91",
    "primary_light":"#eff6ff",
    "accent":       "#10b981",
    "danger":       "#ef4444",
    "warning":      "#f59e0b",
    "text_dark":    "#111827",
    "text_medium":  "#374151",
    "text_light":   "#9ca3af",
    "border":       "#e5e7eb",
    "row_even":     "#f9fafb",
    "row_odd":      "#ffffff",
    "row_selected": "#dbeafe",
    "header_bg":    "#1a56db",
    "stock_ok":     "#d1fae5",   # vert clair
    "stock_low":    "#fef3c7",   # orange clair
    "stock_empty":  "#fee2e2",   # rouge clair
}

FONTS = {
    "title":     ("Segoe UI", 15, "bold"),
    "heading":   ("Segoe UI", 12, "bold"),
    "subhead":   ("Segoe UI", 10, "bold"),
    "body":      ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
}


class StockWindow(tk.Toplevel):
    """Fenêtre principale de gestion des stocks."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("📦 Gestion des Stocks")
        self.geometry("960x620")
        self.minsize(800, 480)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"960x620+{parent.winfo_x()+60}+{parent.winfo_y()+40}")

        self._build()
        self._charger()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        # En-tête
        header = tk.Frame(self, bg=COLORS["primary"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="📦  Gestion des Stocks",
            font=FONTS["title"], bg=COLORS["primary"], fg="white"
        ).pack(side="left", padx=20, pady=12)

        # Compteurs d'alertes dans l'en-tête
        self.lbl_alerte_header = tk.Label(
            header, text="",
            font=FONTS["body_bold"], bg=COLORS["primary"], fg="#fde68a"
        )
        self.lbl_alerte_header.pack(side="right", padx=20)

        # Onglets
        style = ttk.Style()
        style.configure("Stock.TNotebook", background=COLORS["bg_main"], borderwidth=0)
        style.configure("Stock.TNotebook.Tab",
                        font=FONTS["body_bold"], padding=[14, 6])
        style.map("Stock.TNotebook.Tab",
                  background=[("selected", COLORS["primary"]), ("!selected", COLORS["bg_card"])],
                  foreground=[("selected", "white"),           ("!selected", COLORS["text_dark"])])

        self.nb = ttk.Notebook(self, style="Stock.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=10)

        # Onglet 1 : Vue d'ensemble
        self._build_tab_stock()

        # Onglet 2 : Historique des mouvements
        self._build_tab_historique()

    # ── Onglet 1 : Stock ──────────────────────────────────────────────────────

    def _build_tab_stock(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_card"])
        self.nb.add(outer, text="📊  Niveaux de stock")

        # Toolbar
        toolbar = tk.Frame(outer, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        toolbar.pack(fill="x", padx=0, pady=(0, 8))

        tk.Label(toolbar, text="🔍", font=FONTS["body"],
                 bg=COLORS["bg_card"]).pack(side="left", padx=(10, 4), pady=8)
        self.var_search = tk.StringVar()
        self.var_search.trace("w", lambda *_: self._charger())
        tk.Entry(
            toolbar, textvariable=self.var_search,
            font=FONTS["body"], relief="flat", bd=0,
            bg=COLORS["bg_card"], fg=COLORS["text_dark"],
            highlightthickness=0,
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=4)

        # Filtre alertes
        self.var_filtre = tk.StringVar(value="Tous")
        for label in ("Tous", "⚠️ Stock bas", "🔴 Rupture"):
            tk.Radiobutton(
                toolbar, text=label, variable=self.var_filtre, value=label,
                command=self._charger,
                font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_dark"],
                activebackground=COLORS["bg_card"], selectcolor=COLORS["bg_card"],
                relief="flat", bd=0, cursor="hand2"
            ).pack(side="left", padx=6)

        # Tableau
        table_frame = tk.Frame(outer, bg=COLORS["bg_main"])
        table_frame.pack(fill="both", expand=True, padx=0, pady=0)

        scrolly = ttk.Scrollbar(table_frame, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Stk.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=36, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Stk.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Stk.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree_stock = ttk.Treeview(
            table_frame,
            columns=("produit", "stock_actuel", "seuil_alerte", "statut", "valeur"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Stk.Treeview",
        )
        scrolly.config(command=self.tree_stock.yview)

        cols = [
            ("produit",       "Produit / Service",  340, "w"),
            ("stock_actuel",  "Stock actuel",        110, "center"),
            ("seuil_alerte",  "Seuil d'alerte",      110, "center"),
            ("statut",        "Statut",              120, "center"),
            ("valeur",        "Valeur stock",        120, "e"),
        ]
        for col_id, label, width, anchor in cols:
            self.tree_stock.heading(col_id, text=label)
            self.tree_stock.column(col_id, width=width, anchor=anchor, minwidth=60)

        self.tree_stock.pack(side="left", fill="both", expand=True)
        self.tree_stock.tag_configure("ok",    background=COLORS["stock_ok"])
        self.tree_stock.tag_configure("low",   background=COLORS["stock_low"])
        self.tree_stock.tag_configure("empty", background=COLORS["stock_empty"])

        # Barre d'actions
        action_bar = tk.Frame(outer, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x")

        btns = [
            ("➕  Entrée de stock",     self._entree_stock,   COLORS["accent"]),
            ("➖  Sortie de stock",     self._sortie_stock,   COLORS["warning"]),
            ("✏️  Modifier seuil",      self._modifier_seuil, COLORS["primary"]),
            ("🔄  Actualiser",          self._charger,        "#6b7280"),
        ]
        for label, cmd, color in btns:
            tk.Button(
                action_bar, text=label, command=cmd,
                font=FONTS["body_bold"],
                bg=color, fg="white",
                activebackground=COLORS["primary_dark"], activeforeground="white",
                relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
            ).pack(side="left", padx=6, pady=8)

        self.lbl_count = tk.Label(
            action_bar, text="",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        )
        self.lbl_count.pack(side="right", padx=16)

    # ── Onglet 2 : Historique ─────────────────────────────────────────────────

    def _build_tab_historique(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_card"])
        self.nb.add(outer, text="📋  Historique des mouvements")

        # Tableau historique
        table_frame = tk.Frame(outer, bg=COLORS["bg_main"])
        table_frame.pack(fill="both", expand=True, padx=0, pady=0)

        scrolly = ttk.Scrollbar(table_frame, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Hist.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=32, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Hist.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Hist.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree_hist = ttk.Treeview(
            table_frame,
            columns=("date", "produit", "type", "quantite", "stock_avant", "stock_apres", "note"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Hist.Treeview",
        )
        scrolly.config(command=self.tree_hist.yview)

        cols = [
            ("date",        "Date / Heure",    140, "center"),
            ("produit",     "Produit",          260, "w"),
            ("type",        "Type",              90, "center"),
            ("quantite",    "Qté",               60, "center"),
            ("stock_avant", "Avant",             70, "center"),
            ("stock_apres", "Après",             70, "center"),
            ("note",        "Note",             180, "w"),
        ]
        for col_id, label, width, anchor in cols:
            self.tree_hist.heading(col_id, text=label)
            self.tree_hist.column(col_id, width=width, anchor=anchor, minwidth=50)

        self.tree_hist.pack(side="left", fill="both", expand=True)
        self.tree_hist.tag_configure("entree",  foreground="#059669")
        self.tree_hist.tag_configure("sortie",  foreground="#dc2626")
        self.tree_hist.tag_configure("facture", foreground="#7c3aed")

        # Bouton actualiser
        action_bar = tk.Frame(outer, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x")
        tk.Button(
            action_bar, text="🔄  Actualiser", command=self._charger_historique,
            font=FONTS["body_bold"],
            bg="#6b7280", fg="white",
            relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
        ).pack(side="left", padx=6, pady=8)

        self.lbl_hist_count = tk.Label(
            action_bar, text="",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        )
        self.lbl_hist_count.pack(side="right", padx=16)

    # ── Chargement des données ─────────────────────────────────────────────────

    def _charger(self, *_):
        """Charge le tableau de stock."""
        query = self.var_search.get().strip()
        filtre = self.var_filtre.get()
        stocks = db.get_all_stock()

        # Filtrage texte
        if query:
            stocks = [s for s in stocks if query.lower() in s["designation"].lower()]

        # Filtrage statut
        if filtre == "⚠️ Stock bas":
            stocks = [s for s in stocks if 0 < s["stock_actuel"] <= s["seuil_alerte"]]
        elif filtre == "🔴 Rupture":
            stocks = [s for s in stocks if s["stock_actuel"] <= 0]

        for item in self.tree_stock.get_children():
            self.tree_stock.delete(item)

        nb_alertes = 0
        nb_ruptures = 0

        for s in stocks:
            qt = s["stock_actuel"]
            seuil = s["seuil_alerte"]
            prix = s.get("prix_unitaire", 0) or 0

            if qt <= 0:
                statut = "🔴 Rupture"
                tag = "empty"
                nb_ruptures += 1
            elif qt <= seuil:
                statut = "⚠️ Stock bas"
                tag = "low"
                nb_alertes += 1
            else:
                statut = "✅ OK"
                tag = "ok"

            valeur = qt * prix
            self.tree_stock.insert("", "end",
                iid=str(s["catalogue_id"]),
                values=(
                    s["designation"],
                    f"{qt:g}",
                    f"{seuil:g}",
                    statut,
                    f"{_fmt(valeur)} FCFA",
                ),
                tags=(tag,)
            )

        self.lbl_count.config(text=f"{len(stocks)} produit(s)")

        # Alerte dans l'en-tête
        alerte_txt = ""
        if nb_ruptures:
            alerte_txt += f"🔴 {nb_ruptures} rupture(s)  "
        if nb_alertes:
            alerte_txt += f"⚠️ {nb_alertes} stock(s) bas"
        self.lbl_alerte_header.config(text=alerte_txt)

        # Rafraîchir aussi l'historique si visible
        self._charger_historique()

    def _charger_historique(self):
        """Charge l'historique des mouvements."""
        mouvements = db.get_stock_mouvements()

        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)

        for m in mouvements:
            type_mouv = m["type_mouvement"]
            if type_mouv == "entree":
                tag = "entree"
                label_type = "➕ Entrée"
            elif type_mouv == "facture":
                tag = "facture"
                label_type = "🧾 Facture"
            else:
                tag = "sortie"
                label_type = "➖ Sortie"

            self.tree_hist.insert("", "end",
                values=(
                    m["date_mouvement"][:16],
                    m["designation"],
                    label_type,
                    f"{m['quantite']:g}",
                    f"{m['stock_avant']:g}",
                    f"{m['stock_apres']:g}",
                    m.get("note", "") or "",
                ),
                tags=(tag,)
            )

        self.lbl_hist_count.config(text=f"{len(mouvements)} mouvement(s)")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _get_selected_catalogue_id(self):
        sel = self.tree_stock.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Veuillez sélectionner un produit.", parent=self)
            return None, None
        cat_id = int(sel[0])
        nom = self.tree_stock.item(sel[0])["values"][0]
        return cat_id, nom

    def _entree_stock(self):
        """Ajoute du stock pour un produit."""
        cat_id, nom = self._get_selected_catalogue_id()
        if cat_id is None:
            return
        dlg = _MouvementDialog(self, f"Entrée de stock — {nom}", "entree")
        if dlg.result:
            qte, note = dlg.result
            db.ajouter_mouvement_stock(cat_id, "entree", qte, note)
            self._charger()

    def _sortie_stock(self):
        """Retire du stock pour un produit."""
        cat_id, nom = self._get_selected_catalogue_id()
        if cat_id is None:
            return
        stock_actuel = db.get_stock_produit(cat_id)
        dlg = _MouvementDialog(self, f"Sortie de stock — {nom}", "sortie",
                                max_qte=stock_actuel)
        if dlg.result:
            qte, note = dlg.result
            if qte > stock_actuel:
                messagebox.showerror("Stock insuffisant",
                    f"Stock disponible : {stock_actuel:g}\nSortie demandée : {qte:g}",
                    parent=self)
                return
            db.ajouter_mouvement_stock(cat_id, "sortie", qte, note)
            self._charger()

    def _modifier_seuil(self):
        """Modifie le seuil d'alerte d'un produit."""
        cat_id, nom = self._get_selected_catalogue_id()
        if cat_id is None:
            return
        seuil_actuel = db.get_seuil_alerte(cat_id)
        dlg = _SeuilDialog(self, nom, seuil_actuel)
        if dlg.result is not None:
            db.set_seuil_alerte(cat_id, dlg.result)
            self._charger()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUES INTERNES
# ══════════════════════════════════════════════════════════════════════════════

class _MouvementDialog(tk.Toplevel):
    """Dialogue pour saisir une quantité de mouvement de stock."""

    def __init__(self, parent, title, type_mouv, max_qte=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self.geometry(f"380x260+{parent.winfo_x()+180}+{parent.winfo_y()+140}")
        self._build(type_mouv, max_qte)
        self.wait_window(self)

    def _build(self, type_mouv, max_qte):
        color = COLORS["accent"] if type_mouv == "entree" else COLORS["warning"]

        header = tk.Frame(self, bg=color, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self.title(),
                 font=FONTS["heading"], bg=color, fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        if max_qte is not None:
            tk.Label(body, text=f"Stock disponible : {max_qte:g}",
                     font=FONTS["small"], bg=COLORS["bg_card"],
                     fg=COLORS["text_light"]).pack(anchor="w", pady=(0, 8))

        tk.Label(body, text="Quantité *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_qte = tk.StringVar(value="1")
        tk.Entry(body, textvariable=self.var_qte, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6, pady=(0, 10))

        tk.Label(body, text="Note (optionnel)", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_note = tk.StringVar()
        tk.Entry(body, textvariable=self.var_note, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6, pady=(0, 10))

        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="✔ Valider", command=self._validate,
                  font=FONTS["body_bold"], bg=color, fg="white",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")

        self.bind("<Return>", lambda _: self._validate())
        self.bind("<Escape>", lambda _: self.destroy())

    def _validate(self):
        try:
            qte = float(self.var_qte.get().strip().replace(",", "."))
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "La quantité doit être un nombre positif.", parent=self)
            return
        self.result = (qte, self.var_note.get().strip())
        self.destroy()


class _SeuilDialog(tk.Toplevel):
    """Dialogue pour modifier le seuil d'alerte."""

    def __init__(self, parent, nom_produit, seuil_actuel):
        super().__init__(parent)
        self.title(f"Seuil d'alerte — {nom_produit}")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self.geometry(f"360x200+{parent.winfo_x()+200}+{parent.winfo_y()+160}")
        self._build(seuil_actuel)
        self.wait_window(self)

    def _build(self, seuil_actuel):
        header = tk.Frame(self, bg=COLORS["primary"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self.title(),
                 font=FONTS["subhead"], bg=COLORS["primary"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body,
                 text="Déclenche une alerte quand le stock passe sous ce seuil.",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 wraplength=300).pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="Seuil d'alerte *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_seuil = tk.StringVar(value=str(seuil_actuel))
        tk.Entry(body, textvariable=self.var_seuil, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6, pady=(0, 12))

        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="✔ Enregistrer", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")

        self.bind("<Return>", lambda _: self._validate())
        self.bind("<Escape>", lambda _: self.destroy())

    def _validate(self):
        try:
            seuil = float(self.var_seuil.get().strip().replace(",", "."))
            if seuil < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Le seuil doit être un nombre positif ou nul.", parent=self)
            return
        self.result = seuil
        self.destroy()


# ─── Utilitaire ───────────────────────────────────────────────────────────────

def _fmt(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"
