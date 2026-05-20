"""
Module de configuration
Charge et sauvegarde les paramètres du logiciel dans config.json
Le fichier est toujours créé à côté du .exe, jamais dans _MEIPASS.
"""

import json
import os
import sys
from app_path import app_path

CONFIG_PATH = app_path("config.json")

# ─── Valeurs par défaut ────────────────────────────────────────────────────────
DEFAULTS = {
    "nom":                    "MON COMMERCE",
    "slogan":                 "Votre partenaire de confiance",
    "adresse":                "123 Rue du Commerce, Ville",
    "telephone":              "+33 1 23 45 67 89",
    "RC":                     "",
    "NINEA":                  "",
    "logo_path":              "logoAviwalo.png",
    "logo_largeur_mm":        45,
    "logo_hauteur_mm":        18,
    "couleur_primaire":       "#1a56db",
    "couleur_accent":         "#0d3d91",
    "message_remerciement":   "✨ Merci pour votre confiance !",
    "mention_paiement":       "Paiement à réception de facture.",
    "titre_facture":          "FACTURE",
    "dossier_factures":       "factures",
    # ── Signature & cachet ─────────────────────────────────────────────────
    "signature_path":         "",   # Chemin vers l'image de signature
    "cachet_path":            "",   # Chemin vers l'image du cachet/tampon
    "signature_largeur_mm":   40,   # Largeur max de la signature dans le PDF
    "signature_hauteur_mm":   20,   # Hauteur max de la signature dans le PDF
    "cachet_largeur_mm":      35,   # Largeur max du cachet dans le PDF
    "cachet_hauteur_mm":      35,   # Hauteur max du cachet dans le PDF
    "afficher_signature":     True, # Afficher ou masquer la signature sur le PDF
    "afficher_cachet":        True, # Afficher ou masquer le cachet sur le PDF
}


def load() -> dict:
    """Charge la config depuis le JSON, complète les clés manquantes."""
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict):
    """Sauvegarde la config dans config.json (à côté du .exe)."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get(key: str, fallback=None):
    """Raccourci pour lire une clé de config."""
    return load().get(key, fallback if fallback is not None else DEFAULTS.get(key))