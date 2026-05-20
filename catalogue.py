"""
Module du catalogue de produits
Fenêtre de gestion du catalogue : familles d'articles, référence, code-barres.
Peut être utilisé en mode 'sélection' pour pré-remplir une ligne de facture.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser

import database as db


# ─── Couleurs & polices ────────────────────────────────────────────────────────
COLORS = {
    "bg_main":       "#f8fafc",
    "bg_card":       "#ffffff",
    "primary":       "#1a56db",
    "primary_dark":  "#0d3d91",
    "primary_light": "#eff6ff",
    "accent":        "#10b981",
    "danger":        "#ef4444",
    "warning":       "#f59e0b",
    "text_dark":     "#111827",
    "text_medium":   "#374151",
    "text_light":    "#9ca3af",
    "border":        "#e5e7eb",
    "row_even":      "#f9fafb",
    "row_odd":       "#ffffff",
    "row_selected":  "#dbeafe",
    "header_bg":     "#1a56db",
    "sidebar_bg":    "#1e3a5f",
    "barcode_bg":    "#f0fdf4",
    "barcode_border":"#bbf7d0",
}

FONTS = {
    "title":     ("Segoe UI", 15, "bold"),
    "heading":   ("Segoe UI", 12, "bold"),
    "subhead":   ("Segoe UI", 10, "bold"),
    "body":      ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
    "mono":      ("Consolas", 11),
}

PALETTE_FAMILLES = [
    "#1a56db", "#0891b2", "#059669", "#d97706",
    "#7c3aed", "#db2777", "#dc2626", "#374151",
]


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE CATALOGUE (gestion complète)
# ══════════════════════════════════════════════════════════════════════════════

class CatalogueWindow(tk.Toplevel):
    """Fenêtre principale de gestion du catalogue avec panneaux familles + articles."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("📦 Catalogue des Produits")
        self.geometry("1060x640")
        self.minsize(860, 460)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"1150x640+{parent.winfo_x()+40}+{parent.winfo_y()+30}")
        self._famille_selectionnee = None
        self._build()
        self._charger_familles()
        self._charger_articles()

    def _build(self):
        header = tk.Frame(self, bg=COLORS["primary"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="📦  Catalogue des Produits",
                 font=FONTS["title"], bg=COLORS["primary"], fg="white"
                 ).pack(side="left", padx=20, pady=12)
        tk.Label(header, text="Familles · Références · Codes-barres",
                 font=FONTS["small"], bg=COLORS["primary"], fg="#bfdbfe"
                 ).pack(side="right", padx=20)

        body = tk.Frame(self, bg=COLORS["bg_main"])
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_articles(body)

    # ── Sidebar familles ──────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=COLORS["sidebar_bg"], width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="FAMILLES", font=("Segoe UI", 8, "bold"),
                 bg=COLORS["sidebar_bg"], fg="#64748b"
                 ).pack(pady=(14, 4), padx=12, anchor="w")

        self.btn_all = tk.Button(
            sb, text="📦  Tous les articles",
            command=lambda: self._select_famille(None),
            font=FONTS["small"], bg=COLORS["primary"], fg="white",
            relief="flat", bd=0, padx=12, pady=7, cursor="hand2", anchor="w", width=22,
        )
        self.btn_all.pack(fill="x", padx=8, pady=(0, 4))

        fam_canvas = tk.Canvas(sb, bg=COLORS["sidebar_bg"], highlightthickness=0)
        fam_canvas.pack(fill="both", expand=True)
        self._fam_frame = tk.Frame(fam_canvas, bg=COLORS["sidebar_bg"])
        fam_canvas.create_window((0, 0), window=self._fam_frame, anchor="nw")
        self._fam_frame.bind("<Configure>",
            lambda e: fam_canvas.configure(scrollregion=fam_canvas.bbox("all")))

        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=8, pady=8)

        for text, cmd, color in [
            ("＋  Nouvelle famille", self._ajouter_famille,   COLORS["accent"]),
            ("✏️  Modifier famille",  self._modifier_famille,  "#475569"),
            ("🗑  Supprimer famille", self._supprimer_famille, COLORS["danger"]),
        ]:
            tk.Button(sb, text=text, command=cmd, font=FONTS["small"],
                      bg=color, fg="white", relief="flat", bd=0,
                      padx=10, pady=6, cursor="hand2"
                      ).pack(fill="x", padx=8, pady=(0, 4))

    # ── Zone articles ─────────────────────────────────────────────────────────

    def _build_articles(self, parent):
        zone = tk.Frame(parent, bg=COLORS["bg_main"])
        zone.pack(side="left", fill="both", expand=True)

        # Toolbar recherche
        toolbar = tk.Frame(zone, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        toolbar.pack(fill="x", padx=12, pady=10)
        tk.Label(toolbar, text="🔍", font=FONTS["body"],
                 bg=COLORS["bg_card"]).pack(side="left", padx=(10, 4), pady=8)
        self.var_search = tk.StringVar()
        self.var_search.trace("w", lambda *_: self._charger_articles())
        tk.Entry(toolbar, textvariable=self.var_search,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["bg_card"], fg=COLORS["text_dark"], highlightthickness=0,
                 ).pack(side="left", fill="x", expand=True, ipady=6, padx=4)
        tk.Button(toolbar, text="＋  Nouveau produit", command=self._ajouter_article,
                  font=FONTS["body_bold"], bg=COLORS["accent"], fg="white",
                  activebackground="#059669", relief="flat", bd=0,
                  padx=14, pady=6, cursor="hand2"
                  ).pack(side="right", padx=10, pady=6)

        self.lbl_famille_active = tk.Label(
            zone, text="📦  Tous les articles",
            font=FONTS["subhead"], bg=COLORS["bg_main"], fg=COLORS["primary"]
        )
        self.lbl_famille_active.pack(anchor="w", padx=16, pady=(0, 4))

        # Tableau
        tf = tk.Frame(zone, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Cat.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=34, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Cat.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Cat.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree = ttk.Treeview(
            tf,
            columns=("reference", "designation", "famille", "prix_achat", "prix_vente", "marge", "code_barre", "stock"),
            show="headings", yscrollcommand=scrolly.set,
            selectmode="browse", style="Cat.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        for cid, lbl, w, anc in [
            ("reference",   "Référence",    90, "w"),
            ("designation", "Désignation", 210, "w"),
            ("famille",     "Famille",      90, "center"),
            ("prix_achat",  "P. Achat",     90, "e"),
            ("prix_vente",  "P. Vente",     90, "e"),
            ("marge",       "Marge",        80, "center"),
            ("code_barre",  "Code-barres", 110, "center"),
            ("stock",       "Stock",        60, "center"),
        ]:
            self.tree.heading(cid, text=lbl)
            self.tree.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("even", background=COLORS["row_even"])
        self.tree.tag_configure("odd",  background=COLORS["row_odd"])
        self.tree.bind("<Double-1>", lambda _: self._modifier_article())

        # Actions
        action_bar = tk.Frame(zone, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=12, pady=(0, 12))
        for lbl, cmd, color in [
            ("✏️  Modifier",         self._modifier_article,  COLORS["primary"]),
            ("🔲  Voir code-barres", self._voir_barcode,       "#0891b2"),
            ("💾  Exporter code-b.", self._exporter_barcode,   "#7c3aed"),
            ("🗑  Supprimer",        self._supprimer_article,  COLORS["danger"]),
            ("✖  Fermer",           self.destroy,             "#6b7280"),
        ]:
            tk.Button(action_bar, text=lbl, command=cmd,
                      font=FONTS["body_bold"], bg=color, fg="white",
                      activebackground=COLORS["primary_dark"], activeforeground="white",
                      relief="flat", bd=0, padx=12, pady=8, cursor="hand2"
                      ).pack(side="left", padx=4, pady=8)

        self.lbl_count = tk.Label(action_bar, text="",
                                  font=FONTS["small"], bg=COLORS["bg_card"],
                                  fg=COLORS["text_light"])
        self.lbl_count.pack(side="right", padx=16)

    # ── Données ───────────────────────────────────────────────────────────────

    def _charger_familles(self):
        for w in self._fam_frame.winfo_children():
            w.destroy()
        for f in db.get_familles():
            color = f.get("couleur") or COLORS["primary"]
            fid, nom = f["id"], f["nom"]
            tk.Button(
                self._fam_frame, text=f"  {nom}",
                command=lambda fid=fid, nom=nom: self._select_famille(fid, nom),
                font=FONTS["small"], bg=color, fg="white",
                relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                anchor="w", width=22,
            ).pack(fill="x", padx=8, pady=2)

    def _charger_articles(self):
        q = self.var_search.get().strip()
        fid = self._famille_selectionnee
        produits = db.search_catalogue(q, fid) if q else db.get_catalogue(fid)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, p in enumerate(produits):
            cb = p.get("code_barre", "") or ""
            stock_val = db.get_stock_produit(p["id"])
            pa  = float(p.get("prix_achat", 0) or 0)
            pv  = float(p.get("prix_unitaire", 0) or 0)
            if pa > 0:
                marge_val = ((pv - pa) / pa * 100)
                marge_str = f"{marge_val:+.1f}%"
            else:
                marge_str = "—"
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(p["id"]),
                values=(
                    p.get("reference", "") or "—",
                    p["designation"],
                    p.get("famille_nom", "") or "—",
                    f'{_fmt(pa)} FCFA' if pa > 0 else "—",
                    f'{_fmt(pv)} FCFA',
                    marge_str,
                    f"✅ {cb}" if cb else "—",
                    f"{stock_val:g}",
                ), tags=(tag,))
        self.lbl_count.config(text=f"{len(produits)} article(s)")

    def _select_famille(self, famille_id, nom=None):
        self._famille_selectionnee = famille_id
        self.lbl_famille_active.config(
            text="📦  Tous les articles" if famille_id is None else f"📁  {nom}"
        )
        self._charger_articles()

    # ── Familles CRUD ─────────────────────────────────────────────────────────

    def _ajouter_famille(self):
        dlg = _FamilleDialog(self, "Nouvelle famille")
        if dlg.result:
            nom, desc, couleur = dlg.result
            try:
                db.add_famille(nom, desc, couleur)
                self._charger_familles()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def _modifier_famille(self):
        fid = self._famille_selectionnee
        if fid is None:
            messagebox.showinfo("Info",
                "Cliquez d'abord sur une famille dans la sidebar.", parent=self)
            return
        f = next((x for x in db.get_familles() if x["id"] == fid), None)
        if not f:
            return
        dlg = _FamilleDialog(self, "Modifier la famille", initial=f)
        if dlg.result:
            nom, desc, couleur = dlg.result
            try:
                db.update_famille(fid, nom, desc, couleur)
                self._charger_familles()
                self._charger_articles()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def _supprimer_famille(self):
        fid = self._famille_selectionnee
        if fid is None:
            messagebox.showinfo("Info",
                "Cliquez d'abord sur une famille dans la sidebar.", parent=self)
            return
        f = next((x for x in db.get_familles() if x["id"] == fid), None)
        if not f:
            return
        if messagebox.askyesno("Confirmer",
            f"Supprimer la famille « {f['nom']} » ?\n"
            "Les articles liés resteront sans famille.", parent=self):
            db.delete_famille(fid)
            self._famille_selectionnee = None
            self.lbl_famille_active.config(text="📦  Tous les articles")
            self._charger_familles()
            self._charger_articles()

    # ── Articles CRUD ─────────────────────────────────────────────────────────

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Sélectionnez un article.", parent=self)
            return None
        return int(sel[0])

    def _ajouter_article(self):
        next_ref = db.get_next_reference()
        dlg = _ArticleDialog(self, "Ajouter un article",
                             famille_id=self._famille_selectionnee,
                             initial={"reference": next_ref})
        if dlg.result:
            r = dlg.result
            db.add_catalogue_product(
                r["designation"], r["prix_unitaire"], r["description"],
                r["code_barre"], r["reference"], r["famille_id"],
                r["prix_achat"]
            )
            self._charger_articles()

    def _modifier_article(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        p = next((x for x in db.get_catalogue() if x["id"] == pid), None)
        if not p:
            return
        dlg = _ArticleDialog(self, "Modifier l'article", initial=p)
        if dlg.result:
            r = dlg.result
            db.update_catalogue_product(
                pid, r["designation"], r["prix_unitaire"], r["description"],
                r["code_barre"], r["reference"], r["famille_id"],
                r["prix_achat"]
            )
            self._charger_articles()

    def _supprimer_article(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        nom = self.tree.item(str(pid))["values"][1]
        if messagebox.askyesno("Confirmer",
                               f"Supprimer « {nom} » ?", parent=self):
            db.delete_catalogue_product(pid)
            self._charger_articles()

    def _voir_barcode(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        p = next((x for x in db.get_catalogue() if x["id"] == pid), None)
        if not p:
            return
        cb = p.get("code_barre", "") or ""
        if not cb:
            messagebox.showinfo("Pas de code-barres",
                                f"« {p['designation']} » n'a pas de code-barres.", parent=self)
            return
        _BarcodeViewerDialog(self, p["designation"], cb)

    def _exporter_barcode(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        p = next((x for x in db.get_catalogue() if x["id"] == pid), None)
        if not p:
            return
        cb = p.get("code_barre", "") or ""
        if not cb:
            messagebox.showinfo("Pas de code-barres",
                                "Cet article n'a pas de code-barres.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Enregistrer",
            defaultextension=".png", initialfile=f"barcode_{cb}.png",
            filetypes=[("PNG", "*.png"), ("Tous", "*.*")]
        )
        if path:
            ok = _save_barcode_to_file(cb, path)
            if ok:
                messagebox.showinfo("✅ Exporté", f"Exporté :\n{path}", parent=self)
            else:
                messagebox.showerror("Erreur",
                    "Impossible de générer.\npip install python-barcode pillow",
                    parent=self)


# ══════════════════════════════════════════════════════════════════════════════
# SÉLECTEUR CATALOGUE (mode pick)
# ══════════════════════════════════════════════════════════════════════════════

class CataloguePickerDialog(tk.Toplevel):
    """Fenêtre modale de sélection d'un produit du catalogue."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Choisir dans le catalogue")
        self.resizable(True, True)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self.geometry(f"680x470+{parent.winfo_x()+60}+{parent.winfo_y()+60}")
        self._famille_filtre = None
        self._familles_map = {}
        self._build()
        self._charger_familles()
        self._charger()
        self.wait_window(self)

    def _build(self):
        header = tk.Frame(self, bg=COLORS["primary"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="📦  Sélectionner un produit",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white").pack(expand=True)

        fam_bar = tk.Frame(self, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        fam_bar.pack(fill="x", padx=14, pady=(8, 0))
        tk.Label(fam_bar, text="Famille :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(side="left", padx=(10, 4), pady=6)
        self.var_famille = tk.StringVar(value="Toutes")
        self.combo_famille = ttk.Combobox(
            fam_bar, textvariable=self.var_famille,
            font=FONTS["body"], state="readonly", width=22
        )
        self.combo_famille.pack(side="left", pady=6)
        self.combo_famille.bind("<<ComboboxSelected>>", self._on_famille_change)

        search_frame = tk.Frame(self, bg=COLORS["bg_card"],
                                highlightbackground=COLORS["border"], highlightthickness=1)
        search_frame.pack(fill="x", padx=14, pady=(4, 0))
        tk.Label(search_frame, text="🔍", font=FONTS["body"],
                 bg=COLORS["bg_card"]).pack(side="left", padx=(8, 2), pady=6)
        self.var_search = tk.StringVar()
        self.var_search.trace("w", lambda *_: self._charger())
        tk.Entry(search_frame, textvariable=self.var_search,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["bg_card"], fg=COLORS["text_dark"], highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=4)

        tf = tk.Frame(self, bg=COLORS["bg_card"])
        tf.pack(fill="both", expand=True, padx=14, pady=(6, 0))
        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Pick.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=32, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Pick.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Pick.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree = ttk.Treeview(
            tf,
            columns=("reference", "designation", "famille", "prix", "stock"),
            show="headings", yscrollcommand=scrolly.set,
            selectmode="browse", style="Pick.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        for cid, lbl, w, anc in [
            ("reference",   "Référence",   100, "w"),
            ("designation", "Désignation", 230, "w"),
            ("famille",     "Famille",     110, "center"),
            ("prix",        "Prix unit.",  100, "e"),
            ("stock",       "Stock",        70, "center"),
        ]:
            self.tree.heading(cid, text=lbl)
            self.tree.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("even", background=COLORS["row_even"])
        self.tree.tag_configure("odd",  background=COLORS["row_odd"])
        self.tree.bind("<Double-1>", lambda _: self._selectionner())
        self.tree.bind("<Return>",   lambda _: self._selectionner())

        btn_frame = tk.Frame(self, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", padx=14, pady=(4, 12))
        self.lbl_vide = tk.Label(btn_frame,
            text="Le catalogue est vide — ajoutez des produits via « Catalogue ».",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"])
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="✔  Sélectionner", command=self._selectionner,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")
        self.bind("<Escape>", lambda _: self.destroy())

    def _charger_familles(self):
        familles = db.get_familles()
        self._familles_map = {"Toutes": None}
        for f in familles:
            self._familles_map[f["nom"]] = f["id"]
        self.combo_famille["values"] = list(self._familles_map.keys())

    def _on_famille_change(self, *_):
        self._famille_filtre = self._familles_map.get(self.var_famille.get())
        self._charger()

    def _charger(self):
        q = self.var_search.get().strip()
        fid = self._famille_filtre
        produits = db.search_catalogue(q, fid) if q else db.get_catalogue(fid)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, p in enumerate(produits):
            stock_val = db.get_stock_produit(p["id"])
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(p["id"]),
                values=(
                    p.get("reference", "") or "—",
                    p["designation"],
                    p.get("famille_nom", "") or "—",
                    f'{_fmt(p["prix_unitaire"])} FCFA',
                    f"{stock_val:g}",
                ), tags=(tag,))

        if not produits:
            self.lbl_vide.pack(side="left", padx=4)
        else:
            self.lbl_vide.pack_forget()
            first = self.tree.get_children()
            if first:
                self.tree.selection_set(first[0])
                self.tree.focus(first[0])

    def _selectionner(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Sélectionnez un article.", parent=self)
            return
        pid = int(sel[0])
        p = next((x for x in db.get_catalogue() if x["id"] == pid), None)
        if p:
            self.result = p
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUE FAMILLE
# ══════════════════════════════════════════════════════════════════════════════

class _FamilleDialog(tk.Toplevel):
    def __init__(self, parent, title="Famille", initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self._couleur = (initial or {}).get("couleur", PALETTE_FAMILLES[0])
        self.geometry(f"420x280+{parent.winfo_x()+180}+{parent.winfo_y()+120}")
        self._build(initial or {})
        self.wait_window(self)

    def _build(self, initial):
        header = tk.Frame(self, bg=COLORS["primary"], height=46)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self.title(),
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=22, pady=14)
        body.pack(fill="both", expand=True)

        self.var_nom  = tk.StringVar(value=initial.get("nom", ""))
        self.var_desc = tk.StringVar(value=initial.get("description", ""))

        tk.Label(body, text="Nom *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        tk.Entry(body, textvariable=self.var_nom, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6, pady=(0, 10))

        tk.Label(body, text="Description", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        tk.Entry(body, textvariable=self.var_desc, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=6, pady=(0, 10))

        # Couleur
        color_row = tk.Frame(body, bg=COLORS["bg_card"])
        color_row.pack(fill="x", pady=(0, 12))
        tk.Label(color_row, text="Couleur :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(side="left")
        for c in PALETTE_FAMILLES:
            tk.Button(
            color_row,
            bg=c,
            width=2,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda col=c: self._set_color(col)
        ).pack(side="left", padx=2, ipady=6)
        self.preview_color = tk.Label(color_row, text=" ✔ ", bg=self._couleur,
                                      fg="white", font=FONTS["small"])
        self.preview_color.pack(side="left", padx=(8, 0), ipady=4)
        tk.Button(color_row, text="🎨", font=FONTS["small"],
                  bg=COLORS["border"], relief="flat", bd=0,
                  padx=6, cursor="hand2",
                  command=self._choisir_couleur
                  ).pack(side="left", padx=4)

        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="✔ Enregistrer", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")
        self.bind("<Return>", lambda _: self._validate())
        self.bind("<Escape>", lambda _: self.destroy())

    def _set_color(self, color):
        self._couleur = color
        self.preview_color.config(bg=color)

    def _choisir_couleur(self):
        c = colorchooser.askcolor(color=self._couleur, title="Couleur", parent=self)
        if c and c[1]:
            self._set_color(c[1])

    def _validate(self):
        nom = self.var_nom.get().strip()
        if not nom:
            messagebox.showerror("Erreur", "Le nom est obligatoire.", parent=self)
            return
        self.result = (nom, self.var_desc.get().strip(), self._couleur)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUE ARTICLE (créer / modifier)
# ══════════════════════════════════════════════════════════════════════════════

class _ArticleDialog(tk.Toplevel):
    def __init__(self, parent, title="Article", initial=None, famille_id=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self._default_famille_id = famille_id
        self._familles_map = {}
        self.geometry(f"520x540+{parent.winfo_x()+140}+{parent.winfo_y()+60}")
        self._build(initial or {})
        self.wait_window(self)

    def _build(self, initial):
        header = tk.Frame(self, bg=COLORS["primary"], height=46)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self.title(),
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=22, pady=14)
        body.pack(fill="both", expand=True)

        self.var_ref   = tk.StringVar(value=initial.get("reference", ""))
        self.var_desig = tk.StringVar(value=initial.get("designation", ""))
        self.var_pa    = tk.StringVar(value=str(initial.get("prix_achat", "") or ""))
        self.var_prix  = tk.StringVar(value=str(initial.get("prix_unitaire", "")))
        self.var_desc  = tk.StringVar(value=initial.get("description", ""))
        self.var_cb    = tk.StringVar(value=initial.get("code_barre", "") or "")

        # ── Ligne référence + famille
        row_top = tk.Frame(body, bg=COLORS["bg_card"])
        row_top.pack(fill="x", pady=(0, 6))

        col_ref = tk.Frame(row_top, bg=COLORS["bg_card"])
        col_ref.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(col_ref, text="Référence *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        tk.Entry(col_ref, textvariable=self.var_ref, font=("Consolas", 10),
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg="#0d3d91",
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6)

        col_fam = tk.Frame(row_top, bg=COLORS["bg_card"])
        col_fam.pack(side="left", fill="x", expand=True)
        tk.Label(col_fam, text="Famille", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_famille = tk.StringVar()
        self.combo_famille = ttk.Combobox(
            col_fam, textvariable=self.var_famille,
            font=FONTS["body"], state="readonly", width=20
        )
        self.combo_famille.pack(fill="x", ipady=3)

        familles = db.get_familles()
        self._familles_map = {"— Aucune —": None}
        for f in familles:
            self._familles_map[f["nom"]] = f["id"]
        self.combo_famille["values"] = list(self._familles_map.keys())

        famille_actuelle = initial.get("famille_id") or self._default_famille_id
        if famille_actuelle:
            for nom, fid in self._familles_map.items():
                if fid == famille_actuelle:
                    self.var_famille.set(nom)
                    break
        if not self.var_famille.get():
            self.var_famille.set("— Aucune —")

        # ── Désignation
        tk.Label(body, text="Désignation *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w", pady=(4, 0))
        tk.Entry(body, textvariable=self.var_desig, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(fill="x", ipady=6, pady=(0, 6))

        # ── Prix achat + Prix vente + Marge
        row_prix = tk.Frame(body, bg=COLORS["bg_card"])
        row_prix.pack(fill="x", pady=(0, 6))

        col_pa = tk.Frame(row_prix, bg=COLORS["bg_card"])
        col_pa.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_pa, text="Prix d'achat (FCFA)", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_pa.trace("w", self._maj_marge)
        tk.Entry(col_pa, textvariable=self.var_pa, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg="#059669",
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=6)

        col_pv = tk.Frame(row_prix, bg=COLORS["bg_card"])
        col_pv.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_pv, text="Prix de vente (FCFA) *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.var_prix.trace("w", self._maj_marge)
        tk.Entry(col_pv, textvariable=self.var_prix, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=6)

        col_marge = tk.Frame(row_prix, bg=COLORS["bg_card"])
        col_marge.pack(side="left", fill="x", expand=False)
        tk.Label(col_marge, text="Marge", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.lbl_marge = tk.Label(col_marge, text="—",
                                   font=FONTS["body_bold"], width=10,
                                   bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                                   relief="flat")
        self.lbl_marge.pack(fill="x", ipady=6)
        self._maj_marge()

        # ── Description
        tk.Label(body, text="Description", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w", pady=(2, 0))
        tk.Entry(body, textvariable=self.var_desc, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=6, pady=(0, 6))

        # ── Code-barres
        cb_frame = tk.Frame(body, bg=COLORS["barcode_bg"],
                            highlightbackground=COLORS["barcode_border"], highlightthickness=1)
        cb_frame.pack(fill="x", pady=(4, 8))
        tk.Label(cb_frame, text="🔲  Code-barres",
                 font=FONTS["body_bold"], bg=COLORS["barcode_bg"], fg="#065f46"
                 ).pack(anchor="w", padx=10, pady=(8, 2))
        cb_row = tk.Frame(cb_frame, bg=COLORS["barcode_bg"])
        cb_row.pack(fill="x", padx=10, pady=(0, 8))
        self.entry_cb = tk.Entry(
            cb_row, textvariable=self.var_cb,
            font=FONTS["mono"], relief="flat", bd=0,
            bg="white", fg=COLORS["text_dark"],
            highlightbackground=COLORS["barcode_border"], highlightthickness=1,
            highlightcolor="#10b981",
        )
        self.entry_cb.pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(cb_row, text="🔲 Aperçu", command=self._apercu_barcode,
                  font=FONTS["small"], bg="#0891b2", fg="white",
                  relief="flat", bd=0, padx=10, pady=5, cursor="hand2"
                  ).pack(side="right", padx=(6, 0))
        tk.Label(cb_frame,
                 text="Scannez avec votre douchette ou saisissez manuellement.",
                 font=FONTS["small"], bg=COLORS["barcode_bg"], fg="#6b7280",
                 wraplength=420).pack(anchor="w", padx=10, pady=(0, 6))
        self.entry_cb.bind("<Return>", self._on_barcode_scanned)

        # ── Boutons
        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", pady=(4, 0))
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="✔ Enregistrer", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")
        self.entry_cb.focus()
        self.bind("<Escape>", lambda _: self.destroy())

    def _maj_marge(self, *_):
        """Recalcule et affiche la marge en temps réel."""
        try:
            pa = float(self.var_pa.get().strip().replace(",", ".") or "0")
            pv = float(self.var_prix.get().strip().replace(",", ".") or "0")
            if pa > 0 and pv > 0:
                marge_abs = pv - pa
                marge_pct = (marge_abs / pa) * 100
                color = COLORS["accent"] if marge_abs >= 0 else COLORS["danger"]
                self.lbl_marge.config(
                    text=f"{marge_pct:+.1f}%",
                    fg=color
                )
            else:
                self.lbl_marge.config(text="—", fg=COLORS["text_light"])
        except (ValueError, AttributeError):
            self.lbl_marge.config(text="—", fg=COLORS["text_light"])

    def _on_barcode_scanned(self, event):
        cb = self.var_cb.get().strip()
        if cb:
            existing = db.get_product_by_barcode(cb)
            if existing and existing.get("designation") != self.var_desig.get().strip():
                messagebox.showwarning("Code-barres existant",
                    f"Déjà utilisé par :\n« {existing['designation']} »", parent=self)
        self.entry_cb.config(highlightbackground="#10b981", highlightthickness=2)
        self.after(600, lambda: self.entry_cb.config(
            highlightbackground=COLORS["barcode_border"], highlightthickness=1))

    def _apercu_barcode(self):
        cb = self.var_cb.get().strip()
        if not cb:
            messagebox.showinfo("Code vide", "Saisissez d'abord un code.", parent=self)
            return
        _BarcodeViewerDialog(self, self.var_desig.get() or cb, cb)

    def _validate(self):
        ref    = self.var_ref.get().strip()
        desig  = self.var_desig.get().strip()
        prix_s = self.var_prix.get().strip().replace(",", ".")
        pa_s   = self.var_pa.get().strip().replace(",", ".")
        if not ref:
            messagebox.showerror("Erreur", "La référence est obligatoire.", parent=self)
            return
        if not desig:
            messagebox.showerror("Erreur", "La désignation est obligatoire.", parent=self)
            return
        try:
            prix = float(prix_s)
            if prix < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Prix de vente invalide.", parent=self)
            return
        try:
            pa = float(pa_s) if pa_s else 0.0
            if pa < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Prix d'achat invalide.", parent=self)
            return
        self.result = {
            "reference":     ref,
            "designation":   desig,
            "prix_achat":    pa,
            "prix_unitaire": prix,
            "description":   self.var_desc.get().strip(),
            "code_barre":    self.var_cb.get().strip(),
            "famille_id":    self._familles_map.get(self.var_famille.get()),
        }
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# VISIONNEUR CODE-BARRES
# ══════════════════════════════════════════════════════════════════════════════

class _BarcodeViewerDialog(tk.Toplevel):
    def __init__(self, parent, nom_produit, code):
        super().__init__(parent)
        self.title(f"Code-barres — {nom_produit}")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.geometry(f"340x240+{parent.winfo_x()+100}+{parent.winfo_y()+100}")
        header = tk.Frame(self, bg=COLORS["primary"], height=44)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"🔲  {nom_produit[:35]}",
                 font=FONTS["subhead"], bg=COLORS["primary"], fg="white").pack(expand=True)
        body = tk.Frame(self, bg=COLORS["bg_card"], padx=20, pady=16)
        body.pack(fill="both", expand=True)
        img, method = _generate_barcode_image(code, width_px=280, height_px=90)
        if img:
            lbl = tk.Label(body, image=img, bg="white",
                           highlightbackground=COLORS["border"], highlightthickness=1)
            lbl.image = img
            lbl.pack(pady=(0, 10))
        else:
            tk.Label(body,
                     text=f"⚠️  Aperçu non disponible\n({method})\npip install python-barcode pillow",
                     font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                     justify="center").pack(pady=(0, 10))
        tk.Label(body, text=code, font=FONTS["mono"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dark"]).pack()
        tk.Button(body, text="Fermer", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=20, pady=7, cursor="hand2").pack(pady=(12, 0))


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES CODE-BARRES
# ══════════════════════════════════════════════════════════════════════════════

def _generate_barcode_image(code: str, width_px=220, height_px=80):
    if not code:
        return None, "Code vide"
    try:
        import barcode
        from barcode.writer import ImageWriter
        import io
        from PIL import Image as PilImage, ImageTk
        if len(code) == 13 and code.isdigit():
            bc_class = barcode.get_barcode_class("ean13")
        elif len(code) == 12 and code.isdigit():
            bc_class = barcode.get_barcode_class("upca")
        elif len(code) == 8 and code.isdigit():
            bc_class = barcode.get_barcode_class("ean8")
        else:
            bc_class = barcode.get_barcode_class("code128")
        writer = ImageWriter()
        bc = bc_class(code, writer=writer)
        buf = io.BytesIO()
        bc.write(buf, options={"module_height": 10, "module_width": 0.8,
                               "font_size": 7, "text_distance": 2,
                               "quiet_zone": 3, "write_text": True})
        buf.seek(0)
        img = PilImage.open(buf).resize((width_px, height_px), PilImage.LANCZOS)
        return ImageTk.PhotoImage(img), "python-barcode"
    except ImportError:
        pass
    except Exception:
        pass
    try:
        from PIL import Image as PilImage, ImageDraw, ImageFont, ImageTk
        img = PilImage.new("RGB", (width_px, height_px), "white")
        draw = ImageDraw.Draw(img)
        bits = _code128_bits(code)
        bar_w = max(1, (width_px - 20) // max(len(bits), 1))
        x, bar_h = 10, height_px - 18
        for bit in bits:
            draw.rectangle([x, 4, x + bar_w - 1, bar_h],
                           fill="black" if bit == "1" else "white")
            x += bar_w
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except Exception:
            font = ImageFont.load_default()
        text_w = draw.textlength(code, font=font)
        draw.text(((width_px - text_w) / 2, bar_h + 3), code, fill="black", font=font)
        return ImageTk.PhotoImage(img.resize((width_px, height_px), PilImage.LANCZOS)), "pillow"
    except Exception:
        pass
    return None, "Pillow non disponible"


def _code128_bits(data: str) -> str:
    START_B = "11010010000"
    STOP    = "1100011101011"
    patterns = [
        "11011001100","11001101100","11001100110","10010011000","10010001100",
        "10001001100","10011001000","10011000100","10001100100","11001001000",
        "11001000100","11000100100","10110011100","10011011100","10011001110",
        "10111001100","10011101100","10011100110","11001110010","11001011100",
        "11001001110","11011100100","11001110100","11101101110","11101001100",
        "11100101100","11100100110","11101100100","11100110100","11100110010",
        "11011011000","11011000110","11000110110","10100011000","10001011000",
        "10001000110","10110001000","10001101000","10001100010","11010001000",
        "11000101000","11000100010","10110111000","10110001110","10001101110",
        "10111011000","10111000110","10001110110","11101110110","11010001110",
        "11000101110","11011101000","11011100010","11011101110","11101011000",
        "11101000110","11100010110","11101101000","11101100010","11100011010",
        "11101111010","11001000010","11110001010","10100110000","10100001100",
        "10010110000","10010000110","10000101100","10000100110","10110010000",
        "10110000100","10011010000","10011000010","10000110100","10000110010",
        "11000010010","11001010000","11110111010","11000010100","10001111010",
        "10100111100","10010111100","10010011110","10111100100","10011110100",
        "10011110010","11110100100","11110010100","11110010010","11011011110",
        "11011110110","11110110110","10101111000","10100011110","10001011110",
        "10111101000","10111100010","11110101000","11110100010","10111011110",
        "10111101110","11101011110","11110101110","11010000100","11010010000",
    ]
    bits = START_B
    check = 104
    for i, char in enumerate(data):
        val = ord(char) - 32
        if 0 <= val < len(patterns):
            bits += patterns[val]
            check += (i + 1) * val
    check_val = check % 103
    if 0 <= check_val < len(patterns):
        bits += patterns[check_val]
    return bits + STOP


def _save_barcode_to_file(code: str, output_path: str) -> bool:
    if not code:
        return False
    try:
        import barcode
        from barcode.writer import ImageWriter
        if len(code) == 13 and code.isdigit():
            bc_class = barcode.get_barcode_class("ean13")
        elif len(code) == 8 and code.isdigit():
            bc_class = barcode.get_barcode_class("ean8")
        else:
            bc_class = barcode.get_barcode_class("code128")
        bc_class(code, writer=ImageWriter()).save(
            output_path.replace(".png", ""),
            options={"module_height": 15, "write_text": True})
        return True
    except ImportError:
        pass
    try:
        from PIL import Image as PilImage, ImageDraw, ImageFont
        img = PilImage.new("RGB", (400, 120), "white")
        draw = ImageDraw.Draw(img)
        bits = _code128_bits(code)
        bar_w = max(1, 360 // max(len(bits), 1))
        x = 20
        for bit in bits:
            draw.rectangle([x, 8, x + bar_w - 1, 95],
                           fill="black" if bit == "1" else "white")
            x += bar_w
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            font = ImageFont.load_default()
        draw.text((200, 98), code, fill="black", font=font, anchor="mt")
        img.save(output_path, "PNG")
        return True
    except Exception:
        return False


def _fmt(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"