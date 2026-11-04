from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app import catalogue


class FenetreProgression(QDialog):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.setWindowTitle("Progression par set")
        self.setMinimumWidth(700)

        tableau = QGridLayout()
        tableau.setColumnStretch(1, 1)
        tableau.setColumnStretch(2, 1)
        tableau.addWidget(QLabel("Set"), 0, 0)
        tableau.addWidget(QLabel("Cartes de base"), 0, 1)
        tableau.addWidget(QLabel("Avec les variantes"), 0, 2)

        for ligne, (set_nom, cartes) in enumerate(catalogue.cartes_par_set().items(), start=1):
            tableau.addWidget(QLabel(set_nom), ligne, 0)
            if "Promotional" in set_nom:
                tableau.addWidget(QLabel("-"), ligne, 1)
            else:
                de_base = [carte_id for carte_id, est_de_base in cartes if est_de_base]
                tableau.addWidget(self.creer_barre(de_base), ligne, 1)
            toutes = [carte_id for carte_id, _ in cartes]
            tableau.addWidget(self.creer_barre(toutes), ligne, 2)

        bouton_fermer = QPushButton("Fermer")
        bouton_fermer.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(tableau)
        layout.addWidget(bouton_fermer)

    def creer_barre(self, cartes):
        possedees = sum(1 for carte_id in cartes if self.collection.quantite(carte_id) > 0)
        barre = QProgressBar()
        barre.setRange(0, max(len(cartes), 1))
        barre.setValue(possedees)
        barre.setFormat(f"{possedees} / {len(cartes)}  (%p %)")
        return barre