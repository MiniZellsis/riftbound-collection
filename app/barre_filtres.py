import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from app import theme
from app.images import ICONES, fichier_icone

STATUTS = [
    ("possedees", "Possédées", "coche"),
    ("manquantes", "Manquantes", "cercle"),
    ("a_echanger", "À échanger", "fleches"),
    ("recherchees", "Recherchées", "etoile"),
]

DOMAINES = [
    ("Fury", "#e0303a"),
    ("Calm", "#55a843"),
    ("Mind", "#2389c9"),
    ("Body", "#f08a1c"),
    ("Chaos", "#8b5cc4"),
    ("Order", "#d8bc2a"),
    ("Colorless", "#8f9bb3"),
]

RARETES = [
    ("Common", "#a4b8aa"),
    ("Uncommon", "#41b4b8"),
    ("Rare", "#c47bb4"),
    ("Epic", "#d0874f"),
    ("Showcase", "#d4b445"),
    ("Promo", "#f778ba"),
]

TYPES = ["Unit", "Spell", "Gear", "Legend", "Battlefield", "Rune"]


def creer_stylo(couleur, epaisseur):
    stylo = QPen(QColor(couleur), epaisseur)
    stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
    stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return stylo


def icone_loupe():
    pixmap = QPixmap(32, 32)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(creer_stylo(theme.TEXTE_DOUX, 1.6))
    peintre.drawEllipse(QPointF(7, 7), 4.5, 4.5)
    peintre.drawLine(QPointF(10.5, 10.5), QPointF(14, 14))
    peintre.end()
    return QIcon(pixmap)


def dessiner_halo(peintre, centre, rayon, couleur):
    halo = QRadialGradient(centre, rayon)
    lumiere = QColor(couleur)
    lumiere.setAlpha(130)
    halo.setColorAt(0, lumiere)
    lumiere.setAlpha(0)
    halo.setColorAt(1, lumiere)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(halo)
    peintre.drawEllipse(centre, rayon, rayon)


def dessiner_gemme(peintre, centre, rayon, couleur, allumee):
    if allumee:
        dessiner_halo(peintre, centre, rayon * 2, couleur)

    degrade = QRadialGradient(centre - QPointF(rayon * 0.35, rayon * 0.35), rayon * 1.4)
    degrade.setColorAt(0, couleur.lighter(160))
    degrade.setColorAt(0.5, couleur)
    degrade.setColorAt(1, couleur.darker(180))
    peintre.setBrush(degrade)
    peintre.setPen(QPen(couleur.darker(220), 1))
    peintre.drawEllipse(centre, rayon, rayon)

    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(255, 255, 255, 120))
    peintre.drawEllipse(centre + QPointF(-rayon * 0.3, -rayon * 0.45), rayon * 0.38, rayon * 0.22)


def dessiner_symbole(peintre, centre, rayon, symbole, allume):
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(theme.OR if allume else theme.SURFACE_HAUTE))
    peintre.drawEllipse(centre, rayon, rayon)

    stylo = creer_stylo(theme.FOND if allume else theme.TEXTE_DOUX, 2)
    peintre.setPen(stylo)
    peintre.setBrush(Qt.BrushStyle.NoBrush)
    x, y, r = centre.x(), centre.y(), rayon * 0.45

    if symbole == "coche":
        peintre.drawPolyline(QPolygonF([
            QPointF(x - r, y), QPointF(x - r * 0.25, y + r * 0.75), QPointF(x + r, y - r * 0.7),
        ]))
    elif symbole == "cercle":
        stylo.setStyle(Qt.PenStyle.DotLine)
        peintre.setPen(stylo)
        peintre.drawEllipse(centre, r, r)
    elif symbole == "fleches":
        peintre.drawLine(QPointF(x - r, y - r * 0.45), QPointF(x + r, y - r * 0.45))
        peintre.drawPolyline(QPolygonF([
            QPointF(x + r * 0.4, y - r), QPointF(x + r, y - r * 0.45), QPointF(x + r * 0.4, y + r * 0.1),
        ]))
        peintre.drawLine(QPointF(x + r, y + r * 0.45), QPointF(x - r, y + r * 0.45))
        peintre.drawPolyline(QPolygonF([
            QPointF(x - r * 0.4, y - r * 0.1), QPointF(x - r, y + r * 0.45), QPointF(x - r * 0.4, y + r),
        ]))
    elif symbole == "etoile":
        points = []
        for i in range(10):
            longueur = r * 1.15 if i % 2 == 0 else r * 0.5
            angle = math.pi / 5 * i - math.pi / 2
            points.append(QPointF(x + longueur * math.cos(angle), y + longueur * math.sin(angle)))
        peintre.drawPolygon(QPolygonF(points))


