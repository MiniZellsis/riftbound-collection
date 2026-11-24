import json

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.infos import DEPOT, VERSION, version_en_nombres

ADRESSE = f"https://api.github.com/repos/{DEPOT}/releases/latest"
DEBUT_PAGE = f"https://github.com/{DEPOT}/"
DELAI_MAX = 10_000


class VerificationMiseAJour(QObject):
    resultat = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None

    def verifier(self):
        if self.reponse is not None:
            return
        requete = QNetworkRequest(QUrl(ADRESSE))
        requete.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"RiftboundCollection/{VERSION}")
        requete.setRawHeader(b"Accept", b"application/vnd.github+json")
        requete.setTransferTimeout(DELAI_MAX)
        self.reponse = self.reseau.get(requete)
        self.reponse.finished.connect(self.reponse_recue)

    def reponse_recue(self):
        reponse = self.reponse
        self.reponse = None
        reponse.deleteLater()
        statut = reponse.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if statut == 404:
            self.resultat.emit("a_jour", "", "")
            return
        if reponse.error() != QNetworkReply.NetworkError.NoError:
            self.resultat.emit("echec", "", "")
            return
        try:
            donnees = json.loads(bytes(reponse.readAll()).decode("utf-8"))
            version = str(donnees["tag_name"]).lstrip("vV")
            page = str(donnees["html_url"])
        except (ValueError, KeyError, TypeError):
            self.resultat.emit("echec", "", "")
            return
        if not page.startswith(DEBUT_PAGE):
            page = f"{DEBUT_PAGE}releases"
        if version_en_nombres(version) > version_en_nombres(VERSION):
            self.resultat.emit("nouvelle", version, page)
        else:
            self.resultat.emit("a_jour", version, page)
