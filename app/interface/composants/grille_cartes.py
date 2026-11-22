import time

from PySide6.QtCore import QEvent, QPointF, QRectF, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

from app.donnees.catalogue import code_affiche
from app.donnees.images import ARRONDI, charger_miniature
from app.interface import icones, theme
from app.interface.composants.effets import (
    Inclinaison,
    ajouter_effets,
    arc_en_ciel,
    dessiner_avec_bord,
    dessiner_etoile,
    dessiner_ombre,
    incliner,
)

LARGEUR_MIN = 120
LARGEUR_MAX = 280
LARGEUR_DEFAUT = 160
RAPPORT = 1.4
MARGE = 8
HAUTEUR_NOM = 36
TEMPS_PAR_TOUR = 0.008
AGRANDISSEMENT = 0.02
OPACITE_MANQUANTE = 0.35
OPACITE_MANQUANTE_SURVOL = 0.6
ROLE_CARTE_ID = Qt.ItemDataRole.UserRole
ROLE_CODE = Qt.ItemDataRole.UserRole + 1


def lire_largeur():
    largeur = QSettings().value("taille_cartes", LARGEUR_DEFAUT, int)
    return max(LARGEUR_MIN, min(largeur, LARGEUR_MAX))


def dessiner_anneau(peintre, zone):
    rayon = zone.width() * ARRONDI
    peintre.setBrush(Qt.BrushStyle.NoBrush)
    for ecart, epaisseur, alpha in ((6, 10, 26), (3.5, 5, 70)):
        peintre.setPen(QPen(theme.couleur("OR", alpha), epaisseur))
        peintre.drawRoundedRect(zone.adjusted(-ecart, -ecart, ecart, ecart), rayon + ecart, rayon + ecart)
    peintre.setPen(QPen(theme.couleur("OR"), 2))
    peintre.drawRoundedRect(zone.adjusted(-2, -2, 2, 2), rayon + 2, rayon + 2)


def dessiner_pastille(peintre, zone, quantite, foil):
    hauteur = max(16, zone.width() * 0.125)
    police = QFont(peintre.font())
    police.setPixelSize(round(hauteur * 0.6))
    police.setWeight(QFont.Weight.Bold)
    police.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
    peintre.setFont(police)
    texte = f"×{quantite}"
    place_etoile = hauteur * 0.75 if foil else 0
    largeur = peintre.fontMetrics().horizontalAdvance(texte) + hauteur * 0.9 + place_etoile
    pastille = QRectF(
        zone.right() - largeur + hauteur * 0.3,
        zone.bottom() - hauteur * 0.7,
        largeur,
        hauteur,
    )
    rayon = hauteur / 2

    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(0, 0, 0, 90))
    peintre.drawRoundedRect(pastille.translated(0, 1.5), rayon, rayon)
    contour = pastille.adjusted(-2, -2, 2, 2)
    if foil:
        peintre.setBrush(QBrush(arc_en_ciel(pastille.center())))
    else:
        peintre.setBrush(QColor(theme.FOND))
    peintre.drawRoundedRect(contour, rayon + 2, rayon + 2)
    degrade = QLinearGradient(0, pastille.top(), 0, pastille.bottom())
    degrade.setColorAt(0, QColor(theme.OR_HAUT))
    degrade.setColorAt(1, QColor(theme.OR_BAS))
    peintre.setBrush(degrade)
    peintre.drawRoundedRect(pastille, rayon, rayon)

    zone_texte = QRectF(pastille)
    if foil:
        centre_etoile = QPointF(pastille.left() + hauteur * 0.62, pastille.center().y())
        dessiner_etoile(peintre, centre_etoile, hauteur * 0.3, QBrush(QColor(theme.ENCRE)))
        zone_texte.setLeft(pastille.left() + place_etoile * 0.9)
    peintre.setPen(QColor(theme.ENCRE))
    peintre.drawText(zone_texte, Qt.AlignmentFlag.AlignCenter, texte)


