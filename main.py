import sys
import traceback

from PySide6.QtNetwork import QNetworkProxyFactory
from PySide6.QtWidgets import QApplication, QMessageBox

from app import catalogue, supabase_client, theme
from app.fenetre_connexion import FenetreConnexion
from app.fenetre_principale import FenetrePrincipale


def afficher_erreur(type_erreur, erreur, trace):
    details = "".join(traceback.format_exception(type_erreur, erreur, trace))
    print(details, file=sys.stderr)
    boite = QMessageBox(QMessageBox.Icon.Critical, "Erreur inattendue", f"{type_erreur.__name__} : {erreur}")
    boite.setDetailedText(details)
    boite.exec()


class Application:
    def __init__(self):
        self.fenetre_principale = None
        self.fenetre_connexion = FenetreConnexion()
        self.fenetre_connexion.connexion_reussie.connect(self.ouvrir_principale)

        try:
            user_id = supabase_client.reprendre_session()
        except supabase_client.ErreurSupabase as erreur:
            user_id = None
            self.fenetre_connexion.message.setText(str(erreur))

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
    catalogue.creer_base()
    qt_app = QApplication(sys.argv)
    qt_app.setOrganizationName("RiftboundCollection")
    qt_app.setApplicationName("RiftboundCollection")
    theme.appliquer_theme(qt_app)
    sys.excepthook = afficher_erreur
    QNetworkProxyFactory.setUseSystemConfiguration(True)
    application = Application()
    sys.exit(qt_app.exec())