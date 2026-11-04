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
from app.barre_filtres import BarreFiltres
from app.collection import Collection
from app.fenetre_carte import FenetreCarte
from app.fenetre_progression import FenetreProgression
from app.grille_cartes import GrilleCartes
from app.import_catalogue import ImportCatalogue


class FenetrePrincipale(QMainWindow):
    deconnexion = Signal()

    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Riftbound Collection")
        self.resize(1100, 750)

        self.collection = Collection(user_id)
        self.erreur_chargement = ""
        try:
            pseudo = supabase_client.lire_pseudo(user_id)
            self.collection.charger()
            texte_accueil = f"Bienvenue {pseudo} !"
        except supabase_client.ErreurSupabase as erreur:
            texte_accueil = "Bienvenue !"
            self.erreur_chargement = str(erreur)

        accueil = QLabel(texte_accueil)
        accueil.setObjectName("titre")
        self.resume = QLabel()
        self.bouton_progression = QPushButton("Progression")
        self.bouton_progression.setEnabled(self.collection.chargee)
        self.bouton_maj = QPushButton("Mettre à jour le catalogue")
        bouton_deconnexion = QPushButton("Se déconnecter")
        self.barre_filtres = BarreFiltres()
        self.grille = GrilleCartes(self.collection)

        ligne_haut = QHBoxLayout()
        ligne_haut.addWidget(accueil)
        ligne_haut.addStretch()
        ligne_haut.addWidget(self.bouton_progression)
        ligne_haut.addWidget(self.bouton_maj)
        ligne_haut.addWidget(bouton_deconnexion)

        zone_centrale = QWidget()
        layout = QVBoxLayout(zone_centrale)
        layout.addLayout(ligne_haut)
        layout.addWidget(self.resume)
        layout.addWidget(self.barre_filtres)
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

        self.bouton_progression.clicked.connect(self.ouvrir_progression)
        self.bouton_maj.clicked.connect(self.mettre_a_jour_catalogue)
        bouton_deconnexion.clicked.connect(self.se_deconnecter)
        self.barre_filtres.filtres_changes.connect(self.afficher_cartes)
        self.grille.carte_choisie.connect(self.ouvrir_carte)

        self.mettre_a_jour_resume()
        if catalogue.nombre_cartes() == 0:
            self.mettre_a_jour_catalogue()
        else:
            self.charger_catalogue()

    def mettre_a_jour_resume(self):
        if not self.collection.chargee:
            self.resume.setText(f"Collection indisponible : {self.erreur_chargement}")
            return
        total, differentes = self.collection.statistiques()
        nb_catalogue = catalogue.nombre_cartes()
        pourcentage = 100 * differentes / nb_catalogue if nb_catalogue else 0
        self.resume.setText(
            f"Ta collection : {total} carte(s), dont {differentes} différente(s) "
            f"sur {nb_catalogue} ({pourcentage:.1f} %)".replace(".", ",")
        )

    def charger_catalogue(self):
        self.barre_filtres.remplir(catalogue.valeurs_filtres())
        self.afficher_cartes()
        self.mettre_a_jour_resume()

    def afficher_cartes(self):
        filtres = self.barre_filtres.filtres()
        possession = filtres.pop("possession")

        cartes = catalogue.lister_cartes(**filtres)
        if possession:
            cartes = [c for c in cartes if self.collection.correspond(c["carte_id"], possession)]

        self.grille.afficher(cartes)
        self.statusBar().showMessage(
            f"{len(cartes)} carte(s) affichée(s) sur {catalogue.nombre_cartes()}"
        )

    def ouvrir_carte(self, carte_id):
        fenetre = FenetreCarte(carte_id, self.collection, self)
        if fenetre.exec():
            self.grille.rafraichir_carte(carte_id)
            self.mettre_a_jour_resume()

    def ouvrir_progression(self):
        FenetreProgression(self.collection, self).exec()

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
        self.charger_catalogue()

    def import_echoue(self, message):
        self.fin_import()
        self.charger_catalogue()
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