import json

from PySide6.QtCore import QObject, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app import catalogue

URL_API = "https://api.riftcodex.com/cards"
TAILLE_PAGE = 100 
ESSAIS_MAX = 3
DELAI_MAX = 60_000 


class ImportCatalogue(QObject):
    progression = Signal(int, int)
    termine = Signal()
    echec = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None
        self.page = 1
        self.essai = 1
        self.arret_demande = False

    def demarrer(self):
        self.page = 1
        self.essai = 1
        self.arret_demande = False
        self._demander_page()

    def arreter(self):
        self.arret_demande = True
        if self.reponse is not None:
            self.reponse.abort()

    def _demander_page(self):
        if self.arret_demande:
            return
        parametres = QUrlQuery()
        parametres.addQueryItem("page", str(self.page))
        parametres.addQueryItem("size", str(TAILLE_PAGE))
        url = QUrl(URL_API)
        url.setQuery(parametres)

        requete = QNetworkRequest(url)
        requete.setTransferTimeout(DELAI_MAX)
        self.reponse = self.reseau.get(requete)
        self.reponse.finished.connect(self._page_recue)

    def _page_recue(self):
        reponse = self.reponse
        self.reponse = None
        reponse.deleteLater()

        if self.arret_demande:
            return

        if reponse.error() != QNetworkReply.NetworkError.NoError:
            if self.essai < ESSAIS_MAX:
                self.essai += 1
                QTimer.singleShot(3000, self, self._demander_page)
            else:
                self.echec.emit(
                    f"Impossible de télécharger le catalogue (page {self.page}).\n"
                    f"Détail : {reponse.errorString()}\n\n"
                    "Les pages déjà reçues sont enregistrées. "
                    "Réessaie plus tard avec « Mettre à jour le catalogue »."
                )
            return

        try:
            donnees = json.loads(bytes(reponse.readAll()))
            catalogue.enregistrer_cartes(donnees["items"])
            nb_pages = donnees["pages"]
        except (ValueError, KeyError):
            self.echec.emit("Riftcodex a renvoyé une réponse illisible.")
            return

        self.progression.emit(self.page, nb_pages)
        if self.page >= nb_pages:
            self.termine.emit()
        else:
            self.page += 1
            self.essai = 1
            self._demander_page()