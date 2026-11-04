from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QListView, QListWidget, QListWidgetItem

from app.catalogue import DOSSIER_IMAGES

LARGEUR_MINIATURE = 240
TAILLE_ICONE = QSize(160, 223)
TAILLE_CASE = QSize(180, 275)
ROLE_CARTE_ID = Qt.ItemDataRole.UserRole


def creer_image_attente():
    pixmap = QPixmap(LARGEUR_MINIATURE, 335)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor("#c8c8c8"))
    peintre.drawRoundedRect(pixmap.rect(), 14, 14)
    peintre.end()
    return QIcon(pixmap)


class GrilleCartes(QListWidget):
    carte_choisie = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(TAILLE_ICONE)
        self.setGridSize(TAILLE_CASE)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)

        self.reseau = QNetworkAccessManager(self)
        self.image_attente = creer_image_attente()
        self.elements = {}
        self.urls = {}
        self.chargees = set()

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(150)
        self.minuteur.timeout.connect(self.mettre_a_jour_images)
        self.verticalScrollBar().valueChanged.connect(self.planifier_images)

        self.itemActivated.connect(self.element_active)

    def element_active(self, element):
        self.carte_choisie.emit(element.data(ROLE_CARTE_ID))

    def planifier_images(self):
        self.minuteur.start()

    def afficher(self, cartes):
        self.clear()
        self.elements.clear()
        self.urls.clear()
        self.chargees.clear()
        for carte in cartes:
            element = QListWidgetItem(self.image_attente, carte["nom"])
            element.setData(ROLE_CARTE_ID, carte["carte_id"])
            element.setToolTip(
                f"{carte['nom']}\n{carte['set_nom']} - n°{carte['numero']}\n{carte['rarete']}"
            )
            self.addItem(element)
            self.elements[carte["carte_id"]] = element
            self.urls[carte["carte_id"]] = carte["image_url"]
        self.planifier_images()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.planifier_images()

    def mettre_a_jour_images(self):
        ecran = self.viewport().rect()
        zone = ecran.adjusted(0, -ecran.height(), 0, ecran.height())

        for carte_id, element in self.elements.items():
            proche = self.visualItemRect(element).intersects(zone)
            if proche and carte_id not in self.chargees:
                self.chargees.add(carte_id)
                self.charger_image(carte_id)
            elif not proche and carte_id in self.chargees:
                self.chargees.discard(carte_id)
                element.setIcon(self.image_attente)

    def charger_image(self, carte_id):
        url = self.urls[carte_id]
        if not url:
            return
        fichier = DOSSIER_IMAGES / Path(QUrl(url).fileName()).with_suffix(".webp")

        if fichier.exists():
            self.elements[carte_id].setIcon(QIcon(str(fichier)))
            return

        reponse = self.reseau.get(QNetworkRequest(QUrl(url)))
        reponse.finished.connect(lambda: self.image_recue(reponse, carte_id, fichier))

    def image_recue(self, reponse, carte_id, fichier):
        reponse.deleteLater()
        if reponse.error() != QNetworkReply.NetworkError.NoError:
            self.chargees.discard(carte_id) 
            return

        image = QImage()
        if not image.loadFromData(reponse.readAll()):
            return
        miniature = image.scaledToWidth(
            LARGEUR_MINIATURE, Qt.TransformationMode.SmoothTransformation
        )
        miniature.save(str(fichier), quality=85)

        if carte_id in self.chargees:
            self.elements[carte_id].setIcon(QIcon(QPixmap.fromImage(miniature)))