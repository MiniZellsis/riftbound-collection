from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.infos import DOSSIER_DONNEES, NOM, VERSION

MENTION_RIOT = (
    "Riftbound Collection n'est pas approuvé par Riot Games et ne reflète pas les "
    "opinions de Riot Games ni de quiconque officiellement impliqué dans la production "
    "ou la gestion des propriétés de Riot Games. Riot Games et toutes les propriétés "
    "associées sont des marques commerciales ou des marques déposées de Riot Games, Inc."
)

RACCOURCIS = [
    ("Ctrl+F", "rechercher une carte"),
    ("Ctrl+1 à Ctrl+5", "changer de page"),
    ("Flèches", "passer d'une carte à l'autre"),
    ("Échap", "fermer le détail d'une carte"),
]


class PageReglages(QWidget):
    mise_a_jour_demandee = Signal()
    verification_demandee = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_nouvelle_version = ""

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
        texte_donnees = QLabel(f"Catalogue, images et journal des erreurs : {DOSSIER_DONNEES}")
        texte_donnees.setWordWrap(True)
        bouton_dossier = QPushButton("Ouvrir le dossier")
        bouton_dossier.clicked.connect(self.ouvrir_dossier)
        ligne_donnees = QHBoxLayout()
        ligne_donnees.addWidget(bouton_dossier)
        ligne_donnees.addStretch()
        layout_donnees = QVBoxLayout(cadre_donnees)
        layout_donnees.addWidget(texte_donnees)
        layout_donnees.addLayout(ligne_donnees)

        cadre_raccourcis = QGroupBox("Raccourcis clavier")
        grille_raccourcis = QGridLayout(cadre_raccourcis)
        grille_raccourcis.setHorizontalSpacing(16)
        grille_raccourcis.setColumnStretch(1, 1)
        for ligne, (touches, action) in enumerate(RACCOURCIS):
            texte_touches = QLabel(touches)
            texte_touches.setObjectName("touche")
            texte_action = QLabel(action)
            texte_action.setObjectName("sous_titre")
            grille_raccourcis.addWidget(texte_touches, ligne, 0)
            grille_raccourcis.addWidget(texte_action, ligne, 1)

        cadre_a_propos = QGroupBox("À propos")
        texte_version = QLabel(f"{NOM}, version {VERSION}")
        self.bouton_verifier = QPushButton("Vérifier les mises à jour")
        self.bouton_verifier.clicked.connect(self.verifier)
        self.resultat = QLabel("")
        self.resultat.setObjectName("sous_titre")
        self.bouton_telecharger = QPushButton("")
        self.bouton_telecharger.setObjectName("lien")
        self.bouton_telecharger.clicked.connect(self.telecharger)
        self.bouton_telecharger.hide()
        ligne_version = QHBoxLayout()
        ligne_version.addWidget(texte_version)
        ligne_version.addSpacing(12)
        ligne_version.addWidget(self.bouton_verifier)
        ligne_version.addWidget(self.resultat)
        ligne_version.addWidget(self.bouton_telecharger)
        ligne_version.addStretch()
        texte_a_propos = QLabel(
            "Données des cartes : Riftcodex. Images des cartes : Riot Games.\n\n" + MENTION_RIOT
        )
        texte_a_propos.setObjectName("sous_titre")
        texte_a_propos.setWordWrap(True)
        layout_a_propos = QVBoxLayout(cadre_a_propos)
        layout_a_propos.addLayout(ligne_version)
        layout_a_propos.addSpacing(6)
        layout_a_propos.addWidget(texte_a_propos)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)
        layout.addWidget(titre)
        layout.addWidget(cadre_catalogue)
        layout.addWidget(cadre_donnees)
        layout.addWidget(cadre_raccourcis)
        layout.addWidget(cadre_a_propos)
        layout.addStretch()

    def ouvrir_dossier(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOSSIER_DONNEES)))

    def verifier(self):
        self.bouton_verifier.setEnabled(False)
        self.resultat.setText("Vérification…")
        self.bouton_telecharger.hide()
        self.verification_demandee.emit()

    def afficher_verification(self, etat, version, page):
        self.bouton_verifier.setEnabled(True)
        self.page_nouvelle_version = page
        if etat == "nouvelle":
            self.resultat.setText("Une nouvelle version est disponible.")
            self.bouton_telecharger.setText(f"Télécharger la version {version}")
            self.bouton_telecharger.show()
        elif etat == "a_jour":
            self.resultat.setText("Tu as la dernière version.")
            self.bouton_telecharger.hide()
        else:
            self.resultat.setText("Impossible de vérifier pour l'instant (pas de connexion ?).")
            self.bouton_telecharger.hide()

    def telecharger(self):
        if self.page_nouvelle_version:
            QDesktopServices.openUrl(QUrl(self.page_nouvelle_version))
