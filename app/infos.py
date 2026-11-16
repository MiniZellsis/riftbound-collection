import sys
from pathlib import Path

NOM = "Riftbound Collection"
VERSION = "1.0.1"
DEPOT = "MiniZellsis/riftbound-collection"
ID_WINDOWS = "MiniZellsis.RiftboundCollection"
DOSSIER_APPLI = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ICONE = DOSSIER_APPLI / "ressources" / "icone.png"


def version_en_nombres(texte):
    morceaux = texte.strip().lstrip("vV").split(".")
    try:
        return tuple(int(morceau) for morceau in morceaux)
    except ValueError:
        return ()
