"""
Module de gestion des licences — FacturePro
============================================

DEUX TYPES DE LICENCES :
─────────────────────────
  1. ILLIMITÉE  — pas de date d'expiration, valable à vie sur la machine
     Format clé : U-XXXXX-XXXXX-XXXXX-XXXXX
     Exemple    : U-A3F9C-12D4E-BB7A1-09CF2

  2. DURÉE DÉTERMINÉE — expire à une date fixée par l'éditeur
     Format clé : D-AAMMJJ-XXXXX-XXXXX-XXXXX
     Exemple    : D-251231-A3F9C-12D4E-BB7A1   (expire le 31/12/2025)

SÉCURITÉ :
───────────
  - Clé liée à l'ID matériel de la machine (UUID BIOS/OS)
  - Signature HMAC-SHA256 avec secret privé
  - La date d'expiration est intégrée dans la signature → non falsifiable
  - Licence.json lié à la machine (machine_id stocké et revérifié)

OUTIL ÉDITEUR :
────────────────
  Lancer le générateur graphique : python generateur_licence.py
"""

import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date
from app_path import app_path

# ─── SECRET PRIVÉ (NE PAS PARTAGER — changez avant distribution) ──────────────
_SECRET = b"FacturePro_2025_@Aviwalo#XyZ_Private_v2"

# ─── Types de licence ──────────────────────────────────────────────────────────
TYPE_UNLIMITED = "unlimited"   # Licence illimitée
TYPE_TIMED     = "timed"       # Licence à durée déterminée

LICENCE_PATH = app_path("licence.json")

# ─── Couleurs & polices ────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#0f172a",
    "card":         "#1e293b",
    "card2":        "#162032",
    "primary":      "#1a56db",
    "primary_dark": "#0d3d91",
    "accent":       "#10b981",
    "warning":      "#f59e0b",
    "danger":       "#ef4444",
    "text":         "#f1f5f9",
    "text_dim":     "#94a3b8",
    "border":       "#334155",
    "input_bg":     "#0b1120",
}
FONTS = {
    "title": ("Segoe UI", 18, "bold"),
    "h2":    ("Segoe UI", 13, "bold"),
    "body":  ("Segoe UI", 10),
    "bold":  ("Segoe UI", 10, "bold"),
    "small": ("Segoe UI", 9),
    "mono":  ("Consolas", 11),
    "mono_lg": ("Consolas", 13, "bold"),
}


# ══════════════════════════════════════════════════════════════════════════════
# IDENTIFICATION MACHINE
# ══════════════════════════════════════════════════════════════════════════════

def get_machine_id() -> str:
    """Retourne un identifiant stable et unique pour cette machine."""
    try:
        system = platform.system()
        if system == "Windows":
            out = subprocess.check_output(
                ["wmic", "csproduct", "get", "UUID"],
                stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
            uuid = lines[-1] if len(lines) > 1 else ""
            if uuid and uuid.upper() != "UUID" and len(uuid) > 10:
                return uuid.upper()
        elif system == "Darwin":
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2].upper()
        elif system == "Linux":
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if os.path.isfile(path):
                    with open(path) as f:
                        mid = f.read().strip()
                    if mid:
                        return mid.upper()
    except Exception:
        pass
    # Fallback
    raw = f"{platform.node()}-{platform.processor()}-{platform.machine()}-{platform.architecture()}"
    return hashlib.sha256(raw.encode()).hexdigest().upper()[:32]


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DE CLÉS
# ══════════════════════════════════════════════════════════════════════════════

def _hmac_hex(payload: str) -> str:
    """Calcule HMAC-SHA256 du payload avec le secret, retourne hex uppercase."""
    return hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def generate_unlimited_key(machine_id: str) -> str:
    """
    Génère une clé de licence ILLIMITÉE.
    Format : U-XXXXX-XXXXX-XXXXX-XXXXX
    """
    mid = machine_id.strip().upper()
    payload = f"UNLIMITED:{mid}"
    sig = _hmac_hex(payload)[:20]
    groups = "-".join(sig[i:i+5] for i in range(0, 20, 5))
    return f"U-{groups}"