class Choix(QAbstractButton):
    def __init__(self, texte, couleur=None, symbole=None, parent=None):
        super().__init__(parent)
        self.texte = texte
        self.couleur = QColor(couleur) if couleur else None
        self.symbole = symbole
        self.icone = None
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if couleur or symbole:
            self.setFixedSize(88, 76)
        else:
            self.setFixedSize(104, 40)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = self.couleur or QColor(theme.OR)
        cadre = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        if self.isChecked():
            fond = QColor(accent)
            fond.setAlpha(38)
            peintre.setBrush(fond)
            peintre.setPen(QPen(accent, 1.5))
        elif self.underMouse():
            peintre.setBrush(QColor(theme.SURFACE_HAUTE))
            peintre.setPen(Qt.PenStyle.NoPen)
        else:
            peintre.setBrush(QColor(255, 255, 255, 8))
            peintre.setPen(Qt.PenStyle.NoPen)
        peintre.drawRoundedRect(cadre, 10, 10)

        zone_texte = QRectF(self.rect())
        if self.couleur or self.symbole:
            centre = QPointF(self.width() / 2, 28)
            if self.symbole:
                dessiner_symbole(peintre, centre, 14, self.symbole, self.isChecked())
            elif self.charger_icone():
                if self.isChecked():
                    dessiner_halo(peintre, centre, 26, self.couleur)
                taille = self.icone.deviceIndependentSize().scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio)
                cible = QRectF(QPointF(0, 0), taille)
                cible.moveCenter(centre)
                peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                peintre.drawPixmap(cible, self.icone, QRectF(self.icone.rect()))
            else:
                dessiner_gemme(peintre, centre, 13, self.couleur, self.isChecked())
            zone_texte = QRectF(0, 48, self.width(), 22)

        police = self.font()
        police.setPixelSize(12)
        police.setBold(self.isChecked())
        peintre.setFont(police)
        peintre.setPen(QColor(theme.TEXTE if self.isChecked() else theme.TEXTE_DOUX))
        peintre.drawText(zone_texte, Qt.AlignmentFlag.AlignCenter, self.texte)


    def charger_icone(self):
        if self.icone is None and self.texte in ICONES:
            icone = QPixmap(str(fichier_icone(self.texte)))
            if not icone.isNull():
                self.icone = icone
        return self.icone is not None


class BoutonFiltre(QPushButton):
    def __init__(self, texte, parent=None):
        super().__init__(texte, parent)
        self.setObjectName("filtre")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        couleur = theme.OR_CLAIR if self.property("actif") else theme.TEXTE_DOUX
        peintre.setPen(creer_stylo(couleur, 1.6))
        x = self.width() - 24
        y = self.height() / 2
        peintre.drawPolyline(QPolygonF([QPointF(x, y - 2), QPointF(x + 4, y + 2), QPointF(x + 8, y - 2)]))


