from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app import catalogue


class PageProgression(QWidget):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection

        titre = QLabel("Progression")
        titre.setObjectName("titre")
        explication = QLabel(
            "Les cartes de base sont celles numérotées dans le set. Les variantes "
            "ajoutent les arts alternatifs, signatures et cartes surnumérotées."
        )
        explication.setObjectName("sous_titre")
        explication.setWordWrap(True)

        self.tableau = QWidget()

        self.layout_page = QVBoxLayout(self)
        self.layout_page.setContentsMargins(24, 20, 24, 12)
        self.layout_page.setSpacing(12)
        self.layout_page.addWidget(titre)
        self.layout_page.addWidget(explication)
        self.layout_page.addWidget(self.tableau)
        self.layout_page.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.actualiser()

    def actualiser(self):
        nouveau = QWidget()
        grille = QGridLayout(nouveau)
        grille.setContentsMargins(0, 10, 0, 0)
        grille.setHorizontalSpacing(16)
        grille.setVerticalSpacing(10)
        grille.setColumnStretch(1, 1)
        grille.setColumnStretch(2, 1)

        for colonne, texte in enumerate(["Set", "Cartes de base", "Avec les variantes"]):
            entete = QLabel(texte)
            entete.setObjectName("sous_titre")
            grille.addWidget(entete, 0, colonne)

        for ligne, (set_nom, cartes) in enumerate(catalogue.cartes_par_set().items(), start=1):
            grille.addWidget(QLabel(set_nom), ligne, 0)
            if "Promotional" in set_nom:
                grille.addWidget(QLabel("-"), ligne, 1)
            else:
                de_base = [carte_id for carte_id, est_de_base in cartes if est_de_base]
                grille.addWidget(self.creer_barre(de_base), ligne, 1)
            toutes = [carte_id for carte_id, _ in cartes]
            grille.addWidget(self.creer_barre(toutes), ligne, 2)

        self.layout_page.replaceWidget(self.tableau, nouveau)
        self.tableau.deleteLater()
        self.tableau = nouveau

    def creer_barre(self, cartes):
        possedees = sum(1 for carte_id in cartes if self.collection.quantite(carte_id) > 0)
        barre = QProgressBar()
        barre.setRange(0, max(len(cartes), 1))
        barre.setValue(possedees)
        barre.setFormat(f"{possedees} / {len(cartes)}  (%p %)")
        return barre