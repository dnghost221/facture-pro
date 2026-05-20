"""
Module d'inventaire — FacturePro
==================================
Fenêtre d'inventaire du stock avec :
  - Affichage de tous les articles avec leur stock actuel
  - Tri et filtrage par famille
  - Saisie de l'inventaire réel (comptage physique)
  - Mise à jour du stock après validation
  - Impression en format ticket de caisse (80mm)
  - Export résumé par famille
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import database as db
import config as cfg
from app_path import app_path

# ─── Palette ──────────────────────────────────────────────────────────────────
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
    "stock_ok":     "#d1fae5",
    "stock_low":    "#fef3c7",
    "stock_zero":   "#fee2e2",
    "sidebar_bg":   "#1e3a5f",
}
FONTS = {
    "title":     ("Segoe UI", 15, "bold"),
    "heading":   ("Segoe UI", 12, "bold"),
    "subhead":   ("Segoe UI", 10, "bold"),
    "body":      ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
    "mono":      ("Consolas", 10),
}


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE PRINCIPALE INVENTAIRE
# ══════════════════════════════════════════════════════════════════════════════

class InventaireWindow(tk.Toplevel):
    """Fenêtre d'inventaire du stock."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("📋 Inventaire du Stock")
        self.geometry("1080x660")
        self.minsize(860, 500)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"1080x660+{parent.winfo_x()+30}+{parent.winfo_y()+20}")

        # État
        self._famille_filtre = None   # None = toutes
        self._tri_colonne    = "designation"
        self._tri_asc        = True
        self._mode_inventaire = False  # False = lecture, True = saisie
        self._saisies = {}            # catalogue_id → valeur saisie (StringVar)

        self._build()
        self._charger()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        # En-tête
        header = tk.Frame(self, bg=COLORS["primary"], height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="📋  Inventaire du Stock",
                 font=FONTS["title"], bg=COLORS["primary"], fg="white"
                 ).pack(side="left", padx=20, pady=14)
        self.lbl_date_inv = tk.Label(
            header, text=f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            font=FONTS["small"], bg=COLORS["primary"], fg="#bfdbfe"
        )
        self.lbl_date_inv.pack(side="right", padx=20)

        # Corps : sidebar + zone principale
        body = tk.Frame(self, bg=COLORS["bg_main"])
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main(body)

    def _build_sidebar(self, parent):
        """Sidebar de filtrage par famille."""
        sb = tk.Frame(parent, bg=COLORS["sidebar_bg"], width=190)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="FAMILLE",
                 font=("Segoe UI", 8, "bold"),
                 bg=COLORS["sidebar_bg"], fg="#64748b"
                 ).pack(pady=(14, 4), padx=12, anchor="w")

        # Bouton "Toutes"
        self.btn_fam_all = tk.Button(
            sb, text="📦  Tous les articles",
            command=lambda: self._set_famille(None),
            font=FONTS["small"], bg=COLORS["primary"], fg="white",
            relief="flat", bd=0, padx=12, pady=7,
            cursor="hand2", anchor="w", width=22,
        )
        self.btn_fam_all.pack(fill="x", padx=8, pady=(0, 4))

        # Frame scrollable pour familles
        canvas = tk.Canvas(sb, bg=COLORS["sidebar_bg"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._fam_frame = tk.Frame(canvas, bg=COLORS["sidebar_bg"])
        canvas.create_window((0, 0), window=self._fam_frame, anchor="nw")
        self._fam_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=8, pady=8)

        # Résumé rapide
        self.lbl_resume = tk.Label(
            sb, text="", font=FONTS["small"],
            bg=COLORS["sidebar_bg"], fg="#94a3b8",
            wraplength=170, justify="left"
        )
        self.lbl_resume.pack(padx=12, anchor="w")

    def _build_main(self, parent):
        """Zone principale : toolbar + tableau + barre d'actions."""
        main = tk.Frame(parent, bg=COLORS["bg_main"])
        main.pack(side="left", fill="both", expand=True)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = tk.Frame(main, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        toolbar.pack(fill="x", padx=12, pady=10)

        # Recherche
        tk.Label(toolbar, text="🔍", font=FONTS["body"],
                 bg=COLORS["bg_card"]).pack(side="left", padx=(10, 4), pady=8)
        self.var_search = tk.StringVar()
        self.var_search.trace("w", lambda *_: self._charger())
        tk.Entry(toolbar, textvariable=self.var_search,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["bg_card"], fg=COLORS["text_dark"],
                 highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, ipady=6, padx=4)

        # Filtre statut
        tk.Frame(toolbar, bg=COLORS["border"], width=1
                 ).pack(side="left", fill="y", pady=6)

        self.var_filtre = tk.StringVar(value="Tous")
        for label in ("Tous", "⚠️ Stock bas", "🔴 Rupture"):
            tk.Radiobutton(
                toolbar, text=label, variable=self.var_filtre,
                value=label, command=self._charger,
                font=FONTS["small"], bg=COLORS["bg_card"],
                fg=COLORS["text_dark"], activebackground=COLORS["bg_card"],
                selectcolor=COLORS["bg_card"], relief="flat", cursor="hand2"
            ).pack(side="left", padx=6)

        # ── Label famille active ───────────────────────────────────────────────
        self.lbl_famille_active = tk.Label(
            main, text="📦  Tous les articles",
            font=FONTS["subhead"], bg=COLORS["bg_main"], fg=COLORS["primary"]
        )
        self.lbl_famille_active.pack(anchor="w", padx=16, pady=(0, 4))

        # ── Tableau ───────────────────────────────────────────────────────────
        tf = tk.Frame(main, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 0))

        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Inv.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=36, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Inv.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Inv.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree = ttk.Treeview(
            tf,
            columns=("reference", "designation", "famille",
                     "stock_systeme", "seuil", "statut"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Inv.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        self._col_defs = [
            ("reference",    "Référence",      90, "w"),
            ("designation",  "Désignation",   260, "w"),
            ("famille",      "Famille",        110, "center"),
            ("stock_systeme","Stock système",   110, "center"),
            ("seuil",        "Seuil alerte",    90, "center"),
            ("statut",       "Statut",          100, "center"),
        ]
        for cid, lbl, w, anc in self._col_defs:
            self.tree.heading(cid, text=lbl,
                              command=lambda c=cid: self._trier(c))
            self.tree.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("ok",      background=COLORS["stock_ok"])
        self.tree.tag_configure("low",     background=COLORS["stock_low"])
        self.tree.tag_configure("zero",    background=COLORS["stock_zero"])
        self.tree.tag_configure("even",    background=COLORS["row_even"])
        self.tree.tag_configure("odd",     background=COLORS["row_odd"])

        # ── Barre d'actions ───────────────────────────────────────────────────
        action_bar = tk.Frame(main, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=12, pady=(0, 12))

        for txt, cmd, color in [
            ("🖨  Imprimer l'inventaire",      self._imprimer,          COLORS["primary"]),
            ("📄  Imprimer par famille",       self._imprimer_famille,  "#0891b2"),
            ("✏️  Saisir inventaire physique", self._ouvrir_saisie,     COLORS["warning"]),
            ("🔄  Actualiser",                 self._charger,           "#6b7280"),
            ("✖  Fermer",                     self.destroy,             "#374151"),
        ]:
            tk.Button(action_bar, text=txt, command=cmd,
                      font=FONTS["body_bold"], bg=color, fg="white",
                      activebackground=COLORS["primary_dark"],
                      relief="flat", bd=0, padx=12, pady=8, cursor="hand2"
                      ).pack(side="left", padx=4, pady=8)

        self.lbl_total = tk.Label(
            action_bar, text="",
            font=FONTS["body_bold"], bg=COLORS["bg_card"], fg=COLORS["primary"]
        )
        self.lbl_total.pack(side="right", padx=16)

    # ── Données ───────────────────────────────────────────────────────────────

    def _charger_familles(self):
        """Recharge la sidebar des familles."""
        for w in self._fam_frame.winfo_children():
            w.destroy()
        for f in db.get_familles():
            color = f.get("couleur") or COLORS["primary"]
            fid, nom = f["id"], f["nom"]
            tk.Button(
                self._fam_frame, text=f"  {nom}",
                command=lambda fid=fid, nom=nom: self._set_famille(fid, nom),
                font=FONTS["small"], bg=color, fg="white",
                relief="flat", bd=0, padx=12, pady=7,
                cursor="hand2", anchor="w", width=22,
            ).pack(fill="x", padx=8, pady=2)

    def _charger(self, *_):
        """Charge et affiche les stocks."""
        query  = self.var_search.get().strip()
        filtre = self.var_filtre.get()
        fid    = self._famille_filtre

        # Récupérer les stocks
        stocks = db.get_all_stock()

        # Filtrer par famille
        if fid is not None:
            cat_ids = {p["id"] for p in db.get_catalogue(fid)}
            stocks = [s for s in stocks if s["catalogue_id"] in cat_ids]

        # Filtrer par recherche
        if query:
            q = query.lower()
            stocks = [s for s in stocks
                      if q in s["designation"].lower()]

        # Filtrer par statut
        if filtre == "⚠️ Stock bas":
            stocks = [s for s in stocks
                      if 0 < s["stock_actuel"] <= s["seuil_alerte"]]
        elif filtre == "🔴 Rupture":
            stocks = [s for s in stocks if s["stock_actuel"] <= 0]

        # Récupérer infos catalogue (référence, famille)
        catalogue = {p["id"]: p for p in db.get_catalogue()}

        # Tri
        reverse = not self._tri_asc
        if self._tri_colonne == "designation":
            stocks.sort(key=lambda s: s["designation"].lower(), reverse=reverse)
        elif self._tri_colonne == "stock_systeme":
            stocks.sort(key=lambda s: s["stock_actuel"], reverse=reverse)
        elif self._tri_colonne == "famille":
            stocks.sort(
                key=lambda s: (catalogue.get(s["catalogue_id"], {})
                               .get("famille_nom", "") or "").lower(),
                reverse=reverse
            )
        elif self._tri_colonne == "reference":
            stocks.sort(
                key=lambda s: (catalogue.get(s["catalogue_id"], {})
                               .get("reference", "") or "").lower(),
                reverse=reverse
            )

        # Remplir le tableau
        for item in self.tree.get_children():
            self.tree.delete(item)

        nb_ok = nb_bas = nb_zero = 0
        valeur_totale = 0.0

        for s in stocks:
            cat  = catalogue.get(s["catalogue_id"], {})
            ref  = cat.get("reference", "") or "—"
            fam  = cat.get("famille_nom", "") or "—"
            prix = float(cat.get("prix_unitaire", 0) or 0)
            qt   = s["stock_actuel"]
            seuil = s["seuil_alerte"]
            valeur_totale += max(qt, 0) * prix

            if qt <= 0:
                statut = "🔴 Rupture"
                tag    = "zero"
                nb_zero += 1
            elif qt <= seuil:
                statut = "⚠️ Stock bas"
                tag    = "low"
                nb_bas += 1
            else:
                statut = "✅ OK"
                tag    = "ok"
                nb_ok  += 1

            self.tree.insert("", "end",
                iid=str(s["catalogue_id"]),
                values=(
                    ref,
                    s["designation"],
                    fam,
                    f"{qt:g}",
                    f"{seuil:g}",
                    statut,
                ),
                tags=(tag,)
            )

        total = len(stocks)
        self.lbl_total.config(
            text=f"Total : {total} article(s)  |  "
                 f"✅ {nb_ok}  ⚠️ {nb_bas}  🔴 {nb_zero}  |  "
                 f"Valeur : {_fmt(valeur_totale)} FCFA"
        )
        self.lbl_resume.config(
            text=f"Articles : {total}\n"
                 f"✅ OK : {nb_ok}\n"
                 f"⚠️ Bas : {nb_bas}\n"
                 f"🔴 Rupture : {nb_zero}"
        )
        self._stocks_affiches = stocks
        self._catalogue_cache = catalogue

    def _set_famille(self, fid, nom=None):
        """Filtre par famille."""
        self._famille_filtre = fid
        self.lbl_famille_active.config(
            text="📦  Tous les articles" if fid is None else f"📁  {nom}"
        )
        self._charger()

    def _trier(self, colonne: str):
        """Trie le tableau par la colonne cliquée."""
        if self._tri_colonne == colonne:
            self._tri_asc = not self._tri_asc
        else:
            self._tri_colonne = colonne
            self._tri_asc     = True
        self._charger()

    # ── Saisie inventaire physique ────────────────────────────────────────────

    def _ouvrir_saisie(self):
        """Ouvre la fenêtre de saisie de l'inventaire physique."""
        _SaisieInventaireWindow(self)
        self._charger()

    # ── Impression ────────────────────────────────────────────────────────────

    def _imprimer(self):
        """Génère et imprime l'inventaire complet (ou filtré par famille)."""
        stocks   = self._stocks_affiches
        catalogue = self._catalogue_cache
        famille_nom = None
        if self._famille_filtre is not None:
            familles = db.get_familles()
            f = next((x for x in familles if x["id"] == self._famille_filtre), None)
            famille_nom = f["nom"] if f else None

        path = _generer_ticket_inventaire(stocks, catalogue, famille_nom)
        if path:
            _imprimer_pdf(path)
            messagebox.showinfo("✅ Inventaire imprimé",
                                f"Ticket généré :\n{path}", parent=self)
        else:
            messagebox.showerror("Erreur",
                                 "Impossible de générer le ticket.\n"
                                 "Vérifiez que reportlab est installé.",
                                 parent=self)

    def _imprimer_famille(self):
        """Génère un ticket par famille et les imprime."""
        catalogue = self._catalogue_cache
        familles  = db.get_familles()

        if not familles:
            messagebox.showinfo("Info",
                                "Aucune famille définie — impression globale.",
                                parent=self)
            self._imprimer()
            return

        # Demander quelle(s) famille(s) imprimer
        dlg = _ChoixFamilleImpression(self, familles)
        if not dlg.result:
            return

        for fid, nom in dlg.result:
            cat_ids = {p["id"] for p in db.get_catalogue(fid)}
            stocks_fam = [s for s in self._stocks_affiches
                          if s["catalogue_id"] in cat_ids]
            if not stocks_fam:
                continue
            path = _generer_ticket_inventaire(stocks_fam, catalogue, nom)
            if path:
                _imprimer_pdf(path)

        messagebox.showinfo("✅ Impression terminée",
                            "Les tickets ont été envoyés à l'imprimante.",
                            parent=self)


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE DE SAISIE DE L'INVENTAIRE PHYSIQUE
# ══════════════════════════════════════════════════════════════════════════════

class _SaisieInventaireWindow(tk.Toplevel):
    """Fenêtre de comptage physique : saisir le stock réel de chaque article."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("✏️ Saisie de l'inventaire physique")
        self.geometry("820x580")
        self.minsize(700, 440)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"820x580+{parent.winfo_x()+80}+{parent.winfo_y()+40}")

        self._saisies = {}   # catalogue_id → StringVar
        self._famille_filtre = None
        self._build()
        self._charger()

    def _build(self):
        header = tk.Frame(self, bg=COLORS["warning"], height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="✏️  Saisie de l'inventaire physique",
                 font=FONTS["heading"], bg=COLORS["warning"], fg="white"
                 ).pack(side="left", padx=18, pady=14)
        tk.Label(header,
                 text="Saisissez le stock compté physiquement pour chaque article",
                 font=FONTS["small"], bg=COLORS["warning"], fg="#fffbeb"
                 ).pack(side="right", padx=18)

        # Filtre famille
        fam_bar = tk.Frame(self, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        fam_bar.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(fam_bar, text="Famille :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(side="left", padx=(12, 4), pady=8)
        self._fam_map = {"Toutes": None}
        try:
            for f in db.get_familles():
                self._fam_map[f["nom"]] = f["id"]
        except Exception:
            pass
        self.var_fam = tk.StringVar(value="Toutes")
        ttk.Combobox(fam_bar, textvariable=self.var_fam,
                     values=list(self._fam_map.keys()),
                     state="readonly", font=FONTS["body"], width=22
                     ).pack(side="left", pady=8)
        self.var_fam.trace("w", lambda *_: self._charger())

        # Zone de saisie scrollable
        container = tk.Frame(self, bg=COLORS["bg_main"])
        container.pack(fill="both", expand=True, padx=12, pady=8)

        self._canvas = tk.Canvas(container, bg=COLORS["bg_main"],
                                 highlightthickness=0)
        scrolly = ttk.Scrollbar(container, orient="vertical",
                                 command=self._canvas.yview)
        scrolly.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=scrolly.set)
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=COLORS["bg_main"])
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw"
        )
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Molette souris
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Actions
        action_bar = tk.Frame(self, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(action_bar, text="✔  Valider l'inventaire",
                  command=self._valider,
                  font=FONTS["body_bold"], bg=COLORS["accent"], fg="white",
                  activebackground="#059669",
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(side="left", padx=8, pady=8)
        tk.Button(action_bar, text="↺  Tout remettre à zéro",
                  command=self._reset_saisies,
                  font=FONTS["body_bold"], bg="#6b7280", fg="white",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="left")
        tk.Button(action_bar, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="right", padx=8)

        self.lbl_nb = tk.Label(action_bar, text="",
                               font=FONTS["small"], bg=COLORS["bg_card"],
                               fg=COLORS["text_light"])
        self.lbl_nb.pack(side="right", padx=8)

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _charger(self, *_):
        """Construit la grille de saisie."""
        for w in self._inner.winfo_children():
            w.destroy()

        fid = self._fam_map.get(self.var_fam.get())
        stocks = db.get_all_stock()
        catalogue = {p["id"]: p for p in db.get_catalogue(fid)}

        if fid is not None:
            stocks = [s for s in stocks if s["catalogue_id"] in catalogue]

        # En-têtes
        headers = ["Référence", "Désignation", "Stock système", "Stock compté"]
        widths   = [12, 36, 14, 14]
        for col, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(self._inner, text=h, font=FONTS["body_bold"],
                     bg=COLORS["header_bg"], fg="white",
                     width=w, anchor="center", pady=6
                     ).grid(row=0, column=col, sticky="ew", padx=1, pady=(0, 2))

        for row_i, s in enumerate(stocks, start=1):
            cat = catalogue.get(s["catalogue_id"], {})
            ref = cat.get("reference", "") or "—"
            bg  = COLORS["row_even"] if row_i % 2 == 0 else COLORS["row_odd"]

            tk.Label(self._inner, text=ref, font=FONTS["mono"],
                     bg=bg, anchor="w", padx=8, pady=6, width=12
                     ).grid(row=row_i, column=0, sticky="ew", padx=1, pady=1)

            tk.Label(self._inner, text=s["designation"][:38],
                     font=FONTS["body"], bg=bg, anchor="w",
                     padx=8, pady=6, width=36
                     ).grid(row=row_i, column=1, sticky="ew", padx=1, pady=1)

            qt_sys = s["stock_actuel"]
            color_qt = (COLORS["danger"]   if qt_sys <= 0 else
                        COLORS["warning"]  if qt_sys <= s["seuil_alerte"] else
                        COLORS["accent"])
            tk.Label(self._inner, text=f"{qt_sys:g}",
                     font=FONTS["body_bold"], fg=color_qt,
                     bg=bg, anchor="center", pady=6, width=14
                     ).grid(row=row_i, column=2, sticky="ew", padx=1, pady=1)

            # Champ de saisie
            cat_id = s["catalogue_id"]
            if cat_id not in self._saisies:
                self._saisies[cat_id] = tk.StringVar(value="")

            entry = tk.Entry(
                self._inner,
                textvariable=self._saisies[cat_id],
                font=FONTS["body_bold"], width=14,
                relief="flat", bd=0, justify="center",
                bg="#fffbeb", fg=COLORS["text_dark"],
                highlightbackground=COLORS["warning"],
                highlightthickness=1,
                highlightcolor=COLORS["accent"],
            )
            entry.grid(row=row_i, column=3, sticky="ew", padx=1, pady=1, ipady=5)

        self.lbl_nb.config(text=f"{len(stocks)} article(s)")
        self._stocks_saisie = stocks

    def _reset_saisies(self):
        """Remet tous les champs de saisie à vide."""
        for var in self._saisies.values():
            var.set("")

    def _valider(self):
        """Applique l'inventaire : met à jour le stock selon les valeurs saisies."""
        modifies = 0
        erreurs  = []

        for s in self._stocks_saisie:
            cat_id = s["catalogue_id"]
            var    = self._saisies.get(cat_id)
            if var is None:
                continue
            val_str = var.get().strip().replace(",", ".")
            if not val_str:
                continue  # Non saisi → on ne touche pas

            try:
                nouveau_stock = float(val_str)
                if nouveau_stock < 0:
                    raise ValueError
            except ValueError:
                erreurs.append(s["designation"])
                continue

            # Calculer l'écart et enregistrer un mouvement
            stock_actuel = s["stock_actuel"]
            diff = nouveau_stock - stock_actuel
            if diff == 0:
                continue

            try:
                if diff > 0:
                    db.ajouter_mouvement_stock(
                        cat_id, "entree", diff, "Inventaire physique"
                    )
                else:
                    # Sortie forcée pour inventaire (pas de blocage)
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE stock SET stock_actuel=? WHERE catalogue_id=?",
                        (nouveau_stock, cat_id)
                    )
                    cursor.execute("""
                        INSERT INTO stock_mouvements
                            (catalogue_id, type_mouvement, quantite,
                             stock_avant, stock_apres, note)
                        VALUES (?, 'sortie', ?, ?, ?, 'Inventaire physique')
                    """, (cat_id, abs(diff), stock_actuel, nouveau_stock))
                    conn.commit()
                    conn.close()
                modifies += 1
            except Exception as e:
                erreurs.append(f"{s['designation']} ({e})")

        msg = f"✅ {modifies} article(s) mis à jour."
        if erreurs:
            msg += f"\n\n⚠️ Erreurs sur :\n" + "\n".join(f"• {e}" for e in erreurs)

        messagebox.showinfo("Inventaire validé", msg, parent=self)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUE : CHOIX DES FAMILLES À IMPRIMER
# ══════════════════════════════════════════════════════════════════════════════

class _ChoixFamilleImpression(tk.Toplevel):
    """Sélection des familles à inclure dans l'impression."""

    def __init__(self, parent, familles: list):
        super().__init__(parent)
        self.title("Choisir les familles")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self.geometry(f"360x340+{parent.winfo_x()+200}+{parent.winfo_y()+150}")
        self._familles = familles
        self._vars = {}
        self._build()
        self.wait_window(self)

    def _build(self):
        header = tk.Frame(self, bg=COLORS["primary"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="📄  Familles à imprimer",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white"
                 ).pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=20, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Sélectionnez les familles :",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 8))

        for f in self._familles:
            var = tk.BooleanVar(value=True)
            self._vars[f["id"]] = (var, f["nom"])
            tk.Checkbutton(
                body, text=f["nom"], variable=var,
                font=FONTS["body"], bg=COLORS["bg_card"],
                fg=COLORS["text_dark"], activebackground=COLORS["bg_card"],
                selectcolor=COLORS["bg_card"], relief="flat", cursor="hand2"
            ).pack(anchor="w", pady=2)

        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=16, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="🖨  Imprimer", command=self._valider,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=16, pady=7, cursor="hand2"
                  ).pack(side="right")

    def _valider(self):
        self.result = [
            (fid, nom)
            for fid, (var, nom) in self._vars.items()
            if var.get()
        ]
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU TICKET D'INVENTAIRE (format 80mm)
# ══════════════════════════════════════════════════════════════════════════════

def _generer_ticket_inventaire(stocks: list, catalogue: dict,
                                famille_nom: str = None) -> str:
    """Génère un ticket de caisse 80mm pour l'inventaire."""
    try:
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas
    except ImportError:
        return ""

    conf     = cfg.load()
    nom_com  = conf.get("nom", "MON COMMERCE")
    adresse  = conf.get("adresse", "")
    tel      = conf.get("telephone", "")

    # Couleur primaire
    try:
        from reportlab.lib import colors as rl_colors
        coul = rl_colors.HexColor(conf.get("couleur_primaire", "#1a56db"))
    except Exception:
        coul = colors.HexColor("#1a56db")

    # Chemin de sortie
    dossier = cfg.get("dossier_factures", "factures")
    if not os.path.isabs(dossier):
        dossier = app_path(dossier)
    os.makedirs(dossier, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = famille_nom.replace(" ", "_") if famille_nom else "GLOBAL"
    path = os.path.join(dossier, f"INVENTAIRE_{slug}_{ts}.pdf")

    W  = 80 * mm
    MG = 4  * mm

    # Hauteur dynamique
    nb_lignes = len(stocks)
    hauteur   = max(100 * mm, (55 + nb_lignes * 7 + 20) * mm)

    c   = rl_canvas.Canvas(path, pagesize=(W, hauteur))
    y   = hauteur - MG
    x_l = MG + 2
    x_r = W - MG - 2
    x_c = W / 2

    def line(y_pos, dashed=False):
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        if dashed:
            c.setDash(2, 2)
        c.line(x_l, y_pos, x_r, y_pos)
        c.setDash()

    def txt_c(text, y_pos, size=8, bold=False, color=colors.black):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawCentredString(x_c, y_pos, text)

    def txt_l(text, y_pos, size=7.5, bold=False, color=colors.black):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawString(x_l, y_pos, text)

    def txt_r(text, y_pos, size=7.5, bold=False, color=colors.black):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawRightString(x_r, y_pos, text)

    # ── En-tête ────────────────────────────────────────────────────────────────
    txt_c(nom_com, y, size=10, bold=True, color=coul)
    y -= 5 * mm
    if adresse:
        txt_c(adresse, y, size=7)
        y -= 4 * mm
    if tel:
        txt_c(f"Tél : {tel}", y, size=7)
        y -= 4 * mm

    y -= 2 * mm
    line(y)
    y -= 3 * mm

    txt_c("ÉTAT DES STOCKS — INVENTAIRE", y, size=9, bold=True)
    y -= 4 * mm
    txt_c(datetime.now().strftime("%d/%m/%Y à %H:%M"), y, size=7,
          color=colors.grey)
    y -= 4 * mm
    if famille_nom:
        txt_c(f"Famille : {famille_nom}", y, size=8, bold=True, color=coul)
        y -= 4 * mm

    line(y, dashed=True)
    y -= 3 * mm

    # ── En-têtes colonnes ──────────────────────────────────────────────────────
    col_desig_w = (W - 2 * MG) * 0.60
    x_qt  = x_l + col_desig_w
    x_st  = x_qt + (W - 2 * MG) * 0.20

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.grey)
    c.drawString(x_l, y, "Article")
    c.drawString(x_qt, y, "Qté")
    c.drawRightString(x_r, y, "Statut")
    y -= 2 * mm
    line(y)
    y -= 3 * mm

    # ── Lignes ────────────────────────────────────────────────────────────────
    for s in stocks:
        cat  = catalogue.get(s["catalogue_id"], {})
        desig = s["designation"][:28]
        qt    = s["stock_actuel"]
        seuil = s["seuil_alerte"]

        if qt <= 0:
            statut = "RUPTURE"
            color_qt = colors.HexColor("#dc2626")
        elif qt <= seuil:
            statut = "BAS"
            color_qt = colors.HexColor("#d97706")
        else:
            statut = "OK"
            color_qt = colors.HexColor("#059669")

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.black)
        c.drawString(x_l, y, desig)
        c.setFillColor(color_qt)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x_qt, y, f"{qt:g}")
        c.drawRightString(x_r, y, statut)
        y -= 4 * mm

    # ── Pied ──────────────────────────────────────────────────────────────────
    line(y, dashed=True)
    y -= 3 * mm

    # Résumé
    nb_ok   = sum(1 for s in stocks if s["stock_actuel"] > s["seuil_alerte"])
    nb_bas  = sum(1 for s in stocks
                  if 0 < s["stock_actuel"] <= s["seuil_alerte"])
    nb_zero = sum(1 for s in stocks if s["stock_actuel"] <= 0)

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.black)
    c.drawString(x_l, y, f"Total articles : {len(stocks)}")
    y -= 4 * mm
    c.setFillColor(colors.HexColor("#059669"))
    c.drawString(x_l, y, f"✓ OK : {nb_ok}")
    c.setFillColor(colors.HexColor("#d97706"))
    c.drawString(x_l + 25 * mm, y, f"⚠ Bas : {nb_bas}")
    c.setFillColor(colors.HexColor("#dc2626"))
    c.drawString(x_l + 50 * mm, y, f"✗ Rupture : {nb_zero}")
    y -= 5 * mm

    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(x_c, y, f"Imprimé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

    c.save()
    return path


def _imprimer_pdf(path: str):
    """Envoie le PDF à l'imprimante par défaut."""
    import platform, subprocess, os
    if not path or not os.path.exists(path):
        return
    try:
        system = platform.system()
        if system == "Windows":
            try:
                import win32api
                win32api.ShellExecute(0, "print", path, None, ".", 0)
            except ImportError:
                os.startfile(path, "print")
        else:
            subprocess.run(["lpr", path], check=False)
    except Exception:
        pass


def _fmt(value) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", " ")
    except Exception:
        return "0"