class BarreFiltres(QWidget):
    filtres_changes = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupes = {}
        self.boutons = {}
        self.titres = {}

        self.recherche = QLineEdit()
        self.recherche.setObjectName("recherche")
        self.recherche.setPlaceholderText("Rechercher une carte (nom ou code)")
        self.recherche.setClearButtonEnabled(True)
        self.recherche.addAction(icone_loupe(), QLineEdit.ActionPosition.LeadingPosition)
        self.recherche.setMinimumWidth(220)
        self.recherche.setMaximumWidth(420)

        self.bouton_effacer = QPushButton("Réinitialiser")
        self.bouton_effacer.setObjectName("lien")
        self.bouton_effacer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_effacer.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.recherche, stretch=1)
        layout.addSpacing(4)
        layout.addWidget(self.ajouter_groupe("statuts", "Collection", [
            (valeur, Choix(texte, symbole=symbole)) for valeur, texte, symbole in STATUTS
        ]))
        layout.addWidget(self.ajouter_groupe("domaines", "Domaine", [
            (nom, Choix(nom, couleur=couleur)) for nom, couleur in DOMAINES
        ]))
        layout.addWidget(self.ajouter_groupe("raretes", "Rareté", [
            (nom, Choix(nom, couleur=couleur)) for nom, couleur in RARETES
        ]))
        layout.addWidget(self.ajouter_groupe("types", "Type", [
            (nom, Choix(nom)) for nom in TYPES
        ]))
        layout.addStretch()
        layout.addWidget(self.bouton_effacer)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.changement)
        self.recherche.textChanged.connect(self.texte_modifie)
        self.bouton_effacer.clicked.connect(self.effacer)

    def ajouter_groupe(self, nom, titre, choix):
        bouton = BoutonFiltre(titre)

        etiquette = QLabel(titre.upper())
        etiquette.setObjectName("section")
        vider = QPushButton("Effacer")
        vider.setObjectName("lien")
        vider.setCursor(Qt.CursorShape.PointingHandCursor)
        vider.clicked.connect(lambda: self.vider(nom))

        entete = QHBoxLayout()
        entete.addWidget(etiquette)
        entete.addStretch()
        entete.addWidget(vider)

        ligne = QHBoxLayout()
        ligne.setSpacing(6)
        for valeur, element in choix:
            element.toggled.connect(self.changement)
            ligne.addWidget(element)

        contenu = QWidget()
        contenu.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)
        layout = QVBoxLayout(contenu)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(entete)
        layout.addLayout(ligne)

        menu = theme.creer_menu(self)
        menu.setObjectName("popover")
        menu.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        action = QWidgetAction(menu)
        action.setDefaultWidget(contenu)
        menu.addAction(action)
        bouton.clicked.connect(lambda: menu.popup(bouton.mapToGlobal(QPoint(0, bouton.height() + 6))))

        self.groupes[nom] = dict(choix)
        self.boutons[nom] = bouton
        self.titres[nom] = titre
        return bouton

    def texte_modifie(self):
        self.minuteur.start()

    def icone_telechargee(self, cle):
        if cle in ICONES:
            for elements in self.groupes.values():
                for element in elements.values():
                    element.update()

    def changement(self):
        for nom, elements in self.groupes.items():
            coches = [element.texte for element in elements.values() if element.isChecked()]
            if not coches:
                texte = self.titres[nom]
            elif len(coches) == 1:
                texte = f"{self.titres[nom]} · {coches[0]}"
            else:
                texte = f"{self.titres[nom]} · {len(coches)}"
            bouton = self.boutons[nom]
            bouton.setText(texte)
            bouton.setProperty("actif", bool(coches))
            bouton.style().unpolish(bouton)
            bouton.style().polish(bouton)
        self.bouton_effacer.setVisible(self.actifs())
        self.filtres_changes.emit()

    def filtres(self):
        choix = {"texte": self.recherche.text().strip().lower()}
        for nom, elements in self.groupes.items():
            choix[nom] = [valeur for valeur, element in elements.items() if element.isChecked()]
        return choix

    def actifs(self):
        return any(self.filtres().values())

    def vider(self, nom):
        self.blockSignals(True)
        for element in self.groupes[nom].values():
            element.setChecked(False)
        self.blockSignals(False)
        self.changement()

    def effacer(self):
        self.blockSignals(True)
        self.recherche.clear()
        for elements in self.groupes.values():
            for element in elements.values():
                element.setChecked(False)
        self.blockSignals(False)
        self.minuteur.stop()
        self.changement()
