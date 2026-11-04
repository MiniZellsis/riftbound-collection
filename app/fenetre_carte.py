from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app import catalogue
from app.catalogue import DOSSIER_IMAGES

TAILLE_IMAGE = QSize(450, 630)


class FenetreCarte(QDialog):
    def __init__(self, carte_id, parent=None):
        super().__init__(parent)
        self.carte = catalogue.lire_carte(carte_id)
        self.setWindowTitle(self.carte["nom"])
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None  # le téléchargement en cours (ou None)

        self.image = QLabel()
        self.image.setFixedSize(TAILLE_IMAGE)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titre = QLabel(self.carte["nom"])
        titre.setObjectName("titre")
        titre.setWordWrap(True)
        titre.setMinimumWidth(240) 

        infos = QFormLayout()
        infos.addRow("Code :", QLabel(self.carte["code"]))
        infos.addRow("Set :", QLabel(self.carte["set_nom"] or "-"))
        infos.addRow("Numéro :", QLabel(str(self.carte["numero"] or "-")))
        infos.addRow("Rareté :", QLabel(self.carte["rarete"] or "-"))
        infos.addRow("Type :", QLabel(self.carte["type"] or "-"))
        infos.addRow("Domaines :", QLabel(self.carte["domaines"] or "-"))
        infos.addRow("Version :", QLabel(self.texte_version()))

        bouton_tcgplayer = QPushButton("Voir le prix sur TCGplayer")
        bouton_tcgplayer.setEnabled(bool(self.carte["tcgplayer_id"]))
        bouton_tcgplayer.clicked.connect(self.ouvrir_tcgplayer)
        bouton_fermer = QPushButton("Fermer")
        bouton_fermer.clicked.connect(self.accept)

        colonne_droite = QVBoxLayout()
        colonne_droite.addWidget(titre)
        colonne_droite.addLayout(infos)
        colonne_droite.addStretch()
        colonne_droite.addWidget(bouton_tcgplayer)
        colonne_droite.addWidget(bouton_fermer)

        layout = QHBoxLayout(self)
        layout.addWidget(self.image)
        layout.addLayout(colonne_droite)

        self.charger_image()

    def texte_version(self):
        versions = []
        if self.carte["art_alternatif"]:
            versions.append("Art alternatif")
        if self.carte["signature"]:
            versions.append("Signature")
        if self.carte["surnumerotee"]:
            versions.append("Surnumérotée")
        return ", ".join(versions) or "Normale"  

    def ouvrir_tcgplayer(self):
        url = f"https://www.tcgplayer.com/product/{self.carte['tcgplayer_id']}"
        QDesktopServices.openUrl(QUrl(url))

    def charger_image(self):
        url = self.carte["image_url"]
        if not url:
            self.image.setText("Pas d'image")
            return
        nom = Path(QUrl(url).fileName()).stem 
        miniature = DOSSIER_IMAGES / f"{nom}.webp"
        self.fichier_grand = DOSSIER_IMAGES / f"{nom}-grande.webp"

        if self.fichier_grand.exists():
            self.afficher_image(QImage(str(self.fichier_grand)))
            return

        if miniature.exists():
            self.afficher_image(QImage(str(miniature)))
        else:
            self.image.setText("Chargement de l'image...")

        self.reponse = self.reseau.get(QNetworkRequest(QUrl(url)))
        self.reponse.finished.connect(self.image_recue)

    def image_recue(self):
        reponse = self.reponse
        self.reponse = None
        reponse.deleteLater()
        if reponse.error() != QNetworkReply.NetworkError.NoError:
            return 

        image = QImage()
        if not image.loadFromData(reponse.readAll()):
            return
        image.save(str(self.fichier_grand), quality=90) 
        self.afficher_image(image)

    def afficher_image(self, image):
        zoom = self.devicePixelRatioF()
        pixmap = QPixmap.fromImage(image).scaled(
            TAILLE_IMAGE * zoom,
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(zoom)
        self.image.setPixmap(pixmap)

    def done(self, resultat):
        if self.reponse is not None:
            self.reponse.abort()
        super().done(resultat)