"""
Crée automatiquement un raccourci Windows vers FacturePro.exe
sur le Bureau — sans aucune dépendance externe.
Double-cliquez une seule fois pour installer le raccourci.
"""

import os
import ctypes
import subprocess


def creer_raccourci():
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FacturePro.exe")

    if not os.path.isfile(exe_path):
        input("❌ FacturePro.exe introuvable dans ce dossier.\nAppuyez sur Entrée pour quitter.")
        return

    # Récupérer le chemin du Bureau via l'API Windows
    CSIDL_DESKTOP = 0x0000
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, 0, buf)
    bureau = buf.value

    raccourci_path = os.path.join(bureau, "FacturePro.lnk")
    dossier_exe    = os.path.dirname(exe_path)

    # Créer le .lnk via PowerShell (toujours disponible sur Windows)
    script_ps = f"""
$shell = New-Object -ComObject WScript.Shell
$lnk   = $shell.CreateShortcut('{raccourci_path}')
$lnk.TargetPath       = '{exe_path}'
$lnk.WorkingDirectory = '{dossier_exe}'
$lnk.Description      = 'Logiciel de Facturation FacturePro'
$lnk.IconLocation     = '{os.path.join(dossier_exe, "icone.ico")},0'
$lnk.Save()
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script_ps],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"✅ Raccourci créé sur le Bureau : {raccourci_path}")
    else:
        print(f"❌ Erreur : {result.stderr}")

    input("\nAppuyez sur Entrée pour fermer.")


if __name__ == "__main__":
    creer_raccourci()
