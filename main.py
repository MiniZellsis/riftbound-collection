import sys

from PySide6.QtNetwork import QNetworkProxyFactory
from PySide6.QtWidgets import QApplication

from app import catalogue
from app.fenetre_connexion import FenetreConnexion
from app.fenetre_principale import FenetrePrincipale

STYLE = """
QLabel#titre { font-size: 20px; font-weight: bold; }
QLabel#erreur { color: #c0392b; }
QLineEdit, QPushButton { padding: 6px; }
"""


class Application:

    def __init__(self):
        self.fenetre_principale = None
        self.fenetre_connexion = FenetreConnexion()
        self.fenetre_connexion.connexion_reussie.connect(self.ouvrir_principale)
        self.fenetre_connexion.show()

    def ouvrir_principale(self, user_id):
        self.fenetre_principale = FenetrePrincipale(user_id)
        self.fenetre_principale.deconnexion.connect(self.revenir_connexion)
        self.fenetre_connexion.hide()
        self.fenetre_principale.show()

    def revenir_connexion(self):
        self.fenetre_principale.close()
        self.fenetre_principale = None
        self.fenetre_connexion.show()


if __name__ == "__main__":
    catalogue.creer_base()
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLE)
    QNetworkProxyFactory.setUseSystemConfiguration(True)
    application = Application()
    sys.exit(qt_app.exec())