from pathlib import Path

from PySide6.QtCore import QObject, QRectF, Qt, QUrl, QUrlQuery, Signal
from PySide6.QtGui import QBrush, QImage, QPainter
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.catalogue import DOSSIER_ICONES, DOSSIER_IMAGES, DOSSIER_MINIATURES

LARGEUR_MINIATURE = 300
LARGEUR_GRANDE = 744
LARGEUR_ICONE = 64
ARRONDI = 0.048
EN_PARALLELE = 24
DELAI_MAX = 30_000

ADRESSE_ICONES = "https://cmsassets.rgpub.io/sanity/images/dsfx7636/game_data_live/"
ICONES = {
    "Fury": "5aeb4bfd203b5d265902f65aa5afae7da1682eaa-64x64",
    "Calm": "b9ef2f5b74841ad11f3629aa381a76ac0187d007-64x64",
    "Mind": "17ab95a6bd052085b6803d846a287f625f347288-64x64",
    "Body": "7a5533034de5870808347bc4b296f0029bdd8eea-64x64",
    "Chaos": "597ddb82be59e87b467c52bb10204f02c2005d06-64x64",
    "Order": "8bb1b193a8e1adc26ca28e1a21da8d1e2f5d2f72-64x64",
    "Common": "a088ae851d94b5c34aa4900e8ccb4cc103144dce-354x354",
    "Uncommon": "808205a0f070e479107a7655e622fe15a356275b-480x410",
    "Rare": "d90078e1ec2ef7cbcbba2be86da1b192c389581a-429x425",
    "Epic": "5e9799d87d0f8baa55f6d9bddb9750669a0f485b-455x419",
    "Showcase": "a0e92b9edf3291fa62c9b35ffd6363de0d7947c0-376x426",
}


def nom_image(url):
    return Path(QUrl(url).fileName()).stem


def fichier_miniature(url):
    return DOSSIER_MINIATURES / f"{nom_image(url)}.jpg"


def fichier_grand(url):
    return DOSSIER_IMAGES / f"{nom_image(url)}-grande.webp"


def fichier_icone(nom):
    return DOSSIER_ICONES / f"{nom}.png"


def url_redimensionnee(url, largeur, format_image):
    adresse = QUrl(url)
    parametres = QUrlQuery(adresse)
    parametres.addQueryItem("w", str(largeur))
    parametres.addQueryItem("fm", format_image)
    adresse.setQuery(parametres)
    return adresse


def arrondir(image):
    resultat = QImage(image.size(), QImage.Format.Format_ARGB32_Premultiplied)
    resultat.fill(Qt.GlobalColor.transparent)
    rayon = min(image.width(), image.height()) * ARRONDI
    peintre = QPainter(resultat)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QBrush(image))
    peintre.drawRoundedRect(QRectF(resultat.rect()), rayon, rayon)
    peintre.end()
    return resultat


def charger_miniature(url, taille):
    if not url:
        return None
    image = QImage(str(fichier_miniature(url)))
    if image.isNull():
        return None
    image = image.scaled(
        taille,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return arrondir(image)


class TelechargementImages(QObject):
    progression = Signal(int, int)
    image_prete = Signal(str)
    termine = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reseau = QNetworkAccessManager(self)
        self.file = []
        self.en_cours = {}
        self.total = 0
        self.faites = 0
        self.echecs = 0

    def demarrer(self, cartes):
        self.arreter()
        for nom, fichier in ICONES.items():
            if not fichier_icone(nom).exists():
                adresse = url_redimensionnee(f"{ADRESSE_ICONES}{fichier}.png?accountingTag=RB", LARGEUR_ICONE, "png")
                self.file.append((nom, adresse, fichier_icone(nom)))

        vues = set()
        for carte in cartes:
            url = carte["image_url"]
            if url and url not in vues and not fichier_miniature(url).exists():
                adresse = url_redimensionnee(url, LARGEUR_MINIATURE, "jpg")
                self.file.append((url, adresse, fichier_miniature(url)))
            vues.add(url)

        self.total = len(self.file)
        self.faites = 0
        self.echecs = 0
        self.lancer()
        return self.total

    def prioriser(self, cartes):
        demandees = {carte["image_url"] for carte in cartes}
        self.file.sort(key=lambda element: element[0] not in demandees)

    def arreter(self):
        self.file = []
        en_cours = self.en_cours
        self.en_cours = {}
        for reponse in en_cours.values():
            reponse.abort()

    def lancer(self):
        while self.file and len(self.en_cours) < EN_PARALLELE:
            cle, adresse, fichier = self.file.pop(0)
            self.telecharger(cle, adresse, fichier)

    def telecharger(self, cle, adresse, fichier):
        requete = QNetworkRequest(adresse)
        requete.setTransferTimeout(DELAI_MAX)
        reponse = self.reseau.get(requete)
        self.en_cours[cle] = reponse
        reponse.finished.connect(lambda: self.recue(cle, fichier, reponse))

    def recue(self, cle, fichier, reponse):
        reponse.deleteLater()
        if self.en_cours.pop(cle, None) is None:
            return

        donnees = reponse.readAll()
        image = QImage()
        if reponse.error() == QNetworkReply.NetworkError.NoError and image.loadFromData(donnees):
            fichier.write_bytes(bytes(donnees))
            self.image_prete.emit(cle)
        else:
            self.echecs += 1

        self.faites += 1
        self.progression.emit(self.faites, self.total)
        if self.faites == self.total:
            self.termine.emit(self.echecs)
        else:
            self.lancer()
