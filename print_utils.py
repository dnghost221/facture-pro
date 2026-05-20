"""
print_utils.py — Utilitaire d'impression universel pour FacturePro
===================================================================

Stratégie par OS :
  Windows : SumatraPDF si disponible (boîte de dialogue imprimante),
            sinon ShellExecute "print" avec Acrobat/Reader,
            sinon ouverture PDF + instruction manuelle.
  macOS   : lpr avec options, ou open -a Preview pour la boîte de dialogue.
  Linux   : lpr / evince / okular / xdg-open selon ce qui est installé.

La fenêtre de dialogue d'impression native permet à l'utilisateur de :
  - Choisir l'imprimante
  - Régler le format papier (A4, Letter, etc.)
  - Ajuster les marges / mise à l'échelle
  - Choisir le nombre de copies
"""

import os
import platform
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox


SYSTEM = platform.system()


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS INTERNES
# ══════════════════════════════════════════════════════════════════════════════

def _sumatra_path() -> str:
    """Cherche SumatraPDF sur Windows (gratuit, léger, excellent pour l'impression)."""
    candidates = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "SumatraPDF", "SumatraPDF.exe"),
        os.path.join(os.environ.get("APPDATA", ""),    "SumatraPDF", "SumatraPDF.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # Chercher dans le PATH
    found = shutil.which("SumatraPDF")
    return found or ""


def _acrobat_path() -> str:
    """Cherche Acrobat Reader sur Windows."""
    import glob
    patterns = [
        r"C:\Program Files\Adobe\Acrobat*\Acrobat\Acrobat.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat*\Acrobat\Acrobat.exe",
        r"C:\Program Files\Adobe\Acrobat Reader*\Reader\AcroRd32.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat Reader*\Reader\AcroRd32.exe",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return ""


def _print_windows(pdf_path: str, show_dialog: bool = True) -> tuple[bool, str]:
    """
    Impression sur Windows.
    Ordre de préférence :
      1. SumatraPDF avec -print-dialog (boîte de dialogue native)
      2. Acrobat Reader avec /p /h (impression silencieuse avec dialog)
      3. ShellExecute "print" (imprimante par défaut, sans dialog)
    """
    # 1. SumatraPDF
    sumatra = _sumatra_path()
    if sumatra:
        if show_dialog:
            # -print-dialog ouvre la boîte de dialogue d'impression
            cmd = [sumatra, "-print-dialog", pdf_path]
        else:
            cmd = [sumatra, "-print-to-default", pdf_path]
        try:
            subprocess.Popen(cmd)
            return True, "SumatraPDF"
        except Exception as e:
            pass

    # 2. Acrobat Reader
    acrobat = _acrobat_path()
    if acrobat:
        try:
            # /p ouvre la boîte d'impression, /h minimise la fenêtre
            subprocess.Popen([acrobat, "/p", pdf_path])
            return True, "Acrobat Reader"
        except Exception:
            pass

    # 3. ShellExecute "printto" ou "print"
    try:
        if show_dialog:
            # Ouvrir avec le lecteur par défaut (qui a lui-même Ctrl+P)
            os.startfile(pdf_path)
            return True, "lecteur_default_open"
        else:
            os.startfile(pdf_path, "print")
            return True, "ShellExecute_print"
    except Exception as e:
        return False, str(e)


def _print_macos(pdf_path: str, show_dialog: bool = True) -> tuple[bool, str]:
    """Impression sur macOS."""
    if show_dialog:
        # Ouvrir dans Aperçu avec la boîte d'impression
        try:
            subprocess.Popen(["open", "-a", "Preview", pdf_path])
            return True, "Preview"
        except Exception:
            pass
        # Fallback : ouvrir avec l'app par défaut
        try:
            subprocess.Popen(["open", pdf_path])
            return True, "default_app"
        except Exception as e:
            return False, str(e)
    else:
        try:
            subprocess.run(["lpr", pdf_path], check=True)
            return True, "lpr"
        except Exception as e:
            return False, str(e)


def _print_linux(pdf_path: str, show_dialog: bool = True) -> tuple[bool, str]:
    """Impression sur Linux."""
    if show_dialog:
        # Essayer les visionneuses avec boîte de dialogue d'impression
        for viewer, args in [
            ("evince",  ["evince",  "--preview", pdf_path]),
            ("okular",  ["okular",  pdf_path]),
            ("atril",   ["atril",   pdf_path]),
            ("xreader", ["xreader", pdf_path]),
        ]:
            if shutil.which(viewer):
                try:
                    subprocess.Popen(args)
                    return True, viewer
                except Exception:
                    continue
        # Fallback xdg-open
        try:
            subprocess.Popen(["xdg-open", pdf_path])
            return True, "xdg-open"
        except Exception as e:
            return False, str(e)
    else:
        for cmd in [["lpr", pdf_path], ["lp", pdf_path]]:
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, check=True)
                    return True, cmd[0]
                except Exception:
                    continue
        return False, "lpr/lp non trouvé"


# ══════════════════════════════════════════════════════════════════════════════
# API PUBLIQUE
# ══════════════════════════════════════════════════════════════════════════════

def imprimer_pdf(pdf_path: str, parent_widget=None, show_dialog: bool = True) -> bool:
    """
    Imprime un PDF en ouvrant la boîte de dialogue d'impression native.

    Args:
        pdf_path      : Chemin absolu vers le fichier PDF
        parent_widget : Widget Tkinter parent pour les messageboxes
        show_dialog   : True = boîte de dialogue, False = imprimante par défaut directe

    Returns:
        True si l'impression a été lancée, False sinon.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        messagebox.showwarning(
            "PDF introuvable",
            "Le fichier PDF n'existe pas.\nGénérez d'abord la facture.",
            parent=parent_widget
        )
        return False

    if SYSTEM == "Windows":
        ok, method = _print_windows(pdf_path, show_dialog)
    elif SYSTEM == "Darwin":
        ok, method = _print_macos(pdf_path, show_dialog)
    else:
        ok, method = _print_linux(pdf_path, show_dialog)

    if ok:
        if method == "lecteur_default_open":
            # On a ouvert le PDF mais sans dialog automatique → guider l'utilisateur
            messagebox.showinfo(
                "🖨 Impression",
                "Le PDF s'est ouvert dans votre lecteur.\n\n"
                "Pour imprimer :\n"
                "  • Appuyez sur  Ctrl + P  (Windows/Linux)\n"
                "  • Ou  Cmd + P  (Mac)\n\n"
                "Vous pourrez choisir votre imprimante et régler le format.",
                parent=parent_widget
            )
        elif method == "ShellExecute_print":
            messagebox.showinfo(
                "🖨 Impression",
                "La facture a été envoyée à l'imprimante par défaut.",
                parent=parent_widget
            )
        # Pour les autres méthodes (SumatraPDF, Acrobat, Preview…)
        # la boîte de dialogue s'ouvre dans la fenêtre lancée → pas de message ici
        return True
    else:
        messagebox.showerror(
            "Erreur d'impression",
            f"Impossible de lancer l'impression.\n\n"
            f"Détail : {method}\n\n"
            f"Solution : ouvrez manuellement le PDF et utilisez Ctrl+P.",
            parent=parent_widget
        )
        return False


def verifier_sumatra_disponible() -> bool:
    """Vérifie si SumatraPDF est installé (Windows uniquement)."""
    return bool(_sumatra_path())


def get_print_info() -> dict:
    """
    Retourne des informations sur les outils d'impression disponibles.
    Utile pour afficher un conseil à l'utilisateur.
    """
    info = {"system": SYSTEM, "tools": [], "recommended": ""}

    if SYSTEM == "Windows":
        sumatra = _sumatra_path()
        acrobat = _acrobat_path()
        if sumatra:
            info["tools"].append("SumatraPDF")
            info["recommended"] = "SumatraPDF (boîte de dialogue complète)"
        if acrobat:
            info["tools"].append("Acrobat Reader")
        if not sumatra and not acrobat:
            info["tools"].append("Lecteur PDF par défaut")
            info["recommended"] = (
                "Installez SumatraPDF (gratuit) pour une meilleure expérience : "
                "https://www.sumatrapdfreader.org"
            )
    elif SYSTEM == "Darwin":
        info["tools"].append("Aperçu (Preview)")
        info["recommended"] = "Aperçu macOS — boîte de dialogue d'impression complète"
    else:
        for tool in ["evince", "okular", "atril", "lpr", "xdg-open"]:
            if shutil.which(tool):
                info["tools"].append(tool)
        info["recommended"] = info["tools"][0] if info["tools"] else "Aucun outil trouvé"

    return info


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE D'OPTIONS D'IMPRESSION
# ══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "bg":      "#f8fafc",
    "card":    "#ffffff",
    "primary": "#1a56db",
    "accent":  "#10b981",
    "border":  "#e5e7eb",
    "text":    "#111827",
    "dim":     "#6b7280",
}
FONTS = {
    "heading": ("Segoe UI", 12, "bold"),
    "body":    ("Segoe UI", 10),
    "bold":    ("Segoe UI", 10, "bold"),
    "small":   ("Segoe UI", 9),
}


class PrintDialog(tk.Toplevel):
    """
    Boîte de dialogue d'options d'impression FacturePro.
    Permet à l'utilisateur de choisir le mode avant d'imprimer.
    """

    def __init__(self, parent, pdf_path: str):
        super().__init__(parent)
        self.title("🖨  Options d'impression")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.pdf_path = pdf_path
        self.printed  = False

        w, h = 440, 380
        self.geometry(f"{w}x{h}+{parent.winfo_x()+120}+{parent.winfo_y()+120}")

        self._build()

    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=COLORS["primary"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🖨  Imprimer la facture",
                 font=FONTS["heading"], bg=COLORS["primary"], fg="white"
                 ).pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg"], padx=24, pady=18)
        body.pack(fill="both", expand=True)

        # Nom du fichier
        fname = os.path.basename(self.pdf_path)
        tk.Label(body, text=f"📄  {fname}",
                 font=FONTS["bold"], bg=COLORS["bg"], fg=COLORS["text"]
                 ).pack(anchor="w", pady=(0, 16))

        # Option 1 : boîte de dialogue native
        opt1 = tk.Frame(body, bg=COLORS["card"],
                        highlightbackground="#1a56db", highlightthickness=2)
        opt1.pack(fill="x", pady=(0, 10))
        opt1_body = tk.Frame(opt1, bg=COLORS["card"], padx=14, pady=12)
        opt1_body.pack(fill="x")
        tk.Label(opt1_body, text="🖨  Ouvrir la boîte d'impression",
                 font=FONTS["bold"], bg=COLORS["card"], fg=COLORS["primary"]
                 ).pack(anchor="w")
        tk.Label(opt1_body,
                 text="Choisissez votre imprimante, le format papier (A4, Letter…),\n"
                      "la mise à l'échelle et les copies.",
                 font=FONTS["small"], bg=COLORS["card"], fg=COLORS["dim"],
                 justify="left"
                 ).pack(anchor="w", pady=(4, 8))
        tk.Button(opt1_body, text="⚡ Imprimer avec dialogue",
                  command=self._imprimer_avec_dialog,
                  font=FONTS["bold"], bg=COLORS["primary"], fg="white",
                  activebackground="#0d3d91",
                  relief="flat", bd=0, padx=18, pady=8, cursor="hand2"
                  ).pack(anchor="w")

        # Option 2 : imprimante par défaut directement
        opt2 = tk.Frame(body, bg=COLORS["card"],
                        highlightbackground=COLORS["border"], highlightthickness=1)
        opt2.pack(fill="x", pady=(0, 10))
        opt2_body = tk.Frame(opt2, bg=COLORS["card"], padx=14, pady=12)
        opt2_body.pack(fill="x")
        tk.Label(opt2_body, text="⚡  Imprimer directement",
                 font=FONTS["bold"], bg=COLORS["card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(opt2_body,
                 text="Envoi immédiat à l'imprimante par défaut, sans dialogue.",
                 font=FONTS["small"], bg=COLORS["card"], fg=COLORS["dim"],
                 ).pack(anchor="w", pady=(4, 8))
        tk.Button(opt2_body, text="Imprimer (défaut)",
                  command=self._imprimer_direct,
                  font=FONTS["body"], bg="#374151", fg="white",
                  relief="flat", bd=0, padx=16, pady=7, cursor="hand2"
                  ).pack(anchor="w")

        # Info sur les outils
        info = get_print_info()
        if info.get("recommended") and SYSTEM == "Windows" and not verifier_sumatra_disponible():
            tip = tk.Frame(body, bg="#fffbeb",
                           highlightbackground="#fde68a", highlightthickness=1)
            tip.pack(fill="x", pady=(0, 8))
            tk.Label(tip,
                     text="💡  Pour une meilleure expérience, installez SumatraPDF (gratuit) :\n"
                          "sumatrapdfreader.org",
                     font=FONTS["small"], bg="#fffbeb", fg="#92400e",
                     justify="left"
                     ).pack(anchor="w", padx=10, pady=8)

        # Annuler
        tk.Button(body, text="Annuler", command=self.destroy,
                  font=FONTS["body"], bg=COLORS["border"], fg=COLORS["text"],
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2"
                  ).pack(side="right")

    def _imprimer_avec_dialog(self):
        self.printed = imprimer_pdf(self.pdf_path, self, show_dialog=True)
        if self.printed:
            self.destroy()

    def _imprimer_direct(self):
        self.printed = imprimer_pdf(self.pdf_path, self, show_dialog=False)
        if self.printed:
            self.destroy()
