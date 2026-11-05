from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app import catalogue, supabase_client
from app.catalogue import DOSSIER_IMAGES

TAILLE_IMAGE = QSize(450, 630)


class FenetreCarte(QDialog):
    def __init__(self, carte_id, collection, parent=None):
        super().__init__(parent)
        self.carte_id = carte_id
        self.collection = collection
        self.carte = catalogue.lire_carte(carte_id)
        self.setWindowTitle(self.carte["nom"])
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None

        self.image = QLabel()
        self.image.setFixedSize(TAILLE_IMAGE)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titre = QLabel(self.carte["nom"])
        titre.setObjectName("titre")
        titre.setWordWrap(True)
        titre.setMinimumWidth(300)

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

        cadre_collection = QGroupBox("Ma collection")
        tableau = QGridLayout(cadre_collection)
        tableau.addWidget(QLabel("Possédées"), 0, 1)
        tableau.addWidget(QLabel("À échanger"), 0, 2)
        tableau.addWidget(QLabel("Recherchée"), 0, 3)

        self.champs = {}
        for ligne, (foil, texte) in enumerate([(False, "Normale"), (True, "Foil")], start=1):
            version = collection.version(carte_id, foil)

            quantite = QSpinBox()
            quantite.setRange(0, 99)
            quantite.setValue(version["quantite"])

            a_echanger = QSpinBox()
            a_echanger.setRange(0, version["quantite"])
            a_echanger.setValue(version["a_echanger"])
            quantite.valueChanged.connect(a_echanger.setMaximum)

            recherche = QCheckBox()
            recherche.setChecked(version["recherche"])

            tableau.addWidget(QLabel(texte), ligne, 0)
            tableau.addWidget(quantite, ligne, 1)
            tableau.addWidget(a_echanger, ligne, 2)
            tableau.addWidget(recherche, ligne, 3)
            self.champs[foil] = (quantite, a_echanger, recherche)

        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)

        bouton_annuler = QPushButton("Annuler")
        bouton_annuler.clicked.connect(self.reject)
        self.bouton_enregistrer = QPushButton("Enregistrer")
        self.bouton_enregistrer.setObjectName("principal")
        self.bouton_enregistrer.setDefault(True)
        self.bouton_enregistrer.clicked.connect(self.enregistrer)

        if not collection.chargee:
            cadre_collection.setEnabled(False)
            self.bouton_enregistrer.setEnabled(False)
            self.message.setText("Collection indisponible : vérifie ta connexion, puis reconnecte-toi.")

        ligne_boutons = QHBoxLayout()
        ligne_boutons.addWidget(bouton_annuler)
        ligne_boutons.addWidget(self.bouton_enregistrer)

        colonne_droite = QVBoxLayout()
        colonne_droite.addWidget(titre)
        colonne_droite.addLayout(infos)
        colonne_droite.addWidget(bouton_tcgplayer)
        colonne_droite.addStretch()
        colonne_droite.addWidget(cadre_collection)
        colonne_droite.addWidget(self.message)
        colonne_droite.addLayout(ligne_boutons)

        layout = QHBoxLayout(self)
        layout.addWidget(self.image)
        layout.addLayout(colonne_droite)

        self.charger_image()

    def versions_saisies(self):
        versions = []
        for foil, (quantite, a_echanger, recherche) in self.champs.items():
            versions.append({
                "foil": foil,
                "quantite": quantite.value(),
                "a_echanger": a_echanger.value(),
                "recherche": recherche.isChecked(),
            })
        return versions

    def enregistrer(self):
        versions = self.versions_saisies()
        avant = [self.collection.version(self.carte_id, foil) for foil in (False, True)]
        if versions == avant:
            self.accept()
            return

        self.bouton_enregistrer.setEnabled(False)
        self.message.setText("Enregistrement...")
        QApplication.processEvents()
        try:
            self.collection.enregistrer(self.carte_id, versions)
        except supabase_client.ErreurSupabase as erreur:
            self.message.setText(str(erreur))
            self.bouton_enregistrer.setEnabled(True)
            return
        self.accept()

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