def generate_timed_key(machine_id: str, expiry: date) -> str:
    """
    Génère une clé de licence À DURÉE DÉTERMINÉE.
    La date d'expiration est encodée dans la clé.
    Format : D-AAMMJJ-XXXXX-XXXXX-XXXXX
    expiry : objet datetime.date (date d'expiration incluse)
    """
    mid = machine_id.strip().upper()
    date_str = expiry.strftime("%y%m%d")           # ex: "251231" pour 31/12/2025
    payload = f"TIMED:{mid}:{date_str}"
    sig = _hmac_hex(payload)[:15]
    groups = "-".join(sig[i:i+5] for i in range(0, 15, 5))
    return f"D-{date_str}-{groups}"


# ══════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION DE CLÉS
# ══════════════════════════════════════════════════════════════════════════════

def _parse_key(key: str):
    """
    Parse une clé et retourne (type, expiry_date_or_None, signature_part).
    Retourne (None, None, None) si format invalide.
    """
    k = key.strip().upper().replace(" ", "")
    if k.startswith("U-"):
        # Illimitée : U-XXXXX-XXXXX-XXXXX-XXXXX
        parts = k[2:].replace("-", "")
        if len(parts) == 20 and all(c in "0123456789ABCDEF" for c in parts):
            return TYPE_UNLIMITED, None, k
        return None, None, None
    elif k.startswith("D-"):
        # Datée : D-AAMMJJ-XXXXX-XXXXX-XXXXX
        rest = k[2:]
        segments = rest.split("-")
        if len(segments) == 4:
            date_seg = segments[0]   # "AAMMJJ"
            sig_part = "".join(segments[1:])
            if len(date_seg) == 6 and len(sig_part) == 15:
                try:
                    expiry = datetime.strptime(date_seg, "%y%m%d").date()
                    return TYPE_TIMED, expiry, k
                except ValueError:
                    pass
        return None, None, None
    return None, None, None


def verify_key(key: str, machine_id: str):
    """
    Vérifie une clé de licence pour un machine_id donné.

    Retourne un dict :
    {
        "valid":   bool,
        "type":    "unlimited" | "timed" | None,
        "expiry":  date | None,
        "expired": bool,
        "days_left": int | None,
        "message": str
    }
    """
    result = {
        "valid": False, "type": None, "expiry": None,
        "expired": False, "days_left": None, "message": ""
    }

    k_type, expiry, _ = _parse_key(key)

    if k_type is None:
        result["message"] = "Format de clé invalide."
        return result

    mid = machine_id.strip().upper()

    if k_type == TYPE_UNLIMITED:
        expected = generate_unlimited_key(mid)
        k_clean = key.strip().upper().replace(" ", "")
        e_clean = expected.replace(" ", "")
        if hmac.compare_digest(k_clean, e_clean):
            result.update({"valid": True, "type": TYPE_UNLIMITED,
                           "message": "Licence illimitée valide."})
        else:
            result["message"] = "Clé invalide ou non compatible avec cette machine."

    elif k_type == TYPE_TIMED:
        expected = generate_timed_key(mid, expiry)
        k_clean = key.strip().upper().replace(" ", "")
        e_clean = expected.replace(" ", "")
        if hmac.compare_digest(k_clean, e_clean):
            today = date.today()
            days_left = (expiry - today).days
            if today > expiry:
                result.update({
                    "valid": False, "type": TYPE_TIMED,
                    "expiry": expiry, "expired": True,
                    "days_left": days_left,
                    "message": f"Licence expirée depuis le {expiry.strftime('%d/%m/%Y')}."
                })
            else:
                result.update({
                    "valid": True, "type": TYPE_TIMED,
                    "expiry": expiry, "expired": False,
                    "days_left": days_left,
                    "message": f"Licence valide jusqu'au {expiry.strftime('%d/%m/%Y')} ({days_left} jour(s) restant(s))."
                })
        else:
            result["message"] = "Clé invalide ou non compatible avec cette machine."

    return result


