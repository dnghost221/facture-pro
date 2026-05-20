"""
Fenêtre de paramètres
Permet de modifier toutes les informations de la facture sans toucher au code.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import os

import config as cfg
from licence import LicenceInfoWindow


COLORS = {
    "bg_main":      "#f8fafc",
    "bg_card":      "#ffffff",
    "primary":      "#1a56db",
    "primary_dark": "#0d3d91",
    "primary_light":"#eff6ff",
    "accent":       "#10b981",
    "danger":       "#ef4444",
    "text_dark":    "#111827",
    "text_light":   "#9ca3af",
    "border":       "#e5e7eb",
}

FONTS = {
    "title":     ("Segoe UI", 15, "bold"),
    "heading":   ("Segoe UI", 11, "bold"),
    "subhead":   ("Segoe UI", 10, "bold"),
    "body":      ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
}


class ParametresWindow(tk.Toplevel):
    """Fenêtre de paramètres complète avec onglets."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️  Paramètres — FacturePro")
        self.geometry("620x590")
        self.minsize(560, 500)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()
        self.geometry(f"810x730+{parent.winfo_x()+80}+{parent.winfo_y()+50}")

        # Charger la config actuelle
        self.cfg = cfg.load()

        # Variables Tkinter (une par champ)
        self._vars = {}

        self._build()
        self._charger_valeurs()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        # En-tête
        header = tk.Frame(self, bg=COLORS["primary"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="⚙️  Paramètres de la Facture",
                 font=FONTS["title"], bg=COLORS["primary"], fg="white"
                 ).pack(side="left", padx=20, pady=12)

        # Notebook (onglets)
        style = ttk.Style()
        style.configure("Param.TNotebook", background=COLORS["bg_main"], borderwidth=0)
        style.configure("Param.TNotebook.Tab",
                        font=FONTS["body_bold"], padding=[14, 6])
        style.map("Param.TNotebook.Tab",
                  background=[("selected", COLORS["primary"]),
                               ("!selected", COLORS["bg_card"])],
                  foreground=[("selected", "white"),
                               ("!selected", COLORS["text_dark"])])

        nb = ttk.Notebook(self, style="Param.TNotebook")
        nb.pack(fill="both", expand=True, padx=14, pady=10)

        # ── Onglet 1 : Commerce ───────────────────────────────────────────────
        tab1 = self._scrollable_tab(nb)
        nb.add(tab1["frame"], text="🏪  Commerce")
        body1 = tab1["body"]

        self._section(body1, "Identité du commerce")
        self._field(body1, "Nom du commerce",    "nom")
        self._field(body1, "Slogan",             "slogan")
        self._field(body1, "Adresse",            "adresse")
        self._field(body1, "Téléphone",          "telephone")
        self._field(body1, "RC",             "RC")
        self._field(body1, "NINEA",              "NINEA")

        # ── Onglet 2 : Logo ───────────────────────────────────────────────────
        tab2 = self._scrollable_tab(nb)
        nb.add(tab2["frame"], text="🖼  Logo")
        body2 = tab2["body"]

        self._section(body2, "Fichier logo")
        self._field_logo(body2)

        self._section(body2, "Taille du logo sur la facture")
        self._field_number(body2, "Largeur maximale (mm)", "logo_largeur_mm", 10, 100)
        self._field_number(body2, "Hauteur maximale (mm)", "logo_hauteur_mm", 5,  50)

        tk.Label(body2,
                 text="ℹ️  Le ratio original du logo est conservé automatiquement.",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 wraplength=480, justify="left"
                 ).pack(anchor="w", padx=4, pady=(0, 8))

        # ── Onglet 3 : Apparence ──────────────────────────────────────────────
        tab3 = self._scrollable_tab(nb)
        nb.add(tab3["frame"], text="🎨  Apparence")
        body3 = tab3["body"]

        self._section(body3, "Couleurs de la facture PDF")
        self._field_color(body3, "Couleur principale (en-tête, titres)", "couleur_primaire")
        self._field_color(body3, "Couleur accent (bande total)",          "couleur_accent")

        self._section(body3, "Texte de l'en-tête")
        self._field(body3, "Titre facture (ex: FACTURE, DEVIS…)", "titre_facture")

        # ── Onglet 4 : Textes ─────────────────────────────────────────────────
        tab4 = self._scrollable_tab(nb)
        nb.add(tab4["frame"], text="✏️  Textes")
        body4 = tab4["body"]

        self._section(body4, "Messages en bas de facture")
        self._field(body4, "Message de remerciement",  "message_remerciement")
        self._field(body4, "Mention de paiement",      "mention_paiement")

        self._section(body4, "Dossier de sortie des PDFs")
        self._field_dossier(body4)

        # ── Onglet 5 : Signature & Cachet ────────────────────────────────────
        tab5 = self._scrollable_tab(nb)
        nb.add(tab5["frame"], text="✍️  Signature")
        body5 = tab5["body"]

        self._section(body5, "Image de signature")
        tk.Label(body5,
                 text="Image apposée dans la zone signature du PDF (PNG, JPG, BMP, ICO…).",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 wraplength=480, justify="left").pack(anchor="w", pady=(0, 6))
        self._field_image(body5, "Fichier signature", "signature_path", "sig")
        self._field_number(body5, "Largeur max (mm)", "signature_largeur_mm", 10, 100)
        self._field_number(body5, "Hauteur max (mm)", "signature_hauteur_mm",  5,  60)
        self._field_bool(body5, "Afficher la signature sur le PDF", "afficher_signature")

        self._section(body5, "Image du cachet / tampon")
        tk.Label(body5,
                 text="Image du cachet ou tampon officiel (PNG, JPG, BMP, ICO…).",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 wraplength=480, justify="left").pack(anchor="w", pady=(0, 6))
        self._field_image(body5, "Fichier cachet", "cachet_path", "cachet")
        self._field_number(body5, "Largeur max (mm)", "cachet_largeur_mm", 10, 100)
        self._field_number(body5, "Hauteur max (mm)", "cachet_hauteur_mm",  5,  60)
        self._field_bool(body5, "Afficher le cachet sur le PDF", "afficher_cachet")

        # ── Onglet 6 : Méthodes de paiement ──────────────────────────────────
        tab6 = tk.Frame(nb, bg=COLORS["bg_card"])
        nb.add(tab6, text="💳  Paiements")
        self._build_paiements_tab(tab6)

        # ── Onglet 7 : Licence ────────────────────────────────────────────────
        tab7 = self._scrollable_tab(nb)
        nb.add(tab7["frame"], text="🔑  Licence")
        body7 = tab7["body"]
        self._build_licence_tab(body7)

        # ── Barre de boutons bas ──────────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=COLORS["bg_main"])
        btn_bar.pack(fill="x", padx=14, pady=(0, 14))

        tk.Button(btn_bar, text="↩  Réinitialiser", command=self._reinitialiser,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="left")

        tk.Button(btn_bar, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))

        tk.Button(btn_bar, text="✔  Enregistrer", command=self._enregistrer,
                  font=FONTS["body_bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2"
                  ).pack(side="right")

    # ── Helpers de construction ───────────────────────────────────────────────

    def _scrollable_tab(self, parent):
        """Crée un onglet avec scrollbar verticale."""
        outer = tk.Frame(parent, bg=COLORS["bg_card"])
        canvas = tk.Canvas(outer, bg=COLORS["bg_card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=COLORS["bg_card"], padx=20, pady=10)

        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Molette souris
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        return {"frame": outer, "body": body}

    def _section(self, parent, title):
        """Titre de section avec séparateur."""
        tk.Label(parent, text=title, font=FONTS["subhead"],
                 bg=COLORS["bg_card"], fg=COLORS["primary"]
                 ).pack(anchor="w", pady=(14, 2))
        tk.Frame(parent, bg=COLORS["primary"], height=2).pack(fill="x", pady=(0, 8))

    def _field(self, parent, label, key):
        """Champ texte standard."""
        tk.Label(parent, text=label, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(anchor="w")
        var = tk.StringVar()
        self._vars[key] = var
        tk.Entry(parent, textvariable=var, font=FONTS["body"],
                 relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"],
                 highlightthickness=1, highlightcolor=COLORS["primary"],
                 ).pack(fill="x", ipady=6, pady=(0, 6))

    def _field_number(self, parent, label, key, min_val, max_val):
        """Champ numérique avec Spinbox."""
        tk.Label(parent, text=label, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(anchor="w")
        var = tk.IntVar()
        self._vars[key] = var
        ttk.Spinbox(parent, textvariable=var, from_=min_val, to=max_val,
                    font=FONTS["body"], width=8
                    ).pack(anchor="w", pady=(0, 6))

    def _field_logo(self, parent):
        """Champ spécial pour le chemin du logo avec bouton Parcourir."""
        tk.Label(parent, text="Chemin du fichier logo (PNG, JPG)",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(anchor="w")

        row = tk.Frame(parent, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=(0, 6))

        var = tk.StringVar()
        self._vars["logo_path"] = var

        tk.Entry(row, textvariable=var, font=FONTS["body"],
                 relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"],
                 highlightthickness=1, highlightcolor=COLORS["primary"],
                 ).pack(side="left", fill="x", expand=True, ipady=6)

        tk.Button(row, text="📁 Parcourir", command=self._choisir_logo,
                  font=FONTS["small"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2"
                  ).pack(side="right", padx=(6, 0))

    def _field_dossier(self, parent):
        """Champ spécial pour le dossier de sortie avec bouton Parcourir."""
        tk.Label(parent, text="Dossier d'enregistrement des factures PDF",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(anchor="w")

        row = tk.Frame(parent, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=(0, 6))

        var = tk.StringVar()
        self._vars["dossier_factures"] = var

        tk.Entry(row, textvariable=var, font=FONTS["body"],
                 relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"],
                 highlightthickness=1, highlightcolor=COLORS["primary"],
                 ).pack(side="left", fill="x", expand=True, ipady=6)

        tk.Button(row, text="📁 Parcourir", command=self._choisir_dossier,
                  font=FONTS["small"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2"
                  ).pack(side="right", padx=(6, 0))

        tk.Label(parent,
                 text="ℹ️  Le dossier sera créé automatiquement s'il n'existe pas.",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 ).pack(anchor="w", pady=(0, 8))

    def _choisir_dossier(self):
        """Ouvre un explorateur pour choisir le dossier de sortie."""
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier d'enregistrement des factures",
            initialdir=self._vars["dossier_factures"].get() or os.path.expanduser("~"),
        )
        if dossier:
            self._vars["dossier_factures"].set(dossier)

    def _field_color(self, parent, label, key):
        """Champ couleur avec aperçu et sélecteur."""
        tk.Label(parent, text=label, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]
                 ).pack(anchor="w")

        row = tk.Frame(parent, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=(0, 8))

        var = tk.StringVar()
        self._vars[key] = var

        # Aperçu couleur
        preview = tk.Label(row, width=4, relief="flat",
                           highlightbackground=COLORS["border"], highlightthickness=1)
        preview.pack(side="left", padx=(0, 8), ipady=8)

        def update_preview(*_):
            try:
                preview.config(bg=var.get())
            except Exception:
                pass

        var.trace("w", update_preview)

        tk.Entry(row, textvariable=var, font=FONTS["mono"] if hasattr(FONTS, "mono") else FONTS["body"],
                 width=12, relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"],
                 highlightthickness=1, highlightcolor=COLORS["primary"],
                 ).pack(side="left", ipady=6)

        def choisir():
            couleur = colorchooser.askcolor(
                color=var.get(), title=f"Choisir : {label}", parent=self
            )
            if couleur and couleur[1]:
                var.set(couleur[1])

        tk.Button(row, text="🎨 Choisir", command=choisir,
                  font=FONTS["small"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2"
                  ).pack(side="left", padx=(8, 0))

    # ── Chargement / Sauvegarde ───────────────────────────────────────────────

    def _charger_valeurs(self):
        """Pré-remplit tous les champs avec les valeurs de config."""
        for key, var in self._vars.items():
            val = self.cfg.get(key, "")
            if isinstance(var, tk.BooleanVar):
                var.set(bool(val) if not isinstance(val, bool) else val)
            elif isinstance(var, tk.IntVar):
                try:
                    var.set(int(val))
                except Exception:
                    var.set(0)
            else:
                var.set(str(val))

    def _field_image(self, parent, label, key, tag):
        """Champ image avec aperçu miniature et bouton Parcourir."""
        tk.Label(parent, text=label, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_light"]).pack(anchor="w")

        row = tk.Frame(parent, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=(0, 6))

        var = tk.StringVar()
        self._vars[key] = var

        entry = tk.Entry(row, textvariable=var, font=FONTS["body"],
                         relief="flat", bd=0,
                         bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, highlightcolor=COLORS["primary"])
        entry.pack(side="left", fill="x", expand=True, ipady=6)

        # Aperçu miniature
        preview_lbl = tk.Label(row, text="", bg=COLORS["bg_card"],
                               width=5, relief="flat",
                               highlightbackground=COLORS["border"], highlightthickness=1)
        preview_lbl.pack(side="right", padx=(6, 0))

        def _update_preview(*_):
            path = var.get().strip()
            if path and os.path.isfile(path):
                try:
                    from PIL import Image as PilImage, ImageTk
                    img = PilImage.open(path)
                    img.thumbnail((48, 48))
                    photo = ImageTk.PhotoImage(img)
                    preview_lbl.config(image=photo, width=48, height=48)
                    preview_lbl._photo = photo  # garder la référence
                except Exception:
                    preview_lbl.config(image="", text="?", width=5)
            else:
                preview_lbl.config(image="", text="", width=5)

        var.trace("w", _update_preview)

        def _choisir():
            chemin = filedialog.askopenfilename(
                parent=self,
                title=f"Choisir : {label}",
                filetypes=[
                    ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.ico *.tiff *.webp"),
                    ("Tous les fichiers", "*.*")
                ]
            )
            if chemin:
                var.set(chemin)

        tk.Button(row, text="📁 Parcourir", command=_choisir,
                  font=FONTS["small"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2"
                  ).pack(side="right", padx=(6, 6))

    def _field_bool(self, parent, label, key):
        """Case à cocher pour un champ booléen."""
        var = tk.BooleanVar()
        self._vars[key] = var
        tk.Checkbutton(parent, text=label, variable=var,
                       font=FONTS["body"], bg=COLORS["bg_card"],
                       fg=COLORS["text_dark"], activebackground=COLORS["bg_card"],
                       selectcolor=COLORS["bg_card"], relief="flat",
                       cursor="hand2"
                       ).pack(anchor="w", pady=(0, 8))

    def _build_paiements_tab(self, parent):
        """Onglet de gestion des méthodes de paiement."""
        import database as db_mod

        header = tk.Frame(parent, bg=COLORS["primary_light"],
                          highlightbackground=COLORS["border"], highlightthickness=1)
        header.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(header,
                 text="Gérez les méthodes de paiement proposées lors des ventes.\n"
                      "Seules les méthodes actives apparaissent au comptoir.",
                 font=FONTS["small"], bg=COLORS["primary_light"],
                 fg=COLORS["text_dark"], justify="left"
                 ).pack(anchor="w", padx=10, pady=8)

        # Tableau
        tf = tk.Frame(parent, bg=COLORS["bg_card"])
        tf.pack(fill="both", expand=True, padx=16, pady=10)

        scrolly = ttk.Scrollbar(tf, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Pmt.Treeview",
            background=COLORS["bg_card"], foreground=COLORS["text_dark"],
            rowheight=32, fieldbackground=COLORS["bg_card"],
            borderwidth=0, font=FONTS["body"],
        )
        style.configure("Pmt.Treeview.Heading",
            background=COLORS["primary"], foreground="white",
            font=FONTS["body_bold"], relief="flat",
        )
        style.map("Pmt.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree_pmt = ttk.Treeview(
            tf,
            columns=("nom", "statut"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Pmt.Treeview",
        )
        scrolly.config(command=self.tree_pmt.yview)

        self.tree_pmt.heading("nom",    text="Méthode de paiement")
        self.tree_pmt.heading("statut", text="Statut")
        self.tree_pmt.column("nom",    width=350, anchor="w")
        self.tree_pmt.column("statut", width=100, anchor="center")
        self.tree_pmt.pack(side="left", fill="both", expand=True)
        self.tree_pmt.tag_configure("actif",   foreground=COLORS["accent"])
        self.tree_pmt.tag_configure("inactif", foreground=COLORS["text_light"])

        self._pmt_charger()

        # Formulaire ajout
        form = tk.Frame(parent, bg=COLORS["bg_card"],
                        highlightbackground=COLORS["border"], highlightthickness=1)
        form.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(form, text="Nouvelle méthode :",
                 font=FONTS["body_bold"], bg=COLORS["bg_card"],
                 fg=COLORS["primary"]).pack(side="left", padx=(12, 6), pady=10)

        self.var_new_pmt = tk.StringVar()
        tk.Entry(form, textvariable=self.var_new_pmt,
                 font=FONTS["body"], width=24, relief="flat", bd=0,
                 bg=COLORS["bg_main"], fg=COLORS["text_dark"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"]
                 ).pack(side="left", ipady=5, pady=8)

        tk.Button(form, text="＋  Ajouter",
                  command=self._pmt_ajouter,
                  font=FONTS["body_bold"], bg=COLORS["accent"], fg="white",
                  activebackground="#059669",
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
                  ).pack(side="left", padx=(8, 0), pady=8)

        # Actions
        action_bar = tk.Frame(parent, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
        action_bar.pack(fill="x", padx=16, pady=(0, 14))

        for txt, cmd, color in [
            ("✔  Activer/Désactiver", self._pmt_toggle,     COLORS["primary"]),
            ("✏️  Renommer",           self._pmt_renommer,   "#475569"),
            ("🗑  Supprimer",          self._pmt_supprimer,  COLORS["danger"]),
        ]:
            tk.Button(action_bar, text=txt, command=cmd,
                      font=FONTS["body_bold"], bg=color, fg="white",
                      relief="flat", bd=0, padx=12, pady=7, cursor="hand2"
                      ).pack(side="left", padx=4, pady=8)

    def _pmt_charger(self):
        """Recharge le tableau des méthodes de paiement."""
        import database as db_mod
        for item in self.tree_pmt.get_children():
            self.tree_pmt.delete(item)
        for m in db_mod.get_methodes_paiement(actif_seulement=False):
            tag = "actif" if m["actif"] else "inactif"
            statut = "✅ Actif" if m["actif"] else "⛔ Inactif"
            self.tree_pmt.insert("", "end", iid=str(m["id"]),
                values=(m["nom"], statut), tags=(tag,))

    def _pmt_selected_id(self):
        sel = self.tree_pmt.selection()
        if not sel:
            messagebox.showwarning("Aucune sélection",
                                   "Sélectionnez une méthode.", parent=self)
            return None
        return int(sel[0])

    def _pmt_ajouter(self):
        import database as db_mod
        nom = self.var_new_pmt.get().strip()
        if not nom:
            messagebox.showerror("Erreur", "Saisissez un nom.", parent=self)
            return
        try:
            db_mod.add_methode_paiement(nom)
            self.var_new_pmt.set("")
            self._pmt_charger()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def _pmt_toggle(self):
        import database as db_mod
        mid = self._pmt_selected_id()
        if mid is None:
            return
        vals = self.tree_pmt.item(str(mid))["values"]
        nom    = vals[0]
        actuel = "Actif" in vals[1]
        db_mod.update_methode_paiement(mid, nom, not actuel)
        self._pmt_charger()

    def _pmt_renommer(self):
        import database as db_mod
        from tkinter import simpledialog
        mid = self._pmt_selected_id()
        if mid is None:
            return
        ancien = self.tree_pmt.item(str(mid))["values"][0]
        nouveau = simpledialog.askstring(
            "Renommer", f"Nouveau nom pour « {ancien} » :",
            initialvalue=ancien, parent=self
        )
        if nouveau and nouveau.strip():
            db_mod.update_methode_paiement(mid, nouveau.strip(), True)
            self._pmt_charger()

    def _pmt_supprimer(self):
        import database as db_mod
        mid = self._pmt_selected_id()
        if mid is None:
            return
        nom = self.tree_pmt.item(str(mid))["values"][0]
        if messagebox.askyesno("Confirmer",
                               f"Supprimer « {nom} » ?", parent=self):
            db_mod.delete_methode_paiement(mid)
            self._pmt_charger()

    def _build_licence_tab(self, parent):
        """Construit l'onglet informations de licence."""
        from licence import get_licence_info, get_machine_id

        info = get_licence_info()

        if info["is_valid"]:
            days = info.get("days_left")
            if days is not None and days <= 7:
                sc = COLORS["warning"]
                st = f"⚠️  ACTIVE — expire dans {days} jour(s)"
            elif days is not None:
                sc = COLORS["accent"]
                st = f"✅  ACTIVE — {info['type_label']}"
            else:
                sc = COLORS["accent"]
                st = "✅  LICENCE ACTIVE — Illimitée"
        elif info.get("is_expired"):
            sc, st = COLORS["danger"], "❌  LICENCE EXPIRÉE"
        else:
            sc, st = COLORS["danger"], "❌  LICENCE INVALIDE"

        tk.Label(parent, text=st, font=("Segoe UI", 12, "bold"),
                 bg=COLORS["bg_card"], fg=sc).pack(anchor="w", pady=(0, 12))

        rows = [
            ("Titulaire",       info["titulaire"]),
            ("Type",            info.get("type_label", "—")),
            ("Expiration",      info.get("expiry_label", "—")),
            ("ID machine",      info["machine_id"]),
            ("Clé de licence",  info["licence_key"]),
            ("Activée le",      info["activated_at"]),
        ]
        for label, val in rows:
            row = tk.Frame(parent, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"  {label} :", width=16, anchor="w",
                     font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
                     ).pack(side="left", ipady=6)
            fnt = ("Consolas", 9) if label in ("ID machine", "Clé de licence") else FONTS["small"]
            tk.Label(row, text=val, font=fnt,
                     bg=COLORS["bg_card"], fg=COLORS["text_dark"], anchor="w"
                     ).pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(parent,
                 text="⚠️  Cette licence est liée à cette machine. Elle ne peut pas être transférée sur un autre ordinateur.",
                 font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"],
                 wraplength=460, justify="left").pack(anchor="w", pady=(14, 0))

        tk.Button(parent, text="ℹ️  Détails de la licence",
                  command=lambda: LicenceInfoWindow(self),
                  font=FONTS["body_bold"],
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"], activeforeground="white",
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(anchor="w", pady=(14, 0))

    def _choisir_logo(self):
        """Ouvre un explorateur de fichiers pour choisir le logo."""
        chemin = filedialog.askopenfilename(
            parent=self,
            title="Choisir le logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("Tous les fichiers", "*.*")]
        )
        if chemin:
            self._vars["logo_path"].set(chemin)

    def _enregistrer(self):
        """Valide et sauvegarde la configuration."""
        nouvelle_cfg = dict(self.cfg)

        for key, var in self._vars.items():
            if isinstance(var, tk.BooleanVar):
                nouvelle_cfg[key] = var.get()
            elif isinstance(var, tk.IntVar):
                nouvelle_cfg[key] = var.get()
            else:
                nouvelle_cfg[key] = var.get().strip()

        # Validation minimale
        if not nouvelle_cfg.get("nom"):
            messagebox.showerror("Erreur", "Le nom du commerce est obligatoire.", parent=self)
            return

        couleur_p = nouvelle_cfg.get("couleur_primaire", "")
        couleur_a = nouvelle_cfg.get("couleur_accent", "")
        for c, label in [(couleur_p, "couleur principale"), (couleur_a, "couleur accent")]:
            if c and not (c.startswith("#") and len(c) in (4, 7)):
                messagebox.showerror("Erreur",
                    f"La {label} doit être au format hexadécimal (#RRGGBB).", parent=self)
                return

        cfg.save(nouvelle_cfg)
        messagebox.showinfo("✅ Enregistré",
            "Les paramètres ont été sauvegardés.\n"
            "Ils seront appliqués à la prochaine facture générée.",
            parent=self)
        self.destroy()

    def _reinitialiser(self):
        """Réinitialise tous les champs aux valeurs par défaut."""
        if messagebox.askyesno("Réinitialiser",
                "Remettre tous les paramètres aux valeurs par défaut ?", parent=self):
            self.cfg = dict(cfg.DEFAULTS)
            self._charger_valeurs()