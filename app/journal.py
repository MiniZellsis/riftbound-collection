import threading
import traceback
from datetime import datetime

from app.infos import DOSSIER_DONNEES, VERSION

FICHIER = DOSSIER_DONNEES / "erreurs.log"
TAILLE_MAX = 1_000_000

_verrou = threading.Lock()


def noter(texte):
    with _verrou:
        try:
            DOSSIER_DONNEES.mkdir(parents=True, exist_ok=True)
            if FICHIER.exists() and FICHIER.stat().st_size > TAILLE_MAX:
                FICHIER.replace(FICHIER.with_name("erreurs.ancien.log"))
            with FICHIER.open("a", encoding="utf-8") as fichier:
                fichier.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} · version {VERSION}\n{texte.rstrip()}\n\n")
        except OSError:
            pass


def noter_erreur(type_erreur, erreur, trace):
    details = "".join(traceback.format_exception(type_erreur, erreur, trace))
    noter(details)
    return details
