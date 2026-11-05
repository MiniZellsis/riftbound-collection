from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app import catalogue
from app.barre_filtres import BarreFiltres
from app.grille_cartes import GrilleCartes


class PageCatalogue(QWidget):
    carte_choisie = Signal(str)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection

        titre = QLabel("Catalogue")
        titre.setObjectName("titre")
        self.compteur = QLabel("")
        self.compteur.setObjectName("sous_titre")
        self.barre_filtres = BarreFiltres()
        self.grille = GrilleCartes(collection)

        entete = QHBoxLayout()
        entete.addWidget(titre)
        entete.addStretch()
        entete.addWidget(self.compteur)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(self.barre_filtres)
        layout.addWidget(self.grille)

        self.barre_filtres.filtres_changes.connect(self.afficher_cartes)
        self.grille.carte_choisie.connect(self.carte_choisie)

    def charger(self):
        self.barre_filtres.remplir(catalogue.valeurs_filtres())
        self.afficher_cartes()

    def afficher_cartes(self):
        filtres = self.barre_filtres.filtres()
        possession = filtres.pop("possession")
        cartes = catalogue.lister_cartes(**filtres)
        if possession:
            cartes = [c for c in cartes if self.collection.correspond(c["carte_id"], possession)]
        self.grille.afficher(cartes)
        self.compteur.setText(f"{len(cartes)} carte(s) sur {catalogue.nombre_cartes()}")