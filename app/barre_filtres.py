from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

STATUTS = [
    ("possedees", "Possédées", None),
    ("manquantes", "Manquantes", None),
    ("a_echanger", "À échanger", None),
    ("recherchees", "Recherchées", None),
]

DOMAINES = [
    ("Fury", "Fury", "#e5534b"),
    ("Calm", "Calm", "#3fb950"),
    ("Mind", "Mind", "#4c9be8"),
    ("Body", "Body", "#f0883e"),
    ("Chaos", "Chaos", "#a371f7"),
    ("Order", "Order", "#e3c06a"),
    ("Colorless", "Colorless", "#8f9bb3"),
]

RARETES = [
    ("Common", "Common", "#b0b8c8"),
    ("Uncommon", "Uncommon", "#3fb950"),
    ("Rare", "Rare", "#4c9be8"),
    ("Epic", "Epic", "#a371f7"),
    ("Showcase", "Showcase", "#e3c06a"),
    ("Promo", "Promo", "#f778ba"),
]

TYPES = [
    ("Unit", "Unit", None),
    ("Spell", "Spell", None),
    ("Gear", "Gear", None),
    ("Legend", "Legend", None),
    ("Battlefield", "Battlefield", None),
    ("Rune", "Rune", None),
]


def creer_rond(couleur):
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(couleur))
    peintre.drawEllipse(pixmap.rect())
    peintre.end()
    return QIcon(pixmap)


def creer_pastille(texte, couleur):
    pastille = QPushButton(texte)
    pastille.setObjectName("pastille")
    pastille.setCheckable(True)
    pastille.setCursor(Qt.CursorShape.PointingHandCursor)
    if couleur:
        pastille.setIcon(creer_rond(couleur))
        pastille.setIconSize(QSize(10, 10))
        pastille.setStyleSheet(
            f"QPushButton#pastille:checked {{ border-color: {couleur}; color: {couleur}; }}"
        )
    return pastille


class BarreFiltres(QWidget):
    filtres_changes = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupes = {}

        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher une carte (nom ou code)")
        self.recherche.setClearButtonEnabled(True)
        self.bouton_effacer = QPushButton("Effacer les filtres")
        self.bouton_effacer.setEnabled(False)

        ligne_haut = QHBoxLayout()
        ligne_haut.setSpacing(4)
        ligne_haut.addWidget(self.recherche, stretch=1)
        ligne_haut.addSpacing(12)
        self.ajouter_groupe(ligne_haut, "statuts", "Collection", STATUTS)
        ligne_haut.addSpacing(12)
        ligne_haut.addWidget(self.bouton_effacer)

        ligne_milieu = QHBoxLayout()
        ligne_milieu.setSpacing(4)
        self.ajouter_groupe(ligne_milieu, "domaines", "Domaine", DOMAINES)
        ligne_milieu.addStretch()

        ligne_bas = QHBoxLayout()
        ligne_bas.setSpacing(4)
        self.ajouter_groupe(ligne_bas, "raretes", "Rareté", RARETES)
        ligne_bas.addSpacing(20)
        self.ajouter_groupe(ligne_bas, "types", "Type", TYPES)
        ligne_bas.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(ligne_haut)
        layout.addLayout(ligne_milieu)
        layout.addLayout(ligne_bas)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.changement)
        self.recherche.textChanged.connect(self.texte_modifie)
        self.bouton_effacer.clicked.connect(self.effacer)

    def ajouter_groupe(self, ligne, nom, titre, choix):
        etiquette = QLabel(titre)
        etiquette.setObjectName("groupe")
        ligne.addWidget(etiquette)
        self.groupes[nom] = {}
        for valeur, texte, couleur in choix:
            pastille = creer_pastille(texte, couleur)
            pastille.toggled.connect(self.changement)
            ligne.addWidget(pastille)
            self.groupes[nom][valeur] = pastille

    def texte_modifie(self):
        self.minuteur.start()

    def changement(self):
        self.bouton_effacer.setEnabled(self.actifs())
        self.filtres_changes.emit()

    def filtres(self):
        choix = {"texte": self.recherche.text().strip().lower()}
        for nom, pastilles in self.groupes.items():
            choix[nom] = [valeur for valeur, pastille in pastilles.items() if pastille.isChecked()]
        return choix

    def actifs(self):
        return any(self.filtres().values())

    def effacer(self):
        self.blockSignals(True)
        self.recherche.clear()
        for pastilles in self.groupes.values():
            for pastille in pastilles.values():
                pastille.setChecked(False)
        self.blockSignals(False)
        self.minuteur.stop()
        self.changement()