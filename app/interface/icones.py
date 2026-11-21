from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from shiboken6 import isValid

from app.interface import theme

RATIO = 2
_pixmaps = {}
_liens = []
_branche = False


def pixmap(nom, couleur, taille):
    cle = (nom, couleur, taille)
    if cle not in _pixmaps:
        texte = (theme.DOSSIER_ICONES / f"{nom}.svg").read_text(encoding="utf-8").replace("currentColor", couleur)
        rendu = QSvgRenderer(QByteArray(texte.encode("utf-8")))
        image = QPixmap(round(taille * RATIO), round(taille * RATIO))
        image.fill(Qt.GlobalColor.transparent)
        image.setDevicePixelRatio(RATIO)
        peintre = QPainter(image)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        rendu.render(peintre, QRectF(0, 0, taille, taille))
        peintre.end()
        _pixmaps[cle] = image
    return _pixmaps[cle]


def icone(nom, taille=18, normal="TEXTE_DOUX", actif="OR", eteint="TEXTE_ETEINT"):
    resultat = QIcon()
    couleur_normale = getattr(theme, normal)
    couleur_active = getattr(theme, actif)
    couleur_eteinte = getattr(theme, eteint)
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
        resultat.addPixmap(pixmap(nom, couleur_normale, taille), mode, QIcon.State.Off)
        resultat.addPixmap(pixmap(nom, couleur_active, taille), mode, QIcon.State.On)
    for etat in (QIcon.State.Off, QIcon.State.On):
        resultat.addPixmap(pixmap(nom, couleur_eteinte, taille), QIcon.Mode.Disabled, etat)
    return resultat


def _brancher():
    global _branche
    if not _branche:
        theme.signaux().change.connect(rafraichir)
        _branche = True


def lier(cible, nom, taille=18, normal="TEXTE_DOUX", actif="OR"):
    _brancher()
    _liens.append((cible, ("bouton", nom, taille, normal, actif)))
    cible.setIcon(icone(nom, taille, normal, actif))
    if hasattr(cible, "setIconSize"):
        cible.setIconSize(QSize(taille, taille))


def lier_image(etiquette, nom, taille=16, couleur="OR"):
    _brancher()
    _liens.append((etiquette, ("image", nom, taille, couleur, None)))
    etiquette.setPixmap(pixmap(nom, getattr(theme, couleur), taille))


def rafraichir():
    _pixmaps.clear()
    vivants = []
    for cible, (sorte, nom, taille, premier, second) in _liens:
        if not isValid(cible):
            continue
        if sorte == "bouton":
            cible.setIcon(icone(nom, taille, premier, second))
        else:
            cible.setPixmap(pixmap(nom, getattr(theme, premier), taille))
        vivants.append((cible, (sorte, nom, taille, premier, second)))
    _liens[:] = vivants
