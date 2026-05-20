"""
FacturePro — Générateur de Licences (outil éditeur)
=====================================================
Interface graphique autonome pour générer les clés de licence clients.
Ce fichier est RÉSERVÉ À L'ÉDITEUR — ne pas distribuer aux clients.

Usage : python generateur_licence.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
import sys
import os

# Permettre l'import de licence.py depuis le même dossier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importer les fonctions de génération (sans app_path car outil standalone)
# On redéfinit app_path localement pour éviter la dépendance
import types
_ap_mod = types.ModuleType("app_path")
_ap_mod.app_path = lambda *a: os.path.join(os.path.dirname(os.path.abspath(__file__)), *a)
sys.modules["app_path"] = _ap_mod

from licence import (
    generate_unlimited_key,
    generate_timed_key,
    verify_key,
    get_machine_id,
    TYPE_UNLIMITED,
    TYPE_TIMED,
    COLORS,
    FONTS,
)

# ─── Palette étendue pour le générateur ───────────────────────────────────────
GEN_COLORS = {
    **COLORS,
    "unlimited_bg":  "#0d2b1a",
    "unlimited_bd":  "#166534",
    "unlimited_fg":  "#34d399",
    "timed_bg":      "#1c1207",
    "timed_bd":      "#92400e",
    "timed_fg":      "#fbbf24",
    "result_bg":     "#0f172a",
    "tab_active":    "#1a56db",
    "tab_inactive":  "#1e293b",
    "row_bg":        "#162032",
    "row_alt":       "#1a2640",
}

# ─── Historique en mémoire ─────────────────────────────────────────────────────
_history: list[dict] = []


class GenerateurApp(tk.Tk):
    """Application principale du générateur de licences FacturePro."""

    def __init__(self):
        super().__init__()
        self.title("🔑  FacturePro — Générateur de Licences")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)
        w, h = 860, 680
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(760, 580)
        self._build()

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRUCTION UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Topbar ────────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=COLORS["primary"], height=62)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="🔑  Générateur de Licences FacturePro",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["primary"], fg="white").pack(side="left", padx=24, pady=14)
        tk.Label(top, text="⚠️  Outil éditeur — Confidentiel",
                 font=FONTS["small"], bg=COLORS["primary"], fg="#fde68a"
                 ).pack(side="right", padx=24)

        # ── Corps principal : panneau gauche + droit ──────────────────────────
        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=0, pady=0)

        # Panneau gauche : formulaires de génération
        left = tk.Frame(main, bg=COLORS["bg"], width=440)
        left.pack(side="left", fill="both", expand=False, padx=(16, 8), pady=14)
        left.pack_propagate(False)

        # Panneau droit : résultat + historique + vérificateur
        right = tk.Frame(main, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=14)

        self._build_left(left)
        self._build_right(right)

    # ─── Panneau gauche ───────────────────────────────────────────────────────

    def _build_left(self, parent):
        # Section Machine ID saisie
        self._section(parent, "🖥  Machine ID du client")

        mid_frame = tk.Frame(parent, bg=COLORS["input_bg"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
        mid_frame.pack(fill="x", pady=(0, 4))

        self.var_mid = tk.StringVar()
        self.var_mid.trace("w", self._on_mid_change)
        tk.Entry(mid_frame, textvariable=self.var_mid,
                 font=FONTS["mono"], relief="flat", bd=0,
                 bg=COLORS["input_bg"], fg="#34d399",
                 highlightthickness=0, insertbackground="#34d399"
                 ).pack(fill="x", padx=10, ipady=9)

        mid_btns = tk.Frame(parent, bg=COLORS["bg"])
        mid_btns.pack(fill="x", pady=(4, 12))

        tk.Button(mid_btns, text="📋 Coller",
                  command=self._coller_mid,
                  font=FONTS["small"], bg="#374151", fg="white",
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2"
                  ).pack(side="left")
        tk.Button(mid_btns, text="🖥 ID de cette machine",
                  command=self._utiliser_machine_locale,
                  font=FONTS["small"], bg="#374151", fg="#94a3b8",
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2"
                  ).pack(side="left", padx=(8, 0))

        self.lbl_mid_status = tk.Label(mid_btns, text="",
                                       font=FONTS["small"], bg=COLORS["bg"])
        self.lbl_mid_status.pack(side="right")

        # Nom du client (optionnel, pour l'historique)
        self._section(parent, "👤  Nom du client (optionnel)")
        self.var_client = tk.StringVar()
        tk.Entry(parent, textvariable=self.var_client,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["input_bg"], fg=COLORS["text"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"], insertbackground="white"
                 ).pack(fill="x", ipady=7, pady=(0, 14))

        # ── Onglets type de licence ───────────────────────────────────────────
        self._section(parent, "📋  Type de licence")

        tab_bar = tk.Frame(parent, bg=COLORS["bg"])
        tab_bar.pack(fill="x", pady=(0, 0))

        self.var_type = tk.StringVar(value=TYPE_UNLIMITED)

        self.btn_tab_unlimited = tk.Button(
            tab_bar, text="🔓  Illimitée",
            command=lambda: self._switch_tab(TYPE_UNLIMITED),
            font=FONTS["bold"],
            bg=GEN_COLORS["unlimited_bg"], fg=GEN_COLORS["unlimited_fg"],
            relief="flat", bd=0, padx=20, pady=9, cursor="hand2",
            highlightbackground=GEN_COLORS["unlimited_bd"], highlightthickness=2
        )
        self.btn_tab_unlimited.pack(side="left", expand=True, fill="x")

        self.btn_tab_timed = tk.Button(
            tab_bar, text="⏳  Durée déterminée",
            command=lambda: self._switch_tab(TYPE_TIMED),
            font=FONTS["bold"],
            bg=COLORS["card"], fg=COLORS["text_dim"],
            relief="flat", bd=0, padx=20, pady=9, cursor="hand2",
        )
        self.btn_tab_timed.pack(side="left", expand=True, fill="x")

        # ── Panneau illimitée ─────────────────────────────────────────────────
        self.frame_unlimited = tk.Frame(parent, bg=GEN_COLORS["unlimited_bg"],
                                        highlightbackground=GEN_COLORS["unlimited_bd"],
                                        highlightthickness=1)
        self.frame_unlimited.pack(fill="x")

        tk.Label(self.frame_unlimited,
                 text="✅  Accès permanent, sans date limite.\n"
                      "La clé reste valable à vie sur la machine cliente.",
                 font=FONTS["small"], bg=GEN_COLORS["unlimited_bg"],
                 fg=GEN_COLORS["unlimited_fg"], justify="left"
                 ).pack(anchor="w", padx=16, pady=14)

        # ── Panneau durée déterminée ──────────────────────────────────────────
        self.frame_timed = tk.Frame(parent, bg=GEN_COLORS["timed_bg"],
                                    highlightbackground=GEN_COLORS["timed_bd"],
                                    highlightthickness=1)

        tk.Label(self.frame_timed, text="📅  Date d'expiration",
                 font=FONTS["bold"], bg=GEN_COLORS["timed_bg"],
                 fg=GEN_COLORS["timed_fg"]
                 ).pack(anchor="w", padx=16, pady=(14, 4))

        date_row = tk.Frame(self.frame_timed, bg=GEN_COLORS["timed_bg"])
        date_row.pack(fill="x", padx=16, pady=(0, 8))

        # Spinners jour/mois/année
        today = date.today()
        default_expiry = today + timedelta(days=365)

        self.var_day   = tk.StringVar(value=str(default_expiry.day))
        self.var_month = tk.StringVar(value=str(default_expiry.month))
        self.var_year  = tk.StringVar(value=str(default_expiry.year))

        for label, var, vals, w_px in [
            ("Jour",    self.var_day,   [str(i) for i in range(1, 32)],  50),
            ("Mois",    self.var_month, [str(i) for i in range(1, 13)],  50),
            ("Année",   self.var_year,  [str(y) for y in range(today.year, today.year + 11)], 70),
        ]:
            col = tk.Frame(date_row, bg=GEN_COLORS["timed_bg"])
            col.pack(side="left", padx=(0, 10))
            tk.Label(col, text=label, font=FONTS["small"],
                     bg=GEN_COLORS["timed_bg"], fg="#d97706").pack(anchor="w")
            cb = ttk.Combobox(col, textvariable=var, values=vals,
                              width=int(w_px / 8), state="readonly",
                              font=FONTS["body"])
            cb.pack()
            cb.bind("<<ComboboxSelected>>", self._update_expiry_label)

        # Raccourcis durée
        shortcuts = tk.Frame(self.frame_timed, bg=GEN_COLORS["timed_bg"])
        shortcuts.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(shortcuts, text="Raccourcis :", font=FONTS["small"],
                 bg=GEN_COLORS["timed_bg"], fg="#d97706").pack(side="left")
        for label, days in [("1 mois", 30), ("3 mois", 90),
                             ("6 mois", 182), ("1 an", 365), ("2 ans", 730)]:
            tk.Button(shortcuts, text=label,
                      command=lambda d=days: self._set_expiry_days(d),
                      font=FONTS["small"],
                      bg="#451a03", fg="#fbbf24",
                      relief="flat", bd=0, padx=8, pady=3, cursor="hand2"
                      ).pack(side="left", padx=(6, 0))

        self.lbl_expiry_preview = tk.Label(self.frame_timed, text="",
                                           font=FONTS["small"],
                                           bg=GEN_COLORS["timed_bg"], fg="#fbbf24")
        self.lbl_expiry_preview.pack(anchor="w", padx=16, pady=(0, 10))
        self._update_expiry_label()

        # Montrer le bon panneau
        self._switch_tab(TYPE_UNLIMITED)

        # Bouton générer
        tk.Frame(parent, bg=COLORS["bg"], height=12).pack()
        tk.Button(parent, text="⚡  GÉNÉRER LA CLÉ",
                  command=self._generer,
                  font=("Segoe UI", 12, "bold"),
                  bg=COLORS["accent"], fg="white",
                  activebackground="#059669",
                  relief="flat", bd=0, pady=14, cursor="hand2"
                  ).pack(fill="x")

    # ─── Panneau droit ────────────────────────────────────────────────────────

    def _build_right(self, parent):
        # ── Résultat de génération ────────────────────────────────────────────
        self._section(parent, "🔑  Clé générée")

        result_frame = tk.Frame(parent, bg=GEN_COLORS["result_bg"],
                                highlightbackground=COLORS["border"], highlightthickness=1)
        result_frame.pack(fill="x", pady=(0, 4))

        self.var_result = tk.StringVar(value="Aucune clé générée")
        self.lbl_result = tk.Label(result_frame, textvariable=self.var_result,
                                   font=("Consolas", 13, "bold"),
                                   bg=GEN_COLORS["result_bg"], fg="#a3e635",
                                   wraplength=360, justify="center")
        self.lbl_result.pack(pady=18, padx=10)

        result_btns = tk.Frame(parent, bg=COLORS["bg"])
        result_btns.pack(fill="x", pady=(0, 6))
        tk.Button(result_btns, text="📋 Copier la clé",
                  command=self._copier_cle,
                  font=FONTS["bold"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
                  ).pack(side="left")

        self.lbl_result_info = tk.Label(result_btns, text="",
                                        font=FONTS["small"], bg=COLORS["bg"],
                                        fg=COLORS["text_dim"])
        self.lbl_result_info.pack(side="left", padx=12)

        # ── Vérificateur de clé ───────────────────────────────────────────────
        self._section(parent, "🔍  Vérifier une clé existante")

        verif_frame = tk.Frame(parent, bg=COLORS["card"],
                               highlightbackground=COLORS["border"], highlightthickness=1)
        verif_frame.pack(fill="x", pady=(0, 8))

        v_body = tk.Frame(verif_frame, bg=COLORS["card"], padx=14, pady=10)
        v_body.pack(fill="x")

        tk.Label(v_body, text="Machine ID :", font=FONTS["small"],
                 bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor="w")
        self.var_verif_mid = tk.StringVar()
        tk.Entry(v_body, textvariable=self.var_verif_mid,
                 font=FONTS["mono"], relief="flat", bd=0,
                 bg=COLORS["input_bg"], fg="#34d399",
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 insertbackground="#34d399"
                 ).pack(fill="x", ipady=6, pady=(2, 8))

        tk.Label(v_body, text="Clé à vérifier :", font=FONTS["small"],
                 bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor="w")
        self.var_verif_key = tk.StringVar()
        tk.Entry(v_body, textvariable=self.var_verif_key,
                 font=FONTS["mono"], relief="flat", bd=0,
                 bg=COLORS["input_bg"], fg="white",
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 insertbackground="white"
                 ).pack(fill="x", ipady=6, pady=(2, 8))

        v_btns = tk.Frame(v_body, bg=COLORS["card"])
        v_btns.pack(fill="x")
        tk.Button(v_btns, text="🔍 Vérifier", command=self._verifier,
                  font=FONTS["bold"], bg="#0891b2", fg="white",
                  relief="flat", bd=0, padx=16, pady=7, cursor="hand2"
                  ).pack(side="left")
        self.lbl_verif_result = tk.Label(v_btns, text="",
                                         font=FONTS["small"],
                                         bg=COLORS["card"])
        self.lbl_verif_result.pack(side="left", padx=12)

        # ── Historique ────────────────────────────────────────────────────────
        self._section(parent, "📋  Historique de session")

        hist_frame = tk.Frame(parent, bg=COLORS["bg"])
        hist_frame.pack(fill="both", expand=True)

        scrolly = ttk.Scrollbar(hist_frame, orient="vertical")
        scrolly.pack(side="right", fill="y")

        style = ttk.Style()
        style.configure("Gen.Treeview",
            background=COLORS["card"], foreground=COLORS["text"],
            rowheight=28, fieldbackground=COLORS["card"],
            borderwidth=0, font=FONTS["small"],
        )
        style.configure("Gen.Treeview.Heading",
            background="#1e293b", foreground=COLORS["text_dim"],
            font=FONTS["small"], relief="flat",
        )
        style.map("Gen.Treeview",
            background=[("selected", "#2d3f5a")],
            foreground=[("selected", "white")],
        )

        self.tree = ttk.Treeview(
            hist_frame,
            columns=("client", "type", "expiry", "key"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Gen.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        for col_id, label, width, anchor in [
            ("client", "Client",       120, "w"),
            ("type",   "Type",          80, "center"),
            ("expiry", "Expiration",    90, "center"),
            ("key",    "Clé",          230, "w"),
        ]:
            self.tree.heading(col_id, text=label)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=40)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("unlimited", foreground="#34d399")
        self.tree.tag_configure("timed",     foreground="#fbbf24")
        self.tree.bind("<Double-1>", self._copier_depuis_historique)

        hist_btns = tk.Frame(parent, bg=COLORS["bg"])
        hist_btns.pack(fill="x", pady=(4, 0))
        tk.Button(hist_btns, text="📋 Copier sélection",
                  command=self._copier_depuis_historique,
                  font=FONTS["small"], bg="#374151", fg="white",
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2"
                  ).pack(side="left")
        tk.Button(hist_btns, text="🗑 Vider",
                  command=self._vider_historique,
                  font=FONTS["small"], bg="#374151", fg="#ef4444",
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2"
                  ).pack(side="left", padx=(8, 0))
        tk.Label(hist_btns,
                 text="Double-clic pour copier",
                 font=FONTS["small"], bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    # LOGIQUE
    # ─────────────────────────────────────────────────────────────────────────

    def _section(self, parent, title):
        lbl = tk.Label(parent, text=title, font=FONTS["bold"],
                       bg=COLORS["bg"], fg=COLORS["text_dim"])
        lbl.pack(anchor="w", pady=(10, 3))
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", pady=(0, 6))

    def _switch_tab(self, tab_type):
        self.var_type.set(tab_type)
        if tab_type == TYPE_UNLIMITED:
            self.frame_timed.pack_forget()
            self.frame_unlimited.pack(fill="x")
            self.btn_tab_unlimited.config(
                bg=GEN_COLORS["unlimited_bg"], fg=GEN_COLORS["unlimited_fg"],
                highlightbackground=GEN_COLORS["unlimited_bd"], highlightthickness=2)
            self.btn_tab_timed.config(
                bg=COLORS["card"], fg=COLORS["text_dim"], highlightthickness=0)
        else:
            self.frame_unlimited.pack_forget()
            self.frame_timed.pack(fill="x")
            self.btn_tab_timed.config(
                bg=GEN_COLORS["timed_bg"], fg=GEN_COLORS["timed_fg"],
                highlightbackground=GEN_COLORS["timed_bd"], highlightthickness=2)
            self.btn_tab_unlimited.config(
                bg=COLORS["card"], fg=COLORS["text_dim"], highlightthickness=0)

    def _on_mid_change(self, *_):
        mid = self.var_mid.get().strip()
        if len(mid) > 8:
            self.lbl_mid_status.config(text="✅", fg="#34d399")
        elif mid:
            self.lbl_mid_status.config(text="…", fg=COLORS["text_dim"])
        else:
            self.lbl_mid_status.config(text="")

    def _coller_mid(self):
        try:
            self.var_mid.set(self.clipboard_get().strip())
        except Exception:
            pass

    def _utiliser_machine_locale(self):
        mid = get_machine_id()
        self.var_mid.set(mid)
        self.lbl_mid_status.config(text="🖥 Machine locale", fg="#60a5fa")

    def _set_expiry_days(self, days):
        d = date.today() + timedelta(days=days)
        self.var_day.set(str(d.day))
        self.var_month.set(str(d.month))
        self.var_year.set(str(d.year))
        self._update_expiry_label()

    def _update_expiry_label(self, *_):
        try:
            d = self._get_expiry_date()
            days_left = (d - date.today()).days
            self.lbl_expiry_preview.config(
                text=f"⏰ Expire le {d.strftime('%d/%m/%Y')} ({days_left} jour(s) à partir d'aujourd'hui)"
            )
        except Exception:
            self.lbl_expiry_preview.config(text="⚠️ Date invalide")

    def _get_expiry_date(self) -> date:
        return date(int(self.var_year.get()),
                    int(self.var_month.get()),
                    int(self.var_day.get()))

    def _generer(self):
        mid = self.var_mid.get().strip()
        if not mid:
            messagebox.showwarning("Machine ID manquant",
                                   "Veuillez entrer l'identifiant machine du client.",
                                   parent=self)
            return

        lic_type = self.var_type.get()
        client   = self.var_client.get().strip() or "—"

        if lic_type == TYPE_UNLIMITED:
            key = generate_unlimited_key(mid)
            expiry_label = "Illimitée"
            expiry_val   = None
        else:
            try:
                expiry_val = self._get_expiry_date()
                if expiry_val < date.today():
                    messagebox.showwarning("Date passée",
                                           "La date d'expiration est dans le passé.",
                                           parent=self)
                    return
                key = generate_timed_key(mid, expiry_val)
                expiry_label = expiry_val.strftime("%d/%m/%Y")
            except Exception as e:
                messagebox.showerror("Date invalide", str(e), parent=self)
                return

        # Afficher le résultat
        self.var_result.set(key)
        type_label = "🔓 Illimitée" if lic_type == TYPE_UNLIMITED else f"⏳ Jusqu'au {expiry_label}"
        self.lbl_result_info.config(text=f"{type_label}  •  {client}",
                                    fg=GEN_COLORS["unlimited_fg"] if lic_type == TYPE_UNLIMITED
                                    else GEN_COLORS["timed_fg"])

        # Ajouter à l'historique
        entry = {
            "client":  client,
            "type":    lic_type,
            "expiry":  expiry_label,
            "key":     key,
            "mid":     mid,
            "generated_at": datetime.now().strftime("%H:%M:%S"),
        }
        _history.insert(0, entry)

        tag = "unlimited" if lic_type == TYPE_UNLIMITED else "timed"
        self.tree.insert("", 0, values=(
            client,
            "♾ Illimitée" if lic_type == TYPE_UNLIMITED else "⏳ Datée",
            expiry_label,
            key,
        ), tags=(tag,))

        # Copier automatiquement dans le presse-papiers
        self.clipboard_clear()
        self.clipboard_append(key)
        self.lbl_result_info.config(
            text=self.lbl_result_info.cget("text") + "  (copié !)"
        )

    def _copier_cle(self):
        key = self.var_result.get()
        if key and key != "Aucune clé générée":
            self.clipboard_clear()
            self.clipboard_append(key)
            messagebox.showinfo("📋 Copié", "Clé copiée dans le presse-papiers.", parent=self)

    def _verifier(self):
        mid = self.var_verif_mid.get().strip()
        key = self.var_verif_key.get().strip()

        if not mid or not key:
            self.lbl_verif_result.config(
                text="⚠️ Remplissez les deux champs.", fg=COLORS["warning"])
            return

        result = verify_key(key, mid)

        if result["valid"]:
            if result.get("days_left") is not None:
                msg = f"✅ Valide — expire {result['expiry'].strftime('%d/%m/%Y')} ({result['days_left']}j)"
                fg = GEN_COLORS["timed_fg"]
            else:
                msg = "✅ Valide — Licence illimitée"
                fg = GEN_COLORS["unlimited_fg"]
        elif result.get("expired"):
            msg = f"❌ Expirée — {result['expiry'].strftime('%d/%m/%Y')}"
            fg = COLORS["danger"]
        else:
            msg = f"❌ Invalide — {result['message']}"
            fg = COLORS["danger"]

        self.lbl_verif_result.config(text=msg, fg=fg)

    def _copier_depuis_historique(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        if vals:
            key = vals[3]
            self.clipboard_clear()
            self.clipboard_append(key)
            messagebox.showinfo("📋 Copié", f"Clé copiée :\n{key}", parent=self)

    def _vider_historique(self):
        if messagebox.askyesno("Vider l'historique",
                               "Supprimer tout l'historique de cette session ?",
                               parent=self):
            _history.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = GenerateurApp()
    app.mainloop()
