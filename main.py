"""
FacturePro — Logiciel de facturation desktop
Point d'entrée principal de l'application.

Usage :
    python main.py

Dépendances :
    pip install reportlab pillow
"""

import os
import sys

# Ajouter le répertoire courant au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from licence import check_licence_or_exit
from ui import FacturationApp


def main():
    """Lance l'application de facturation."""
    # ── Vérification de la licence avant tout ──────────────────────────────
    if not check_licence_or_exit():
        # L'utilisateur a fermé la fenêtre sans activer → on quitte
        sys.exit(0)

    # Initialiser la base de données AVANT de lancer l'interface
    db.init_db()

    app = FacturationApp()
    app.mainloop()


if __name__ == "__main__":
    main()