from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.catalogue import DOSSIER_DONNEES

MENTION_RIOT = (
    "Riftbound Collection n'est pas approuvé par Riot Games et ne reflète pas les "
    "opinions de Riot Games ni de quiconque officiellement impliqué dans la production "
    "ou la gestion des propriétés de Riot Games. Riot Games et toutes les propriétés "
    "associées sont des marques commerciales ou des marques déposées de Riot Games, Inc."
)


class PageReglages(QWidget):
    mise_a_jour_demandee = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        titre = QLabel("Réglages")
        titre.setObjectName("titre")

        cadre_catalogue = QGroupBox("Catalogue des cartes")
        texte_catalogue = QLabel(
            "Les cartes viennent de Riftcodex. Mets le catalogue à jour quand un "
            "nouveau set sort."
        )
        texte_catalogue.setWordWrap(True)
        self.bouton_maj = QPushButton("Mettre à jour le catalogue")
        self.bouton_maj.setObjectName("principal")
        self.bouton_maj.clicked.connect(self.mise_a_jour_demandee)
        ligne_catalogue = QHBoxLayout()
        ligne_catalogue.addWidget(self.bouton_maj)
        ligne_catalogue.addStretch()
        layout_catalogue = QVBoxLayout(cadre_catalogue)
        layout_catalogue.addWidget(texte_catalogue)
        layout_catalogue.addLayout(ligne_catalogue)

        cadre_donnees = QGroupBox("Données sur ce PC")
        texte_donnees = QLabel(f"Catalogue et images : {DOSSIER_DONNEES}")
        texte_donnees.setWordWrap(True)
        bouton_dossier = QPushButton("Ouvrir le dossier")
        bouton_dossier.clicked.connect(self.ouvrir_dossier)
        ligne_donnees = QHBoxLayout()
        ligne_donnees.addWidget(bouton_dossier)
        ligne_donnees.addStretch()
        layout_donnees = QVBoxLayout(cadre_donnees)
        layout_donnees.addWidget(texte_donnees)
        layout_donnees.addLayout(ligne_donnees)

        cadre_a_propos = QGroupBox("À propos")
        texte_a_propos = QLabel(
            "Données des cartes : Riftcodex. Images des cartes : Riot Games.\n\n" + MENTION_RIOT
        )
        texte_a_propos.setObjectName("sous_titre")
        texte_a_propos.setWordWrap(True)
        layout_a_propos = QVBoxLayout(cadre_a_propos)
        layout_a_propos.addWidget(texte_a_propos)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)
        layout.addWidget(titre)
        layout.addWidget(cadre_catalogue)
        layout.addWidget(cadre_donnees)
        layout.addWidget(cadre_a_propos)
        layout.addStretch()

    def ouvrir_dossier(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOSSIER_DONNEES)))