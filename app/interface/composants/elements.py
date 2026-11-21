from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.interface import icones, theme

THEMES = [
    ("clair", "sun", "Clair"),
    ("sombre", "moon", "Sombre"),
    ("systeme", "monitor", "Système"),
]


def dessiner_losange(peintre, centre, demi, couleur, lueur=True):
    if lueur:
        halo = QRadialGradient(centre, demi * 2.6)
        teinte = QColor(couleur)
        teinte.setAlpha(120)
        halo.setColorAt(0, teinte)
        teinte.setAlpha(0)
        halo.setColorAt(1, teinte)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(halo)
        peintre.drawEllipse(centre, demi * 2.6, demi * 2.6)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(couleur))
    peintre.drawPolygon(QPolygonF([
        QPointF(centre.x(), centre.y() - demi),
        QPointF(centre.x() + demi, centre.y()),
        QPointF(centre.x(), centre.y() + demi),
        QPointF(centre.x() - demi, centre.y()),
    ]))


class Titre(QLabel):
    def __init__(self, texte, nom="titre", parent=None):
        super().__init__(texte.upper(), parent)
        self.setObjectName(nom)

    def setText(self, texte):
        super().setText(texte.upper())


class Filet(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        peintre = QPainter(self)
        degrade = QLinearGradient(0, 0, self.width(), 0)
        degrade.setColorAt(0, theme.trait())
        fin = theme.trait()
        fin.setAlpha(0)
        degrade.setColorAt(1, fin)
        peintre.fillRect(self.rect(), degrade)


class Separateur(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        milieu = self.height() / 2
        centre = self.width() / 2
        transparent = theme.trait()
        transparent.setAlpha(0)
        for depart, arrivee, debut, fin in (
            (0, centre - 9, transparent, theme.trait()),
            (centre + 9, self.width(), theme.trait(), transparent),
        ):
            degrade = QLinearGradient(depart, 0, arrivee, 0)
            degrade.setColorAt(0, debut)
            degrade.setColorAt(1, fin)
            peintre.fillRect(QRectF(depart, milieu - 0.5, arrivee - depart, 1), degrade)
        dessiner_losange(peintre, QPointF(centre, milieu), 3.2, theme.OR, lueur=False)


class Carte(QFrame):
    def __init__(self, titre, nom_icone, parent=None):
        super().__init__(parent)
        self.setObjectName("carte")
        icone = QLabel()
        icones.lier_image(icone, nom_icone, 16, "OR")
        entete = QHBoxLayout()
        entete.setSpacing(10)
        entete.addWidget(icone)
        entete.addWidget(Titre(titre, "titre_section"))
        entete.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.contenu = QVBoxLayout(self)
        self.contenu.setContentsMargins(20, 18, 20, 20)
        self.contenu.setSpacing(14)
        self.contenu.addLayout(entete)


class Interrupteur(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 22)
        self.position = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(140)
        self.animation.valueChanged.connect(self.avancer)
        self.toggled.connect(self.animer)

    def definir(self, coche):
        self.blockSignals(True)
        self.setChecked(coche)
        self.blockSignals(False)
        self.animation.stop()
        self.position = 1.0 if coche else 0.0
        self.update()

    def avancer(self, valeur):
        self.position = valeur
        self.update()

    def animer(self, coche):
        self.animation.stop()
        self.animation.setStartValue(self.position)
        self.animation.setEndValue(1.0 if coche else 0.0)
        self.animation.start()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            peintre.setOpacity(0.5)
        piste = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        rayon = piste.height() / 2
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(theme.couleur("SURFACE_HAUTE"))
        peintre.drawRoundedRect(piste, rayon, rayon)
        if self.position > 0:
            peintre.save()
            peintre.setOpacity(peintre.opacity() * self.position)
            degrade = QLinearGradient(0, 0, 0, self.height())
            degrade.setColorAt(0, theme.couleur("OR_HAUT"))
            degrade.setColorAt(1, theme.couleur("OR_BAS"))
            peintre.setPen(QPen(theme.couleur("OR_BAS"), 1))
            peintre.setBrush(degrade)
            peintre.drawRoundedRect(piste, rayon, rayon)
            peintre.restore()
        cote = self.height() - 6
        x = 3 + self.position * (self.width() - 6 - cote)
        bouton = QColor(theme.TEXTE_DOUX)
        blanc = QColor("#ffffff")
        melange = QColor(
            round(bouton.red() + (blanc.red() - bouton.red()) * self.position),
            round(bouton.green() + (blanc.green() - bouton.green()) * self.position),
            round(bouton.blue() + (blanc.blue() - bouton.blue()) * self.position),
        )
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(melange)
        peintre.drawEllipse(QRectF(x, 3, cote, cote))


class Avatar(QWidget):
    def __init__(self, texte="", taille=34, parent=None):
        super().__init__(parent)
        self.lettre = ""
        self.setFixedSize(taille, taille)
        self.definir(texte)

    def definir(self, texte):
        self.lettre = (texte or "?")[:1].upper()
        self.update()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        cadre = QRectF(self.rect())
        degrade = QLinearGradient(0, 0, 0, self.height())
        degrade.setColorAt(0, theme.couleur("OR_HAUT"))
        degrade.setColorAt(1, theme.couleur("OR_BAS"))
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(degrade)
        peintre.drawEllipse(cadre)
        peintre.setBrush(theme.couleur("SURFACE"))
        peintre.drawEllipse(cadre.adjusted(2, 2, -2, -2))
        peintre.setFont(theme.police_titres(round(self.height() * 0.42)))
        peintre.setPen(theme.couleur("OR_CLAIR"))
        peintre.drawText(cadre.adjusted(0, 1, 0, 0), Qt.AlignmentFlag.AlignCenter, self.lettre)


class ChoixTheme(QFrame):
    def __init__(self, avec_texte=False, parent=None):
        super().__init__(parent)
        self.setObjectName("segments")
        self.boutons = {}
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        for valeur, nom_icone, texte in THEMES:
            bouton = QPushButton(texte if avec_texte else "")
            bouton.setObjectName("segment")
            bouton.setCheckable(True)
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.setToolTip(f"Thème {texte.lower()}")
            icones.lier(bouton, nom_icone, 15, "TEXTE_DOUX", "OR")
            bouton.clicked.connect(lambda _=False, choix=valeur: theme.choisir(choix))
            self.groupe.addButton(bouton)
            self.boutons[valeur] = bouton
            layout.addWidget(bouton, stretch=1)
        theme.signaux().change.connect(self.synchroniser)
        self.synchroniser()

    def synchroniser(self):
        self.boutons[theme.choix()].setChecked(True)


def dessiner_apercu(peintre, zone, palette):
    peintre.fillRect(zone, QColor(palette["FOND"]))
    barre = QRectF(zone.left(), zone.top(), zone.width() * 0.24, zone.height())
    peintre.fillRect(barre, QColor(palette["BARRE"]))
    peintre.fillRect(QRectF(barre.right() - 1, zone.top(), 1, zone.height()), QColor(palette["BORDURE"]))
    peintre.setPen(Qt.PenStyle.NoPen)
    for rang, cle in enumerate(("OR", "BORDURE", "BORDURE")):
        peintre.setBrush(QColor(palette[cle]))
        peintre.drawRoundedRect(QRectF(barre.left() + 6, zone.top() + 10 + rang * 9, barre.width() - 12, 4), 2, 2)
    gauche = barre.right() + 9
    largeur = zone.right() - gauche - 9
    titre = QColor(palette["TEXTE"])
    titre.setAlpha(210)
    peintre.setBrush(titre)
    peintre.drawRoundedRect(QRectF(gauche, zone.top() + 10, largeur * 0.5, 5), 2, 2)
    ecart = 5
    largeur_carte = (largeur - 2 * ecart) / 3
    hauteur_carte = largeur_carte * 88 / 63
    for rang, nom in enumerate(("Fury", "Mind", "Order")):
        vive = QColor(dict(theme.DOMAINES)[nom])
        degrade = QLinearGradient(0, zone.top() + 22, 0, zone.top() + 22 + hauteur_carte)
        degrade.setColorAt(0, vive)
        degrade.setColorAt(1, vive.darker(260))
        peintre.setBrush(degrade)
        peintre.drawRoundedRect(QRectF(gauche + rang * (largeur_carte + ecart), zone.top() + 22, largeur_carte, hauteur_carte), 3, 3)


class TuileTheme(QAbstractButton):
    HAUTEUR_APERCU = 84

    def __init__(self, valeur, nom_icone, texte, parent=None):
        super().__init__(parent)
        self.valeur = valeur
        self.nom_icone = nom_icone
        self.texte = texte
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Thème {texte.lower()}")
        self.setMinimumSize(120, self.HAUTEUR_APERCU + 34)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        zone = QRectF(1, 1, self.width() - 2, self.HAUTEUR_APERCU)
        chemin = QPainterPath()
        chemin.addRoundedRect(zone, 10, 10)
        peintre.save()
        peintre.setClipPath(chemin)
        if self.valeur == "systeme":
            moitie = zone.width() / 2
            for palette, gauche in ((theme.PALETTES["clair"], 0), (theme.PALETTES["sombre"], moitie)):
                peintre.save()
                peintre.setClipRect(QRectF(zone.left() + gauche, zone.top(), moitie, zone.height()), Qt.ClipOperation.IntersectClip)
                dessiner_apercu(peintre, zone, palette)
                peintre.restore()
        else:
            dessiner_apercu(peintre, zone, theme.PALETTES[self.valeur])
        peintre.restore()
        if self.isChecked():
            peintre.setPen(QPen(theme.couleur("OR"), 2))
        elif self.underMouse():
            peintre.setPen(QPen(theme.couleur("TEXTE_ETEINT"), 1))
        else:
            peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRoundedRect(zone, 10, 10)

        ligne = QRectF(0, self.HAUTEUR_APERCU + 8, self.width(), 22)
        couleur = theme.OR_CLAIR if self.isChecked() else theme.TEXTE_DOUX
        peintre.drawPixmap(QPointF(2, ligne.top() + 3), icones.pixmap(self.nom_icone, couleur, 15))
        police = self.font()
        police.setPixelSize(13)
        police.setWeight(police.Weight.Bold if self.isChecked() else police.Weight.DemiBold)
        peintre.setFont(police)
        peintre.setPen(theme.couleur("TEXTE" if self.isChecked() else "TEXTE_DOUX"))
        peintre.drawText(ligne.adjusted(24, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.texte)
        if self.isChecked():
            peintre.drawPixmap(QPointF(self.width() - 18, ligne.top() + 3), icones.pixmap("check", theme.OR_CLAIR, 15))


class TuilesTheme(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        self.tuiles = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for valeur, nom_icone, texte in THEMES:
            tuile = TuileTheme(valeur, nom_icone, texte)
            tuile.clicked.connect(lambda _=False, choix=valeur: theme.choisir(choix))
            self.groupe.addButton(tuile)
            self.tuiles[valeur] = tuile
            layout.addWidget(tuile)
        theme.signaux().change.connect(self.synchroniser)
        self.synchroniser()

    def synchroniser(self):
        self.tuiles[theme.choix()].setChecked(True)
        for tuile in self.tuiles.values():
            tuile.update()


class BoutonMenu(QPushButton):
    def __init__(self, texte, nom_icone, parent=None):
        super().__init__(texte, parent)
        self.setObjectName("menu")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        icones.lier(self, nom_icone, 18, "TEXTE_DOUX", "OR")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            peintre = QPainter(self)
            peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
            dessiner_losange(peintre, QPointF(7.5, self.height() / 2), 4, theme.OR)


def touches(*noms):
    ligne = QHBoxLayout()
    ligne.setSpacing(5)
    for nom in noms:
        if nom == "à":
            etiquette = QLabel("à")
            etiquette.setObjectName("aide")
        else:
            etiquette = QLabel(nom)
            etiquette.setObjectName("touche")
        ligne.addWidget(etiquette)
    ligne.addStretch()
    return ligne


def ligne_reglage(titre, aide, controle):
    textes = QVBoxLayout()
    textes.setSpacing(2)
    etiquette = QLabel(titre)
    etiquette.setObjectName("libelle")
    textes.addWidget(etiquette)
    if aide:
        explication = QLabel(aide)
        explication.setObjectName("aide")
        explication.setWordWrap(True)
        textes.addWidget(explication)
    ligne = QHBoxLayout()
    ligne.setSpacing(16)
    ligne.addLayout(textes, stretch=1)
    ligne.addWidget(controle, alignment=Qt.AlignmentFlag.AlignVCenter)
    return ligne
