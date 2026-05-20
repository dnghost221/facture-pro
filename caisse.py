"""
Module de gestion de la caisse — FacturePro
============================================
Fenêtre principale de caisse avec :
  - Ouverture / clôture de session journalière
  - Enregistrement des mouvements (entrées / sorties)
  - Comparaison montant théorique ↔ montant réel (comptage caisse)
  - Écart de caisse en fin de journée
  - Historique des sessions
  - Rapport de ventes par date (produit / quantité / montant)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta

import database as db

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
    "info":         "#0891b2",
    "text_dark":    "#111827",
    "text_medium":  "#374151",
    "text_light":   "#9ca3af",
    "border":       "#e5e7eb",
    "row_even":     "#f9fafb",
    "row_odd":      "#ffffff",
    "row_selected": "#dbeafe",
    "header_bg":    "#1a56db",
    "sidebar_bg":   "#1e3a5f",
    "entree_bg":    "#d1fae5",
    "sortie_bg":    "#fee2e2",
    "ecart_pos":    "#059669",
    "ecart_neg":    "#dc2626",
    "ecart_zero":   "#374151",
}
FONTS = {
    "title":     ("Segoe UI", 15, "bold"),
    "heading":   ("Segoe UI", 12, "bold"),
    "subhead":   ("Segoe UI", 10, "bold"),
    "body":      ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
    "mono":      ("Consolas", 11),
    "big":       ("Segoe UI", 22, "bold"),
    "medium":    ("Segoe UI", 14, "bold"),
}


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE PRINCIPALE CAISSE
# ══════════════════════════════════════════════════════════════════════════════

class CaisseWindow(tk.Toplevel):
    """Fenêtre de gestion de caisse avec onglets."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("💰 Gestion de Caisse")
        self.geometry("1050x680")
        self.minsize(900, 560)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"1050x680+{parent.winfo_x()+30}+{parent.winfo_y()+20}")

        self._session = db.get_session_ouverte()
        self._build()
        self._refresh()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        # En-tête
        header = tk.Frame(self, bg=COLORS["primary"], height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="💰  Gestion de Caisse",
                 font=FONTS["title"], bg=COLORS["primary"], fg="white"
                 ).pack(side="left", padx=20, pady=12)
        self.lbl_statut_header = tk.Label(
            header, text="",
            font=FONTS["body_bold"], bg=COLORS["primary"], fg="#fde68a"
        )
        self.lbl_statut_header.pack(side="right", padx=20)

        # Notebook
        style = ttk.Style()
        style.configure("Caisse.TNotebook", background=COLORS["bg_main"], borderwidth=0)
        style.configure("Caisse.TNotebook.Tab",
                        font=FONTS["body_bold"], padding=[16, 7])
        style.map("Caisse.TNotebook.Tab",
                  background=[("selected", COLORS["primary"]),
                               ("!selected", COLORS["bg_card"])],
                  foreground=[("selected", "white"),
                               ("!selected", COLORS["text_dark"])])

        self.nb = ttk.Notebook(self, style="Caisse.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=10)

        self._build_tab_session()
        self._build_tab_mouvements()
        self._build_tab_historique()
        self._build_tab_rapport()

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 1 : SESSION EN COURS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_session(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_main"])
        self.nb.add(outer, text="📊  Session en cours")

        # Panneau principal : 2 colonnes
        pane = tk.Frame(outer, bg=COLORS["bg_main"])
        pane.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Colonne gauche : statut + solde ──────────────────────────────────
        left = tk.Frame(pane, bg=COLORS["bg_main"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Carte statut
        self.card_statut = self._card(left, "📋  Statut de la session")

        self.lbl_statut = tk.Label(self.card_statut, text="",
                                   font=FONTS["medium"], bg=COLORS["bg_card"])
        self.lbl_statut.pack(pady=(8, 4))

        self.lbl_ouverture = tk.Label(self.card_statut, text="",
                                      font=FONTS["small"], bg=COLORS["bg_card"],
                                      fg=COLORS["text_light"])
        self.lbl_ouverture.pack()

        self.lbl_fond = tk.Label(self.card_statut, text="",
                                 font=FONTS["body"], bg=COLORS["bg_card"],
                                 fg=COLORS["text_medium"])
        self.lbl_fond.pack(pady=(4, 12))

        # Boutons session
        btn_frame = tk.Frame(self.card_statut, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", pady=(0, 10))

        self.btn_ouvrir = tk.Button(
            btn_frame, text="🔓  Ouvrir la caisse",
            command=self._ouvrir_session,
            font=FONTS["body_bold"], bg=COLORS["accent"], fg="white",
            activebackground="#059669", relief="flat", bd=0,
            padx=20, pady=10, cursor="hand2"
        )
        self.btn_ouvrir.pack(side="left", padx=(0, 8))

        self.btn_cloturer = tk.Button(
            btn_frame, text="🔒  Clôturer la journée",
            command=self._cloturer_session,
            font=FONTS["body_bold"], bg=COLORS["danger"], fg="white",
            activebackground="#b91c1c", relief="flat", bd=0,
            padx=20, pady=10, cursor="hand2"
        )
        self.btn_cloturer.pack(side="left")

        # Carte solde
        card_solde = self._card(left, "💵  Solde théorique en caisse")
        self.lbl_solde = tk.Label(card_solde, text="0,00 FCFA",
                                  font=FONTS["big"], bg=COLORS["bg_card"],
                                  fg=COLORS["primary"])
        self.lbl_solde.pack(pady=20)

        self.lbl_nb_ventes = tk.Label(card_solde, text="",
                                      font=FONTS["small"], bg=COLORS["bg_card"],
                                      fg=COLORS["text_light"])
        self.lbl_nb_ventes.pack(pady=(0, 12))

        # ── Colonne droite : comptage caisse ─────────────────────────────────
        right = tk.Frame(pane, bg=COLORS["bg_main"], width=340)
        right.pack(side="left", fill="both", expand=False)
        right.pack_propagate(False)

        card_comptage = self._card(right, "🧮  Comptage caisse physique")

        tk.Label(card_comptage,
                 text="Saisissez le montant compté physiquement\npour calculer l'écart :",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"], justify="center"
                 ).pack(pady=(6, 8))

        self.var_montant_reel = tk.StringVar(value="0")
        entry_reel = tk.Entry(
            card_comptage, textvariable=self.var_montant_reel,
            font=("Segoe UI", 18, "bold"), width=14,
            relief="flat", bd=0, justify="center",
            bg=COLORS["bg_main"], fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=2,
            highlightcolor=COLORS["primary"],
        )
        entry_reel.pack(ipady=10, pady=(0, 4))
        tk.Label(card_comptage, text="FCFA", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack()

        tk.Button(
            card_comptage, text="🧮  Calculer l'écart",
            command=self._calculer_ecart,
            font=FONTS["body_bold"], bg=COLORS["info"], fg="white",
            activebackground="#0e7490", relief="flat", bd=0,
            padx=16, pady=8, cursor="hand2"
        ).pack(pady=(10, 8))

        # Résultat écart
        self.frame_ecart = tk.Frame(card_comptage, bg=COLORS["bg_card"])
        self.frame_ecart.pack(fill="x", padx=10, pady=(0, 12))

        self.lbl_theorique_comptage = tk.Label(
            self.frame_ecart, text="", font=FONTS["small"],
            bg=COLORS["bg_card"], fg=COLORS["text_medium"])
        self.lbl_theorique_comptage.pack()

        self.lbl_ecart_val = tk.Label(
            self.frame_ecart, text="", font=FONTS["medium"],
            bg=COLORS["bg_card"])
        self.lbl_ecart_val.pack(pady=4)

        self.lbl_ecart_msg = tk.Label(
            self.frame_ecart, text="", font=FONTS["small"],
            bg=COLORS["bg_card"], wraplength=280, justify="center")
        self.lbl_ecart_msg.pack()

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 2 : MOUVEMENTS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_mouvements(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_main"])
        self.nb.add(outer, text="↕️  Mouvements")

        # Formulaire saisie mouvement
        form = tk.Frame(outer, bg=COLORS["bg_card"],
                        highlightbackground=COLORS["border"], highlightthickness=1)
        form.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(form, text="Nouveau mouvement :",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["primary"]).pack(side="left", padx=(12, 8), pady=10)

        # Type
        self.var_type_mouv = tk.StringVar(value="entree")
        for val, txt, color in [("entree", "➕ Entrée", COLORS["accent"]),
                                  ("sortie", "➖ Sortie", COLORS["danger"])]:
            tk.Radiobutton(
                form, text=txt, variable=self.var_type_mouv, value=val,
                font=FONTS["body_bold"], bg=COLORS["bg_card"],
                fg=color, activebackground=COLORS["bg_card"],
                selectcolor=COLORS["bg_card"], relief="flat",
                cursor="hand2"
            ).pack(side="left", padx=6, pady=10)

        tk.Frame(form, bg=COLORS["border"], width=1).pack(side="left", fill="y", pady=6)

        # Libellé
        tk.Label(form, text="Libellé :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(side="left", padx=(10, 4))
        self.var_libelle_mouv = tk.StringVar()
        tk.Entry(form, textvariable=self.var_libelle_mouv,
                 font=FONTS["body"], width=22, relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(side="left", ipady=5, pady=8)

        # Montant
        tk.Label(form, text="Montant (FCFA) :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(side="left", padx=(10, 4))
        self.var_montant_mouv = tk.StringVar()
        tk.Entry(form, textvariable=self.var_montant_mouv,
                 font=FONTS["body"], width=12, relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(side="left", ipady=5, pady=8)

        tk.Button(form, text="Valider",
                  command=self._saisir_mouvement,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2"
                  ).pack(side="left", padx=(10, 12), pady=8)

        # Tableau mouvements
        tf = tk.Frame(outer, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=10, pady=8)

        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Mouv.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=34, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Mouv.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Mouv.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree_mouv = ttk.Treeview(
            tf,
            columns=("heure", "type", "libelle", "montant", "cumul"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Mouv.Treeview",
        )
        scrolly.config(command=self.tree_mouv.yview)

        for cid, lbl, w, anc in [
            ("heure",   "Heure",          90, "center"),
            ("type",    "Type",           90, "center"),
            ("libelle", "Libellé",       360, "w"),
            ("montant", "Montant",       130, "e"),
            ("cumul",   "Solde cumulé",  130, "e"),
        ]:
            self.tree_mouv.heading(cid, text=lbl)
            self.tree_mouv.column(cid, width=w, anchor=anc, minwidth=60)

        self.tree_mouv.pack(side="left", fill="both", expand=True)
        self.tree_mouv.tag_configure("entree",  background=COLORS["entree_bg"])
        self.tree_mouv.tag_configure("sortie",  background=COLORS["sortie_bg"])
        self.tree_mouv.tag_configure("vente",   background="#eff6ff")

        # Barre résumé
        resume_bar = tk.Frame(outer, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        resume_bar.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_total_entrees = tk.Label(resume_bar, text="Entrées : —",
                                          font=FONTS["body_bold"],
                                          bg=COLORS["bg_card"], fg=COLORS["accent"])
        self.lbl_total_entrees.pack(side="left", padx=16, pady=8)

        self.lbl_total_sorties = tk.Label(resume_bar, text="Sorties : —",
                                          font=FONTS["body_bold"],
                                          bg=COLORS["bg_card"], fg=COLORS["danger"])
        self.lbl_total_sorties.pack(side="left", padx=16)

        self.lbl_solde_mouv = tk.Label(resume_bar, text="Solde : —",
                                       font=FONTS["body_bold"],
                                       bg=COLORS["bg_card"], fg=COLORS["primary"])
        self.lbl_solde_mouv.pack(side="right", padx=16)

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 3 : HISTORIQUE DES SESSIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_historique(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_main"])
        self.nb.add(outer, text="📋  Historique sessions")

        tf = tk.Frame(outer, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=10, pady=10)

        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Hist.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=36, fieldbackground=COLORS["bg_card"],
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
            tf,
            columns=("id", "ouverture", "cloture", "fond",
                     "theorique", "reel", "ecart", "statut"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Hist.Treeview",
        )
        scrolly.config(command=self.tree_hist.yview)

        for cid, lbl, w, anc in [
            ("id",        "N°",           40, "center"),
            ("ouverture", "Ouverture",   150, "center"),
            ("cloture",   "Clôture",     150, "center"),
            ("fond",      "Fond",        110, "e"),
            ("theorique", "Théorique",   120, "e"),
            ("reel",      "Réel compté", 120, "e"),
            ("ecart",     "Écart",       110, "e"),
            ("statut",    "Statut",       90, "center"),
        ]:
            self.tree_hist.heading(cid, text=lbl)
            self.tree_hist.column(cid, width=w, anchor=anc, minwidth=40)

        self.tree_hist.pack(side="left", fill="both", expand=True)
        self.tree_hist.tag_configure("ouverte",   foreground=COLORS["accent"])
        self.tree_hist.tag_configure("cloturee",  foreground=COLORS["text_dark"])
        self.tree_hist.tag_configure("ecart_neg", foreground=COLORS["danger"])
        self.tree_hist.tag_configure("ecart_pos", foreground=COLORS["ecart_pos"])

        # Bouton voir mouvements d'une session
        action_bar = tk.Frame(outer, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(action_bar, text="🔍  Voir les mouvements de cette session",
                  command=self._voir_mouvements_session,
                  font=FONTS["body_bold"], bg=COLORS["info"], fg="white",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="left", padx=8, pady=8)
        tk.Button(action_bar, text="🔄  Actualiser",
                  command=self._charger_historique,
                  font=FONTS["body_bold"], bg="#6b7280", fg="white",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="left", padx=(0, 8))

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 4 : RAPPORT DE VENTES
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_rapport(self):
        outer = tk.Frame(self.nb, bg=COLORS["bg_main"])
        self.nb.add(outer, text="📈  Rapport de ventes")

        # Sélecteur de date
        top = tk.Frame(outer, bg=COLORS["bg_card"],
                       highlightbackground=COLORS["border"], highlightthickness=1)
        top.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(top, text="📅  Date :", font=FONTS["body_bold"],
                 bg=COLORS["bg_card"], fg=COLORS["primary"]
                 ).pack(side="left", padx=(14, 6), pady=10)

        today = datetime.now()
        self.var_rapport_jour  = tk.StringVar(value=str(today.day))
        self.var_rapport_mois  = tk.StringVar(value=str(today.month))
        self.var_rapport_annee = tk.StringVar(value=str(today.year))

        for var, vals, w in [
            (self.var_rapport_jour,
             [str(i) for i in range(1, 32)], 5),
            (self.var_rapport_mois,
             [str(i) for i in range(1, 13)], 5),
            (self.var_rapport_annee,
             [str(y) for y in range(today.year - 3, today.year + 2)], 7),
        ]:
            ttk.Combobox(top, textvariable=var, values=vals,
                         state="readonly", font=FONTS["body"], width=w
                         ).pack(side="left", padx=3, pady=10)

        for label, delta in [("Aujourd'hui", 0), ("Hier", -1), ("Avant-hier", -2)]:
            d = date.today() + timedelta(days=delta)
            tk.Button(
                top, text=label,
                command=lambda d=d: self._set_date_rapport(d),
                font=FONTS["small"], bg=COLORS["primary_light"],
                fg=COLORS["primary"], relief="flat", bd=0,
                padx=8, pady=4, cursor="hand2"
            ).pack(side="left", padx=4)

        tk.Button(top, text="📊  Générer le rapport",
                  command=self._generer_rapport,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(side="right", padx=14, pady=8)

        # ── Résumé du rapport ─────────────────────────────────────────────────
        self.rapport_resume = tk.Frame(outer, bg=COLORS["bg_card"],
                                       highlightbackground=COLORS["border"],
                                       highlightthickness=1)
        self.rapport_resume.pack(fill="x", padx=10, pady=(8, 0))

        self.lbl_rapport_date = tk.Label(
            self.rapport_resume, text="Sélectionnez une date et cliquez sur « Générer »",
            font=FONTS["body"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        )
        self.lbl_rapport_date.pack(side="left", padx=14, pady=10)

        self.lbl_rapport_total = tk.Label(
            self.rapport_resume, text="",
            font=FONTS["medium"], bg=COLORS["bg_card"], fg=COLORS["primary"]
        )
        self.lbl_rapport_total.pack(side="right", padx=14)

        self.lbl_rapport_nb = tk.Label(
            self.rapport_resume, text="",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        )
        self.lbl_rapport_nb.pack(side="right", padx=8)

        # ── Tableau produits vendus ───────────────────────────────────────────
        pane = tk.Frame(outer, bg=COLORS["bg_main"])
        pane.pack(fill="both", expand=True, padx=10, pady=8)

        # Tableau produits (gauche)
        left = tk.Frame(pane, bg=COLORS["bg_main"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(left, text="Produits vendus",
                 font=FONTS["subhead"], bg=COLORS["bg_main"],
                 fg=COLORS["primary"]).pack(anchor="w", pady=(0, 4))

        tf_prod = tk.Frame(left, bg=COLORS["bg_main"])
        tf_prod.pack(fill="both", expand=True)
        scrolly_p = ttk.Scrollbar(tf_prod, orient="vertical")
        scrolly_p.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Prod.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=32, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Prod.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Prod.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree_produits = ttk.Treeview(
            tf_prod,
            columns=("designation", "quantite", "prix_moyen", "montant", "pct"),
            show="headings",
            yscrollcommand=scrolly_p.set,
            selectmode="browse",
            style="Prod.Treeview",
        )
        scrolly_p.config(command=self.tree_produits.yview)

        for cid, lbl, w, anc in [
            ("designation", "Article",       260, "w"),
            ("quantite",    "Qté vendue",    100, "center"),
            ("prix_moyen",  "Prix moyen",    120, "e"),
            ("montant",     "Montant total", 130, "e"),
            ("pct",         "% CA",           70, "center"),
        ]:
            self.tree_produits.heading(cid, text=lbl)
            self.tree_produits.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree_produits.pack(side="left", fill="both", expand=True)
        self.tree_produits.tag_configure("even", background=COLORS["row_even"])
        self.tree_produits.tag_configure("odd",  background=COLORS["row_odd"])
        self.tree_produits.tag_configure("top",  background="#fef3c7")

        # Tableau factures (droite)
        right = tk.Frame(pane, bg=COLORS["bg_main"], width=300)
        right.pack(side="left", fill="both", expand=False)
        right.pack_propagate(False)

        tk.Label(right, text="Factures du jour",
                 font=FONTS["subhead"], bg=COLORS["bg_main"],
                 fg=COLORS["primary"]).pack(anchor="w", pady=(0, 4))

        tf_fac = tk.Frame(right, bg=COLORS["bg_main"])
        tf_fac.pack(fill="both", expand=True)
        scrolly_f = ttk.Scrollbar(tf_fac, orient="vertical")
        scrolly_f.pack(side="right", fill="y")

        self.tree_factures_rapport = ttk.Treeview(
            tf_fac,
            columns=("numero", "client", "total"),
            show="headings",
            yscrollcommand=scrolly_f.set,
            selectmode="browse",
            style="Prod.Treeview",
        )
        scrolly_f.config(command=self.tree_factures_rapport.yview)

        for cid, lbl, w, anc in [
            ("numero", "N° Facture", 130, "w"),
            ("client", "Client",     100, "w"),
            ("total",  "Total",       90, "e"),
        ]:
            self.tree_factures_rapport.heading(cid, text=lbl)
            self.tree_factures_rapport.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree_factures_rapport.pack(side="left", fill="both", expand=True)
        self.tree_factures_rapport.tag_configure("even", background=COLORS["row_even"])
        self.tree_factures_rapport.tag_configure("odd",  background=COLORS["row_odd"])

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — SESSION
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh(self):
        """Rafraîchit toute l'interface selon l'état de la session."""
        self._session = db.get_session_ouverte()
        self._refresh_session()
        self._charger_mouvements()
        self._charger_historique()

    def _refresh_session(self):
        s = self._session
        if s:
            self.lbl_statut.config(text="🟢  CAISSE OUVERTE", fg=COLORS["accent"])
            self.lbl_statut_header.config(text="🟢 Caisse ouverte")
            self.lbl_ouverture.config(
                text=f"Ouverte le {s['date_ouverture'][:16]}")
            self.lbl_fond.config(
                text=f"Fond de caisse : {_fmt(s['montant_ouverture'])} FCFA")
            self.btn_ouvrir.config(state="disabled")
            self.btn_cloturer.config(state="normal")

            solde = db.get_solde_caisse(s["id"])
            self.lbl_solde.config(text=f"{_fmt(solde)} FCFA")

            # Compter ventes du jour
            mouvs = db.get_mouvements_caisse(s["id"])
            ventes = [m for m in mouvs if "Vente" in m.get("libelle", "")]
            self.lbl_nb_ventes.config(
                text=f"{len(ventes)} vente(s) enregistrée(s) dans cette session")
        else:
            self.lbl_statut.config(text="🔴  CAISSE FERMÉE", fg=COLORS["danger"])
            self.lbl_statut_header.config(text="🔴 Caisse fermée")
            self.lbl_ouverture.config(text="Aucune session ouverte")
            self.lbl_fond.config(text="")
            self.btn_ouvrir.config(state="normal")
            self.btn_cloturer.config(state="disabled")
            self.lbl_solde.config(text="—")
            self.lbl_nb_ventes.config(text="")

    def _ouvrir_session(self):
        dlg = _OuvertureDialog(self)
        if dlg.result is not None:
            fond, note = dlg.result
            db.ouvrir_session_caisse(fond, note)
            self._refresh()
            messagebox.showinfo("✅ Caisse ouverte",
                                f"Session ouverte avec un fond de {_fmt(fond)} FCFA.",
                                parent=self)

    def _cloturer_session(self):
        s = self._session
        if not s:
            return
        solde_th = db.get_solde_caisse(s["id"])
        dlg = _CloturDialog(self, solde_th)
        if dlg.result is not None:
            montant_reel, note = dlg.result
            res = db.cloturer_session_caisse(s["id"], montant_reel, note)
            ecart = res["ecart"]
            ecart_str = f"{'+' if ecart >= 0 else ''}{_fmt(ecart)} FCFA"
            couleur = COLORS["ecart_pos"] if ecart >= 0 else COLORS["ecart_neg"]
            msg = (
                f"Session clôturée.\n\n"
                f"Montant théorique : {_fmt(res['theorique'])} FCFA\n"
                f"Montant compté    : {_fmt(montant_reel)} FCFA\n"
                f"Écart             : {ecart_str}"
            )
            messagebox.showinfo("🔒 Caisse clôturée", msg, parent=self)
            self._refresh()

    def _calculer_ecart(self):
        s = self._session
        if not s:
            messagebox.showwarning("Caisse fermée",
                                   "Ouvrez d'abord une session de caisse.", parent=self)
            return
        try:
            montant_reel = float(
                self.var_montant_reel.get().strip().replace(",", ".").replace(" ", "")
            )
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide.", parent=self)
            return

        theorique = db.get_solde_caisse(s["id"])
        ecart = montant_reel - theorique

        self.lbl_theorique_comptage.config(
            text=f"Théorique : {_fmt(theorique)} FCFA"
        )
        if ecart == 0:
            self.lbl_ecart_val.config(
                text="Écart : 0,00 FCFA", fg=COLORS["ecart_zero"])
            self.lbl_ecart_msg.config(
                text="✅ Caisse parfaitement équilibrée.", fg=COLORS["ecart_zero"])
        elif ecart > 0:
            self.lbl_ecart_val.config(
                text=f"Écart : +{_fmt(ecart)} FCFA", fg=COLORS["ecart_pos"])
            self.lbl_ecart_msg.config(
                text="⬆️ Excédent en caisse.", fg=COLORS["ecart_pos"])
        else:
            self.lbl_ecart_val.config(
                text=f"Écart : {_fmt(ecart)} FCFA", fg=COLORS["ecart_neg"])
            self.lbl_ecart_msg.config(
                text="⬇️ Manque en caisse.", fg=COLORS["ecart_neg"])

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — MOUVEMENTS
    # ══════════════════════════════════════════════════════════════════════════

    def _saisir_mouvement(self):
        s = self._session
        if not s:
            messagebox.showwarning("Caisse fermée",
                                   "Ouvrez d'abord une session de caisse.", parent=self)
            return
        libelle = self.var_libelle_mouv.get().strip()
        if not libelle:
            messagebox.showerror("Erreur", "Le libellé est obligatoire.", parent=self)
            return
        try:
            montant = float(
                self.var_montant_mouv.get().strip().replace(",", ".").replace(" ", "")
            )
            if montant <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide (doit être > 0).", parent=self)
            return

        type_m = self.var_type_mouv.get()
        db.ajouter_mouvement_caisse(s["id"], type_m, montant, libelle)
        self.var_libelle_mouv.set("")
        self.var_montant_mouv.set("")
        self._charger_mouvements()
        self._refresh_session()

    def _charger_mouvements(self):
        for item in self.tree_mouv.get_children():
            self.tree_mouv.delete(item)

        s = self._session
        if not s:
            self.lbl_total_entrees.config(text="Entrées : —")
            self.lbl_total_sorties.config(text="Sorties : —")
            self.lbl_solde_mouv.config(text="Solde : —")
            return

        mouvs   = db.get_mouvements_caisse(s["id"])
        cumul   = 0.0
        total_e = 0.0
        total_s = 0.0

        for m in mouvs:
            t = m["type_mouvement"]
            if t == "entree":
                cumul   += m["montant"]
                total_e += m["montant"]
                tag      = "entree"
                signe    = f"+{_fmt(m['montant'])}"
            else:
                cumul   -= m["montant"]
                total_s += m["montant"]
                tag      = "sortie"
                signe    = f"-{_fmt(m['montant'])}"

            heure = m["created_at"][11:16] if len(m["created_at"]) >= 16 else m["created_at"]
            self.tree_mouv.insert("", "end",
                values=(
                    heure,
                    "➕ Entrée" if t == "entree" else "➖ Sortie",
                    m.get("libelle", ""),
                    f"{signe} FCFA",
                    f"{_fmt(cumul)} FCFA",
                ),
                tags=(tag,))

        self.lbl_total_entrees.config(text=f"Entrées : {_fmt(total_e)} FCFA")
        self.lbl_total_sorties.config(text=f"Sorties : {_fmt(total_s)} FCFA")
        self.lbl_solde_mouv.config(text=f"Solde : {_fmt(cumul)} FCFA")

        # Scroll en bas
        children = self.tree_mouv.get_children()
        if children:
            self.tree_mouv.see(children[-1])

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════

    def _charger_historique(self):
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)

        sessions = db.get_all_sessions_caisse()
        for s in sessions:
            statut   = s["statut"]
            ecart    = s.get("ecart")
            theorique = s.get("montant_cloture_theorique")
            reel      = s.get("montant_cloture_reel")

            ecart_str    = f"{'+' if ecart and ecart >= 0 else ''}{_fmt(ecart)}" if ecart is not None else "—"
            theorique_str = _fmt(theorique) + " FCFA" if theorique is not None else "—"
            reel_str      = _fmt(reel) + " FCFA" if reel is not None else "—"

            tag = "ouverte" if statut == "ouverte" else (
                "ecart_neg" if ecart and ecart < 0 else "cloturee"
            )

            self.tree_hist.insert("", "end", iid=str(s["id"]),
                values=(
                    s["id"],
                    s["date_ouverture"][:16],
                    s.get("date_cloture", "—")[:16] if s.get("date_cloture") else "—",
                    f"{_fmt(s['montant_ouverture'])} FCFA",
                    theorique_str,
                    reel_str,
                    f"{ecart_str} FCFA" if ecart is not None else "—",
                    "🟢 Ouverte" if statut == "ouverte" else "🔒 Clôturée",
                ),
                tags=(tag,))

    def _voir_mouvements_session(self):
        sel = self.tree_hist.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Sélectionnez une session dans le tableau.", parent=self)
            return
        sid = int(sel[0])
        _MouvementsSessionWindow(self, sid)

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — RAPPORT
    # ══════════════════════════════════════════════════════════════════════════

    def _set_date_rapport(self, d: date):
        self.var_rapport_jour.set(str(d.day))
        self.var_rapport_mois.set(str(d.month))
        self.var_rapport_annee.set(str(d.year))

    def _generer_rapport(self):
        try:
            j = int(self.var_rapport_jour.get())
            m = int(self.var_rapport_mois.get())
            a = int(self.var_rapport_annee.get())
            date_str = f"{j:02d}/{m:02d}/{a}"
        except ValueError:
            messagebox.showerror("Erreur", "Date invalide.", parent=self)
            return

        rapport = db.get_rapport_ventes_jour(date_str)

        # Résumé
        self.lbl_rapport_date.config(
            text=f"📅  Rapport du {rapport['date']}",
            fg=COLORS["primary"]
        )
        self.lbl_rapport_nb.config(
            text=f"{rapport['nb_factures']} facture(s)")
        self.lbl_rapport_total.config(
            text=f"Total : {_fmt(rapport['total_jour'])} FCFA")

        # Tableau produits
        for item in self.tree_produits.get_children():
            self.tree_produits.delete(item)

        produits = rapport["produits"]
        total = rapport["total_jour"] or 1

        for i, p in enumerate(produits):
            pct = (p["montant_total"] / total * 100) if total > 0 else 0
            tag = "top" if i == 0 else ("even" if i % 2 == 0 else "odd")
            self.tree_produits.insert("", "end",
                values=(
                    p["designation"],
                    f"{p['quantite_totale']:g}",
                    f"{_fmt(p['prix_moyen'])} FCFA",
                    f"{_fmt(p['montant_total'])} FCFA",
                    f"{pct:.1f}%",
                ),
                tags=(tag,))

        # Ligne total
        if produits:
            self.tree_produits.insert("", "end",
                values=("TOTAL", "", "",
                        f"{_fmt(rapport['total_jour'])} FCFA", "100%"),
                tags=("top",))

        # Tableau factures
        for item in self.tree_factures_rapport.get_children():
            self.tree_factures_rapport.delete(item)

        for i, f in enumerate(rapport["factures"]):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree_factures_rapport.insert("", "end",
                values=(
                    f["numero_facture"],
                    f["client"][:18],
                    f"{_fmt(f['total'])} FCFA",
                ),
                tags=(tag,))

        if not rapport["factures"]:
            self.lbl_rapport_date.config(
                text=f"📅  Aucune vente le {rapport['date']}",
                fg=COLORS["text_light"]
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _card(self, parent, title):
        frame = tk.Frame(parent, bg=COLORS["bg_card"],
                         highlightbackground=COLORS["border"], highlightthickness=1)
        frame.pack(fill="x", pady=(0, 8))
        title_bar = tk.Frame(frame, bg=COLORS["primary_light"])
        title_bar.pack(fill="x")
        tk.Label(title_bar, text=title, font=FONTS["subhead"],
                 bg=COLORS["primary_light"], fg=COLORS["primary"]
                 ).pack(side="left", padx=12, pady=6)
        content = tk.Frame(frame, bg=COLORS["bg_card"])
        content.pack(fill="both", expand=True, padx=14, pady=6)
        return content


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUE : OUVERTURE DE SESSION
# ══════════════════════════════════════════════════════════════════════════════

class _OuvertureDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🔓 Ouverture de caisse")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self.geometry(f"420x300+{parent.winfo_x()+200}+{parent.winfo_y()+150}")
        self._build()
        self.wait_window(self)

    def _build(self):
        header = tk.Frame(self, bg=COLORS["accent"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔓  Ouverture de caisse",
                 font=FONTS["heading"], bg=COLORS["accent"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=24, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="Fond de caisse initial (FCFA) *",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dark"]).pack(anchor="w")
        self.var_fond = tk.StringVar(value="0")
        entry = tk.Entry(body, textvariable=self.var_fond,
                         font=("Segoe UI", 16, "bold"), width=16,
                         relief="flat", bd=0, justify="center",
                         bg=COLORS["bg_main"], fg=COLORS["primary"],
                         highlightbackground=COLORS["border"], highlightthickness=2,
                         highlightcolor=COLORS["accent"])
        entry.pack(ipady=8, pady=(4, 12))
        entry.select_range(0, tk.END)
        entry.focus()

        tk.Label(body, text="Note (optionnel)",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w")
        self.var_note = tk.StringVar()
        tk.Entry(body, textvariable=self.var_note, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=5, pady=(2, 14))

        btns = tk.Frame(body, bg=COLORS["bg_card"])
        btns.pack(fill="x")
        tk.Button(btns, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="✔  Ouvrir la caisse", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["accent"], fg="white",
                  activebackground="#059669",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")
        self.bind("<Return>", lambda _: self._validate())
        self.bind("<Escape>", lambda _: self.destroy())

    def _validate(self):
        try:
            fond = float(self.var_fond.get().strip().replace(",", ".").replace(" ", ""))
            if fond < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide.", parent=self)
            return
        self.result = (fond, self.var_note.get().strip())
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGUE : CLÔTURE DE SESSION
# ══════════════════════════════════════════════════════════════════════════════

class _CloturDialog(tk.Toplevel):
    def __init__(self, parent, solde_theorique: float):
        super().__init__(parent)
        self.title("🔒 Clôture de caisse")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.result = None
        self._theorique = solde_theorique
        self.geometry(f"440x350+{parent.winfo_x()+180}+{parent.winfo_y()+130}")
        self._build()
        self.wait_window(self)

    def _build(self):
        header = tk.Frame(self, bg=COLORS["danger"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔒  Clôture de caisse",
                 font=FONTS["heading"], bg=COLORS["danger"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w", pady=(0, 6))

        # Montant théorique
        th_frame = tk.Frame(body, bg=COLORS["primary_light"],
                            highlightbackground=COLORS["primary"], highlightthickness=1)
        th_frame.pack(fill="x", pady=(0, 12))
        tk.Label(th_frame,
                 text=f"Montant théorique en caisse : {_fmt(self._theorique)} FCFA",
                 font=FONTS["body_bold"], bg=COLORS["primary_light"],
                 fg=COLORS["primary"]).pack(padx=12, pady=8)

        tk.Label(body, text="Montant compté physiquement (FCFA) *",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dark"]).pack(anchor="w")
        self.var_reel = tk.StringVar(value=str(int(self._theorique)))
        entry = tk.Entry(body, textvariable=self.var_reel,
                         font=("Segoe UI", 16, "bold"), width=16,
                         relief="flat", bd=0, justify="center",
                         bg=COLORS["bg_main"], fg=COLORS["primary"],
                         highlightbackground=COLORS["border"], highlightthickness=2,
                         highlightcolor=COLORS["danger"])
        entry.pack(ipady=8, pady=(4, 10))
        entry.select_range(0, tk.END)
        entry.focus()

        tk.Label(body, text="Note de clôture (optionnel)",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w")
        self.var_note = tk.StringVar()
        tk.Entry(body, textvariable=self.var_note, font=FONTS["body"],
                 relief="flat", bd=0, bg=COLORS["bg_main"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 ).pack(fill="x", ipady=5, pady=(2, 14))

        btns = tk.Frame(body, bg=COLORS["bg_card"])
        btns.pack(fill="x")
        tk.Button(btns, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="🔒  Clôturer", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["danger"], fg="white",
                  activebackground="#b91c1c",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")
        self.bind("<Return>", lambda _: self._validate())
        self.bind("<Escape>", lambda _: self.destroy())

    def _validate(self):
        try:
            reel = float(self.var_reel.get().strip().replace(",", ".").replace(" ", ""))
            if reel < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide.", parent=self)
            return
        self.result = (reel, self.var_note.get().strip())
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE : MOUVEMENTS D'UNE SESSION HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════

class _MouvementsSessionWindow(tk.Toplevel):
    def __init__(self, parent, caisse_id: int):
        super().__init__(parent)
        self.title(f"Mouvements — Session #{caisse_id}")
        self.geometry("720x480")
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"720x480+{parent.winfo_x()+100}+{parent.winfo_y()+80}")
        self._build(caisse_id)

    def _build(self, caisse_id):
        header = tk.Frame(self, bg=COLORS["primary"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"📋  Mouvements de la session #{caisse_id}",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white").pack(expand=True)

        tf = tk.Frame(self, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=12, pady=10)
        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("MH.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=30, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("MH.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("MH.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        tree = ttk.Treeview(tf,
            columns=("datetime", "type", "libelle", "montant", "cumul"),
            show="headings", yscrollcommand=scrolly.set,
            selectmode="browse", style="MH.Treeview",
        )
        scrolly.config(command=tree.yview)

        for cid, lbl, w, anc in [
            ("datetime", "Date / Heure",  140, "center"),
            ("type",     "Type",           90, "center"),
            ("libelle",  "Libellé",       310, "w"),
            ("montant",  "Montant",       120, "e"),
            ("cumul",    "Solde cumulé",  120, "e"),
        ]:
            tree.heading(cid, text=lbl)
            tree.column(cid, width=w, anchor=anc, minwidth=50)

        tree.pack(side="left", fill="both", expand=True)
        tree.tag_configure("entree", background=COLORS["entree_bg"])
        tree.tag_configure("sortie", background=COLORS["sortie_bg"])

        mouvs = db.get_mouvements_caisse(caisse_id)
        cumul = 0.0
        total_e = total_s = 0.0
        for m in mouvs:
            t = m["type_mouvement"]
            if t == "entree":
                cumul   += m["montant"]
                total_e += m["montant"]
                signe    = f"+{_fmt(m['montant'])}"
            else:
                cumul   -= m["montant"]
                total_s += m["montant"]
                signe    = f"-{_fmt(m['montant'])}"
            dt = m["created_at"][:16] if len(m["created_at"]) >= 16 else m["created_at"]
            tree.insert("", "end",
                values=(dt, "➕ Entrée" if t == "entree" else "➖ Sortie",
                        m.get("libelle", ""),
                        f"{signe} FCFA",
                        f"{_fmt(cumul)} FCFA"),
                tags=(t,))

        # Résumé
        resume = tk.Frame(self, bg=COLORS["bg_card"],
                          highlightbackground=COLORS["border"], highlightthickness=1)
        resume.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(resume, text=f"Entrées : {_fmt(total_e)} FCFA",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["accent"]).pack(side="left", padx=14, pady=8)
        tk.Label(resume, text=f"Sorties : {_fmt(total_s)} FCFA",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["danger"]).pack(side="left", padx=14)
        tk.Label(resume, text=f"Solde : {_fmt(cumul)} FCFA",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["primary"]).pack(side="right", padx=14)
        tk.Button(resume, text="Fermer", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2"
                  ).pack(side="right", padx=8)


# ─── Utilitaire ───────────────────────────────────────────────────────────────

def _fmt(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"
