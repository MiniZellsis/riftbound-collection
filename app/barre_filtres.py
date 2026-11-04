"""Barre de recherche et de filtres, au-dessus de la grille."""
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget


class BarreFiltres(QWidget):
    filtres_changes = Signal()  # prévient la fenêtre qu'il faut relancer la recherche

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher un nom ou un code (ex. ogn-001)")
        self.recherche.setClearButtonEnabled(True)  # petite croix pour vider le champ

        # Filtre "Ma collection" : ses choix ne dépendent pas du catalogue
        self.liste_collection = QComboBox()
        self.liste_collection.addItem("Toutes les cartes", "")
        self.liste_collection.addItem("Possédées", "possedees")
        self.liste_collection.addItem("Manquantes", "manquantes")
        self.liste_collection.addItem("À échanger", "a_echanger")
        self.liste_collection.addItem("Recherchées", "recherchees")

        self.liste_set = QComboBox()
        self.liste_rarete = QComboBox()
        self.liste_domaine = QComboBox()
        self.liste_type = QComboBox()
        self.listes = [
            self.liste_collection,
            self.liste_set,
            self.liste_rarete,
            self.liste_domaine,
            self.liste_type,
        ]

        bouton_effacer = QPushButton("Effacer les filtres")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.recherche, stretch=1)  # la recherche prend la place restante
        for liste in self.listes:
            # Les noms de sets sont longs : la liste fermée les coupe, la liste
            # ouverte les montre en entier
            liste.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            liste.setMinimumContentsLength(10)
            liste.currentIndexChanged.connect(self.changement)
            layout.addWidget(liste)
        layout.addWidget(bouton_effacer)

        # Pour la recherche texte, on attend 250 ms après la dernière touche :
        # pas de recherche à chaque lettre quand on tape vite
        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.changement)
        self.recherche.textChanged.connect(self.texte_modifie)

        bouton_effacer.clicked.connect(self.effacer)

    def texte_modifie(self):
        self.minuteur.start()

    def changement(self):
        self.filtres_changes.emit()

    def remplir(self, valeurs):
        """Remplit les listes avec les choix donnés par catalogue.valeurs_filtres()."""
        self._remplir_liste(self.liste_set, "Tous les sets", valeurs["sets"])
        self._remplir_liste(self.liste_rarete, "Toutes les raretés", valeurs["raretes"])
        self._remplir_liste(self.liste_domaine, "Tous les domaines", valeurs["domaines"])
        self._remplir_liste(self.liste_type, "Tous les types", valeurs["types"])

    def _remplir_liste(self, liste, texte_tous, choix):
        actuel = liste.currentData()  # on garde le choix en cours si possible
        liste.blockSignals(True)      # pas de recherche pendant qu'on remplit
        liste.clear()
        # Chaque choix a un texte (affiché) et une valeur (utilisée pour le filtre)
        liste.addItem(texte_tous, "")
        for texte, valeur in choix:
            liste.addItem(texte, valeur)
        liste.setCurrentIndex(max(liste.findData(actuel), 0))
        liste.blockSignals(False)

    def filtres(self):
        """Les filtres choisis, sous forme de dictionnaire."""
        return {
            "possession": self.liste_collection.currentData(),
            "texte": self.recherche.text().strip(),
            "set_code": self.liste_set.currentData(),
            "rarete": self.liste_rarete.currentData(),
            "domaine": self.liste_domaine.currentData(),
            "type_carte": self.liste_type.currentData(),
        }

    def effacer(self):
        # On bloque les signaux pour ne lancer qu'une seule recherche à la fin
        for widget in [self.recherche] + self.listes:
            widget.blockSignals(True)
        self.recherche.clear()
        for liste in self.listes:
            liste.setCurrentIndex(0)
        for widget in [self.recherche] + self.listes:
            widget.blockSignals(False)
        self.minuteur.stop()  # au cas où une recherche texte était en attente
        self.changement()