def dessiner_coeur(peintre, zone):
    cote = max(18, zone.width() * 0.14)
    cercle = QRectF(zone.right() - cote * 0.7, zone.bottom() - cote * 0.7, cote, cote)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(0, 0, 0, 90))
    peintre.drawEllipse(cercle.translated(0, 1.5))
    peintre.setBrush(QColor(theme.FOND))
    peintre.drawEllipse(cercle.adjusted(-2, -2, 2, 2))
    peintre.setBrush(QColor(theme.AZUR))
    peintre.drawEllipse(cercle)
    taille = round(cote * 0.55)
    coeur = icones.pixmap("heart", "#ffffff", taille, rempli=True)
    peintre.drawPixmap(QPointF(cercle.center().x() - taille / 2, cercle.center().y() - taille / 2 + 0.5), coeur)


class ReglageTaille(QWidget):
    def __init__(self, grille, parent=None):
        super().__init__(parent)
        self.setToolTip("Taille des cartes")
        self.curseur = QSlider(Qt.Orientation.Horizontal)
        self.curseur.setRange(LARGEUR_MIN, LARGEUR_MAX)
        self.curseur.setSingleStep(10)
        self.curseur.setPageStep(20)
        self.curseur.setFixedWidth(120)
        self.curseur.setValue(grille.largeur)
        self.curseur.valueChanged.connect(grille.definir_largeur)

        petite = QLabel()
        petite.setFixedSize(13, 13)
        icones.lier_image(petite, "rectangle-vertical", 13, "TEXTE_DOUX")
        grande = QLabel()
        grande.setFixedSize(19, 19)
        icones.lier_image(grande, "rectangle-vertical", 19, "TEXTE_DOUX")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(petite)
        layout.addWidget(self.curseur)
        layout.addWidget(grande)

    def synchroniser(self):
        self.curseur.setValue(lire_largeur())


class DelegueCarte(QStyledItemDelegate):
    def __init__(self, grille):
        super().__init__(grille)
        self.grille = grille

    def sizeHint(self, option, index):
        return self.grille.gridSize()

    def paint(self, peintre, option, index):
        grille = self.grille
        case = grille.case(QRectF(option.rect))
        quantite = grille.collection.quantite(index.data(ROLE_CARTE_ID))
        selectionnee = bool(option.state & QStyle.StateFlag.State_Selected)

        peintre.save()
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if selectionnee:
            dessiner_anneau(peintre, grille.zone_image(index.data(ROLE_CARTE_ID), QRectF(option.rect)))

        if index.row() not in grille.animations:
            self.dessiner_carte(peintre, index, QRectF(option.rect), None)

        if selectionnee:
            peintre.setPen(QColor(theme.OR_CLAIR))
        elif quantite > 0:
            peintre.setPen(QColor(theme.TEXTE))
        else:
            peintre.setPen(QColor(theme.TEXTE_DOUX))
        police = QFont(option.font)
        police.setPixelSize(13)
        police.setWeight(QFont.Weight.DemiBold)
        peintre.setFont(police)
        haut_texte = case.y() + MARGE + grille.hauteur() + grille.ecart_nom()
        texte = QRectF(case.x() + 4, haut_texte, case.width() - 8, 18)
        nom = peintre.fontMetrics().elidedText(index.data(), Qt.TextElideMode.ElideRight, int(texte.width()))
        peintre.drawText(texte, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, nom)

        police.setPixelSize(11)
        police.setWeight(QFont.Weight.Medium)
        police.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        peintre.setFont(police)
        peintre.setPen(QColor(theme.TEXTE_ETEINT))
        peintre.drawText(
            QRectF(texte.x(), texte.bottom() + 1, texte.width(), 15),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            index.data(ROLE_CODE) or "",
        )

        peintre.restore()

    def dessiner_carte(self, peintre, index, rect, inclinaison):
        grille = self.grille
        carte_id = index.data(ROLE_CARTE_ID)
        quantite = grille.collection.quantite(carte_id)
        foil = grille.collection.a_une_foil(carte_id)
        image = grille.images.get(carte_id)
        zone = grille.zone_image(carte_id, rect)
        rayon = zone.width() * ARRONDI
        if inclinaison is None:
            x = y = force = 0
        else:
            x, y, force = inclinaison.x, inclinaison.y, inclinaison.force

        if force > 0:
            dessiner_ombre(peintre, zone, rayon, 0.6 * force, 2 + 8 * force)

        peintre.save()
        locale = incliner(peintre, zone, x, y, force, AGRANDISSEMENT)
        if image is None:
            peintre.setPen(Qt.PenStyle.NoPen)
            peintre.setBrush(QColor(theme.SURFACE_HAUTE))
            peintre.drawRoundedRect(locale, rayon, rayon)
        else:
            if quantite == 0:
                peintre.setOpacity(OPACITE_MANQUANTE + (OPACITE_MANQUANTE_SURVOL - OPACITE_MANQUANTE) * force)
            if force > 0:
                dessiner_avec_bord(peintre, locale, ajouter_effets(image, foil, x, y, force))
            elif foil:
                dessiner_avec_bord(peintre, locale, grille.image_foil(carte_id))
            else:
                peintre.drawPixmap(locale, image, QRectF(image.rect()))
            peintre.setOpacity(1)

        if quantite > 0:
            dessiner_pastille(peintre, locale, quantite, foil)
        elif grille.collection.correspond(carte_id, "recherchees"):
            dessiner_coeur(peintre, locale)
        peintre.restore()

