from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app import catalogue
from app.grille_cartes import ReglageTaille
from app.zone_cartes import ZoneCartes

TUILES = [
    ("total", "cartes"),
    ("differentes", "différentes"),
    ("foils", "foils"),
    ("a_echanger", "à échanger"),
    ("recherchees", "recherchées"),
]

MESSAGE_VIDE = (
    "Ta collection est vide pour l'instant. Va dans le catalogue, clique sur une carte "
    "et indique combien tu en as. Le clic droit permet aussi d'en ajouter une vite."
)


class PageCollection(QWidget):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection

        titre = QLabel("Ma collection")
        titre.setObjectName("titre")
        self.zone = ZoneCartes(collection)
        self.grille = self.zone.grille
        self.reglage = ReglageTaille(self.grille)

        entete = QHBoxLayout()
        entete.addWidget(titre)
        entete.addStretch()
        entete.addWidget(self.reglage)

        ligne_tuiles = QHBoxLayout()
        ligne_tuiles.setSpacing(12)
        self.chiffres = {}
        self.legendes = {}
        for cle, legende in TUILES:
            ligne_tuiles.addWidget(self.creer_tuile(cle, legende))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)
        layout.addLayout(entete)
        layout.addLayout(ligne_tuiles)
        layout.addWidget(self.zone, stretch=1)

        self.zone.collection_modifiee.connect(self.actualiser_chiffres)

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

    def actualiser_chiffres(self):
        chiffres = self.collection.chiffres_cles()
        for cle, label in self.chiffres.items():
            label.setText(str(chiffres[cle]))

        nb_catalogue = catalogue.nombre_cartes()
        pourcentage = 100 * chiffres["differentes"] / nb_catalogue if nb_catalogue else 0
        self.legendes["differentes"].setText(
            f"différentes ({pourcentage:.1f} %)".replace(".", ",")
        )

    def actualiser(self):
        self.actualiser_chiffres()
        cartes = [c for c in catalogue.lister_cartes() if self.collection.quantite(c["carte_id"]) > 0]
        self.grille.precharger(cartes)
        self.zone.afficher(cartes, MESSAGE_VIDE)

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.reglage.synchroniser()
            self.actualiser()
