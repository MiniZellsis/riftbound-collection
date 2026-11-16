import base64
import binascii
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

from app.infos import NOM, VERSION, version_en_nombres

RACINE = Path(__file__).resolve().parent
CONSTRUCTION = RACINE / "build"
DISTRIBUTION = RACINE / "dist"
NOM_EXE = "RiftboundCollection"
EDITEUR = "MiniZellsis"
VARIABLES = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")


class ErreurConstruction(Exception):
    pass


def role_jwt(cle):
    morceaux = cle.split(".")
    if len(morceaux) != 3:
        return ""
    try:
        charge = json.loads(base64.urlsafe_b64decode(morceaux[1] + "=" * (-len(morceaux[1]) % 4)))
    except (binascii.Error, ValueError):
        return ""
    return charge.get("role", "") if isinstance(charge, dict) else ""


def lire_reglages():
    fichier = RACINE / ".env"
    if not fichier.exists():
        raise ErreurConstruction("le fichier .env est introuvable à côté de construire.py.")
    valeurs = dotenv_values(fichier)
    manquantes = [nom for nom in VARIABLES if not valeurs.get(nom)]
    if manquantes:
        raise ErreurConstruction(f"il manque {', '.join(manquantes)} dans le fichier .env.")

    url = valeurs["SUPABASE_URL"].strip()
    cle = valeurs["SUPABASE_PUBLISHABLE_KEY"].strip()
    if not url.startswith("https://"):
        raise ErreurConstruction("SUPABASE_URL doit commencer par https://.")
    if cle.startswith("sb_secret_") or role_jwt(cle) == "service_role":
        raise ErreurConstruction(
            "SUPABASE_PUBLISHABLE_KEY contient une clé SECRÈTE. Elle ne doit jamais être mise "
            "dans l'appli : prends la clé « publishable » dans Supabase (Project Settings, API Keys)."
        )
    if not cle.startswith("sb_publishable_") and role_jwt(cle) != "anon":
        raise ErreurConstruction("SUPABASE_PUBLISHABLE_KEY ne ressemble pas à une clé publique (sb_publishable_...).")
    return {"SUPABASE_URL": url, "SUPABASE_PUBLISHABLE_KEY": cle}


def ecrire_reglages(reglages):
    dossier = CONSTRUCTION / "reglages"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    fichier = dossier / ".env"
    fichier.write_text("".join(f"{nom}={valeur}\n" for nom, valeur in reglages.items()), encoding="utf-8")
    return fichier


def ecrire_infos_exe():
    nombres = (version_en_nombres(VERSION) + (0, 0, 0, 0))[:4]
    fichier = CONSTRUCTION / "infos_exe.txt"
    fichier.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nombres}, prodvers={nombres}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040C04B0', [
      StringStruct('CompanyName', '{EDITEUR}'),
      StringStruct('FileDescription', '{NOM}'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{NOM_EXE}'),
      StringStruct('OriginalFilename', '{NOM_EXE}.exe'),
      StringStruct('ProductName', '{NOM}'),
      StringStruct('ProductVersion', '{VERSION}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1036, 1200])]),
  ]
)
""",
        encoding="utf-8",
    )
    return fichier


def fabriquer_exe(fichier_reglages):
    import PyInstaller.__main__

    arguments = [
        str(RACINE / "main.py"),
        "--name", NOM_EXE,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(RACINE / "ressources" / "icone.ico"),
        "--add-data", f"{fichier_reglages}{os.pathsep}.",
        "--add-data", f"{RACINE / 'ressources'}{os.pathsep}ressources",
        "--exclude-module", "tkinter",
        "--distpath", str(DISTRIBUTION),
        "--workpath", str(CONSTRUCTION / "pyinstaller"),
        "--specpath", str(CONSTRUCTION),
    ]
    if sys.platform == "win32":
        arguments += ["--version-file", str(ecrire_infos_exe())]
    PyInstaller.__main__.run(arguments)
    return DISTRIBUTION / NOM_EXE


def trouver_inno_setup():
    chemin = shutil.which("ISCC")
    if chemin:
        return chemin
    dossiers = [
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("ProgramFiles", ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    for dossier in dossiers:
        if dossier:
            candidats = sorted(Path(dossier).glob("Inno Setup*/ISCC.exe"), reverse=True)
            if candidats:
                return str(candidats[0])
    return None


def fabriquer_installateur():
    iscc = trouver_inno_setup()
    if iscc is None:
        return None
    subprocess.run([iscc, f"/DVersion={VERSION}", str(RACINE / "installateur.iss")], check=True)
    return DISTRIBUTION / f"{NOM_EXE}-Setup-{VERSION}.exe"


def main():
    print(f"Fabrication de {NOM} {VERSION}")
    try:
        reglages = lire_reglages()
    except ErreurConstruction as erreur:
        print(f"\nArrêt : {erreur}")
        sys.exit(1)

    dossier_exe = fabriquer_exe(ecrire_reglages(reglages))
    print(f"\nAppli prête : {dossier_exe}")

    if sys.platform != "win32":
        print("L'installateur se fabrique seulement sous Windows.")
        return
    installateur = fabriquer_installateur()
    if installateur is None:
        print(
            "Inno Setup est introuvable : installe-le (https://jrsoftware.org/isdl.php), "
            "puis relance python construire.py."
        )
        return
    print(f"Installateur prêt : {installateur}")


if __name__ == "__main__":
    main()
