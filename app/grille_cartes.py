from PySide6.QtCore import QPointF, QRectF, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QSlider,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

from app import theme
from app.images import ARRONDI, charger_miniature

LARGEUR_MIN = 120
LARGEUR_MAX = 280
LARGEUR_DEFAUT = 160
RAPPORT = 1.4
MARGE = 8
HAUTEUR_NOM = 22
PAR_TOUR = 12
OPACITE_MANQUANTE = 0.35
COULEUR_QUANTITE = QColor("#2e7d32")
COULEUR_QUANTITE_FOIL = QColor("#b8860b")
ROLE_CARTE_ID = Qt.ItemDataRole.UserRole


def lire_largeur():
    largeur = QSettings().value("taille_cartes", LARGEUR_DEFAUT, int)
    return max(LARGEUR_MIN, min(largeur, LARGEUR_MAX))


def icone_carte(largeur, hauteur):
    pixmap = QPixmap(largeur * 2, hauteur * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(QPen(QColor(theme.TEXTE_DOUX), 1.4))
    peintre.drawRoundedRect(QRectF(1, 1, largeur - 2, hauteur - 2), 2, 2)
    peintre.end()
    return pixmap


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
        petite.setPixmap(icone_carte(10, 14))
        grande = QLabel()
        grande.setPixmap(icone_carte(14, 20))

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
        carte_id = index.data(ROLE_CARTE_ID)
        quantite = grille.collection.quantite(carte_id)
        selectionnee = bool(option.state & QStyle.StateFlag.State_Selected)
        survolee = bool(option.state & QStyle.StateFlag.State_MouseOver)
        taille_case = grille.taille_case()
        case = QRectF(
            option.rect.x() + (option.rect.width() - taille_case.width()) / 2,
            option.rect.y(),
            taille_case.width(),
            taille_case.height(),
        )

        peintre.save()
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if selectionnee:
            peintre.setPen(QPen(QColor(theme.OR), 1))
            peintre.setBrush(QColor(theme.SURFACE_HAUTE))
            peintre.drawRoundedRect(case.adjusted(2, 2, -2, -2), 10, 10)
        elif survolee:
            peintre.setPen(Qt.PenStyle.NoPen)
            peintre.setBrush(QColor(theme.SURFACE))
            peintre.drawRoundedRect(case.adjusted(2, 2, -2, -2), 10, 10)

        zone = QRectF(case.x() + MARGE, case.y() + MARGE, grille.largeur, grille.hauteur())
        image = grille.images.get(carte_id)
        if image is None:
            rayon = zone.width() * ARRONDI
            peintre.setPen(Qt.PenStyle.NoPen)
            peintre.setBrush(QColor(theme.SURFACE_HAUTE))
            peintre.drawRoundedRect(zone, rayon, rayon)
        else:
            taille = image.deviceIndependentSize().scaled(zone.size(), Qt.AspectRatioMode.KeepAspectRatio)
            cible = QRectF(QPointF(0, 0), taille)
            cible.moveCenter(zone.center())
            if quantite == 0:
                peintre.setOpacity(OPACITE_MANQUANTE)
            peintre.drawPixmap(cible, image, QRectF(image.rect()))
            peintre.setOpacity(1)
            zone = cible

        if quantite > 0:
            self.dessiner_quantite(peintre, zone, quantite, grille.collection.a_une_foil(carte_id))

        if selectionnee:
            peintre.setPen(QColor(theme.OR_CLAIR))
        elif quantite > 0:
            peintre.setPen(QColor(theme.TEXTE))
        else:
            peintre.setPen(QColor(theme.TEXTE_DOUX))
        police = QFont(option.font)
        police.setPixelSize(12)
        peintre.setFont(police)
        texte = QRectF(case.x() + 4, case.y() + MARGE + grille.hauteur() + 4, case.width() - 8, HAUTEUR_NOM)
        nom = peintre.fontMetrics().elidedText(index.data(), Qt.TextElideMode.ElideRight, int(texte.width()))
        peintre.drawText(texte, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, nom)

        peintre.restore()

    def dessiner_quantite(self, peintre, zone, quantite, foil):
        diametre = max(22, zone.width() * 0.22)
        decalage = zone.width() * 0.04
        rond = QRectF(
            zone.right() - diametre - decalage,
            zone.bottom() - diametre - decalage,
            diametre,
            diametre,
        )
        peintre.setPen(QPen(QColor("white"), max(2, diametre / 16)))
        peintre.setBrush(COULEUR_QUANTITE_FOIL if foil else COULEUR_QUANTITE)
        peintre.drawEllipse(rond)

        police = QFont(peintre.font())
        police.setPixelSize(round(diametre * 0.5))
        police.setBold(True)
        peintre.setFont(police)
        peintre.drawText(rond, Qt.AlignmentFlag.AlignCenter, str(quantite))


class GrilleCartes(QListWidget):
    carte_choisie = Signal(str)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.largeur = lire_largeur()
        self.images = {}
        self.urls = {}
        self.a_charger = []

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(40)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setItemDelegate(DelegueCarte(self))
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

    def taille_case(self):
        return QSize(self.largeur + 2 * MARGE, self.hauteur() + 2 * MARGE + HAUTEUR_NOM)

    def ajuster_colonnes(self):
        case = self.taille_case()
        largeur_visible = self.viewport().width()
        colonnes = max(1, largeur_visible // case.width())
        self.setGridSize(QSize(max(case.width(), largeur_visible // colonnes), case.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.ajuster_colonnes()

    def element_active(self, element):
        self.carte_choisie.emit(element.data(ROLE_CARTE_ID))

    def precharger(self, cartes):
        self.urls = {carte["carte_id"]: carte["image_url"] for carte in cartes}
        self.images = {carte_id: image for carte_id, image in self.images.items() if carte_id in self.urls}
        self.a_charger = [carte_id for carte_id in self.urls if carte_id not in self.images]
        self.chargeur.start()

    def afficher(self, cartes):
        self.clear()
        for carte in cartes:
            element = QListWidgetItem(carte["nom"])
            element.setData(ROLE_CARTE_ID, carte["carte_id"])
            element.setToolTip(
                f"{carte['nom']}\n{carte['set_nom']} - n°{carte['numero']}\n{carte['rarete']}"
            )
            self.addItem(element)

    def charger_suite(self):
        zoom = self.devicePixelRatioF()
        taille = QSize(round(self.largeur * zoom), round(self.hauteur() * zoom))
        for carte_id in self.a_charger[:PAR_TOUR]:
            image = charger_miniature(self.urls[carte_id], taille)
            if image is not None:
                pixmap = QPixmap.fromImage(image)
                pixmap.setDevicePixelRatio(zoom)
                self.images[carte_id] = pixmap
        del self.a_charger[:PAR_TOUR]
        if not self.a_charger:
            self.chargeur.stop()
        self.viewport().update()

    def image_telechargee(self, url):
        for carte_id, adresse in self.urls.items():
            if adresse == url and carte_id not in self.a_charger:
                self.a_charger.append(carte_id)
        self.chargeur.start()

    def definir_largeur(self, largeur):
        self.largeur = largeur
        QSettings().setValue("taille_cartes", largeur)
        self.ajuster_colonnes()
        self.minuteur_taille.start()

    def recharger_images(self):
        self.a_charger = list(self.urls)
        self.chargeur.start()

    def rafraichir(self):
        self.viewport().update()
