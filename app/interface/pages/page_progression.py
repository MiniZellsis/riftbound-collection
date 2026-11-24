from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.interface.composants.elements import Filet, Titre

COLONNES = 2


def pourcentage(possedees, total):
    return round(100 * possedees / total) if total else 0


class CarteSet(QFrame):
    def __init__(self, nom, lignes, parent=None):
        super().__init__(parent)
        self.setObjectName("carte")
        principal_possedees, principal_total = lignes[0][1], lignes[0][2]

        nom_set = Titre(nom, "nom_set")
        grand = QLabel(f"{pourcentage(principal_possedees, principal_total)} %")
        grand.setObjectName("grand_pourcentage")
        entete = QHBoxLayout()
        entete.addWidget(nom_set)
        entete.addStretch()
        entete.addWidget(grand)

        grille = QGridLayout()
        grille.setHorizontalSpacing(14)
        grille.setVerticalSpacing(10)
        grille.setColumnStretch(1, 1)
        for rang, (texte, possedees, total) in enumerate(lignes):
            libelle = QLabel(texte)
            libelle.setObjectName("sous_titre")
            barre = QProgressBar()
            barre.setObjectName("fine")
            barre.setTextVisible(False)
            barre.setRange(0, max(total, 1))
            barre.setValue(possedees)
            chiffres = QLabel(f"{possedees} / {total}")
            chiffres.setObjectName("chiffres_set")
            chiffres.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            chiffres.setMinimumWidth(76)
            grille.addWidget(libelle, rang, 0)
            grille.addWidget(barre, rang, 1)
            grille.addWidget(chiffres, rang, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(Filet())
        layout.addLayout(grille)
        layout.addStretch()


class PageProgression(QWidget):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection

        titre = Titre("Progression")
        explication = QLabel(
            "Les cartes de base sont celles numérotées dans le set. Les variantes "
            "ajoutent les arts alternatifs, signatures et cartes surnumérotées."
        )
        explication.setObjectName("sous_titre")
        explication.setWordWrap(True)

        self.contenu = QWidget()
        self.contenu.setObjectName("contenu_defilement")
        self.grille = QGridLayout()
        self.grille.setHorizontalSpacing(16)
        self.grille.setVerticalSpacing(16)
        for colonne in range(COLONNES):
            self.grille.setColumnStretch(colonne, 1)
        disposition = QVBoxLayout(self.contenu)
        disposition.setContentsMargins(0, 4, 8, 8)
        disposition.addLayout(self.grille)
        disposition.addStretch(1)

        defilement = QScrollArea()
        defilement.setObjectName("defilement")
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QScrollArea.Shape.NoFrame)
        defilement.viewport().setAutoFillBackground(False)
        defilement.setWidget(self.contenu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 24, 12)
        layout.setSpacing(12)
        layout.addWidget(titre)
        layout.addWidget(explication)
        layout.addSpacing(4)
        layout.addWidget(defilement, stretch=1)

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.actualiser()

    def possedees(self, cartes):
        return sum(1 for carte_id in cartes if self.collection.quantite(carte_id) > 0)

    def actualiser(self):
        while self.grille.count():
            element = self.grille.takeAt(0)
            if element.widget() is not None:
                element.widget().hide()
                element.widget().deleteLater()

        position = 0
        for set_nom, cartes in catalogue.cartes_par_set().items():
            toutes = [carte_id for carte_id, _ in cartes]
            de_base = [carte_id for carte_id, est_de_base in cartes if est_de_base]
            lignes = []
            if "Promotional" not in set_nom and de_base:
                lignes.append(("Cartes de base", self.possedees(de_base), len(de_base)))
                lignes.append(("Avec les variantes", self.possedees(toutes), len(toutes)))
            else:
                lignes.append(("Toutes les cartes", self.possedees(toutes), len(toutes)))
            ligne, colonne = divmod(position, COLONNES)
            self.grille.addWidget(CarteSet(set_nom or "-", lignes), ligne, colonne)
            position += 1
