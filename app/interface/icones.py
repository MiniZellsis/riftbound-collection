from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton
from shiboken6 import isValid

from app.interface import theme

RATIO = 2
ECART_TEXTE = 4
_pixmaps = {}
_liens = []
_branche = False
_seuil = [500]


def pixmap(nom, couleur, taille, rempli=False, marge=0):
    cle = (nom, couleur, taille, rempli, marge)
    if cle not in _pixmaps:
        texte = (theme.DOSSIER_ICONES / f"{nom}.svg").read_text(encoding="utf-8").replace("currentColor", couleur)
        if rempli:
            texte = texte.replace('fill="none"', f'fill="{couleur}"')
        rendu = QSvgRenderer(QByteArray(texte.encode("utf-8")))
        image = QPixmap(round((taille + abs(marge)) * RATIO), round(taille * RATIO))
        image.fill(Qt.GlobalColor.transparent)
        image.setDevicePixelRatio(RATIO)
        peintre = QPainter(image)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        rendu.render(peintre, QRectF(max(0, -marge), 0, taille, taille))
        peintre.end()
        _pixmaps[cle] = image
    return _pixmaps[cle]


def icone(nom, taille=18, normal="TEXTE_DOUX", actif="OR", eteint="TEXTE_ETEINT", marge=0):
    resultat = QIcon()
    couleur_normale = getattr(theme, normal)
    couleur_active = getattr(theme, actif)
    couleur_eteinte = getattr(theme, eteint)
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
        resultat.addPixmap(pixmap(nom, couleur_normale, taille, marge=marge), mode, QIcon.State.Off)
        resultat.addPixmap(pixmap(nom, couleur_active, taille, marge=marge), mode, QIcon.State.On)
    for etat in (QIcon.State.Off, QIcon.State.On):
        resultat.addPixmap(pixmap(nom, couleur_eteinte, taille, marge=marge), QIcon.Mode.Disabled, etat)
    return resultat


def marge_texte(cible):
    if not isinstance(cible, QAbstractButton) or not cible.text():
        return 0
    if cible.layoutDirection() == Qt.LayoutDirection.RightToLeft:
        return -ECART_TEXTE
    return ECART_TEXTE


def _brancher():
    global _branche
    if not _branche:
        theme.signaux().change.connect(rafraichir)
        _branche = True
    if len(_liens) > _seuil[0]:
        _liens[:] = [lien for lien in _liens if isValid(lien[0])]
        _seuil[0] = max(500, 2 * len(_liens))


def lier(cible, nom, taille=18, normal="TEXTE_DOUX", actif="OR"):
    _brancher()
    _liens.append((cible, ("bouton", nom, taille, normal, actif)))
    marge = marge_texte(cible)
    cible.setIcon(icone(nom, taille, normal, actif, marge=marge))
    if hasattr(cible, "setIconSize"):
        cible.setIconSize(QSize(taille + abs(marge), taille))


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
            cible.setIcon(icone(nom, taille, premier, second, marge=marge_texte(cible)))
        else:
            cible.setPixmap(pixmap(nom, getattr(theme, premier), taille))
        vivants.append((cible, (sorte, nom, taille, premier, second)))
    _liens[:] = vivants
