import ctypes
import sys

from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QNetworkProxyFactory, QSslConfiguration
from PySide6.QtWidgets import QApplication, QMessageBox

from app import journal
from app.donnees import catalogue, supabase_client
from app.infos import ICONE, ID_WINDOWS, VERSION
from app.interface import theme
from app.interface.fenetre_connexion import FenetreConnexion
from app.interface.fenetre_principale import FenetrePrincipale


def afficher_erreur(type_erreur, erreur, trace):
    details = journal.noter_erreur(type_erreur, erreur, trace)
    print(details, file=sys.stderr)
    boite = QMessageBox(
        QMessageBox.Icon.Critical,
        "Erreur inattendue",
        f"{type_erreur.__name__} : {erreur}\n\n"
        f"Les détails sont enregistrés dans le fichier {journal.FICHIER.name} : "
        "page Réglages, bouton « Ouvrir le dossier ».",
    )
    boite.setDetailedText(details)
    boite.exec()


def preparer_windows():
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_WINDOWS)


class Application:
    def __init__(self):
        self.fenetre_principale = None
        self.fenetre_connexion = FenetreConnexion()
        self.fenetre_connexion.connexion_reussie.connect(self.ouvrir_principale)

        try:
            user_id = supabase_client.reprendre_session()
        except supabase_client.ErreurSupabase as erreur:
            user_id = None
            self.fenetre_connexion.afficher_message(str(erreur))

        if user_id:
            self.ouvrir_principale(user_id)
        else:
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
    preparer_windows()
    catalogue.creer_base()
    qt_app = QApplication(sys.argv)
    qt_app.setOrganizationName("RiftboundCollection")
    qt_app.setApplicationName("RiftboundCollection")
    qt_app.setApplicationVersion(VERSION)
    qt_app.setWindowIcon(QIcon(str(ICONE)))
    theme.appliquer_theme(qt_app)
    sys.excepthook = afficher_erreur
    QNetworkProxyFactory.setUseSystemConfiguration(True)
    QSslConfiguration.defaultConfiguration().caCertificates()
    application = Application()
    sys.exit(qt_app.exec())
