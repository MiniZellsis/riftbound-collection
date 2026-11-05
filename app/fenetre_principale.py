from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import catalogue, supabase_client
from app.collection import Collection
from app.fenetre_carte import FenetreCarte
from app.import_catalogue import ImportCatalogue
from app.page_catalogue import PageCatalogue
from app.page_collection import PageCollection
from app.page_echanges import PageEchanges
from app.page_progression import PageProgression
from app.page_reglages import PageReglages


class FenetrePrincipale(QMainWindow):
    deconnexion = Signal()

    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Riftbound Collection")
        self.resize(1280, 800)

        self.collection = Collection(user_id)
        self.pseudo = None
        erreur_chargement = ""
        try:
            self.pseudo = supabase_client.lire_pseudo(user_id)
            self.collection.charger()
        except supabase_client.ErreurSupabase as erreur:
            erreur_chargement = str(erreur)

        self.page_catalogue = PageCatalogue(self.collection)
        self.page_collection = PageCollection(self.collection)
        self.page_echanges = PageEchanges(self.collection, self.pseudo)
        self.page_progression = PageProgression(self.collection)
        self.page_reglages = PageReglages()

        self.pages = QStackedWidget()
        self.groupe_menu = QButtonGroup(self)
        self.boutons = {}

        barre = QWidget()
        barre.setObjectName("barre_laterale")
        barre.setFixedWidth(220)
        layout_barre = QVBoxLayout(barre)
        layout_barre.setContentsMargins(0, 0, 0, 16)
        layout_barre.setSpacing(4)

        logo = QLabel("RIFTBOUND")
        logo.setObjectName("logo")
        layout_barre.addWidget(logo)

        menu_haut = [
            ("Catalogue", self.page_catalogue, False),
            ("Ma collection", self.page_collection, True),
            ("Échanges", self.page_echanges, True),
            ("Progression", self.page_progression, True),
        ]
        for texte, page, besoin_collection in menu_haut:
            layout_barre.addWidget(self.ajouter_page(texte, page, besoin_collection))

        layout_barre.addStretch()

        pseudo = QLabel(self.pseudo or "Hors ligne")
        pseudo.setObjectName("pseudo")
        layout_barre.addWidget(pseudo)
        layout_barre.addSpacing(6)
        layout_barre.addWidget(self.ajouter_page("Réglages", self.page_reglages, False))
        bouton_deconnexion = QPushButton("Se déconnecter")
        bouton_deconnexion.setObjectName("discret")
        layout_barre.addWidget(bouton_deconnexion)

        self.groupe_menu.idClicked.connect(self.pages.setCurrentIndex)
        self.boutons["Catalogue"].setChecked(True)

        zone_centrale = QWidget()
        layout = QHBoxLayout(zone_centrale)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(barre)
        layout.addWidget(self.pages, stretch=1)
        self.setCentralWidget(zone_centrale)

        self.barre_progression = QProgressBar()
        self.barre_progression.setMaximumWidth(250)
        self.barre_progression.hide()
        self.statusBar().addPermanentWidget(self.barre_progression)
        if erreur_chargement:
            alerte = QLabel(f"Collection indisponible : {erreur_chargement}")
            alerte.setObjectName("erreur")
            self.statusBar().addPermanentWidget(alerte)

        self.import_catalogue = ImportCatalogue(self)
        self.import_catalogue.progression.connect(self.import_progresse)
        self.import_catalogue.termine.connect(self.import_termine)
        self.import_catalogue.echec.connect(self.import_echoue)

        self.page_catalogue.carte_choisie.connect(self.ouvrir_carte)
        self.page_collection.carte_choisie.connect(self.ouvrir_carte)
        self.page_reglages.mise_a_jour_demandee.connect(self.mettre_a_jour_catalogue)
        bouton_deconnexion.clicked.connect(self.se_deconnecter)

        if catalogue.nombre_cartes() == 0:
            self.mettre_a_jour_catalogue()
        else:
            self.page_catalogue.charger()

    def ajouter_page(self, texte, page, besoin_collection):
        index = self.pages.addWidget(page)
        bouton = QPushButton(texte)
        bouton.setObjectName("menu")
        bouton.setCheckable(True)
        bouton.setEnabled(self.collection.chargee or not besoin_collection)
        self.groupe_menu.addButton(bouton, index)
        self.boutons[texte] = bouton
        return bouton

    def ouvrir_carte(self, carte_id):
        fenetre = FenetreCarte(carte_id, self.collection, self)
        if fenetre.exec():
            self.page_catalogue.grille.rafraichir_carte(carte_id)
            if self.pages.currentWidget() is self.page_collection:
                self.page_collection.actualiser()

    def mettre_a_jour_catalogue(self):
        self.page_reglages.bouton_maj.setEnabled(False)
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
        self.statusBar().showMessage("Catalogue à jour.", 5000)

    def import_echoue(self, message):
        self.fin_import()
        QMessageBox.warning(self, "Catalogue", message)

    def fin_import(self):
        self.barre_progression.hide()
        self.statusBar().clearMessage()
        self.page_reglages.bouton_maj.setEnabled(True)
        self.page_catalogue.charger()

    def se_deconnecter(self):
        supabase_client.se_deconnecter()
        self.deconnexion.emit()

    def closeEvent(self, event):
        self.import_catalogue.arreter()
        super().closeEvent(event)