"""
Utilitaire de résolution de chemins.
Garantit que les fichiers persistants (DB, config, factures)
sont toujours créés À CÔTÉ du .exe, pas dans le dossier temporaire
de PyInstaller (_MEIPASS) qui est recréé à chaque lancement.
"""

import os
import sys


def get_app_dir() -> str:
    """
    Retourne le dossier racine de l'application :
    - En mode .exe (PyInstaller --onefile) : dossier contenant le .exe
    - En mode script normal               : dossier contenant main.py
    """
    if getattr(sys, "frozen", False):
        # sys.executable = chemin vers le .exe
        return os.path.dirname(sys.executable)
    else:
        # __file__ de ce module est dans le dossier du projet
        return os.path.dirname(os.path.abspath(__file__))


def app_path(*parts) -> str:
    """Construit un chemin absolu à partir du dossier de l'application."""
    return os.path.join(get_app_dir(), *parts)
