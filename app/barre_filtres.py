from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget


class BarreFiltres(QWidget):
    filtres_changes = Signal()  

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher un nom ou un code (ex. ogn-001)")
        self.recherche.setClearButtonEnabled(True) 

        self.liste_set = QComboBox()
        self.liste_rarete = QComboBox()
        self.liste_domaine = QComboBox()
        self.liste_type = QComboBox()
        self.listes = [self.liste_set, self.liste_rarete, self.liste_domaine, self.liste_type]

        bouton_effacer = QPushButton("Effacer les filtres")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.recherche, stretch=1)  # la recherche prend la place restante
        for liste in self.listes:
            liste.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            liste.setMinimumContentsLength(12)
            liste.currentIndexChanged.connect(self.changement)
            layout.addWidget(liste)
        layout.addWidget(bouton_effacer)

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
        self._remplir_liste(self.liste_set, "Tous les sets", valeurs["sets"])
        self._remplir_liste(self.liste_rarete, "Toutes les raretés", valeurs["raretes"])
        self._remplir_liste(self.liste_domaine, "Tous les domaines", valeurs["domaines"])
        self._remplir_liste(self.liste_type, "Tous les types", valeurs["types"])

    def _remplir_liste(self, liste, texte_tous, choix):
        actuel = liste.currentData()
        liste.blockSignals(True)  
        liste.clear()
        liste.addItem(texte_tous, "")
        for texte, valeur in choix:
            liste.addItem(texte, valeur)
        liste.setCurrentIndex(max(liste.findData(actuel), 0))
        liste.blockSignals(False)

    def filtres(self):
        return {
            "texte": self.recherche.text().strip(),
            "set_code": self.liste_set.currentData(),
            "rarete": self.liste_rarete.currentData(),
            "domaine": self.liste_domaine.currentData(),
            "type_carte": self.liste_type.currentData(),
        }

    def effacer(self):
        for widget in [self.recherche] + self.listes:
            widget.blockSignals(True)
        self.recherche.clear()
        for liste in self.listes:
            liste.setCurrentIndex(0)
        for widget in [self.recherche] + self.listes:
            widget.blockSignals(False)
        self.minuteur.stop() 
        self.changement()