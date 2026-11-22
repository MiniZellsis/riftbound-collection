from PySide6.QtCore import QSettings, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.infos import DOSSIER_DONNEES, NOM, VERSION
from app.interface import icones
from app.interface.composants import effets
from app.interface.composants.elements import (
    Avatar,
    Carte,
    Filet,
    Interrupteur,
    Titre,
    TuilesTheme,
    ligne_reglage,
    touches,
)
from app.interface.composants.grille_cartes import LARGEUR_MAX, LARGEUR_MIN, lire_largeur

MENTION_RIOT = (
    "Riftbound Collection n'est pas approuvé par Riot Games et ne reflète pas les "
    "opinions de Riot Games ni de quiconque officiellement impliqué dans la production "
    "ou la gestion des propriétés de Riot Games. Riot Games et toutes les propriétés "
    "associées sont des marques commerciales ou des marques déposées de Riot Games, Inc."
)

CREDITS = (
    "Données des cartes : Riftcodex. Images des cartes : Riot Games. "
    "Polices : Cinzel et Albert Sans (licence OFL). Icônes : Lucide (licence ISC)."
)

RACCOURCIS = [
    (("Ctrl", "F"), "Rechercher une carte"),
    (("Ctrl", "1", "à", "6"), "Changer de page"),
    (("Flèches",), "Passer d'une carte ou d'une pochette à l'autre"),
    (("Page préc.", "Page suiv."), "Tourner les pages d'un classeur"),
    (("Suppr",), "Vider la pochette choisie"),
    (("Échap",), "Fermer le détail d'une carte"),
]


def bouton(texte, nom_icone=None, nom="", normal="OR_CLAIR"):
    resultat = QPushButton(texte)
    if nom:
        resultat.setObjectName(nom)
    resultat.setCursor(Qt.CursorShape.PointingHandCursor)
    if nom_icone:
        icones.lier(resultat, nom_icone, 16, normal, normal)
    return resultat


