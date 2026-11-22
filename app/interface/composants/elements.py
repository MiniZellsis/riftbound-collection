from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (
    QActionGroup,
    QColor,
    QFont,
    QFontMetrics,
    QIntValidator,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabBar,
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


class Onglets(QTabBar):
    HAUTEUR = 46
    BASE = 41

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nombres = []
        self.survol = -1
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setElideMode(Qt.TextElideMode.ElideNone)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def tabInserted(self, index):
        self.nombres.insert(index, None)
        super().tabInserted(index)

    def tabRemoved(self, index):
        del self.nombres[index]
        super().tabRemoved(index)

    def nombre(self, index):
        return self.nombres[index] if 0 <= index < len(self.nombres) else None

    def definir_nombre(self, index, nombre):
        if self.nombre(index) != nombre:
            self.nombres[index] = nombre
            self.setTabText(index, self.tabText(index))

    def police_nom(self):
        police = theme.police_titres(13)
        police.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        return police

    def police_nombre(self):
        police = QFont(self.font())
        police.setPixelSize(12)
        police.setWeight(QFont.Weight.DemiBold)
        return police

    def tabSizeHint(self, index):
        largeur = QFontMetrics(self.police_nom()).horizontalAdvance(self.tabText(index).upper())
        nombre = self.nombre(index)
        if nombre is not None:
            largeur += 8 + QFontMetrics(self.police_nombre()).horizontalAdvance(str(nombre))
        return QSize(largeur + 28, self.HAUTEUR)

    def minimumTabSizeHint(self, index):
        return self.tabSizeHint(index)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.changer_survol(self.tabAt(event.position().toPoint()))

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.changer_survol(-1)

    def changer_survol(self, index):
        if index != self.survol:
            self.survol = index
            self.update()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.fillRect(QRectF(0, self.BASE, self.width(), 1), theme.couleur("BORDURE"))
        police_nom = self.police_nom()
        ligne = self.BASE / 2 + QFontMetrics(police_nom).capHeight() / 2
        for index in range(self.count()):
            zone = QRectF(self.tabRect(index))
            choisi = index == self.currentIndex()
            if choisi:
                couleur = "OR_CLAIR"
            elif index == self.survol:
                couleur = "TEXTE"
            else:
                couleur = "TEXTE_DOUX"
            texte = self.tabText(index).upper()
            peintre.setFont(police_nom)
            peintre.setPen(theme.couleur(couleur))
            peintre.drawText(QPointF(zone.left() + 14, ligne), texte)
            nombre = self.nombre(index)
            if nombre is not None:
                x = zone.left() + 14 + QFontMetrics(police_nom).horizontalAdvance(texte) + 8
                peintre.setFont(self.police_nombre())
                peintre.setPen(theme.couleur("OR_CLAIR" if choisi else "TEXTE_ETEINT"))
                peintre.drawText(QPointF(x, ligne), str(nombre))
            if choisi:
                gauche = zone.left() + 10
                droite = zone.right() - 10
                degrade = QLinearGradient(gauche, 0, droite, 0)
                degrade.setColorAt(0, theme.couleur("OR", 0))
                degrade.setColorAt(0.2, theme.couleur("OR"))
                degrade.setColorAt(0.8, theme.couleur("OR"))
                degrade.setColorAt(1, theme.couleur("OR", 0))
                peintre.fillRect(QRectF(gauche, self.BASE - 0.5, droite - gauche, 2), degrade)
                dessiner_losange(peintre, QPointF(zone.center().x(), self.BASE + 0.5), 3.6, theme.OR)


class Flux(QLayout):
    def __init__(self, ecart_horizontal=8, ecart_vertical=6, parent=None):
        super().__init__(parent)
        self.elements = []
        self.ecart_horizontal = ecart_horizontal
        self.ecart_vertical = ecart_vertical
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, element):
        self.elements.append(element)

    def count(self):
        return len(self.elements)

    def itemAt(self, index):
        return self.elements[index] if 0 <= index < len(self.elements) else None

    def takeAt(self, index):
        return self.elements.pop(index) if 0 <= index < len(self.elements) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largeur):
        return self.placer(QRect(0, 0, largeur, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.placer(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        taille = QSize()
        for element in self.elements:
            if not element.isEmpty():
                taille = taille.expandedTo(element.minimumSize())
        return taille

    def placer(self, rect, appliquer):
        lignes = [[]]
        x = rect.x()
        for element in self.elements:
            if element.isEmpty():
                continue
            largeur = element.sizeHint().width()
            if lignes[-1] and x + largeur > rect.right() + 1:
                lignes.append([])
                x = rect.x()
            lignes[-1].append(element)
            x += largeur + self.ecart_horizontal
        y = rect.y()
        for ligne in lignes:
            hauteur = max((element.sizeHint().height() for element in ligne), default=0)
            if appliquer:
                x = rect.x()
                for element in ligne:
                    taille = element.sizeHint()
                    element.setGeometry(QRect(QPoint(x, y + (hauteur - taille.height()) // 2), taille))
                    x += taille.width() + self.ecart_horizontal
            y += hauteur + self.ecart_vertical
        return max(0, y - self.ecart_vertical - rect.y())


class Statut(QWidget):
    ETATS = {
        "ok": ("VERT", "circle-check"),
        "envoi": ("OR", "refresh-cw"),
        "erreur": ("ROUGE", "circle-alert"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.etat = None
        self.texte = ""
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def definir(self, etat, texte=""):
        self.etat = etat
        self.texte = texte if etat else ""
        self.updateGeometry()
        self.update()

    def police(self):
        police = QFont(self.font())
        police.setPixelSize(12)
        police.setWeight(QFont.Weight.DemiBold)
        return police

    def sizeHint(self):
        if self.etat is None:
            return QSize(0, 26)
        return QSize(34 + QFontMetrics(self.police()).horizontalAdvance(self.texte) + 10, 26)

    def paintEvent(self, event):
        if self.etat is None:
            return
        nom_couleur, nom_icone = self.ETATS[self.etat]
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(theme.couleur(nom_couleur, 34))
        peintre.drawRoundedRect(QRectF(self.rect()), 13, 13)
        couleur = getattr(theme, nom_couleur)
        peintre.drawPixmap(QPointF(11, 6), icones.pixmap(nom_icone, couleur, 14))
        peintre.setFont(self.police())
        peintre.setPen(QColor(couleur))
        peintre.drawText(QRectF(32, 0, self.width() - 32, self.height()), Qt.AlignmentFlag.AlignVCenter, self.texte)


def dessin_vide(nom_icone):
    taille = 112
    image = QPixmap(taille * 2, taille * 2)
    image.setDevicePixelRatio(2)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    centre = QPointF(taille / 2, taille / 2)
    halo = QRadialGradient(centre, taille / 2)
    halo.setColorAt(0, theme.couleur("OR", 46))
    halo.setColorAt(1, theme.couleur("OR", 0))
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(halo)
    peintre.drawEllipse(centre, taille / 2, taille / 2)
    pointilles = QPen(theme.trait(), 1.2)
    pointilles.setDashPattern([2.5, 3.5])
    peintre.setPen(pointilles)
    peintre.setBrush(Qt.BrushStyle.NoBrush)
    peintre.drawEllipse(centre, 44, 44)
    peintre.setPen(QPen(theme.trait(), 1))
    peintre.setBrush(theme.voile())
    peintre.drawEllipse(centre, 31, 31)
    for x in (centre.x() - 44, centre.x() + 44):
        dessiner_losange(peintre, QPointF(x, centre.y()), 3.5, theme.OR, lueur=False)
    peintre.drawPixmap(QPointF(centre.x() - 14, centre.y() - 14), icones.pixmap(nom_icone, theme.OR_CLAIR, 28))
    peintre.end()
    return image


class EtatVide(QWidget):
    action = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dessin = QLabel()
        self.dessin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titre = QLabel("")
        self.titre.setObjectName("titre_vide")
        self.titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte = QLabel("")
        self.texte.setObjectName("sous_titre")
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte.setWordWrap(True)
        self.texte.setFixedWidth(440)
        self.bouton = QPushButton("")
        self.bouton.setObjectName("principal")
        self.bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton.clicked.connect(self.action)
        self.arguments = None
        theme.signaux().change.connect(self.redessiner)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addStretch(2)
        layout.addWidget(self.dessin)
        layout.addSpacing(4)
        layout.addWidget(self.titre)
        layout.addWidget(self.texte, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.bouton, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(3)

    def redessiner(self):
        if self.arguments is not None:
            self.definir(*self.arguments)

    def definir(self, titre, texte="", bouton="", nom_icone="search"):
        self.arguments = (titre, texte, bouton, nom_icone)
        self.dessin.setPixmap(dessin_vide(nom_icone))
        self.titre.setText(titre)
        self.texte.setText(texte)
        hauteur = self.texte.heightForWidth(self.texte.width())
        if hauteur > 0:
            self.texte.setFixedHeight(hauteur)
        self.texte.setVisible(bool(texte))
        self.bouton.setText(bouton)
        self.bouton.setVisible(bool(bouton))


class ListeChoix(QAbstractButton):
    change = Signal()

    def __init__(self, choix, parent=None):
        super().__init__(parent)
        self.choix = list(choix)
        self.valeur = self.choix[0][0] if self.choix else None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.clicked.connect(self.ouvrir)

    def texte(self):
        return dict(self.choix).get(self.valeur, "")

    def definir(self, valeur):
        if valeur in dict(self.choix):
            self.valeur = valeur
            self.update()

    def definir_choix(self, choix):
        self.choix = list(choix)
        if self.valeur not in dict(self.choix):
            self.valeur = self.choix[0][0] if self.choix else None
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        metrique = QFontMetrics(self.font())
        largeur = max((metrique.horizontalAdvance(texte) for _, texte in self.choix), default=60)
        return QSize(largeur + 52, 36)

    def ouvrir(self):
        menu = theme.creer_menu(self)
        groupe = QActionGroup(menu)
        actions = {}
        for valeur, texte in self.choix:
            action = menu.addAction(texte)
            action.setCheckable(True)
            action.setChecked(valeur == self.valeur)
            groupe.addAction(action)
            actions[action] = valeur
        menu.setMinimumWidth(self.width())
        choisie = menu.exec(self.mapToGlobal(QPoint(0, self.height() + 4)))
        menu.deleteLater()
        if choisie in actions and actions[choisie] != self.valeur:
            self.valeur = actions[choisie]
            self.update()
            self.change.emit()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        survol = self.underMouse() or self.hasFocus()
        peintre.setPen(QPen(theme.couleur("TEXTE_ETEINT" if survol else "BORDURE"), 1))
        peintre.setBrush(theme.couleur("SURFACE"))
        peintre.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        peintre.setPen(theme.couleur("TEXTE"))
        peintre.setFont(self.font())
        texte = QFontMetrics(self.font()).elidedText(self.texte(), Qt.TextElideMode.ElideRight, self.width() - 52)
        peintre.drawText(QRectF(12, 0, self.width() - 40, self.height()), Qt.AlignmentFlag.AlignVCenter, texte)
        couleur = theme.TEXTE if survol else theme.TEXTE_DOUX
        peintre.drawPixmap(QPointF(self.width() - 28, self.height() / 2 - 8), icones.pixmap("chevron-down", couleur, 16))


class Segments(QFrame):
    change = Signal()

    def __init__(self, choix, parent=None):
        super().__init__(parent)
        self.setObjectName("segments")
        self.boutons = {}
        self.groupe = QButtonGroup(self)
        self.groupe.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        for valeur, texte in choix:
            bouton = QPushButton(texte)
            bouton.setObjectName("segment_texte")
            bouton.setCheckable(True)
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.clicked.connect(self.change)
            self.groupe.addButton(bouton)
            self.boutons[valeur] = bouton
            layout.addWidget(bouton)
        if choix:
            self.boutons[choix[0][0]].setChecked(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def valeur(self):
        for valeur, bouton in self.boutons.items():
            if bouton.isChecked():
                return valeur
        return None

    def definir(self, valeur):
        if valeur in self.boutons:
            self.boutons[valeur].setChecked(True)


class ChampNombre(QWidget):
    change = Signal(int)

    def __init__(self, minimum, maximum, pas=1, unite="", parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.pas = pas
        self.nombre = minimum
        self.moins = QPushButton("")
        self.moins.setObjectName("rond")
        icones.lier(self.moins, "minus", 13, "TEXTE", "TEXTE")
        self.plus = QPushButton("")
        self.plus.setObjectName("rond_or")
        icones.lier(self.plus, "plus", 13, "OR_CLAIR", "OR_CLAIR")
        for bouton in (self.moins, self.plus):
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.setAutoRepeat(True)
        self.champ = QLineEdit(str(minimum))
        self.champ.setObjectName("nombre")
        self.champ.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.champ.setValidator(QIntValidator(0, 99999, self))
        self.champ.setFixedWidth(64 if unite else 48)
        self.champ.installEventFilter(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.moins)
        layout.addWidget(self.champ)
        layout.addWidget(self.plus)
        if unite:
            texte = QLabel(unite)
            texte.setObjectName("sous_titre")
            layout.addSpacing(2)
            layout.addWidget(texte)
        self.moins.clicked.connect(lambda: self.definir(self.nombre - self.pas))
        self.plus.clicked.connect(lambda: self.definir(self.nombre + self.pas))
        self.champ.editingFinished.connect(self.saisie_finie)
        self.actualiser_boutons()

    def valeur(self):
        return self.nombre

    def definir(self, valeur):
        valeur = max(self.minimum, min(self.maximum, valeur))
        self.champ.setText(str(valeur))
        if valeur != self.nombre:
            self.nombre = valeur
            self.actualiser_boutons()
            self.change.emit(valeur)
        else:
            self.actualiser_boutons()

    def definir_limites(self, minimum, maximum, pas=None):
        self.minimum = minimum
        self.maximum = maximum
        if pas is not None:
            self.pas = pas
        self.definir(self.nombre)

    def saisie_finie(self):
        texte = self.champ.text()
        self.definir(int(texte) if texte.isdigit() else self.nombre)

    def actualiser_boutons(self):
        self.moins.setEnabled(self.nombre > self.minimum)
        self.plus.setEnabled(self.nombre < self.maximum)

    def eventFilter(self, objet, evenement):
        if objet is self.champ and evenement.type() == QEvent.Type.KeyPress:
            if evenement.key() == Qt.Key.Key_Up:
                self.definir(self.nombre + self.pas)
                return True
            if evenement.key() == Qt.Key.Key_Down:
                self.definir(self.nombre - self.pas)
                return True
        if objet is self.champ and evenement.type() == QEvent.Type.Wheel:
            self.definir(self.nombre + (self.pas if evenement.angleDelta().y() > 0 else -self.pas))
            return True
        return super().eventFilter(objet, evenement)