class GrilleCartes(QListWidget):
    carte_choisie = Signal(str)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.largeur = lire_largeur()
        self.images = {}
        self.images_foil = {}
        self.urls = {}
        self.a_charger = []
        self.animations = {}
        self.survol = None

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(40)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.delegue = DelegueCarte(self)
        self.setItemDelegate(self.delegue)
        self.ajuster_colonnes()

        self.chargeur = QTimer(self)
        self.chargeur.setInterval(0)
        self.chargeur.timeout.connect(self.charger_suite)

        self.minuteur_taille = QTimer(self)
        self.minuteur_taille.setSingleShot(True)
        self.minuteur_taille.setInterval(250)
        self.minuteur_taille.timeout.connect(self.recharger_images)

        self.itemActivated.connect(self.element_active)

    def hauteur(self):
        return round(self.largeur * RAPPORT)

    def ecart_nom(self):
        return 8 + round(self.largeur * 0.04)

    def taille_case(self):
        return QSize(self.largeur + 2 * MARGE, self.hauteur() + MARGE + self.ecart_nom() + HAUTEUR_NOM)

    def case(self, rect):
        taille = self.taille_case()
        x = rect.x() + (rect.width() - taille.width()) / 2
        return QRectF(x, rect.y(), taille.width(), taille.height())

    def zone_image(self, carte_id, rect):
        case = self.case(rect)
        zone = QRectF(case.x() + MARGE, case.y() + MARGE, self.largeur, self.hauteur())
        image = self.images.get(carte_id)
        if image is None:
            return zone
        taille = image.deviceIndependentSize().scaled(zone.size(), Qt.AspectRatioMode.KeepAspectRatio)
        cible = QRectF(QPointF(0, 0), taille)
        cible.moveCenter(zone.center())
        return cible

    def ajuster_colonnes(self):
        case = self.taille_case()
        largeur_visible = self.viewport().width() - 2
        colonnes = max(1, largeur_visible // case.width())
        self.setGridSize(QSize(max(case.width(), largeur_visible // colonnes), case.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arreter_animations()
        self.ajuster_colonnes()

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.HoverMove:
            self.suivre_souris(event.position())
        elif event.type() == QEvent.Type.HoverLeave:
            self.changer_survol(None)
        return super().viewportEvent(event)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        position = self.viewport().mapFromGlobal(QCursor.pos())
        if self.viewport().rect().contains(position):
            self.suivre_souris(QPointF(position))

    def suivre_souris(self, position):
        index = self.indexAt(position.toPoint())
        if index.isValid():
            zone = self.zone_image(index.data(ROLE_CARTE_ID), QRectF(self.visualRect(index)))
            if zone.adjusted(-4, -4, 4, 4).contains(position):
                self.changer_survol(index.row())
                self.animations[index.row()].viser(zone, position)
                return
        self.changer_survol(None)

    def changer_survol(self, ligne):
        if ligne == self.survol:
            return
        if self.survol is not None:
            self.animations[self.survol].relacher()
        self.survol = ligne
        if ligne is not None and ligne not in self.animations:
            animation = Inclinaison(self)
            animation.change.connect(lambda: self.animation_avancee(ligne))
            self.animations[ligne] = animation

    def animation_avancee(self, ligne):
        animation = self.animations.get(ligne)
        if animation is None:
            return
        self.viewport().update(self.zone_repeinte(ligne))
        if ligne != self.survol and animation.au_repos():
            del self.animations[ligne]
            animation.deleteLater()

    def zone_repeinte(self, ligne):
        marge = round(self.largeur * 0.2) + 16
        rect = self.visualRect(self.model().index(ligne, 0))
        return rect.adjusted(-marge, -marge, marge, marge)

    def arreter_animations(self):
        for ligne, animation in self.animations.items():
            animation.remettre_a_zero()
            animation.deleteLater()
            self.viewport().update(self.zone_repeinte(ligne))
        self.animations = {}
        self.survol = None

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.animations:
            return
        peintre = QPainter(self.viewport())
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for ligne in sorted(self.animations, key=lambda autre: autre == self.survol):
            index = self.model().index(ligne, 0)
            if index.isValid():
                self.delegue.dessiner_carte(peintre, index, QRectF(self.visualRect(index)), self.animations[ligne])
        peintre.end()

    def element_active(self, element):
        self.carte_choisie.emit(element.data(ROLE_CARTE_ID))

    def precharger(self, cartes):
        self.urls = {carte["carte_id"]: carte["image_url"] for carte in cartes}
        self.images = {carte_id: image for carte_id, image in self.images.items() if carte_id in self.urls}
        self.images_foil = {carte_id: image for carte_id, image in self.images_foil.items() if carte_id in self.urls}
        self.a_charger = [carte_id for carte_id in self.urls if carte_id not in self.images]
        self.chargeur.start()

    def afficher(self, cartes):
        self.arreter_animations()
        self.clear()
        for carte in cartes:
            element = QListWidgetItem(carte["nom"])
            element.setData(ROLE_CARTE_ID, carte["carte_id"])
            element.setData(ROLE_CODE, code_affiche(carte))
            element.setToolTip(
                f"{carte['nom']}\n{carte['set_nom']} · {code_affiche(carte, True)}\n{carte['rarete']}"
            )
            self.addItem(element)

    def charger_suite(self):
        zoom = self.devicePixelRatioF()
        taille = QSize(round(self.largeur * zoom), round(self.hauteur() * zoom))
        fin = time.perf_counter() + TEMPS_PAR_TOUR
        while self.a_charger and time.perf_counter() < fin:
            carte_id = self.a_charger.pop(0)
            image = charger_miniature(self.urls[carte_id], taille)
            if image is None:
                continue
            pixmap = QPixmap.fromImage(image)
            pixmap.setDevicePixelRatio(zoom)
            self.images[carte_id] = pixmap
            self.images_foil.pop(carte_id, None)
            if self.collection.a_une_foil(carte_id):
                self.images_foil[carte_id] = ajouter_effets(pixmap, True, 0, 0, 0)
        if not self.a_charger:
            self.chargeur.stop()
        self.viewport().update()

    def image_foil(self, carte_id):
        if carte_id not in self.images_foil:
            self.images_foil[carte_id] = ajouter_effets(self.images[carte_id], True, 0, 0, 0)
        return self.images_foil[carte_id]

    def image_telechargee(self, url):
        for carte_id, adresse in self.urls.items():
            if adresse == url and carte_id not in self.a_charger:
                self.a_charger.append(carte_id)
        self.chargeur.start()

    def definir_largeur(self, largeur):
        self.largeur = largeur
        QSettings().setValue("taille_cartes", largeur)
        self.arreter_animations()
        self.ajuster_colonnes()
        self.minuteur_taille.start()

    def recharger_images(self):
        self.a_charger = list(self.urls)
        self.chargeur.start()

    def rafraichir(self):
        self.viewport().update()
