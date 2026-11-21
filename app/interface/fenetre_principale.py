from PySide6.QtCore import QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue, supabase_client
from app.donnees.collection import Collection
from app.donnees.images import TelechargementImages
from app.donnees.import_catalogue import ImportCatalogue
from app.donnees.mises_a_jour import VerificationMiseAJour
from app.infos import NOM
from app.interface.pages.page_catalogue import PageCatalogue
from app.interface.pages.page_collection import PageCollection
from app.interface.pages.page_echanges import PageEchanges
from app.interface.pages.page_progression import PageProgression
from app.interface.pages.page_reglages import PageReglages

PAGES = ["Catalogue", "Ma collection", "Échanges", "Progression", "Réglages"]
DELAI_VERIFICATION = 3000


class BandeauMiseAJour(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bandeau")
        self.page = ""
        self.texte = QLabel("")
        bouton = QPushButton("Télécharger")
        bouton.setObjectName("principal")
        bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton.clicked.connect(self.telecharger)
        fermer = QPushButton("×")
        fermer.setObjectName("fermer")
        fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        fermer.setToolTip("Masquer")
        fermer.clicked.connect(self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 8, 16, 8)
        layout.addWidget(self.texte)
        layout.addStretch()
        layout.addWidget(bouton)
        layout.addWidget(fermer)
        self.hide()

    def afficher(self, version, page):
        self.page = page
        self.texte.setText(f"✦  La version {version} de {NOM} est disponible.")
        self.show()

    def telecharger(self):
        QDesktopServices.openUrl(QUrl(self.page))


class FenetrePrincipale(QMainWindow):
    deconnexion = Signal()

    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle(NOM)
        geometrie = QSettings().value("fenetre_principale")
        if geometrie is None or not self.restoreGeometry(geometrie):
            self.resize(1280, 800)

        self.collection = Collection(user_id)
        self.pseudo = None
        erreur_chargement = ""
        try:
            self.pseudo = supabase_client.lire_pseudo(user_id)
            self.collection.charger()
        except supabase_client.ErreurSupabase as erreur:
            erreur_chargement = str(erreur)

        self.page_catalogue = PageCatalogue(self.collection)
        self.page_collection = PageCollection(self.collection)
        self.page_echanges = PageEchanges(self.collection, self.pseudo)
        self.page_progression = PageProgression(self.collection)
        self.page_reglages = PageReglages()

        self.pages = QStackedWidget()
        self.groupe_menu = QButtonGroup(self)
        self.boutons = {}

        barre = QWidget()
        barre.setObjectName("barre_laterale")
        barre.setFixedWidth(220)
        layout_barre = QVBoxLayout(barre)
        layout_barre.setContentsMargins(0, 0, 0, 16)
        layout_barre.setSpacing(4)

        logo = QLabel("RIFTBOUND")
        logo.setObjectName("logo")
        layout_barre.addWidget(logo)

        menu_haut = [
            ("Catalogue", self.page_catalogue, False),
            ("Ma collection", self.page_collection, True),
            ("Échanges", self.page_echanges, True),
            ("Progression", self.page_progression, True),
        ]
        for texte, page, besoin_collection in menu_haut:
            layout_barre.addWidget(self.ajouter_page(texte, page, besoin_collection))

        layout_barre.addStretch()

        pseudo = QLabel(self.pseudo or "Hors ligne")
        pseudo.setObjectName("pseudo")
        layout_barre.addWidget(pseudo)
        layout_barre.addSpacing(6)
        layout_barre.addWidget(self.ajouter_page("Réglages", self.page_reglages, False))
        bouton_deconnexion = QPushButton("Se déconnecter")
        bouton_deconnexion.setObjectName("discret")
        layout_barre.addWidget(bouton_deconnexion)

        self.groupe_menu.idClicked.connect(self.pages.setCurrentIndex)
        self.boutons["Catalogue"].setChecked(True)

        self.bandeau = BandeauMiseAJour()
        droite = QVBoxLayout()
        droite.setContentsMargins(0, 0, 0, 0)
        droite.setSpacing(0)
        droite.addWidget(self.bandeau)
        droite.addWidget(self.pages, stretch=1)

        zone_centrale = QWidget()
        layout = QHBoxLayout(zone_centrale)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(barre)
        layout.addLayout(droite, stretch=1)
        self.setCentralWidget(zone_centrale)

        for numero, texte in enumerate(PAGES, start=1):
            self.boutons[texte].setToolTip(f"Ctrl+{numero}")
            raccourci = QShortcut(QKeySequence(f"Ctrl+{numero}"), self)
            raccourci.activated.connect(lambda texte=texte: self.aller_a(texte))
        recherche = QShortcut(QKeySequence.StandardKey.Find, self)
        recherche.activated.connect(self.chercher)
        self.page_catalogue.barre_filtres.recherche.setToolTip("Ctrl+F")

        self.barre_progression = QProgressBar()
        self.barre_progression.setMaximumWidth(250)
        self.barre_progression.hide()
        self.statusBar().addPermanentWidget(self.barre_progression)
        if erreur_chargement:
            alerte = QLabel(f"Collection indisponible : {erreur_chargement}")
            alerte.setObjectName("erreur")
            self.statusBar().addPermanentWidget(alerte)

        self.import_catalogue = ImportCatalogue(self)
        self.import_catalogue.progression.connect(self.import_progresse)
        self.import_catalogue.termine.connect(self.import_termine)
        self.import_catalogue.echec.connect(self.import_echoue)

        self.telechargement = TelechargementImages(self)
        self.telechargement.progression.connect(self.images_progressent)
        self.telechargement.termine.connect(self.images_terminees)
        self.telechargement.image_prete.connect(self.page_catalogue.grille.image_telechargee)
        self.telechargement.image_prete.connect(self.page_collection.grille.image_telechargee)
        self.telechargement.image_prete.connect(self.page_catalogue.barre_filtres.icone_telechargee)
        self.page_catalogue.set_affiche.connect(self.telechargement.prioriser)

        self.page_reglages.mise_a_jour_demandee.connect(self.mettre_a_jour_catalogue)
        self.page_collection.catalogue_demande.connect(lambda: self.aller_a("Catalogue"))
        bouton_deconnexion.clicked.connect(self.se_deconnecter)
        self.collection.envoi_echoue.connect(self.envoi_echoue)

        self.verification = VerificationMiseAJour(self)
        self.verification.resultat.connect(self.verification_terminee)
        self.page_reglages.verification_demandee.connect(self.verification.verifier)
        QTimer.singleShot(DELAI_VERIFICATION, self.verification.verifier)

        if catalogue.nombre_cartes() == 0:
            self.mettre_a_jour_catalogue()
        else:
            self.preparer_catalogue()

    def ajouter_page(self, texte, page, besoin_collection):
        index = self.pages.addWidget(page)
        bouton = QPushButton(texte)
        bouton.setObjectName("menu")
        bouton.setCheckable(True)
        bouton.setEnabled(self.collection.chargee or not besoin_collection)
        self.groupe_menu.addButton(bouton, index)
        self.boutons[texte] = bouton
        return bouton

    def aller_a(self, texte):
        bouton = self.boutons[texte]
        if bouton.isEnabled():
            bouton.click()

    def chercher(self):
        self.aller_a("Catalogue")
        recherche = self.page_catalogue.barre_filtres.recherche
        recherche.setFocus(Qt.FocusReason.ShortcutFocusReason)
        recherche.selectAll()

    def verification_terminee(self, etat, version, page):
        self.page_reglages.afficher_verification(etat, version, page)
        if etat == "nouvelle":
            self.bandeau.afficher(version, page)

    def envoi_echoue(self, carte_id, erreur):
        carte = catalogue.lire_carte(carte_id)
        nom = carte["nom"] if carte is not None else carte_id
        self.statusBar().showMessage(f"⚠ {nom} : pas enregistré. {erreur}", 15000)

    def enregistrer_en_attente(self):
        self.page_catalogue.zone.enregistrer_maintenant()
        self.page_collection.zone.enregistrer_maintenant()

    def terminer_envois(self):
        self.enregistrer_en_attente()
        if not self.collection.attendre_envois():
            QMessageBox.warning(
                self,
                "Collection",
                "Certains changements n'ont pas pu être enregistrés. Vérifie ta connexion Internet.",
            )
        self.collection.arreter()

    def preparer_catalogue(self):
        nombre = self.telechargement.demarrer(catalogue.lister_cartes())
        self.page_catalogue.charger()
        if nombre:
            self.barre_progression.setRange(0, nombre)
            self.barre_progression.setValue(0)
            self.barre_progression.show()
            self.statusBar().showMessage(f"Téléchargement des images : 0/{nombre}")

    def images_progressent(self, faites, total):
        self.barre_progression.setRange(0, total)
        self.barre_progression.setValue(faites)
        self.statusBar().showMessage(f"Téléchargement des images : {faites}/{total}")

    def images_terminees(self, echecs):
        self.barre_progression.hide()
        if echecs:
            self.statusBar().showMessage(
                f"{echecs} image(s) n'ont pas pu être téléchargées. Nouvel essai au prochain lancement.",
                10000,
            )
        else:
            self.statusBar().showMessage("Toutes les images sont téléchargées.", 5000)

    def mettre_a_jour_catalogue(self):
        self.telechargement.arreter()
        self.page_reglages.bouton_maj.setEnabled(False)
        self.barre_progression.setRange(0, 0)
        self.barre_progression.show()
        self.statusBar().showMessage("Connexion à Riftcodex... (le serveur peut être lent)")
        self.import_catalogue.demarrer()

    def import_progresse(self, page, nb_pages):
        self.barre_progression.setRange(0, nb_pages)
        self.barre_progression.setValue(page)
        self.statusBar().showMessage(f"Téléchargement du catalogue : page {page}/{nb_pages}")

    def import_termine(self):
        self.statusBar().showMessage("Catalogue à jour.", 5000)
        self.fin_import()

    def import_echoue(self, message):
        self.statusBar().clearMessage()
        self.fin_import()
        QMessageBox.warning(self, "Catalogue", message)

    def fin_import(self):
        self.barre_progression.hide()
        self.page_reglages.bouton_maj.setEnabled(True)
        self.preparer_catalogue()

    def se_deconnecter(self):
        self.terminer_envois()
        supabase_client.se_deconnecter()
        self.deconnexion.emit()

    def closeEvent(self, event):
        self.terminer_envois()
        QSettings().setValue("fenetre_principale", self.saveGeometry())
        self.import_catalogue.arreter()
        self.telechargement.arreter()
        super().closeEvent(event)
