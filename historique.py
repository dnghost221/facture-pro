"""
Module de l'historique des factures
Fenêtre secondaire affichant toutes les factures passées avec recherche
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import platform
import subprocess

import database as db
from print_utils import PrintDialog
import pdf_generator as pdf_gen


COLORS = {
    "bg_main":      "#f8fafc",
    "bg_card":      "#ffffff",
    "primary":      "#1a56db",
    "primary_dark": "#0d3d91",
    "primary_light":"#eff6ff",
    "accent":       "#10b981",
    "danger":       "#ef4444",
    "text_dark":    "#111827",
    "text_medium":  "#374151",
    "text_light":   "#9ca3af",
    "border":       "#e5e7eb",
    "row_even":     "#f9fafb",
    "row_odd":      "#ffffff",
    "row_selected": "#dbeafe",
    "header_bg":    "#1a56db",
}

FONTS = {
    "title":    ("Segoe UI", 15, "bold"),
    "heading":  ("Segoe UI", 12, "bold"),
    "subhead":  ("Segoe UI", 10, "bold"),
    "body":     ("Segoe UI", 10),
    "body_bold":("Segoe UI", 10, "bold"),
    "small":    ("Segoe UI", 9),
}


class HistoriqueWindow(tk.Toplevel):
    """Fenêtre d'historique des factures."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("📋 Historique des Factures")
        self.geometry("820x560")
        self.minsize(700, 400)
        self.configure(bg=COLORS["bg_main"])
        self.grab_set()

        # Centrer
        self.geometry(f"820x560+{parent.winfo_x()+100}+{parent.winfo_y()+80}")

        self._build()
        self._charger_factures()

    def _build(self):
        """Construit l'interface."""
        # En-tête
        header = tk.Frame(self, bg=COLORS["primary"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="📋  Historique des Factures",
            font=FONTS["title"], bg=COLORS["primary"], fg="white"
        ).pack(side="left", padx=20, pady=12)

        # Barre de recherche
        search_frame = tk.Frame(self, bg=COLORS["bg_card"],
                                highlightbackground=COLORS["border"],
                                highlightthickness=1)
        search_frame.pack(fill="x", padx=16, pady=10)

        tk.Label(
            search_frame, text="🔍",
            font=FONTS["body"], bg=COLORS["bg_card"],
        ).pack(side="left", padx=(10, 4), pady=8)

        self.var_search = tk.StringVar()
        self.var_search.trace("w", lambda *a: self._rechercher())
        tk.Entry(
            search_frame, textvariable=self.var_search,
            font=FONTS["body"], relief="flat", bd=0,
            bg=COLORS["bg_card"], fg=COLORS["text_dark"],
            highlightthickness=0,
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=4)

        tk.Label(
            search_frame,
            text="Rechercher par numéro ou nom de client",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        ).pack(side="right", padx=12)

        # Tableau
        table_frame = tk.Frame(self, bg=COLORS["bg_main"])
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        scrolly = ttk.Scrollbar(table_frame, orient="vertical")
        scrolly.pack(side="right", fill="y")

        # Style
        style = ttk.Style()
        style.configure(
            "Hist.Treeview",
            background=COLORS["bg_card"],
            foreground=COLORS["text_dark"],
            rowheight=34,
            fieldbackground=COLORS["bg_card"],
            borderwidth=0,
            font=FONTS["body"],
        )
        style.configure(
            "Hist.Treeview.Heading",
            background=COLORS["header_bg"],
            foreground="white",
            font=FONTS["body_bold"],
            relief="flat",
        )
        style.map("Hist.Treeview",
            background=[("selected", COLORS["row_selected"])],
            foreground=[("selected", COLORS["text_dark"])],
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=("numero", "client", "telephone", "date", "total"),
            show="headings",
            yscrollcommand=scrolly.set,
            selectmode="browse",
            style="Hist.Treeview",
        )
        scrolly.config(command=self.tree.yview)

        cols = [
            ("numero",    "N° Facture",   160, "w"),
            ("client",    "Client",        220, "w"),
            ("telephone", "Téléphone",    120, "w"),
            ("date",      "Date",          100, "center"),
            ("total",     "Total",         100, "e"),
        ]
        for col_id, label, width, anchor in cols:
            self.tree.heading(col_id, text=label)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=60)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("even", background=COLORS["row_even"])
        self.tree.tag_configure("odd",  background=COLORS["row_odd"])

        # Barre d'actions
        action_bar = tk.Frame(self, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"],
                              highlightthickness=1)
        action_bar.pack(fill="x", padx=16, pady=(0, 12))

        buttons = [
            ("👁  Voir détails",    self._voir_details,    COLORS["primary"]),
            ("📄  Régénérer PDF",   self._regenerer_pdf,   COLORS["accent"]),
            ("🖨  Imprimer",        self._imprimer,        "#7c3aed"),
            ("✖  Fermer",          self.destroy,           "#6b7280"),
        ]
        for label, cmd, color in buttons:
            tk.Button(
                action_bar, text=label, command=cmd,
                font=FONTS["body_bold"],
                bg=color, fg="white",
                activebackground=COLORS["primary_dark"], activeforeground="white",
                relief="flat", bd=0, padx=16, pady=8, cursor="hand2"
            ).pack(side="left", padx=6, pady=8)

        # Compteur
        self.lbl_count = tk.Label(
            action_bar, text="",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_light"]
        )
        self.lbl_count.pack(side="right", padx=16)

    def _charger_factures(self, factures=None):
        """Charge et affiche les factures dans le tableau."""
        if factures is None:
            factures = db.get_all_invoices()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, f in enumerate(factures):
            tag = "even" if i % 2 == 0 else "odd"
            total_str = self._fmt_price(f.get("total", 0))
            self.tree.insert(
                "", "end",
                iid=str(f["id"]),
                values=(
                    f.get("numero_facture", ""),
                    f.get("client", ""),
                    f.get("telephone", ""),
                    f.get("date_facture", ""),
                    f"{total_str} FCFA",
                ),
                tags=(tag,)
            )

        self.lbl_count.config(text=f"{len(factures)} facture(s)")

    def _rechercher(self):
        """Effectue une recherche en temps réel."""
        query = self.var_search.get().strip()
        if query:
            factures = db.search_invoices(query)
        else:
            factures = db.get_all_invoices()
        self._charger_factures(factures)

    def _get_selected_id(self):
        """Retourne l'ID de la facture sélectionnée ou None."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Aucune sélection",
                "Veuillez sélectionner une facture.",
                parent=self
            )
            return None
        return int(sel[0])

    def _voir_details(self):
        """Affiche les détails d'une facture."""
        fid = self._get_selected_id()
        if fid is None:
            return

        sel = self.tree.item(str(fid))["values"]
        numero, client, tel, date, total = sel

        lignes = db.get_invoice_lines(fid)
        details = f"Facture : {numero}\nClient : {client}\nDate : {date}\nTotal : {total}\n\n"
        details += "─" * 40 + "\n"
        details += f"{'Désignation':<30} {'Qté':>6} {'P.U.':>10} {'Montant':>12}\n"
        details += "─" * 40 + "\n"
        for l in lignes:
            details += (
                f"{l['designation'][:30]:<30} {l['quantite']:>6.0f} "
                f"{l['prix_unitaire']:>10.2f} {l['montant']:>12.2f} FCFA\n"
            )
        details += "─" * 40 + "\n"
        details += f"{'TOTAL':>52} {total}\n"

        win = tk.Toplevel(self)
        win.title(f"Détails — {numero}")
        win.configure(bg=COLORS["bg_card"])
        win.geometry(f"540x420+{self.winfo_x()+80}+{self.winfo_y()+60}")

        header = tk.Frame(win, bg=COLORS["primary"], height=45)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"📄  Détails de {numero}",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white").pack(expand=True)

        txt = tk.Text(win, font=("Consolas", 10), bg=COLORS["bg_card"],
                      fg=COLORS["text_dark"], relief="flat", padx=16, pady=12,
                      wrap="none", state="normal")
        txt.pack(fill="both", expand=True, padx=16, pady=12)
        txt.insert("end", details)
        txt.config(state="disabled")

        tk.Button(win, text="Fermer", command=win.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text_dark"],
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2").pack(pady=(0, 12))

    def _get_facture_data(self, fid):
        """Récupère les données complètes d'une facture."""
        factures = db.get_all_invoices()
        facture = next((f for f in factures if f["id"] == fid), None)
        if not facture:
            return None, None
        lignes = db.get_invoice_lines(fid)
        return facture, lignes

    def _regenerer_pdf(self):
        """Régénère le PDF d'une facture existante."""
        fid = self._get_selected_id()
        if fid is None:
            return

        facture, lignes = self._get_facture_data(fid)
        if not facture:
            messagebox.showerror("Erreur", "Facture introuvable.", parent=self)
            return

        try:
            path = pdf_gen.generate_pdf(
                facture["numero_facture"],
                facture["client"],
                facture.get("telephone", ""),
                facture["date_facture"],
                lignes,
                facture["total"]
            )
            messagebox.showinfo(
                "✅ PDF régénéré",
                f"Le PDF a été régénéré :\n{path}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Erreur PDF", str(e), parent=self)

    def _imprimer(self):
        """Imprime une facture via la boîte de dialogue d'impression."""
        fid = self._get_selected_id()
        if fid is None:
            return

        facture, lignes = self._get_facture_data(fid)
        if not facture:
            return

        # S'assurer que le PDF existe
        pdf_path = pdf_gen.get_output_path(facture["numero_facture"])
        if not os.path.exists(pdf_path):
            self._regenerer_pdf()
            if not os.path.exists(pdf_path):
                return

        PrintDialog(self, pdf_path)

    @staticmethod
    def _fmt_price(value):
        try:
            return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
        except:
            return "0,00"