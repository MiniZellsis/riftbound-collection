from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import catalogue, supabase_client
from app.grille_cartes import GrilleCartes
from app.import_catalogue import ImportCatalogue


class FenetrePrincipale(QMainWindow):
    deconnexion = Signal()

    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Riftbound Collection")
        self.resize(1000, 700)

        try:
            pseudo = supabase_client.lire_pseudo(user_id)
            differentes, total = supabase_client.resume_collection()
            texte_accueil = f"Bienvenue {pseudo} !"
            texte_collection = (
                f"Ta collection : {total} carte(s), dont {differentes} différente(s)."
            )
        except supabase_client.ErreurSupabase as erreur:
            texte_accueil = "Bienvenue !"
            texte_collection = str(erreur)

        # 2. Les widgets
        accueil = QLabel(texte_accueil)
        accueil.setObjectName("titre")
        collection = QLabel(texte_collection)
        self.bouton_maj = QPushButton("Mettre à jour le catalogue")
        bouton_deconnexion = QPushButton("Se déconnecter")
        self.grille = GrilleCartes()

        ligne_haut = QHBoxLayout()
        ligne_haut.addWidget(accueil)
        ligne_haut.addStretch()
        ligne_haut.addWidget(self.bouton_maj)
        ligne_haut.addWidget(bouton_deconnexion)

        zone_centrale = QWidget()
        layout = QVBoxLayout(zone_centrale)
        layout.addLayout(ligne_haut)
        layout.addWidget(collection)
        layout.addWidget(self.grille)
        self.setCentralWidget(zone_centrale)

        self.barre_progression = QProgressBar()
        self.barre_progression.setMaximumWidth(250)
        self.barre_progression.hide()
        self.statusBar().addPermanentWidget(self.barre_progression)

        self.import_catalogue = ImportCatalogue(self)
        self.import_catalogue.progression.connect(self.import_progresse)
        self.import_catalogue.termine.connect(self.import_termine)
        self.import_catalogue.echec.connect(self.import_echoue)

        self.bouton_maj.clicked.connect(self.mettre_a_jour_catalogue)
        bouton_deconnexion.clicked.connect(self.se_deconnecter)

        if catalogue.nombre_cartes() == 0:
            self.mettre_a_jour_catalogue()
        else:
            self.afficher_catalogue()

    def afficher_catalogue(self):
        cartes = catalogue.lister_cartes()
        self.grille.afficher(cartes)
        self.statusBar().showMessage(f"{len(cartes)} cartes dans le catalogue")

    def mettre_a_jour_catalogue(self):
        self.bouton_maj.setEnabled(False)
        self.barre_progression.setRange(0, 0) 
        self.barre_progression.show()
        self.statusBar().showMessage("Connexion à Riftcodex... (le serveur peut être lent)")
        self.import_catalogue.demarrer()

    def import_progresse(self, page, nb_pages):
        self.barre_progression.setRange(0, nb_pages)
        self.barre_progression.setValue(page)
        self.statusBar().showMessage(f"Téléchargement du catalogue : page {page}/{nb_pages}")

    def import_termine(self):
        self.fin_import()
        self.afficher_catalogue()

    def import_echoue(self, message):
        self.fin_import()
        self.afficher_catalogue() 
        QMessageBox.warning(self, "Catalogue", message)

    def fin_import(self):
        self.barre_progression.hide()
        self.bouton_maj.setEnabled(True)

    def se_deconnecter(self):
        supabase_client.se_deconnecter()
        self.deconnexion.emit()

    def closeEvent(self, event):
        self.import_catalogue.arreter()
        super().closeEvent(event)