"""
Module de l'interface graphique principale
Interface moderne et professionnelle avec Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
import subprocess
import platform
from datetime import datetime

import database as db
from database import StockInsuffisantError
from print_utils import PrintDialog, imprimer_pdf
from stock import StockWindow
from licence import LicenceInfoWindow, get_expiry_warning
import pdf_generator as pdf_gen
from historique import HistoriqueWindow
from catalogue import CatalogueWindow, CataloguePickerDialog
from parametres import ParametresWindow
from caisse import CaisseWindow
from inventaire import InventaireWindow


# ─── Palette de couleurs ───────────────────────────────────────────────────────
COLORS = {
    "bg_main":      "#f8fafc",   # Fond principal gris très clair
    "bg_card":      "#ffffff",   # Fond des cartes blanc
    "bg_sidebar":   "#1e3a5f",   # Sidebar bleu foncé
    "primary":      "#1a56db",   # Bleu principal
    "primary_dark": "#0d3d91",   # Bleu foncé
    "primary_light":"#eff6ff",   # Bleu très clair
    "accent":       "#10b981",   # Vert pour succès
    "danger":       "#ef4444",   # Rouge pour supprimer
    "warning":      "#f59e0b",   # Orange avertissement
    "text_dark":    "#111827",   # Texte principal
    "text_medium":  "#374151",   # Texte secondaire
    "text_light":   "#9ca3af",   # Texte désactivé
    "border":       "#e5e7eb",   # Bordure grise
    "row_even":     "#f9fafb",   # Ligne paire du tableau
    "row_odd":      "#ffffff",   # Ligne impaire
    "row_selected": "#dbeafe",   # Ligne sélectionnée
    "header_bg":    "#1a56db",   # En-tête tableau
}

FONTS = {
    "title":    ("Segoe UI", 20, "bold"),
    "heading":  ("Segoe UI", 13, "bold"),
    "subhead":  ("Segoe UI", 11, "bold"),
    "body":     ("Segoe UI", 10),
    "body_bold":("Segoe UI", 10, "bold"),
    "small":    ("Segoe UI", 9),
    "mono":     ("Consolas", 10),
}


class FacturationApp(tk.Tk):
    """Application principale de facturation."""

    def __init__(self):
        super().__init__()
        self.title("Logiciel de Facturation Pro")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg=COLORS["bg_main"])
        self.resizable(True, True)

        # Centrer la fenêtre
        self._center_window()

        # Initialiser la base de données
        db.init_db()

        # Variables d'état
        self.produits = []       # Liste des lignes de produits
        self.pdf_path = None     # Chemin du dernier PDF généré

        # Construction de l'interface
        self._build_ui()

        # Charger le prochain numéro de facture
        self._load_next_invoice_number()
        self._set_today_date()
        self.after(100, self._charger_methodes_paiement)
        self.after(500, self._refresh_stock_badge)
        self.after(600, self._refresh_caisse_badge)
        self.after(800, self._check_licence_expiry)

    def _center_window(self):
        """Centre la fenêtre à l'écran."""
        self.update_idletasks()
        w, h = 1500, 900
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ──────────────────────────────────────────────────────────────────────────
    # CONSTRUCTION DE L'INTERFACE
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        """Construit l'interface principale."""
        # Barre de navigation supérieure
        self._build_topbar()

        # Corps principal (sidebar + contenu)
        body = tk.Frame(self, bg=COLORS["bg_main"])
        body.pack(fill="both", expand=True)

        # Sidebar gauche
        self._build_sidebar(body)

        # Zone de contenu principal
        self._build_main_content(body)

    def _build_topbar(self):
        """Construit la barre supérieure."""
        topbar = tk.Frame(self, bg=COLORS["bg_sidebar"], height=58)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        # Logo / Titre
        tk.Label(
            topbar, text="💼 FacturePro",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_sidebar"], fg="white",
        ).pack(side="left", padx=22, pady=12)

        # Info version
        tk.Label(
            topbar, text="v1.0 — Logiciel de Facturation",
            font=FONTS["small"],
            bg=COLORS["bg_sidebar"], fg="#94a3b8",
        ).pack(side="left", padx=4)

        # Boutons dans la topbar
        btn_frame = tk.Frame(topbar, bg=COLORS["bg_sidebar"])
        btn_frame.pack(side="right", padx=16)

        self._topbar_btn(btn_frame, "📋 Historique",   self._open_historique)
        self._topbar_btn(btn_frame, "📦 Catalogue",    self._open_catalogue)
        self._topbar_btn(btn_frame, "📦 Stock",        self._open_stock,      color="#059669")
        self._topbar_btn(btn_frame, "📋 Inventaire",   self._open_inventaire, color="#0891b2")
        self._topbar_btn(btn_frame, "💰 Caisse",       self._open_caisse,     color="#d97706")
        self._topbar_btn(btn_frame, "📊 Statistiques", self._show_stats)
        self._topbar_btn(btn_frame, "⚙️ Paramètres",   self._open_parametres)
        self._topbar_btn(btn_frame, "🔑 Licence",      self._open_licence,    color="#4b5563")

        # Badge alerte stock
        self.lbl_stock_alerte = tk.Label(
            topbar, text="",
            font=FONTS["small"], bg=COLORS["bg_sidebar"], fg="#fde68a"
        )
        self.lbl_stock_alerte.pack(side="right", padx=8)

        # Badge statut caisse
        self.lbl_caisse_statut = tk.Label(
            topbar, text="",
            font=FONTS["small"], bg=COLORS["bg_sidebar"], fg="#fde68a"
        )
        self.lbl_caisse_statut.pack(side="right", padx=4)

    def _topbar_btn(self, parent, text, command, color=None):
        btn = tk.Button(
            parent, text=text, command=command,
            font=FONTS["small"],
            bg=color or COLORS["primary"], fg="white",
            activebackground=COLORS["primary_dark"], activeforeground="white",
            relief="flat", bd=0,
            padx=14, pady=6, cursor="hand2"
        )
        btn.pack(side="right", padx=4, pady=10)
        return btn

    def _build_sidebar(self, parent):
        """Construit la sidebar gauche avec les actions."""
        sidebar = tk.Frame(parent, bg=COLORS["bg_sidebar"], width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Titre sidebar
        tk.Label(
            sidebar, text="ACTIONS",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_sidebar"], fg="#64748b",
        ).pack(pady=(20, 8), padx=16, anchor="w")

        # Boutons d'action principaux
        actions = [
            ("➕  Ajouter un produit",   self._ajouter_produit,   COLORS["primary"]),
            ("📦  Catalogue produits",   self._open_catalogue,    "#475569"),
            ("📦  Gestion du stock",     self._open_stock,        "#059669"),
            ("📋  Inventaire",           self._open_inventaire,   "#0891b2"),
            ("🗑  Supprimer produit",     self._supprimer_produit, "#374151"),
            ("🖨  Valider Ticket",        self._valider_ticket,    "#7c3aed"),
            ("📄  Valider Facture",       self._valider_facture,   COLORS["accent"]),
            
            ("🔄  Nouvelle vente",        self._nouvelle_facture,  COLORS["warning"]),
        ]

        self.sidebar_buttons = {}
        for label, cmd, color in actions:
            btn = tk.Button(
                sidebar, text=label, command=cmd,
                font=FONTS["body_bold"],
                bg=color, fg="white",
                activebackground=COLORS["primary_dark"], activeforeground="white",
                relief="flat", bd=0,
                width=22, pady=9, cursor="hand2", anchor="w", padx=12,
            )
            btn.pack(pady=4, padx=12, fill="x")
            self.sidebar_buttons[label] = btn

        # Séparateur
        ttk.Separator(sidebar, orient="horizontal").pack(
            fill="x", padx=12, pady=16
        )

        # Info numéro de facture dans la sidebar
        tk.Label(
            sidebar, text="Numéro de facture :",
            font=FONTS["small"], bg=COLORS["bg_sidebar"], fg="#94a3b8"
        ).pack(padx=16, anchor="w")

        self.lbl_num_sidebar = tk.Label(
            sidebar, text="...",
            font=("Consolas", 11, "bold"),
            bg=COLORS["bg_sidebar"], fg="white"
        )
        self.lbl_num_sidebar.pack(padx=16, pady=(2, 12), anchor="w")

        # Total sidebar
        tk.Label(
            sidebar, text="Total :",
            font=FONTS["small"], bg=COLORS["bg_sidebar"], fg="#94a3b8"
        ).pack(padx=16, anchor="w")

        self.lbl_total_sidebar = tk.Label(
            sidebar, text="0,00 FCFA",
            font=("Segoe UI", 18, "bold"),
            bg=COLORS["bg_sidebar"], fg=COLORS["accent"]
        )
        self.lbl_total_sidebar.pack(padx=16, pady=(2, 0), anchor="w")

    def _build_main_content(self, parent):
        """Construit la zone de contenu principale."""
        main = tk.Frame(parent, bg=COLORS["bg_main"])
        main.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        # Carte : Informations facture + client
        self._build_invoice_info_card(main)

        tk.Frame(main, bg=COLORS["bg_main"], height=10).pack()

        # Carte : Tableau des produits
        self._build_products_card(main)

    def _card(self, parent, title):
        """Crée une carte avec titre."""
        card = tk.Frame(parent, bg=COLORS["bg_card"],
                        relief="flat", bd=0,
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        card.pack(fill="x", pady=(0, 0))

        # Titre de la carte
        title_bar = tk.Frame(card, bg=COLORS["primary_light"])
        title_bar.pack(fill="x")
        tk.Label(
            title_bar, text=title,
            font=FONTS["subhead"],
            bg=COLORS["primary_light"], fg=COLORS["primary"]
        ).pack(side="left", padx=14, pady=8)

        content = tk.Frame(card, bg=COLORS["bg_card"])
        content.pack(fill="both", expand=True, padx=14, pady=10)
        return content

    def _build_invoice_info_card(self, parent):
        """Carte avec les informations de facture et client."""
        content = self._card(parent, "📋  Informations de la Facture")

        row1 = tk.Frame(content, bg=COLORS["bg_card"])
        row1.pack(fill="x")

        # Numéro de facture (lecture seule)
        self._field(row1, "N° Facture", readonly=True, var_name="num_facture").pack(
            side="left", expand=True, fill="x", padx=(0, 12))

        # Date
        self._field(row1, "Date", readonly=True, var_name="date_facture").pack(
            side="left", expand=True, fill="x")

        tk.Frame(content, bg=COLORS["bg_card"], height=8).pack()

        row2 = tk.Frame(content, bg=COLORS["bg_card"])
        row2.pack(fill="x")

        # Nom client
        self._field(row2, "Nom du client *", var_name="client_nom").pack(
            side="left", expand=True, fill="x", padx=(0, 12))

        # Téléphone
        self._field(row2, "Téléphone", var_name="client_tel").pack(
            side="left", expand=True, fill="x")

    def _field(self, parent, label_text, readonly=False, var_name=None):
        """Crée un champ de formulaire avec label."""
        frame = tk.Frame(parent, bg=COLORS["bg_card"])

        tk.Label(
            frame, text=label_text,
            font=FONTS["small"], bg=COLORS["bg_card"],
            fg=COLORS["text_light"]
        ).pack(anchor="w")

        var = tk.StringVar()
        if var_name:
            setattr(self, f"var_{var_name}", var)

        state = "readonly" if readonly else "normal"
        entry = tk.Entry(
            frame, textvariable=var,
            font=FONTS["body"], state=state,
            relief="flat", bd=0,
            bg="#f1f5f9" if readonly else COLORS["bg_card"],
            fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            highlightcolor=COLORS["primary"],
            readonlybackground="#f1f5f9",
        )
        entry.pack(fill="x", ipady=6)

        if var_name:
            setattr(self, f"entry_{var_name}", entry)

        return frame

    def _build_products_card(self, parent):
        """Carte Vente au comptoir avec saisie rapide, tableau et actions."""
        card = tk.Frame(parent, bg=COLORS["bg_card"],
                        relief="flat", bd=0,
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        card.pack(fill="both", expand=True)

        # ── Titre ──────────────────────────────────────────────────────────────
        title_bar = tk.Frame(card, bg=COLORS["primary_light"])
        title_bar.pack(fill="x")
        tk.Label(
            title_bar, text="🏪  Vente au comptoir",
            font=FONTS["subhead"],
            bg=COLORS["primary_light"], fg=COLORS["primary"]
        ).pack(side="left", padx=14, pady=8)
        tk.Label(
            title_bar, text="Double-cliquez sur une ligne pour modifier",
            font=FONTS["small"],
            bg=COLORS["primary_light"], fg=COLORS["text_light"]
        ).pack(side="right", padx=14)

        # ── Barre de saisie rapide ─────────────────────────────────────────────
        self._build_quick_entry(card)

        # ── Tableau ────────────────────────────────────────────────────────────
        table_frame = tk.Frame(card, bg=COLORS["bg_card"])
        table_frame.pack(fill="both", expand=True, padx=14, pady=(6, 0))
        self._build_table(table_frame)

        # ── Barre inférieure : paiement + total + boutons ──────────────────────
        bottom = tk.Frame(card, bg=COLORS["bg_card"],
                          highlightbackground=COLORS["border"], highlightthickness=1)
        bottom.pack(fill="x")

        # Méthode de paiement
        pmt_frame = tk.Frame(bottom, bg=COLORS["bg_card"])
        pmt_frame.pack(side="left", padx=14, pady=8)

        tk.Label(pmt_frame, text="💳  Paiement :",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dark"]).pack(side="left", padx=(0, 6))

        self.var_paiement = tk.StringVar(value="")
        self.combo_paiement = ttk.Combobox(
            pmt_frame, textvariable=self.var_paiement,
            font=FONTS["body"], state="readonly", width=18
        )
        self.combo_paiement.pack(side="left")
        self._charger_methodes_paiement()

        # Total
        total_frame = tk.Frame(bottom, bg=COLORS["primary_light"],
                               highlightbackground=COLORS["border"],
                               highlightthickness=1)
        total_frame.pack(side="left", padx=14, pady=8, ipady=4, ipadx=10)

        tk.Label(total_frame, text="TOTAL :",
                 font=FONTS["subhead"],
                 bg=COLORS["primary_light"], fg=COLORS["text_dark"]
                 ).pack(side="left", padx=(8, 4))

        self.lbl_total = tk.Label(
            total_frame, text="0 FCFA",
            font=("Segoe UI", 15, "bold"),
            bg=COLORS["primary_light"], fg=COLORS["primary"]
        )
        self.lbl_total.pack(side="left", padx=(0, 8))

        # Boutons Valider Ticket / Valider Facture
        btns_frame = tk.Frame(bottom, bg=COLORS["bg_card"])
        btns_frame.pack(side="right", padx=14, pady=8)

        self.btn_valider_ticket = tk.Button(
            btns_frame, text="🖨  Valider Ticket",
            command=self._valider_ticket,
            font=FONTS["body_bold"],
            bg="#7c3aed", fg="white",
            activebackground="#6d28d9", activeforeground="white",
            relief="flat", bd=0, padx=16, pady=10, cursor="hand2"
        )
        self.btn_valider_ticket.pack(side="left", padx=(0, 6))

        self.btn_valider_facture = tk.Button(
            btns_frame, text="📄  Valider Facture",
            command=self._valider_facture,
            font=FONTS["body_bold"],
            bg=COLORS["accent"], fg="white",
            activebackground="#059669", activeforeground="white",
            relief="flat", bd=0, padx=16, pady=10, cursor="hand2"
        )
        self.btn_valider_facture.pack(side="left")

    def _build_quick_entry(self, parent):
        """
        Barre de saisie rapide : Référence/Scan | Désignation | Quantité | Montant | ➕
        - La référence sert de champ de scan code-barres ET de recherche textuelle.
        - Un dropdown apparaît si plusieurs correspondances sont trouvées.
        - Les autres champs sont auto-complétés quand un produit est identifié.
        """
        bar = tk.Frame(parent, bg="#f0fdf4",
                       highlightbackground="#bbf7d0", highlightthickness=1)
        bar.pack(fill="x", padx=14, pady=(8, 0))

        # ── Label section ──────────────────────────────────────────────────────
        lbl_section = tk.Frame(bar, bg="#f0fdf4")
        lbl_section.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(lbl_section, text="➕  Saisie rapide",
                 font=FONTS["body_bold"], bg="#f0fdf4", fg="#065f46").pack(side="left")
        self.lbl_quick_status = tk.Label(lbl_section, text="",
                                         font=FONTS["small"], bg="#f0fdf4", fg="#059669")
        self.lbl_quick_status.pack(side="right")

        # ── Ligne des champs ───────────────────────────────────────────────────
        fields_row = tk.Frame(bar, bg="#f0fdf4")
        fields_row.pack(fill="x", padx=10, pady=(0, 8))

        # ─ Col 1 : Référence / Code-barres (champ de recherche)
        col1 = tk.Frame(fields_row, bg="#f0fdf4")
        col1.pack(side="left", fill="x", expand=False, padx=(0, 6))
        tk.Label(col1, text="Réf. / Code-barres",
                 font=FONTS["small"], bg="#f0fdf4", fg="#374151").pack(anchor="w")

        ref_wrap = tk.Frame(col1, bg="#f0fdf4")
        ref_wrap.pack(fill="x")

        self.var_quick_ref = tk.StringVar()
        self.entry_quick_ref = tk.Entry(
            ref_wrap, textvariable=self.var_quick_ref,
            font=("Consolas", 10), width=18,
            relief="flat", bd=0,
            bg="white", fg="#065f46",
            highlightbackground="#10b981", highlightthickness=1,
            insertbackground="#065f46",
        )
        self.entry_quick_ref.pack(side="left", fill="x", ipady=6)

        # Dropdown de suggestions (Listbox flottante)
        self._quick_popup = None
        self._quick_popup_items = []

        # Bindings
        self.entry_quick_ref.bind("<Return>",    self._quick_ref_enter)
        self.entry_quick_ref.bind("<KeyRelease>", self._quick_ref_key)
        self.entry_quick_ref.bind("<Down>",       self._quick_popup_focus)
        self.entry_quick_ref.bind("<Escape>",     lambda e: self._quick_reset())
        self.var_quick_ref.trace("w", self._quick_ref_trace)

        # ─ Col 2 : Désignation (lecture auto-remplie, modifiable)
        col2 = tk.Frame(fields_row, bg="#f0fdf4")
        col2.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(col2, text="Désignation",
                 font=FONTS["small"], bg="#f0fdf4", fg="#374151").pack(anchor="w")
        self.var_quick_desig = tk.StringVar()
        tk.Entry(
            col2, textvariable=self.var_quick_desig,
            font=FONTS["body"], width=24,
            relief="flat", bd=0,
            bg="white", fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            highlightcolor=COLORS["primary"],
        ).pack(fill="x", ipady=6)

        # ─ Col 3 : Quantité
        col3 = tk.Frame(fields_row, bg="#f0fdf4")
        col3.pack(side="left", fill="x", expand=False, padx=(0, 6))
        tk.Label(col3, text="Quantité",
                 font=FONTS["small"], bg="#f0fdf4", fg="#374151").pack(anchor="w")
        self.var_quick_qte = tk.StringVar(value="1")
        self.entry_quick_qte = tk.Entry(
            col3, textvariable=self.var_quick_qte,
            font=FONTS["body"], width=7,
            relief="flat", bd=0,
            bg="white", fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            highlightcolor=COLORS["primary"],
        )
        self.entry_quick_qte.pack(fill="x", ipady=6)
        # Return sur la quantité ajoute l'article
        self.entry_quick_qte.bind("<Return>", lambda e: self._quick_ajouter())
        # Recalcul montant en temps réel
        self.var_quick_qte.trace("w", self._quick_recalc)

        # ─ Prix unitaire (stocké en mémoire, non affiché)
        self._quick_prix_unitaire = 0.0
        self._quick_catalogue_id  = None  # ID catalogue pour déduction stock

        # ─ Col 5 : Montant (lecture seule, calculé)
        col4 = tk.Frame(fields_row, bg="#f0fdf4")
        col4.pack(side="left", fill="x", expand=False, padx=(0, 8))
        tk.Label(col4, text="Montant",
                 font=FONTS["small"], bg="#f0fdf4", fg="#374151").pack(anchor="w")
        self.var_quick_montant = tk.StringVar(value="—")
        tk.Entry(
            col4, textvariable=self.var_quick_montant,
            font=FONTS["body_bold"], width=14,
            relief="flat", bd=0,
            bg="#ecfdf5", fg="#065f46",
            highlightbackground=COLORS["border"], highlightthickness=1,
            state="readonly", readonlybackground="#ecfdf5",
        ).pack(fill="x", ipady=6)

        # ─ Bouton Ajouter
        col5 = tk.Frame(fields_row, bg="#f0fdf4")
        col5.pack(side="left", fill="x", expand=False)
        tk.Label(col5, text=" ", font=FONTS["small"], bg="#f0fdf4").pack(anchor="w")
        self.btn_quick_ajouter = tk.Button(
            col5, text="➕  Ajouter",
            command=self._quick_ajouter,
            font=FONTS["body_bold"],
            bg="#059669", fg="white",
            activebackground="#047857", activeforeground="white",
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        )
        self.btn_quick_ajouter.pack(ipady=1)
        # Return sur le bouton (focus après scan) ajoute l'article
        self.btn_quick_ajouter.bind("<Return>", lambda e: self._quick_ajouter())

    def _build_table(self, parent):
        """Construit le tableau des produits avec Treeview."""
        # Scrollbars
        scrolly = ttk.Scrollbar(parent, orient="vertical")
        scrolly.pack(side="right", fill="y")

        # Style du Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Invoice.Treeview",
            background=COLORS["bg_card"],
            foreground=COLORS["text_dark"],
            rowheight=36,
            fieldbackground=COLORS["bg_card"],
            bordercolor=COLORS["border"],
            borderwidth=0,
            font=FONTS["body"],
        )
        style.configure(
            "Invoice.Treeview.Heading",
            background=COLORS["header_bg"],
            foreground="white",
            font=FONTS["body_bold"],
            relief="flat",
            borderwidth=0,
        )
        style.map("Invoice.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )
        style.map("Invoice.Treeview.Heading",
            background=[("active", COLORS["primary_dark"])],
        )

        self.tree = ttk.Treeview(
            parent,
            columns=("reference", "designation", "quantite", "prix_unitaire", "montant"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Invoice.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        # Colonnes
        cols = [
            ("reference",     "Réf.",          90, "w"),
            ("designation",   "Désignation",   320, "w"),
            ("quantite",      "Quantité",       80, "center"),
            ("prix_unitaire", "Prix Unitaire", 120, "e"),
            ("montant",       "Montant",       120, "e"),
        ]
        for col_id, col_label, width, anchor in cols:
            self.tree.heading(col_id, text=col_label)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=50)

        self.tree.pack(side="left", fill="both", expand=True)

        # Tags pour l'alternance des couleurs
        self.tree.tag_configure("even", background=COLORS["row_even"])
        self.tree.tag_configure("odd",  background=COLORS["row_odd"])
        self.tree.tag_configure("stock_insuffisant",
                                background="#fee2e2", foreground="#b91c1c")

        # Double-clic pour modifier une ligne
        self.tree.bind("<Double-1>", self._modifier_produit)

    # ──────────────────────────────────────────────────────────────────────────
    # LOGIQUE MÉTIER
    # ──────────────────────────────────────────────────────────────────────────

    def _load_next_invoice_number(self):
        """Charge et affiche le prochain numéro de facture."""
        num = db.get_next_invoice_number()
        self.var_num_facture.set(num)
        self.lbl_num_sidebar.config(text=num)

    def _set_today_date(self):
        """Affiche la date du jour."""
        today = datetime.now().strftime("%d/%m/%Y")
        self.var_date_facture.set(today)

    # ──────────────────────────────────────────────────────────────────────────
    # SAISIE RAPIDE (barre inline au-dessus du tableau)
    # ──────────────────────────────────────────────────────────────────────────

    def _quick_ref_trace(self, *_):
        """Trace sur la variable : efface le statut si l'utilisateur tape."""
        pass  # On gère dans KeyRelease pour ne pas interférer avec le remplissage auto

    def _quick_ref_key(self, event):
        """KeyRelease dans le champ Référence : ouvre la fenêtre de sélection article."""
        # Ignorer les touches de navigation et de contrôle
        if event.keysym in ("Return", "Down", "Up", "Escape", "Tab",
                             "Shift_L", "Shift_R", "Control_L", "Control_R",
                             "Alt_L", "Alt_R", "BackSpace", "Delete"):
            return
        # Dès qu'une lettre ou chiffre est tapé → ouvrir la fenêtre modale
        query = self.var_quick_ref.get().strip()
        if query:
            self._ouvrir_selection_article(query)

    def _quick_ref_enter(self, event=None):
        """Return dans le champ Référence : recherche par référence/code-barres ou dropdown."""
        # Si popup ouverte → valider le premier élément
        if self._quick_popup and self._quick_popup.winfo_exists():
            self._quick_popup_select(0)
            return
        code = self.var_quick_ref.get().strip()
        if not code:
            return
        # 1. Correspondance exacte code-barres
        produit = db.get_product_by_barcode(code)
        if produit:
            self._quick_fill(produit)
            return
        # 2. Correspondance exacte référence article
        produit = db.get_product_by_reference(code)
        if produit:
            self._quick_fill(produit)
            return
        # 3. Recherche textuelle (désignation, description…)
        results = db.search_catalogue(code)
        if len(results) == 1:
            self._quick_fill(results[0])
        elif len(results) > 1:
            self._quick_show_popup(results)
        else:
            self.lbl_quick_status.config(text=f"❌ Aucun article : {code}", fg="#dc2626")
            self._flash_entry(self.entry_quick_ref, "#ef4444")

    def _quick_search_live(self):
        """Appelé uniquement lors d'un scan (code-barres ou référence exacte)."""
        query = self.var_quick_ref.get().strip()
        if not query:
            return
        # 1. Code-barres exact → remplissage immédiat
        produit = db.get_product_by_barcode(query)
        if produit:
            self._quick_fill(produit)
            return
        # 2. Référence exacte → remplissage immédiat
        produit = db.get_product_by_reference(query)
        if produit:
            self._quick_fill(produit)
            return
        # 3. Pas de correspondance exacte → ouvrir la fenêtre modale
        self._ouvrir_selection_article(query)

    def _ouvrir_selection_article(self, query_initiale: str = ""):
        """Ouvre la fenêtre modale de sélection d'article."""
        # Empêcher l'ouverture en double
        if hasattr(self, "_selection_win") and self._selection_win and \
                self._selection_win.winfo_exists():
            # Mettre à jour la recherche si la fenêtre est déjà ouverte
            self._selection_win.var_search.set(query_initiale)
            self._selection_win.focus()
            return
        win = _ArticleSelectionWindow(self, query_initiale)
        self._selection_win = win
        # Attendre le résultat
        self.wait_window(win)
        self._selection_win = None
        if win.result:
            self._quick_fill(win.result)

    def _quick_fill(self, produit: dict):
        """Remplit les champs avec les données du produit trouvé."""
        ref = produit.get("reference", "") or produit.get("code_barre", "") or ""
        self.var_quick_ref.set(ref)
        self.var_quick_desig.set(produit["designation"])
        self._quick_prix_unitaire = float(produit["prix_unitaire"])
        self._quick_catalogue_id  = produit.get("id")
        self._quick_ref_article   = produit.get("reference", "") or ""
        famille = produit.get("famille_nom", "")
        famille_txt = f"  [{famille}]" if famille else ""
        self._quick_recalc()

        # Afficher le stock disponible dans le statut
        cat_id = produit.get("id")
        if cat_id:
            stock = db.get_stock_produit(cat_id)
            if stock <= 0:
                stock_txt = f"  |  🚫 Rupture de stock"
                self.lbl_quick_status.config(
                    text=f"⚠️ {produit['designation'][:28]}{famille_txt}"
                         f"  —  {self._fmt_price(self._quick_prix_unitaire)} FCFA/u{stock_txt}",
                    fg="#dc2626"
                )
            else:
                stock_txt = f"  |  Stock : {stock:g}"
                self.lbl_quick_status.config(
                    text=f"✅ {produit['designation'][:28]}{famille_txt}"
                         f"  —  {self._fmt_price(self._quick_prix_unitaire)} FCFA/u{stock_txt}",
                    fg="#059669"
                )
        else:
            self.lbl_quick_status.config(
                text=f"✅ {produit['designation'][:30]}{famille_txt}"
                     f"  —  {self._fmt_price(self._quick_prix_unitaire)} FCFA/u",
                fg="#059669"
            )

        self._flash_entry(self.entry_quick_ref, "#10b981")
        self._quick_popup_close()
        # Verrouiller le champ référence pour bloquer tout débordement de la douchette
        # Le champ passe en readonly : plus rien ne peut s'insérer dedans
        self.entry_quick_ref.config(state="readonly",
                                    readonlybackground="#ecfdf5")
        # Le focus va sur le bouton Ajouter (neutre) — ni ref ni qte
        self.btn_quick_ajouter.focus()

    def _quick_recalc(self, *_):
        """Recalcule le montant en fonction de la quantité."""
        try:
            qte = float(self.var_quick_qte.get().strip().replace(",", "."))
            if qte > 0 and self._quick_prix_unitaire > 0:
                montant = qte * self._quick_prix_unitaire
                self.var_quick_montant.set(f"{self._fmt_price(montant)} FCFA")
            else:
                self.var_quick_montant.set("—")
        except ValueError:
            self.var_quick_montant.set("—")

    def _quick_ajouter(self):
        """Valide la saisie rapide — bloqué si caisse fermée ou stock insuffisant."""
        # ── 1. Caisse ouverte obligatoire ────────────────────────────────────
        if not db.get_session_ouverte():
            messagebox.showerror(
                "🔴 Caisse fermée",
                "Impossible d'ajouter un article : la caisse est fermée.\n\n"
                "Ouvrez une session de caisse via le bouton 💰 Caisse.",
                parent=self
            )
            return

        # ── 2. Résolution de l'article ────────────────────────────────────────
        desig = self.var_quick_desig.get().strip()
        if not desig:
            ref = self.var_quick_ref.get().strip()
            if ref:
                self._quick_ref_enter()
                desig = self.var_quick_desig.get().strip()
            if not desig:
                self.lbl_quick_status.config(text="⚠️ Renseignez un article.", fg="#f59e0b")
                self.entry_quick_ref.focus()
                return

        try:
            qte = float(self.var_quick_qte.get().strip().replace(",", "."))
            if qte <= 0:
                raise ValueError
        except ValueError:
            self.lbl_quick_status.config(text="⚠️ Quantité invalide.", fg="#f59e0b")
            return

        prix = self._quick_prix_unitaire
        if prix <= 0:
            self.lbl_quick_status.config(text="⚠️ Prix unitaire introuvable.", fg="#f59e0b")
            return

        cat_id = getattr(self, "_quick_catalogue_id", None)

        # ── 3. Vérification stock AVANT déduction ─────────────────────────────
        if cat_id:
            stock_actuel = db.get_stock_produit(cat_id)
            if stock_actuel <= 0:
                self.lbl_quick_status.config(
                    text=f"🚫 Stock insuffisant — stock : {stock_actuel:g}",
                    fg="#dc2626"
                )
                self._flash_entry(self.entry_quick_ref, "#ef4444")
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} » est en rupture de stock.\n\n"
                    f"Stock disponible : {stock_actuel:g}\n"
                    f"Quantité demandée : {qte:g}\n\n"
                    "Approvisionnez le stock avant de vendre cet article.",
                    parent=self
                )
                return
            if stock_actuel < qte:
                self.lbl_quick_status.config(
                    text=f"🚫 Stock insuffisant — disponible : {stock_actuel:g}",
                    fg="#dc2626"
                )
                self._flash_entry(self.entry_quick_ref, "#ef4444")
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} »\n\n"
                    f"Stock disponible : {stock_actuel:g}\n"
                    f"Quantité demandée : {qte:g}\n\n"
                    "Réduisez la quantité ou approvisionnez le stock.",
                    parent=self
                )
                return

        # ── 4. Déduction stock et ajout ───────────────────────────────────────
        montant = qte * prix
        if cat_id:
            try:
                db.deduire_stock_article(cat_id, qte, "Vente directe")
                self._refresh_stock_badge()
            except StockInsuffisantError as e:
                self.lbl_quick_status.config(
                    text=f"🚫 Stock insuffisant — disponible : {e.stock_disponible:g}",
                    fg="#dc2626"
                )
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} »\n\n"
                    f"Stock disponible : {e.stock_disponible:g}\n"
                    f"Quantité demandée : {e.quantite_demandee:g}\n\n"
                    "Le stock ne peut pas être négatif.",
                    parent=self
                )
                return
            except Exception:
                pass

        self.produits.append({
            "designation":   desig,
            "quantite":      qte,
            "prix_unitaire": prix,
            "montant":       montant,
            "catalogue_id":  cat_id,
            "reference":     getattr(self, "_quick_ref_article", ""),
        })
        self._refresh_table()

        self.lbl_quick_status.config(
            text=f"✅ « {desig[:28]} » ajouté — {self._fmt_price(montant)} FCFA",
            fg="#059669"
        )
        self._quick_reset()

    def _quick_reset(self):
        """Réinitialise les champs de saisie rapide pour le prochain article."""
        # Déverrouiller le champ référence avant de le vider
        self.entry_quick_ref.config(state="normal",
                                    bg="white",
                                    highlightbackground="#10b981")
        self.var_quick_ref.set("")
        self.var_quick_desig.set("")
        self.var_quick_qte.set("1")
        self.var_quick_montant.set("—")
        self._quick_prix_unitaire = 0.0
        self._quick_catalogue_id  = None
        self._quick_ref_article   = ""
        self._quick_popup_close()
        self.entry_quick_ref.focus()

    # ── Méthodes popup — conservées pour compatibilité, plus utilisées ────────

    def _quick_show_popup(self, produits: list):
        """Obsolète — remplacé par _ouvrir_selection_article."""
        self._ouvrir_selection_article()

    def _check_popup_focus(self):
        pass

    def _quick_popup_focus(self, event=None):
        pass

    def _quick_popup_select(self, index: int):
        if 0 <= index < len(self._quick_popup_items):
            self._quick_fill(self._quick_popup_items[index])

    def _quick_popup_close(self):
        if self._quick_popup:
            try:
                self._quick_popup.destroy()
            except Exception:
                pass
            self._quick_popup = None
            self._quick_popup_items = []

    def _flash_entry(self, entry, color):
        """Flash visuel sur un champ (confirmation ou erreur)."""
        entry.config(highlightbackground=color, highlightthickness=2)
        self.after(700, lambda: entry.config(
            highlightbackground="#10b981", highlightthickness=1))

    # ──────────────────────────────────────────────────────────────────────────

    def _ajouter_produit(self):
        """Ouvre la boîte de dialogue — bloqué si caisse fermée."""
        # ── Caisse ouverte obligatoire ────────────────────────────────────────
        if not db.get_session_ouverte():
            messagebox.showerror(
                "🔴 Caisse fermée",
                "Impossible d'ajouter un article : la caisse est fermée.\n\n"
                "Ouvrez une session de caisse via le bouton 💰 Caisse.",
                parent=self
            )
            return

        dialog = ProduitDialog(self, title="Ajouter un produit")
        if not dialog.result:
            return

        desig, qte, prix = dialog.result

        # ── Vérification stock ────────────────────────────────────────────────
        cat_id = None
        resultats = db.search_catalogue(desig)
        exact = next((p for p in resultats
                      if p["designation"].lower() == desig.lower()), None)
        if exact:
            cat_id = exact["id"]
            stock_actuel = db.get_stock_produit(cat_id)
            if stock_actuel <= 0:
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} » est en rupture de stock.\n\n"
                    f"Stock disponible : {stock_actuel:g}\n"
                    "Approvisionnez le stock avant de vendre cet article.",
                    parent=self
                )
                return
            if stock_actuel < qte:
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} »\n\n"
                    f"Stock disponible : {stock_actuel:g}\n"
                    f"Quantité demandée : {qte:g}\n\n"
                    "Réduisez la quantité ou approvisionnez le stock.",
                    parent=self
                )
                return
            # Déduction stock
            try:
                db.deduire_stock_article(cat_id, qte, "Vente directe")
                self._refresh_stock_badge()
            except StockInsuffisantError as e:
                messagebox.showerror(
                    "🚫 Stock insuffisant",
                    f"« {desig} »\n\n"
                    f"Stock disponible : {e.stock_disponible:g}\n"
                    f"Quantité demandée : {e.quantite_demandee:g}\n\n"
                    "Le stock ne peut pas être négatif.",
                    parent=self
                )
                return
            except Exception:
                pass

        montant = qte * prix
        self.produits.append({
            "designation":   desig,
            "quantite":      qte,
            "prix_unitaire": prix,
            "montant":       montant,
            "catalogue_id":  cat_id,
        })
        self._refresh_table()

    def _modifier_produit(self, event):
        """Modifie une ligne existante et ajuste le stock si la quantité change."""
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(self.tree.index(selected[0]))
        produit = self.produits[idx]

        dialog = ProduitDialog(
            self,
            title="Modifier le produit",
            initial={
                "designation":   produit["designation"],
                "quantite":      produit["quantite"],
                "prix_unitaire": produit["prix_unitaire"],
            }
        )
        if dialog.result:
            desig, qte, prix = dialog.result
            montant = qte * prix

            # Ajustement stock si l'article vient du catalogue
            cat_id   = produit.get("catalogue_id")
            qte_old  = produit["quantite"]
            qte_diff = qte - qte_old  # positif → on vend plus → déduire
            if cat_id and qte_diff != 0:
                try:
                    if qte_diff > 0:
                        db.deduire_stock_article(cat_id, qte_diff, "Ajustement ligne")
                    else:
                        db.restituer_stock_article(cat_id, abs(qte_diff), "Ajustement ligne")
                    self._refresh_stock_badge()
                except StockInsuffisantError as e:
                    messagebox.showerror(
                        "🚫 Stock insuffisant",
                        f"Impossible d'augmenter la quantité.\n\n"
                        f"Stock disponible : {e.stock_disponible:g}\n"
                        f"Supplément demandé : {e.quantite_demandee:g}\n\n"
                        "Le stock ne peut pas être négatif.",
                        parent=self
                    )
                    return
                except Exception:
                    pass

            self.produits[idx] = {
                "designation":   desig,
                "quantite":      qte,
                "prix_unitaire": prix,
                "montant":       montant,
                "catalogue_id":  cat_id,
            }
            self._refresh_table()

    def _supprimer_produit(self):
        """Supprime la ligne sélectionnée et restitue le stock."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "Aucune sélection",
                "Veuillez sélectionner un produit à supprimer.",
                parent=self
            )
            return
        idx = int(self.tree.index(selected[0]))
        p   = self.produits[idx]
        nom = p["designation"]
        if messagebox.askyesno(
            "Confirmer",
            f"Supprimer le produit « {nom} » ?",
            parent=self
        ):
            # Restituer le stock si l'article vient du catalogue
            cat_id = p.get("catalogue_id")
            if cat_id:
                try:
                    db.restituer_stock_article(cat_id, p["quantite"], "Annulation ligne")
                    self._refresh_stock_badge()
                except Exception:
                    pass
            self.produits.pop(idx)
            self._refresh_table()

    def _refresh_table(self):
        """Rafraîchit le tableau et recalcule le total."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        total = 0.0
        for i, p in enumerate(self.produits):
            qte_str  = self._fmt_nb(p["quantite"])
            prix_str = self._fmt_price(p["prix_unitaire"])
            mont_str = self._fmt_price(p["montant"])

            # Récupérer la référence depuis le dict produit (stockée à l'ajout)
            ref = p.get("reference", "") or ""

            # Vérifier le stock
            tag = "even" if i % 2 == 0 else "odd"
            desig_display = p["designation"]
            cat_id = p.get("catalogue_id")
            if cat_id:
                stock_actuel = db.get_stock_produit(cat_id)
                if stock_actuel < 0:
                    tag = "stock_insuffisant"
                    desig_display += "  ⚠️ Stock insuffisant"

            self.tree.insert(
                "", "end",
                values=(
                    ref,
                    desig_display,
                    qte_str,
                    f"{prix_str} FCFA",
                    f"{mont_str} FCFA",
                ),
                tags=(tag,)
            )
            total += p["montant"]

        total_str = self._fmt_price(total)
        self.lbl_total.config(text=f"{total_str} FCFA")
        self.lbl_total_sidebar.config(text=f"{total_str} FCFA")

    def _valider_formulaire(self):
        """Valide les champs et retourne True si tout est correct."""
        # ── Caisse ouverte obligatoire ────────────────────────────────────────
        if not db.get_session_ouverte():
            messagebox.showerror(
                "🔴 Caisse fermée",
                "Aucune vente ne peut être enregistrée : la caisse est fermée.\n\n"
                "Ouvrez une session de caisse via le bouton 💰 Caisse.",
                parent=self
            )
            return False

        if not self.produits:
            messagebox.showerror(
                "Aucun article",
                "Ajoutez au moins un article avant de valider.",
                parent=self
            )
            return False
        return True

    def _charger_methodes_paiement(self):
        """Charge les méthodes de paiement actives dans le combobox."""
        try:
            methodes = db.get_methodes_paiement(actif_seulement=True)
            noms = [m["nom"] for m in methodes]
        except Exception:
            noms = ["Espèces"]
        self.combo_paiement["values"] = noms
        if noms:
            self.var_paiement.set(noms[0])

    def _verifier_stocks(self) -> list:
        """
        Vérifie le stock de chaque ligne.
        Retourne la liste des articles en stock insuffisant.
        """
        alertes = []
        for p in self.produits:
            cat_id = p.get("catalogue_id")
            if cat_id:
                stock = db.get_stock_produit(cat_id)
                # Le stock a déjà été déduit à l'ajout de la ligne
                # On vérifie si le stock résultant est négatif
                if stock < 0:
                    alertes.append({
                        "designation": p["designation"],
                        "stock": stock,
                        "quantite": p["quantite"],
                    })
        return alertes

    def _valider_vente(self, type_doc: str):
        """Logique commune de validation (ticket ou facture)."""
        # Caisse + produits (vérifié dans _valider_formulaire)
        if not self._valider_formulaire():
            return False

        # ── Blocage strict : aucun article en stock négatif ───────────────────
        alertes_stock = self._verifier_stocks()
        if alertes_stock:
            msg = "🚫  Vente bloquée — stock insuffisant pour :\n\n"
            for a in alertes_stock:
                msg += (f"• {a['designation']}\n"
                        f"  Stock après déduction : {a['stock']:g}\n")
            msg += ("\nSupprimez ou réduisez les lignes concernées\n"
                    "puis approvisionnez le stock.")
            messagebox.showerror("🚫 Stock insuffisant", msg, parent=self)
            return False

        # ── Méthode de paiement ───────────────────────────────────────────────
        methode = self.var_paiement.get().strip()
        if not methode:
            messagebox.showwarning(
                "Paiement manquant",
                "Sélectionnez une méthode de paiement.",
                parent=self
            )
            return False

        numero = self.var_num_facture.get()
        client = self.var_client_nom.get().strip() or "Client comptoir"
        tel    = self.var_client_tel.get().strip()
        date   = self.var_date_facture.get()
        total  = sum(p["montant"] for p in self.produits)

        # Sauvegarde en base
        try:
            db.save_invoice(
                numero, client, tel, date, total,
                [(p["designation"], p["quantite"], p["prix_unitaire"], p["montant"])
                 for p in self.produits]
            )
        except Exception as e:
            messagebox.showerror("Erreur base de données", str(e), parent=self)
            return False

        # Génération PDF
        try:
            self.pdf_path = pdf_gen.generate_pdf(
                numero, client, tel, date, self.produits, total,
                methode_paiement=methode, type_doc=type_doc
            )
        except Exception as e:
            messagebox.showerror("Erreur PDF", str(e), parent=self)
            return False

        # Enregistrement en caisse (session déjà vérifiée)
        try:
            session = db.get_session_ouverte()
            if session:
                db.enregistrer_vente_en_caisse(session["id"], numero, total)
                self._refresh_caisse_badge()
        except Exception:
            pass

        self._refresh_stock_badge()
        return True

    def _valider_ticket(self):
        """Valide la vente, génère et imprime directement le ticket."""
        if not self._valider_vente("ticket"):
            return
        # Impression directe sans confirmation
        self._imprimer_direct(self.pdf_path)
        # Vider le tableau immédiatement sans confirmation
        self._reset_apres_vente()

    def _valider_facture(self):
        """Valide la vente, génère la facture et ouvre le PDF."""
        if not self._valider_vente("facture"):
            return
        # Ouvrir la facture directement
        self._ouvrir_pdf()
        # Vider le tableau immédiatement sans confirmation
        self._reset_apres_vente()

    def _imprimer_direct(self, pdf_path: str):
        """Envoie le PDF directement à l'imprimante par défaut."""
        if not pdf_path or not os.path.exists(pdf_path):
            return
        try:
            if platform.system() == "Windows":
                # Essayer win32api en premier (impression native)
                try:
                    import win32api
                    win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
                except ImportError:
                    # Fallback : ouvrir avec l'application par défaut
                    os.startfile(pdf_path, "print")
            elif platform.system() == "Darwin":
                subprocess.run(["lpr", pdf_path], check=False)
            else:
                subprocess.run(["lpr", pdf_path], check=False)
        except Exception:
            # En dernier recours, ouvrir le PDF
            self._ouvrir_pdf()

    def _proposer_nouvelle_vente(self, numero: str):
        """Obsolète — gardé pour compatibilité."""
        pass

    def _generer_pdf(self):
        """Redirige vers _valider_facture pour compatibilité."""
        self._valider_facture()

    def _ouvrir_pdf(self):
        """Ouvre le PDF avec l'application par défaut."""
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            messagebox.showwarning("PDF introuvable", "Le fichier PDF n'existe pas encore.", parent=self)
            return
        try:
            if platform.system() == "Windows":
                os.startfile(self.pdf_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", self.pdf_path])
            else:
                subprocess.run(["xdg-open", self.pdf_path])
        except Exception as e:
            messagebox.showerror("Erreur ouverture", str(e), parent=self)

    def _imprimer(self):
        """Imprime la facture PDF via la boîte de dialogue d'impression."""
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            messagebox.showwarning(
                "PDF non généré",
                "Veuillez d'abord générer la facture PDF avant d'imprimer.",
                parent=self
            )
            return
        PrintDialog(self, self.pdf_path)

    def _reset_apres_vente(self):
        """
        Réinitialise silencieusement après une vente validée.
        Pas de confirmation, pas de restitution stock (déjà vendu).
        """
        self.produits.clear()
        self.var_client_nom.set("")
        self.var_client_tel.set("")
        self.pdf_path = None
        self._refresh_table()
        self._load_next_invoice_number()
        self._set_today_date()
        self._quick_reset()
        self.entry_quick_ref.focus()

    def _nouvelle_facture(self):
        """Réinitialise manuellement — avec confirmation si des articles sont présents."""
        if self.produits:
            if not messagebox.askyesno(
                "Nouvelle vente",
                "Des articles sont en cours de saisie.\n"
                "Annuler et commencer une nouvelle vente ?",
                parent=self
            ):
                return
            # Restituer le stock des articles non encore facturés
            for p in self.produits:
                cat_id = p.get("catalogue_id")
                if cat_id:
                    try:
                        db.restituer_stock_article(
                            cat_id, p["quantite"], "Vente annulée"
                        )
                    except Exception:
                        pass

        self.produits.clear()
        self.var_client_nom.set("")
        self.var_client_tel.set("")
        self.pdf_path = None
        self._refresh_table()
        self._load_next_invoice_number()
        self._set_today_date()
        self._quick_reset()
        self.entry_quick_ref.focus()

    def _scanner_barcode(self):
        """Ouvre le dialogue d'ajout avec le focus sur le champ de scan code-barres."""
        dialog = ProduitDialog(self, title="Scanner un produit", scan_mode=True)
        if dialog.result:
            desig, qte, prix = dialog.result
            self.produits.append({
                "designation":   desig,
                "quantite":      qte,
                "prix_unitaire": prix,
                "montant":       qte * prix,
            })
            self._refresh_table()

    def _open_inventaire(self):
        """Ouvre la fenêtre d'inventaire du stock."""
        InventaireWindow(self)

    def _open_caisse(self):
        """Ouvre la fenêtre de gestion de caisse."""
        CaisseWindow(self)
        self._refresh_caisse_badge()

    def _refresh_caisse_badge(self):
        """Met à jour le badge caisse et l'état des boutons de vente."""
        try:
            session = db.get_session_ouverte()
            if session:
                solde = db.get_solde_caisse(session["id"])
                from caisse import _fmt
                self.lbl_caisse_statut.config(
                    text=f"💰 Caisse : {_fmt(solde)} FCFA",
                    fg="#86efac"
                )
                # Débloquer les boutons de vente
                self._set_vente_buttons_state(True)
            else:
                self.lbl_caisse_statut.config(
                    text="🔴 Caisse fermée", fg="#fca5a5"
                )
                # Bloquer les boutons de vente
                self._set_vente_buttons_state(False)
        except Exception:
            pass

    def _set_vente_buttons_state(self, caisse_ouverte: bool):
        """Active ou grise les boutons Valider Ticket / Valider Facture."""
        try:
            if caisse_ouverte:
                self.btn_valider_ticket.config(
                    state="normal", bg="#7c3aed",
                    cursor="hand2"
                )
                self.btn_valider_facture.config(
                    state="normal", bg=COLORS["accent"],
                    cursor="hand2"
                )
            else:
                self.btn_valider_ticket.config(
                    state="disabled", bg="#9ca3af",
                    cursor="arrow"
                )
                self.btn_valider_facture.config(
                    state="disabled", bg="#9ca3af",
                    cursor="arrow"
                )
        except Exception:
            pass

    def _open_stock(self):
        """Ouvre la fenêtre de gestion des stocks."""
        StockWindow(self)
        self._refresh_stock_badge()

    def _open_licence(self):
        """Affiche les informations de licence."""
        LicenceInfoWindow(self)

    def _envoyer_whatsapp(self):
        """Ouvre WhatsApp Web pour envoyer la facture PDF au client."""
        import webbrowser, urllib.parse
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            if messagebox.askyesno(
                "PDF requis",
                "La facture PDF n'a pas encore été générée.\n"
                "Voulez-vous la générer maintenant ?",
                parent=self
            ):
                self._generer_pdf()
            return
        tel_client = self.var_client_tel.get().strip()
        numero_fac = self.var_num_facture.get()
        client     = self.var_client_nom.get().strip()
        total      = sum(p["montant"] for p in self.produits)
        total_str  = self._fmt_price(total)
        import config as cfg_mod
        nom_commerce = cfg_mod.get("nom", "notre commerce")
        message = (
            f"Bonjour {client},\n\n"
            f"Veuillez trouver ci-joint votre facture {numero_fac} "
            f"d'un montant de {total_str} FCFA.\n\n"
            f"Merci pour votre confiance.\n"
            f"— {nom_commerce}"
        )
        #_WhatsAppDialog(self, tel_client, message, self.pdf_path)

    def _refresh_stock_badge(self):
        """Met à jour le badge d'alerte stock dans la topbar."""
        try:
            alertes = db.get_stock_alerts()
            ruptures = [a for a in alertes if a["stock_actuel"] <= 0]
            bas      = [a for a in alertes if 0 < a["stock_actuel"] <= a["seuil_alerte"]]
            parts = []
            if ruptures:
                parts.append(f"🔴 {len(ruptures)} rupture(s)")
            if bas:
                parts.append(f"⚠️ {len(bas)} stock(s) bas")
            self.lbl_stock_alerte.config(text="  ".join(parts))
        except Exception:
            pass

    def _check_licence_expiry(self):
        """Avertissement si la licence expire bientôt."""
        try:
            warning = get_expiry_warning()
            if warning:
                messagebox.showwarning("⏳ Expiration de licence", warning, parent=self)
        except Exception:
            pass

    def _open_historique(self):
        """Ouvre la fenêtre d'historique des factures."""
        HistoriqueWindow(self)

    def _open_catalogue(self):
        """Ouvre la fenêtre de gestion du catalogue."""
        CatalogueWindow(self)

    def _open_parametres(self):
        """Ouvre la fenêtre de paramètres."""
        ParametresWindow(self)

    def _show_stats(self):
        """Affiche les statistiques dans une fenêtre."""
        try:
            stats = db.get_statistics()
            total = stats.get("total_factures") or 0
            ca = stats.get("chiffre_affaires") or 0.0
            mois = stats.get("factures_mois") or 0
            ca_mois = stats.get("ca_mois") or 0.0

            messagebox.showinfo(
                "📊 Statistiques",
                f"📄 Total factures    : {total}\n"
                f"💰 Chiffre d'affaires : {self._fmt_price(ca)} FCFA\n\n"
                f"📅 Factures ce mois  : {mois}\n"
                f"💵 CA ce mois        : {self._fmt_price(ca_mois)} FCFA",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    @staticmethod
    def _fmt_price(value):
        """Formate un prix."""
        try:
            return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
        except:
            return "0,00"

    @staticmethod
    def _fmt_nb(value):
        """Formate un nombre (enlève les décimales inutiles)."""
        try:
            f = float(value)
            return str(int(f)) if f == int(f) else f"{f:g}"
        except:
            return str(value)


# ──────────────────────────────────────────────────────────────────────────────
# FENÊTRE DE SÉLECTION D'ARTICLE (remplace le dropdown flottant)
# ──────────────────────────────────────────────────────────────────────────────

class _ArticleSelectionWindow(tk.Toplevel):
    """
    Fenêtre modale de sélection d'article.
    S'ouvre dès qu'une lettre est tapée dans le champ référence.
    Barre de recherche en tête, tableau complet des articles.
    """

    def __init__(self, parent, query_initiale: str = ""):
        super().__init__(parent)
        self.title("🔍 Sélectionner un article")
        self.resizable(True, True)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.result = None

        # Centrer sous la barre de saisie rapide
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = 780, 480
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build(query_initiale)
        self._charger(query_initiale)

    def _build(self, query_initiale: str):
        # ── En-tête ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=COLORS["primary"], height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔍  Sélectionner un article",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white"
                 ).pack(side="left", padx=18, pady=14)
        tk.Label(header, text="Double-clic ou Entrée pour sélectionner  •  Échap pour annuler",
                 font=FONTS["small"], bg=COLORS["primary"], fg="#bfdbfe"
                 ).pack(side="right", padx=18)

        # ── Barre de recherche ─────────────────────────────────────────────────
        search_bar = tk.Frame(self, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        search_bar.pack(fill="x", padx=12, pady=(10, 0))

        tk.Label(search_bar, text="🔍", font=FONTS["heading"],
                 bg=COLORS["bg_card"], fg=COLORS["primary"]
                 ).pack(side="left", padx=(12, 4), pady=8)

        self.var_search = tk.StringVar(value=query_initiale)
        self.entry_search = tk.Entry(
            search_bar, textvariable=self.var_search,
            font=("Segoe UI", 13), relief="flat", bd=0,
            bg=COLORS["bg_card"], fg=COLORS["text_dark"],
            highlightthickness=0,
            insertbackground=COLORS["primary"],
        )
        self.entry_search.pack(side="left", fill="x", expand=True, ipady=8, padx=4)
        self.entry_search.focus()

        tk.Button(search_bar, text="✖ Effacer",
                  command=lambda: self.var_search.set(""),
                  font=FONTS["small"], bg=COLORS["border"],
                  fg=COLORS["text_dark"], relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2"
                  ).pack(side="right", padx=(0, 8), pady=8)

        self.var_search.trace("w", lambda *_: self._charger())

        # ── Filtre famille ─────────────────────────────────────────────────────
        fam_bar = tk.Frame(self, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        fam_bar.pack(fill="x", padx=12, pady=(4, 0))

        tk.Label(fam_bar, text="Famille :", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(side="left", padx=(12, 4), pady=6)

        self._familles_map = {"Toutes": None}
        try:
            for f in db.get_familles():
                self._familles_map[f["nom"]] = f["id"]
        except Exception:
            pass

        self.var_famille = tk.StringVar(value="Toutes")
        combo = ttk.Combobox(
            fam_bar, textvariable=self.var_famille,
            values=list(self._familles_map.keys()),
            state="readonly", font=FONTS["body"], width=22
        )
        combo.pack(side="left", pady=6)
        combo.bind("<<ComboboxSelected>>", lambda _: self._charger())

        self.lbl_count = tk.Label(fam_bar, text="",
                                  font=FONTS["small"], bg=COLORS["bg_card"],
                                  fg=COLORS["text_light"])
        self.lbl_count.pack(side="right", padx=12)

        # ── Tableau ────────────────────────────────────────────────────────────
        tf = tk.Frame(self, bg=COLORS["bg_main"])
        tf.pack(fill="both", expand=True, padx=12, pady=8)

        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Sel.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=34, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Sel.Treeview.Heading",
            background=COLORS["header_bg"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Sel.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree = ttk.Treeview(
            tf,
            columns=("reference", "designation", "famille",
                     "prix_achat", "prix_vente", "stock"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Sel.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        for cid, lbl, w, anc in [
            ("reference",   "Référence",    100, "w"),
            ("designation", "Désignation",  280, "w"),
            ("famille",     "Famille",      110, "center"),
            ("prix_achat",  "P. Achat",      90, "e"),
            ("prix_vente",  "P. Vente",      90, "e"),
            ("stock",       "Stock",          70, "center"),
        ]:
            self.tree.heading(cid, text=lbl)
            self.tree.column(cid, width=w, anchor=anc, minwidth=50)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("even",       background=COLORS["row_even"])
        self.tree.tag_configure("odd",        background=COLORS["row_odd"])
        self.tree.tag_configure("rupture",    background="#fee2e2",
                                              foreground="#b91c1c")
        self.tree.tag_configure("stock_bas",  background="#fef3c7")

        self.tree.bind("<Double-1>",  lambda _: self._selectionner())
        self.tree.bind("<Return>",    lambda _: self._selectionner())
        self.tree.bind("<Escape>",    lambda _: self.destroy())
        self.entry_search.bind("<Return>",  lambda _: self._selectionner())
        self.entry_search.bind("<Escape>",  lambda _: self.destroy())
        self.entry_search.bind("<Down>",    lambda _: self._focus_tree())

        # ── Barre d'actions ────────────────────────────────────────────────────
        action_bar = tk.Frame(self, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(action_bar, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=18, pady=8, cursor="hand2"
                  ).pack(side="right", padx=(8, 12), pady=8)

        tk.Button(action_bar, text="✔  Sélectionner",
                  command=self._selectionner,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=18, pady=8, cursor="hand2"
                  ).pack(side="right", pady=8)

        self.lbl_hint = tk.Label(action_bar,
                                 text="💡 Tapez pour filtrer — ↓ pour naviguer",
                                 font=FONTS["small"], bg=COLORS["bg_card"],
                                 fg=COLORS["text_light"])
        self.lbl_hint.pack(side="left", padx=14)

    def _charger(self, *_):
        """Charge et filtre la liste des articles."""
        query = self.var_search.get().strip()
        fid   = self._familles_map.get(self.var_famille.get())

        if query:
            produits = db.search_catalogue(query, fid)
        else:
            produits = db.get_catalogue(fid)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, p in enumerate(produits):
            stock_val = db.get_stock_produit(p["id"])
            pa  = float(p.get("prix_achat", 0) or 0)
            pv  = float(p.get("prix_unitaire", 0) or 0)

            # Tag selon stock
            if stock_val <= 0:
                tag = "rupture"
            elif stock_val <= p.get("seuil_alerte", 5):
                tag = "stock_bas"
            else:
                tag = "even" if i % 2 == 0 else "odd"

            self.tree.insert("", "end", iid=str(p["id"]),
                values=(
                    p.get("reference", "") or "—",
                    p["designation"],
                    p.get("famille_nom", "") or "—",
                    f"{pa:,.0f} FCFA".replace(",", " ") if pa > 0 else "—",
                    f"{pv:,.0f} FCFA".replace(",", " "),
                    f"{stock_val:g}",
                ),
                tags=(tag,)
            )

        self.lbl_count.config(text=f"{len(produits)} article(s)")

        # Sélectionner automatiquement le premier
        first = self.tree.get_children()
        if first:
            self.tree.selection_set(first[0])
            self.tree.focus(first[0])

    def _focus_tree(self):
        """Déplace le focus dans le tableau pour navigation clavier."""
        sel = self.tree.get_children()
        if sel:
            self.tree.focus_set()
            self.tree.selection_set(sel[0])
            self.tree.focus(sel[0])

    def _selectionner(self):
        """Valide la sélection et ferme la fenêtre."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Sélectionnez un article.", parent=self)
            return
        pid = int(sel[0])
        produits = db.get_catalogue()
        p = next((x for x in produits if x["id"] == pid), None)
        if p:
            self.result = p
        self.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# DIALOGUE : AJOUTER / MODIFIER UN PRODUIT (avec accès catalogue)
# ──────────────────────────────────────────────────────────────────────────────

class ProduitDialog(tk.Toplevel):
    """
    Boîte de dialogue pour saisir un produit sur une facture.
    Permet : saisie manuelle, sélection catalogue, OU scan code-barres douchette.
    """

    def __init__(self, parent, title="Produit", initial=None, scan_mode=False):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.geometry(f"460x450+{parent.winfo_x()+260}+{parent.winfo_y()+140}")

        self._build(initial or {}, scan_mode)
        self.wait_window(self)

    def _build(self, initial, scan_mode=False):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=COLORS["primary"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text=self.title(),
            font=FONTS["heading"], bg=COLORS["primary"], fg="white"
        ).pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=22, pady=12)
        body.pack(fill="both", expand=True)

        # ── Zone SCAN CODE-BARRES ─────────────────────────────────────────────
        scan_frame = tk.Frame(body, bg="#f0fdf4",
                              highlightbackground="#bbf7d0", highlightthickness=1)
        scan_frame.pack(fill="x", pady=(0, 10))

        scan_top = tk.Frame(scan_frame, bg="#f0fdf4")
        scan_top.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(scan_top, text="🔲  Scanner ou saisir un code-barres",
                 font=FONTS["body_bold"], bg="#f0fdf4", fg="#065f46"
                 ).pack(side="left")

        self.lbl_scan_status = tk.Label(scan_top, text="",
                                        font=FONTS["small"], bg="#f0fdf4", fg="#059669")
        self.lbl_scan_status.pack(side="right")

        scan_row = tk.Frame(scan_frame, bg="#f0fdf4")
        scan_row.pack(fill="x", padx=10, pady=(0, 8))

        self.var_scan = tk.StringVar()
        self.entry_scan = tk.Entry(
            scan_row, textvariable=self.var_scan,
            font=("Consolas", 12), relief="flat", bd=0,
            bg="white", fg="#065f46",
            highlightbackground="#bbf7d0", highlightthickness=2,
            highlightcolor="#10b981",
            insertbackground="#065f46",
        )
        self.entry_scan.pack(side="left", fill="x", expand=True, ipady=8)
        # La douchette envoie Return après le scan → on intercepte
        self.entry_scan.bind("<Return>", self._on_barcode_scan)
        self.entry_scan.bind("<KeyRelease>", self._on_scan_key)

        tk.Button(scan_row, text="🔍 Rechercher",
                  command=self._on_barcode_scan,
                  font=FONTS["small"],
                  bg="#059669", fg="white",
                  activebackground="#047857",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2"
                  ).pack(side="right", padx=(6, 0))

        tk.Label(scan_frame,
                 text="Scannez avec votre douchette. Le produit se pré-remplit automatiquement.",
                 font=FONTS["small"], bg="#f0fdf4", fg="#6b7280",
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # ── Bouton catalogue ──────────────────────────────────────────────────
        cat_frame = tk.Frame(body, bg=COLORS["primary_light"],
                             highlightbackground=COLORS["primary"],
                             highlightthickness=1)
        cat_frame.pack(fill="x", pady=(0, 10))

        tk.Label(cat_frame, text="Ou choisir dans le catalogue :",
                 font=FONTS["small"], bg=COLORS["primary_light"],
                 fg=COLORS["primary"]).pack(side="left", padx=10, pady=8)

        tk.Button(cat_frame, text="📦  Catalogue",
                  command=self._choisir_catalogue,
                  font=FONTS["body_bold"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=14, pady=5, cursor="hand2"
                  ).pack(side="right", padx=10, pady=6)

        # ── Séparateur ────────────────────────────────────────────────────────
        sep = tk.Frame(body, bg=COLORS["bg_card"])
        sep.pack(fill="x", pady=(0, 8))
        tk.Frame(sep, bg=COLORS["border"], height=1).pack(fill="x", side="left", expand=True)
        tk.Label(sep, text="  ou saisir manuellement  ",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(side="left")
        tk.Frame(sep, bg=COLORS["border"], height=1).pack(fill="x", side="left", expand=True)

        # ── Champs de saisie ──────────────────────────────────────────────────
        self.var_desig = tk.StringVar(value=initial.get("designation", ""))
        self.var_qte   = tk.StringVar(value=str(initial.get("quantite", "1")))
        self.var_prix  = tk.StringVar(value=str(initial.get("prix_unitaire", "")))

        tk.Label(body, text="Désignation *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.entry_desig = tk.Entry(
            body, textvariable=self.var_desig, font=FONTS["body"],
            relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            highlightcolor=COLORS["primary"],
        )
        self.entry_desig.pack(fill="x", ipady=6, pady=(0, 8))

        row = tk.Frame(body, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=(0, 8))

        left_col = tk.Frame(row, bg=COLORS["bg_card"])
        left_col.pack(side="left", expand=True, fill="x", padx=(0, 8))
        tk.Label(left_col, text="Quantité *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        self.entry_qte = tk.Entry(
            left_col, textvariable=self.var_qte, font=FONTS["body"],
            relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            highlightcolor=COLORS["primary"],
        )
        self.entry_qte.pack(fill="x", ipady=6)

        right_col = tk.Frame(row, bg=COLORS["bg_card"])
        right_col.pack(side="left", expand=True, fill="x")
        tk.Label(right_col, text="Prix unitaire (FCFA) *", font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")
        tk.Entry(
            right_col, textvariable=self.var_prix, font=FONTS["body"],
            relief="flat", bd=0, bg=COLORS["bg_main"], fg=COLORS["text_dark"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            highlightcolor=COLORS["primary"],
        ).pack(fill="x", ipady=6)

        # Focus : champ scan si mode scan, sinon désignation
        if scan_mode:
            self.entry_scan.focus()
        else:
            self.entry_desig.focus()

        # ── Boutons Valider / Annuler ─────────────────────────────────────────
        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x", pady=(10, 0))

        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))

        tk.Button(btn_frame, text="✔ Valider", command=self._validate,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2"
                  ).pack(side="right")

        # Return valide sauf si le focus est dans le champ scan
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_scan_key(self, event):
        """Efface le statut dès que l'utilisateur tape un nouveau code."""
        self.lbl_scan_status.config(text="")

    def _on_barcode_scan(self, event=None):
        """
        Appelé quand la douchette scanne (ou Return dans le champ scan).
        Recherche le code dans le catalogue et pré-remplit les champs si trouvé.
        """
        code = self.var_scan.get().strip()
        if not code:
            return

        produit = db.get_product_by_barcode(code)
        if produit:
            # ✅ Produit trouvé → pré-remplir
            self.var_desig.set(produit["designation"])
            self.var_prix.set(str(produit["prix_unitaire"]))
            self.var_qte.set("1")
            self.lbl_scan_status.config(
                text=f"✅ Trouvé : {produit['designation'][:30]}", fg="#059669"
            )
            # Flash vert sur le champ scan
            self.entry_scan.config(highlightbackground="#10b981", highlightthickness=3)
            self.after(800, lambda: self.entry_scan.config(
                highlightbackground="#bbf7d0", highlightthickness=2))
            # Déplacer le focus sur la quantité
            self.entry_qte.focus()
            self.entry_qte.select_range(0, tk.END)
        else:
            # ❌ Code inconnu
            self.lbl_scan_status.config(
                text=f"❌ Code inconnu : {code}", fg="#dc2626"
            )
            self.entry_scan.config(highlightbackground="#ef4444", highlightthickness=2)
            self.after(600, lambda: self.entry_scan.config(
                highlightbackground="#bbf7d0", highlightthickness=2))

    def _choisir_catalogue(self):
        """Ouvre le sélecteur de catalogue et pré-remplit les champs."""
        picker = CataloguePickerDialog(self)
        if picker.result:
            p = picker.result
            self.var_desig.set(p["designation"])
            self.var_prix.set(str(p["prix_unitaire"]))
            self.var_qte.set("1")

    def _validate(self):
        """Valide les entrées et ferme le dialogue."""
        desig    = self.var_desig.get().strip()
        qte_str  = self.var_qte.get().strip()
        prix_str = self.var_prix.get().strip().replace(",", ".")

        if not desig:
            messagebox.showerror("Erreur", "La désignation est obligatoire.", parent=self)
            return
        try:
            qte = float(qte_str)
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "La quantité doit être un nombre positif.", parent=self)
            return
        try:
            prix = float(prix_str)
            if prix < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Le prix unitaire doit être un nombre positif.", parent=self)
            return

        self.result = (desig, qte, prix)
        self.destroy()

# ──────────────────────────────────────────────────────────────────────────────
# DIALOGUE WHATSAPP
# ──────────────────────────────────────────────────────────────────────────────
"""
class _WhatsAppDialog(tk.Toplevel):
    Dialogue pour envoyer la facture via WhatsApp Web.

    def __init__(self, parent, telephone, message, pdf_path):
        super().__init__(parent)
        self.title("💬 Envoyer via WhatsApp")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        self.pdf_path = pdf_path
        self.geometry(f"500x440+{parent.winfo_x()+120}+{parent.winfo_y()+100}")
        self._build(telephone, message)

    def _build(self, telephone, message):
        hdr = tk.Frame(self, bg="#25d366", height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💬  Envoyer la facture via WhatsApp",
                 font=("Segoe UI", 12, "bold"),
                 bg="#25d366", fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg_card"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body,
                 text="Numéro WhatsApp du client (avec indicatif, ex: +221XXXXXXXXX) :",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w")
        self.var_tel = tk.StringVar(value=telephone)
        tk.Entry(body, textvariable=self.var_tel,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor="#25d366"
                 ).pack(fill="x", ipady=7, pady=(2, 12))

        tk.Label(body, text="Message :",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_light"]).pack(anchor="w")
        self.txt_msg = tk.Text(body, font=FONTS["body"],
                               relief="flat", bd=0, height=6,
                               bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                               highlightbackground=COLORS["border"], highlightthickness=1,
                               wrap="word")
        self.txt_msg.pack(fill="x", pady=(2, 12))
        self.txt_msg.insert("1.0", message)

        pdf_frame = tk.Frame(body, bg="#f0fdf4",
                             highlightbackground="#bbf7d0", highlightthickness=1)
        pdf_frame.pack(fill="x", pady=(0, 12))
        tk.Label(pdf_frame, text="📄  Fichier PDF à joindre manuellement :",
                 font=FONTS["small"], bg="#f0fdf4", fg="#166534"
                 ).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(pdf_frame, text=os.path.basename(self.pdf_path),
                 font=("Consolas", 9), bg="#f0fdf4", fg="#15803d"
                 ).pack(anchor="w", padx=10, pady=(0, 4))
        tk.Label(pdf_frame,
                 text="ℹ️  WhatsApp Web s\'ouvrira avec votre message. Joignez ensuite le PDF via l\'icône trombone.",
                 font=FONTS["small"], bg="#f0fdf4", fg="#166534",
                 wraplength=430, justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

        btns = tk.Frame(body, bg=COLORS["bg_card"])
        btns.pack(fill="x")
        tk.Button(btns, text="📋 Copier chemin PDF",
                  command=lambda: (self.clipboard_clear(),
                                   self.clipboard_append(self.pdf_path)),
                  font=FONTS["small"],
                  bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2"
                  ).pack(side="left")
        tk.Button(btns, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="💬  Ouvrir WhatsApp Web",
                  command=self._ouvrir_whatsapp,
                  font=FONTS["body_bold"],
                  bg="#25d366", fg="white",
                  activebackground="#16a34a",
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(side="right")

    def _ouvrir_whatsapp(self):
        import webbrowser, urllib.parse
        tel = "".join(c for c in self.var_tel.get() if c.isdigit() or c == "+")
        msg = self.txt_msg.get("1.0", "end").strip()
        msg_enc = urllib.parse.quote(msg)
        url = (f"https://wa.me/{tel.lstrip('+')}?text={msg_enc}"
               if tel else f"https://web.whatsapp.com/send?text={msg_enc}")
        webbrowser.open(url)
        messagebox.showinfo(
            "💬 WhatsApp ouvert",
            "WhatsApp Web s\'est ouvert dans votre navigateur.\n\n"
            "Pour joindre le PDF :\n"
            "1. Sélectionnez la conversation\n"
            "2. Cliquez sur l\'icône 📎 (trombone)\n"
            "3. Choisissez le fichier PDF",
            parent=self
        )
        self.destroy()

"""