class PageReglages(QWidget):
    mise_a_jour_demandee = Signal()
    verification_demandee = Signal()
    deconnexion_demandee = Signal()

    def __init__(self, pseudo=None, parent=None):
        super().__init__(parent)
        self.page_nouvelle_version = ""

        colonne_gauche = QVBoxLayout()
        colonne_gauche.setSpacing(20)
        colonne_gauche.addWidget(self.carte_apparence())
        colonne_gauche.addWidget(self.carte_raccourcis())
        colonne_gauche.addStretch()

        colonne_droite = QVBoxLayout()
        colonne_droite.setSpacing(20)
        colonne_droite.addWidget(self.carte_compte(pseudo))
        colonne_droite.addWidget(self.carte_donnees())
        colonne_droite.addWidget(self.carte_a_propos())
        colonne_droite.addStretch()

        contenu = QWidget()
        contenu.setObjectName("contenu_defilement")
        colonnes = QHBoxLayout(contenu)
        colonnes.setContentsMargins(0, 0, 8, 0)
        colonnes.setSpacing(20)
        colonnes.addLayout(colonne_gauche, stretch=1)
        colonnes.addLayout(colonne_droite, stretch=1)

        defilement = QScrollArea()
        defilement.setObjectName("defilement")
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QScrollArea.Shape.NoFrame)
        defilement.viewport().setAutoFillBackground(False)
        defilement.setWidget(contenu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 20, 12)
        layout.setSpacing(18)
        layout.addWidget(Titre("Réglages"))
        layout.addWidget(defilement, stretch=1)

    def carte_apparence(self):
        carte = Carte("Apparence", "palette")
        entete = QHBoxLayout()
        libelle = QLabel("Thème")
        libelle.setObjectName("libelle")
        aide = QLabel("« Système » suit le réglage de Windows.")
        aide.setObjectName("aide")
        entete.addWidget(libelle)
        entete.addStretch()
        entete.addWidget(aide)
        carte.contenu.addLayout(entete)
        carte.contenu.addWidget(TuilesTheme())
        carte.contenu.addWidget(Filet())

        self.interrupteur_effets = Interrupteur()
        self.interrupteur_effets.setToolTip("Effets 3D des cartes")
        self.interrupteur_effets.definir(effets.effets_actifs())
        self.interrupteur_effets.toggled.connect(effets.definir_effets)
        carte.contenu.addLayout(ligne_reglage(
            "Effets 3D des cartes", "Les cartes s'inclinent sous la souris.", self.interrupteur_effets
        ))

        self.curseur = QSlider(Qt.Orientation.Horizontal)
        self.curseur.setRange(LARGEUR_MIN, LARGEUR_MAX)
        self.curseur.setSingleStep(10)
        self.curseur.setPageStep(20)
        self.curseur.setFixedWidth(150)
        self.curseur.setToolTip("Taille des cartes")
        self.curseur.setValue(lire_largeur())
        self.curseur.valueChanged.connect(lambda valeur: QSettings().setValue("taille_cartes", valeur))
        carte.contenu.addLayout(ligne_reglage(
            "Taille des cartes", "Gardée d'un lancement à l'autre.", self.curseur
        ))
        return carte

    def carte_raccourcis(self):
        carte = Carte("Raccourcis clavier", "keyboard")
        for noms, texte in RACCOURCIS:
            ligne = QHBoxLayout()
            ligne.setSpacing(14)
            zone_touches = QWidget()
            zone_touches.setFixedWidth(150)
            zone_touches.setLayout(touches(*noms))
            zone_touches.layout().setContentsMargins(0, 0, 0, 0)
            action = QLabel(texte)
            ligne.addWidget(zone_touches)
            ligne.addWidget(action, stretch=1)
            carte.contenu.addLayout(ligne)
        return carte

    def carte_compte(self, pseudo):
        carte = Carte("Compte", "user-round")
        textes = QVBoxLayout()
        textes.setSpacing(2)
        nom = QLabel(pseudo or "Hors ligne")
        nom.setObjectName("pseudo")
        etat = QLabel("Connecté" if pseudo else "Collection indisponible")
        etat.setObjectName("aide")
        textes.addWidget(nom)
        textes.addWidget(etat)
        deconnexion = bouton("Se déconnecter", "log-out", "danger", "ROUGE")
        deconnexion.clicked.connect(self.deconnexion_demandee)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        ligne.addWidget(Avatar(pseudo or "?", 44))
        ligne.addLayout(textes, stretch=1)
        ligne.addWidget(deconnexion)
        carte.contenu.addLayout(ligne)
        return carte

    def carte_donnees(self):
        carte = Carte("Catalogue et données", "database")
        texte_catalogue = QLabel(
            "Les cartes viennent de Riftcodex. Mets le catalogue à jour quand un nouveau set sort."
        )
        texte_catalogue.setObjectName("sous_titre")
        texte_catalogue.setWordWrap(True)
        self.bouton_maj = bouton("Mettre à jour", "refresh-cw", "principal", "ENCRE")
        self.bouton_maj.clicked.connect(self.mise_a_jour_demandee)
        ligne_catalogue = QHBoxLayout()
        ligne_catalogue.setSpacing(16)
        ligne_catalogue.addWidget(texte_catalogue, stretch=1)
        ligne_catalogue.addWidget(self.bouton_maj)
        carte.contenu.addLayout(ligne_catalogue)
        carte.contenu.addWidget(Filet())

        titre_donnees = QLabel("Données sur ce PC")
        titre_donnees.setObjectName("libelle")
        chemin = QLabel(str(DOSSIER_DONNEES))
        chemin.setObjectName("chemin")
        chemin.setWordWrap(True)
        chemin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        textes = QVBoxLayout()
        textes.setSpacing(4)
        textes.addWidget(titre_donnees)
        textes.addWidget(chemin)
        bouton_dossier = bouton("Ouvrir le dossier", "folder-open")
        bouton_dossier.clicked.connect(self.ouvrir_dossier)
        ligne_donnees = QHBoxLayout()
        ligne_donnees.setSpacing(16)
        ligne_donnees.addLayout(textes, stretch=1)
        ligne_donnees.addWidget(bouton_dossier)
        carte.contenu.addLayout(ligne_donnees)
        return carte

    def carte_a_propos(self):
        carte = Carte("À propos", "info")
        nom = QLabel(NOM)
        nom.setObjectName("libelle")
        version = QLabel(VERSION)
        version.setObjectName("puce")
        self.bouton_verifier = bouton("Vérifier les mises à jour", "refresh-cw")
        self.bouton_verifier.clicked.connect(self.verifier)
        ligne = QHBoxLayout()
        ligne.setSpacing(10)
        ligne.addWidget(nom)
        ligne.addWidget(version)
        ligne.addStretch()
        ligne.addWidget(self.bouton_verifier)
        carte.contenu.addLayout(ligne)

        self.resultat = QLabel("")
        self.resultat.setObjectName("aide")
        self.bouton_telecharger = QPushButton("")
        self.bouton_telecharger.setObjectName("lien")
        self.bouton_telecharger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_telecharger.clicked.connect(self.telecharger)
        self.bouton_telecharger.hide()
        ligne_resultat = QHBoxLayout()
        ligne_resultat.addWidget(self.resultat)
        ligne_resultat.addWidget(self.bouton_telecharger)
        ligne_resultat.addStretch()
        carte.contenu.addLayout(ligne_resultat)

        texte = QLabel(CREDITS + "\n\n" + MENTION_RIOT)
        texte.setObjectName("aide")
        texte.setWordWrap(True)
        carte.contenu.addWidget(texte)
        return carte

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.curseur.blockSignals(True)
            self.curseur.setValue(lire_largeur())
            self.curseur.blockSignals(False)
            self.interrupteur_effets.definir(effets.effets_actifs())

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
