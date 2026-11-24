import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPen, QPixmap, QPolygonF, QRadialGradient
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

from app.donnees.images import ICONES, fichier_icone
from app.interface import icones, theme

STATUTS = [
    ("possedees", "Possédées", "coche"),
    ("manquantes", "Manquantes", "cercle"),
    ("a_echanger", "À échanger", "fleches"),
    ("recherchees", "Recherchées", "etoile"),
]

TYPES = ["Unit", "Spell", "Gear", "Legend", "Battlefield", "Rune"]

GROUPES = [
    ("statuts", "Collection", "library"),
    ("domaines", "Domaine", "hexagon"),
    ("raretes", "Rareté", "gem"),
    ("types", "Type", "sword"),
]


def creer_stylo(couleur, epaisseur):
    stylo = QPen(QColor(couleur), epaisseur)
    stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
    stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return stylo


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

    stylo = creer_stylo(theme.ENCRE if allume else theme.TEXTE_DOUX, 2)
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
            peintre.setBrush(theme.couleur("TEXTE", 10))
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


class BoutonFiltre(QAbstractButton):
    vider = Signal()

    def __init__(self, texte, nom_icone, parent=None):
        super().__init__(parent)
        self.nom_icone = nom_icone
        self.actif = False
        self.sur_croix = False
        self.appui_croix = False
        self.setText(texte)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFixedHeight(36)

    def definir(self, texte, actif):
        self.setText(texte)
        self.actif = actif
        if not actif:
            self.sur_croix = False
        self.updateGeometry()
        self.update()

    def police(self):
        police = QFont(self.font())
        police.setPixelSize(13)
        police.setWeight(QFont.Weight.DemiBold if self.actif else QFont.Weight.Medium)
        return police

    def sizeHint(self):
        largeur = QFontMetrics(self.police()).horizontalAdvance(self.text())
        return QSize(largeur + (83 if self.actif else 74), 36)

    def zone_croix(self):
        return QRectF(self.width() - 42, 0, 42, self.height())

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.sur_croix = False
        self.update()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        sur_croix = self.actif and self.zone_croix().contains(event.position())
        if sur_croix != self.sur_croix:
            self.sur_croix = sur_croix
            self.setToolTip("Retirer ce filtre" if sur_croix else "")
            self.update()

    def mousePressEvent(self, event):
        if self.actif and event.button() == Qt.MouseButton.LeftButton and self.zone_croix().contains(event.position()):
            self.appui_croix = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.appui_croix:
            self.appui_croix = False
            event.accept()
            if self.zone_croix().contains(event.position()):
                self.vider.emit()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        survol = self.underMouse()
        if self.actif:
            fond = theme.voile()
            bord = theme.trait()
            encre = theme.OR_CLAIR
        else:
            fond = theme.couleur("SURFACE")
            bord = theme.couleur("TEXTE_ETEINT" if survol else "BORDURE")
            encre = theme.TEXTE if survol else theme.TEXTE_DOUX
        peintre.setPen(QPen(bord, 1))
        peintre.setBrush(fond)
        peintre.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        milieu = self.height() / 2
        peintre.drawPixmap(QPointF(12, milieu - 8), icones.pixmap(self.nom_icone, encre, 16))
        peintre.setFont(self.police())
        peintre.setPen(QColor(encre))
        peintre.drawText(
            QRectF(36, 0, self.width() - 36, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )

        droite = self.width() - 12
        if self.actif:
            if self.sur_croix:
                peintre.setPen(Qt.PenStyle.NoPen)
                peintre.setBrush(theme.voile())
                peintre.drawEllipse(QPointF(droite - 8, milieu), 13, 13)
            peintre.fillRect(QRectF(droite - 25, milieu - 8, 1, 16), theme.trait())
            peintre.drawPixmap(QPointF(droite - 16, milieu - 8), icones.pixmap("x", theme.OR_CLAIR, 16))
        else:
            couleur = encre if survol else theme.TEXTE_ETEINT
            peintre.drawPixmap(QPointF(droite - 16, milieu - 8), icones.pixmap("chevron-down", couleur, 16))


class ChampRecherche(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recherche")
        self.setPlaceholderText("Rechercher une carte (nom ou code)")
        self.setClearButtonEnabled(True)
        loupe = self.addAction(QIcon(), QLineEdit.ActionPosition.LeadingPosition)
        icones.lier(loupe, "search", 16, "TEXTE_DOUX", "TEXTE_DOUX")
        self.touche = QLabel("Ctrl F", self)
        self.touche.setObjectName("touche_champ")
        self.touche.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.textChanged.connect(self.placer_touche)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.placer_touche()

    def placer_touche(self):
        self.touche.adjustSize()
        vide = not self.text()
        self.touche.setVisible(vide)
        self.setTextMargins(0, 0, self.touche.width() + 6 if vide else 0, 0)
        self.touche.move(self.width() - self.touche.width() - 9, (self.height() - self.touche.height()) // 2)


class BarreFiltres(QWidget):
    filtres_changes = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupes = {}
        self.boutons = {}
        self.titres = {}

        self.recherche = ChampRecherche()
        self.recherche.setMinimumWidth(220)
        self.recherche.setMaximumWidth(360)

        self.bouton_effacer = QPushButton("Réinitialiser")
        self.bouton_effacer.setObjectName("lien")
        self.bouton_effacer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_effacer.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.recherche, stretch=1)
        layout.addSpacing(4)
        choix = {
            "statuts": [(valeur, Choix(texte, symbole=symbole)) for valeur, texte, symbole in STATUTS],
            "domaines": [(nom, Choix(nom, couleur=couleur)) for nom, couleur in theme.DOMAINES],
            "raretes": [(nom, Choix(nom, couleur=couleur)) for nom, couleur in theme.RARETES],
            "types": [(nom, Choix(nom)) for nom in TYPES],
        }
        for nom, titre, nom_icone in GROUPES:
            layout.addWidget(self.ajouter_groupe(nom, titre, nom_icone, choix[nom]))
        layout.addStretch()
        layout.addWidget(self.bouton_effacer)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.changement)
        self.recherche.textChanged.connect(self.texte_modifie)
        self.bouton_effacer.clicked.connect(self.effacer)

    def ajouter_groupe(self, nom, titre, nom_icone, choix):
        bouton = BoutonFiltre(titre, nom_icone)
        bouton.vider.connect(lambda: self.vider(nom))

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
            self.boutons[nom].definir(texte, bool(coches))
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