# ══════════════════════════════════════════════════════════════════════════════
# GESTION LOCALE DE LA LICENCE
# ══════════════════════════════════════════════════════════════════════════════

def load_licence() -> dict:
    if os.path.isfile(LICENCE_PATH):
        try:
            with open(LICENCE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_licence(machine_id: str, key: str, titulaire: str = "", info: dict = None):
    """Enregistre la licence validée localement."""
    info = info or {}
    data = {
        "machine_id":   machine_id,
        "licence_key":  key.strip().upper(),
        "titulaire":    titulaire,
        "type":         info.get("type", TYPE_UNLIMITED),
        "expiry":       info.get("expiry").strftime("%Y-%m-%d") if info.get("expiry") else None,
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(LICENCE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_licenced() -> bool:
    """
    Retourne True si la licence est valide et non expirée sur CETTE machine.
    """
    lic = load_licence()
    if not lic:
        return False
    stored_mid = lic.get("machine_id", "")
    stored_key = lic.get("licence_key", "")
    current_mid = get_machine_id()

    if stored_mid.upper() != current_mid.upper():
        return False

    result = verify_key(stored_key, current_mid)
    return result["valid"]


def get_licence_info() -> dict:
    """Retourne toutes les infos de la licence active (pour affichage)."""
    lic = load_licence()
    mid = get_machine_id()
    stored_key = lic.get("licence_key", "")

    if stored_key and lic.get("machine_id", "").upper() == mid.upper():
        v = verify_key(stored_key, mid)
    else:
        v = {"valid": False, "type": None, "expiry": None,
             "expired": False, "days_left": None, "message": "Aucune licence."}

    # Label type lisible
    if v["type"] == TYPE_UNLIMITED:
        type_label = "🔓 Illimitée"
    elif v["type"] == TYPE_TIMED:
        type_label = "⏳ Durée déterminée"
    else:
        type_label = "—"

    expiry_label = v["expiry"].strftime("%d/%m/%Y") if v.get("expiry") else "—"

    return {
        "machine_id":    mid,
        "titulaire":     lic.get("titulaire", "—"),
        "activated_at":  lic.get("activated_at", "—"),
        "licence_key":   stored_key or "—",
        "type_label":    type_label,
        "expiry_label":  expiry_label,
        "days_left":     v.get("days_left"),
        "is_valid":      v["valid"],
        "is_expired":    v.get("expired", False),
        "message":       v.get("message", ""),
    }


def get_expiry_warning() -> str:
    """
    Retourne un message d'avertissement si la licence expire bientôt (≤ 30 jours).
    Retourne "" si aucun avertissement.
    """
    info = get_licence_info()
    if not info["is_valid"]:
        return ""
    days = info.get("days_left")
    if days is None:
        return ""  # Illimitée
    if days <= 7:
        return f"⚠️  Votre licence expire dans {days} jour(s) !"
    if days <= 30:
        return f"ℹ️  Votre licence expire dans {days} jour(s)."
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE D'ACTIVATION (côté client)
# ══════════════════════════════════════════════════════════════════════════════

class ActivationWindow(tk.Tk):
    """Fenêtre d'activation — bloque le démarrage si non licencié."""

    def __init__(self):
        super().__init__()
        self.title("FacturePro — Activation de la licence")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.activated = False
        self.machine_id = get_machine_id()
        w, h = 540, 510
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._build()

    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=COLORS["primary"], height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💼  FacturePro",
                 font=("Segoe UI", 20, "bold"),
                 bg=COLORS["primary"], fg="white").pack(side="left", padx=24)
        tk.Label(hdr, text="Activation requise",
                 font=FONTS["small"], bg=COLORS["primary"], fg="#bfdbfe"
                 ).pack(side="right", padx=24)

        body = tk.Frame(self, bg=COLORS["bg"], padx=30, pady=18)
        body.pack(fill="both", expand=True)

        # Bloc ID machine
        box = tk.Frame(body, bg=COLORS["card"],
                       highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="x", pady=(0, 16))

        tk.Label(box, text="🖥  Identifiant de votre machine",
                 font=FONTS["bold"], bg=COLORS["card"], fg=COLORS["text"]
                 ).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(box,
                 text="Communiquez cet identifiant à votre revendeur pour obtenir votre clé de licence.",
                 font=FONTS["small"], bg=COLORS["card"], fg=COLORS["text_dim"],
                 wraplength=460, justify="left"
                 ).pack(anchor="w", padx=14, pady=(0, 8))

        mid_row = tk.Frame(box, bg=COLORS["input_bg"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
        mid_row.pack(fill="x", padx=14, pady=(0, 12))

        self.mid_var = tk.StringVar(value=self.machine_id)
        tk.Entry(mid_row, textvariable=self.mid_var,
                 font=FONTS["mono"], state="readonly",
                 readonlybackground=COLORS["input_bg"],
                 fg="#34d399", relief="flat", bd=0
                 ).pack(side="left", fill="x", expand=True, padx=10, ipady=8)
        tk.Button(mid_row, text="📋 Copier", command=self._copy_mid,
                  font=FONTS["small"], bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_dark"],
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2"
                  ).pack(side="right", padx=6, pady=4)

        # Nom titulaire
        tk.Label(body, text="Nom du titulaire (optionnel)",
                 font=FONTS["small"], bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(anchor="w")
        self.var_nom = tk.StringVar()
        tk.Entry(body, textvariable=self.var_nom,
                 font=FONTS["body"], relief="flat", bd=0,
                 bg=COLORS["input_bg"], fg=COLORS["text"],
                 highlightbackground=COLORS["border"], highlightthickness=1,
                 highlightcolor=COLORS["primary"], insertbackground="white"
                 ).pack(fill="x", ipady=7, pady=(2, 14))

        # Clé de licence
        tk.Label(body, text="Clé de licence *",
                 font=FONTS["small"], bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(anchor="w")

        # Indication du format
        tk.Label(body,
                 text="Illimitée : U-XXXXX-XXXXX-XXXXX-XXXXX  |  Datée : D-AAMMJJ-XXXXX-XXXXX-XXXXX",
                 font=("Consolas", 8), bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(anchor="w", pady=(1, 3))

        key_frame = tk.Frame(body, bg=COLORS["input_bg"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
        key_frame.pack(fill="x", pady=(0, 6))

        self.var_key = tk.StringVar()
        self.key_entry = tk.Entry(key_frame, textvariable=self.var_key,
                                  font=FONTS["mono"], relief="flat", bd=0,
                                  bg=COLORS["input_bg"], fg="white",
                                  highlightthickness=0, insertbackground="white")
        self.key_entry.pack(fill="x", padx=10, ipady=10)
        self.key_entry.focus()

        # Statut
        self.lbl_status = tk.Label(body, text="",
                                   font=FONTS["small"], bg=COLORS["bg"])
        self.lbl_status.pack(anchor="w", pady=(4, 12))

        # Boutons
        btns = tk.Frame(body, bg=COLORS["bg"])
        btns.pack(fill="x")
        tk.Button(btns, text="✖  Quitter", command=self.destroy,
                  font=FONTS["body"], bg="#374151", fg="white",
                  relief="flat", bd=0, padx=18, pady=9, cursor="hand2"
                  ).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="✔  Activer", command=self._activer,
                  font=FONTS["bold"], bg=COLORS["accent"], fg="white",
                  activebackground="#059669",
                  relief="flat", bd=0, padx=24, pady=9, cursor="hand2"
                  ).pack(side="right")

        self.bind("<Return>", lambda _: self._activer())

    def _copy_mid(self):
        self.clipboard_clear()
        self.clipboard_append(self.machine_id)
        self._set_status("✅ Identifiant copié dans le presse-papiers.", "ok")

    def _activer(self):
        key = self.var_key.get().strip()
        if not key:
            self._set_status("⚠️  Veuillez entrer votre clé de licence.", "warning")
            return

        result = verify_key(key, self.machine_id)

        if result["valid"]:
            save_licence(self.machine_id, key, self.var_nom.get().strip(), result)
            self.activated = True
            self._set_status(f"✅  {result['message']}", "ok")
            self.after(1600, self.destroy)
        elif result["expired"]:
            self._set_status(f"❌  {result['message']}", "error")
        else:
            self._set_status(f"❌  {result['message']}", "error")

    def _set_status(self, msg, level="ok"):
        c = {"ok": "#34d399", "error": COLORS["danger"], "warning": "#fbbf24"}
        self.lbl_status.config(text=msg, fg=c.get(level, "white"))


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE INFO LICENCE (depuis Paramètres de l'app cliente)
# ══════════════════════════════════════════════════════════════════════════════

class LicenceInfoWindow(tk.Toplevel):
    """Affiche les informations complètes de la licence installée."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("ℹ️  Informations de licence")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        w, h = 520, 420
        self.geometry(f"{w}x{h}+{parent.winfo_x()+60}+{parent.winfo_y()+60}")
        self._build()

    def _build(self):
        info = get_licence_info()

        hdr = tk.Frame(self, bg=COLORS["primary"], height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="ℹ️  Licence FacturePro",
                 font=("Segoe UI", 14, "bold"),
                 bg=COLORS["primary"], fg="white").pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg"], padx=26, pady=16)
        body.pack(fill="both", expand=True)

        # Statut principal
        if info["is_valid"]:
            if info.get("days_left") is not None:
                if info["days_left"] <= 7:
                    sc, st = COLORS["warning"], f"⚠️  ACTIVE — expire dans {info['days_left']} jour(s)"
                else:
                    sc, st = COLORS["accent"], f"✅  LICENCE ACTIVE ({info['type_label']})"
            else:
                sc, st = COLORS["accent"], "✅  LICENCE ACTIVE — Illimitée"
        elif info["is_expired"]:
            sc, st = COLORS["danger"], "❌  LICENCE EXPIRÉE"
        else:
            sc, st = COLORS["danger"], "❌  LICENCE INVALIDE"

        tk.Label(body, text=st, font=("Segoe UI", 12, "bold"),
                 bg=COLORS["bg"], fg=sc).pack(pady=(0, 12))

        # Détails
        rows = [
            ("Titulaire",      info["titulaire"]),
            ("Type",           info["type_label"]),
            ("Expiration",     info["expiry_label"]),
            ("ID machine",     info["machine_id"]),
            ("Clé enregistrée",info["licence_key"]),
            ("Activée le",     info["activated_at"]),
        ]
        for label, val in rows:
            row = tk.Frame(body, bg=COLORS["card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"  {label} :", width=18, anchor="w",
                     font=FONTS["small"], bg=COLORS["card"], fg=COLORS["text_dim"]
                     ).pack(side="left", ipady=5)
            fnt = FONTS["mono"] if label in ("ID machine", "Clé enregistrée") else FONTS["small"]
            tk.Label(row, text=str(val), font=fnt,
                     bg=COLORS["card"], fg=COLORS["text"], anchor="w"
                     ).pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(body,
                 text="⚠️  Cette licence est liée à cette machine et n'est pas transférable.",
                 font=FONTS["small"], bg=COLORS["bg"], fg=COLORS["text_dim"],
                 wraplength=460, justify="left").pack(pady=(10, 0), anchor="w")

        tk.Button(body, text="Fermer", command=self.destroy,
                  font=FONTS["body"], bg="#374151", fg="white",
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2"
                  ).pack(side="right", pady=(12, 0))


# ══════════════════════════════════════════════════════════════════════════════
# VÉRIFICATION AU DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════

def check_licence_or_exit() -> bool:
    """
    Vérifie la licence. Si invalide/expirée, affiche la fenêtre d'activation.
    Retourne True si l'app peut démarrer.
    """
    if is_licenced():
        return True
    win = ActivationWindow()
    win.mainloop()
    return win.activated