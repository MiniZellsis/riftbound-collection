from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app import catalogue
from app.grille_cartes import GrilleCartes

TUILES = [
    ("total", "cartes"),
    ("differentes", "différentes"),
    ("foils", "foils"),
    ("a_echanger", "à échanger"),
    ("recherchees", "recherchées"),
]


class PageCollection(QWidget):
    carte_choisie = Signal(str)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection

        titre = QLabel("Ma collection")
        titre.setObjectName("titre")

        ligne_tuiles = QHBoxLayout()
        ligne_tuiles.setSpacing(12)
        self.chiffres = {}
        self.legendes = {}
        for cle, legende in TUILES:
            ligne_tuiles.addWidget(self.creer_tuile(cle, legende))

        self.message_vide = QLabel(
            "Ta collection est vide pour l'instant. Va dans le catalogue et "
            "double-clique sur une carte pour indiquer combien tu en as."
        )
        self.message_vide.setObjectName("sous_titre")
        self.message_vide.setWordWrap(True)
        self.message_vide.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grille = GrilleCartes(collection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)
        layout.addWidget(titre)
        layout.addLayout(ligne_tuiles)
        layout.addWidget(self.message_vide, stretch=1)
        layout.addWidget(self.grille, stretch=1)

        self.grille.carte_choisie.connect(self.carte_choisie)

    def creer_tuile(self, cle, legende):
        tuile = QFrame()
        tuile.setObjectName("tuile")
        chiffre = QLabel("0")
        chiffre.setObjectName("chiffre")
        texte = QLabel(legende)
        texte.setObjectName("sous_titre")

        layout = QVBoxLayout(tuile)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(chiffre)
        layout.addWidget(texte)

        self.chiffres[cle] = chiffre
        self.legendes[cle] = texte
        return tuile

    def actualiser(self):
        chiffres = self.collection.chiffres_cles()
        for cle, label in self.chiffres.items():
            label.setText(str(chiffres[cle]))

        nb_catalogue = catalogue.nombre_cartes()
        pourcentage = 100 * chiffres["differentes"] / nb_catalogue if nb_catalogue else 0
        self.legendes["differentes"].setText(
            f"différentes ({pourcentage:.1f} %)".replace(".", ",")
        )

        cartes = [c for c in catalogue.lister_cartes() if self.collection.quantite(c["carte_id"]) > 0]
        self.grille.afficher(cartes)
        self.message_vide.setVisible(not cartes)
        self.grille.setVisible(bool(cartes))

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.actualiser()