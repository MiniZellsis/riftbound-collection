from pathlib import Path

from PySide6.QtCore import QObject, QRectF, Qt, QUrl, QUrlQuery, Signal
from PySide6.QtGui import QBrush, QImage, QPainter
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.catalogue import DOSSIER_IMAGES, DOSSIER_MINIATURES

LARGEUR_MINIATURE = 300
LARGEUR_GRANDE = 744
ARRONDI = 0.048
EN_PARALLELE = 24
DELAI_MAX = 30_000


def nom_image(url):
    return Path(QUrl(url).fileName()).stem


def fichier_miniature(url):
    return DOSSIER_MINIATURES / f"{nom_image(url)}.jpg"


def fichier_grand(url):
    return DOSSIER_IMAGES / f"{nom_image(url)}-grande.webp"


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
        vues = set()
        for carte in cartes:
            url = carte["image_url"]
            if url and url not in vues and not fichier_miniature(url).exists():
                self.file.append(url)
            vues.add(url)

        self.total = len(self.file)
        self.faites = 0
        self.echecs = 0
        self.lancer()
        return self.total

    def prioriser(self, cartes):
        demandees = {carte["image_url"] for carte in cartes}
        self.file.sort(key=lambda url: url not in demandees)

    def arreter(self):
        self.file = []
        en_cours = self.en_cours
        self.en_cours = {}
        for reponse in en_cours.values():
            reponse.abort()

    def lancer(self):
        while self.file and len(self.en_cours) < EN_PARALLELE:
            self.telecharger(self.file.pop(0))

    def telecharger(self, url):
        requete = QNetworkRequest(url_redimensionnee(url, LARGEUR_MINIATURE, "jpg"))
        requete.setTransferTimeout(DELAI_MAX)
        reponse = self.reseau.get(requete)
        self.en_cours[url] = reponse
        reponse.finished.connect(lambda: self.recue(url, reponse))

    def recue(self, url, reponse):
        reponse.deleteLater()
        if self.en_cours.pop(url, None) is None:
            return

        donnees = reponse.readAll()
        image = QImage()
        if reponse.error() == QNetworkReply.NetworkError.NoError and image.loadFromData(donnees):
            fichier_miniature(url).write_bytes(bytes(donnees))
            self.image_prete.emit(url)
        else:
            self.echecs += 1

        self.faites += 1
        self.progression.emit(self.faites, self.total)
        if self.faites == self.total:
            self.termine.emit(self.echecs)
        else:
            self.lancer()
