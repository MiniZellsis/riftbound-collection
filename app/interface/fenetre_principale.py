from PySide6.QtCore import QPoint, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QActionGroup, QDesktopServices, QKeySequence, QPixmap, QShortcut
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
from app.donnees.classeurs import Classeurs
from app.donnees.collection import Collection
from app.donnees.images import TelechargementImages
from app.donnees.import_catalogue import ImportCatalogue
from app.donnees.mises_a_jour import VerificationMiseAJour
from app.infos import ICONE, NOM
from app.interface import icones, theme
from app.interface.composants.elements import THEMES, Avatar, BoutonMenu, ChoixTheme, Separateur
from app.interface.pages.page_catalogue import PageCatalogue
from app.interface.pages.page_classeurs import PageClasseurs
from app.interface.pages.page_collection import PageCollection
from app.interface.pages.page_echanges import PageEchanges
from app.interface.pages.page_progression import PageProgression
from app.interface.pages.page_reglages import PageReglages

PAGES = ["Catalogue", "Ma collection", "Classeurs", "Échanges", "Progression", "Réglages"]
ICONES_PAGES = {
    "Catalogue": "library-big",
    "Ma collection": "gem",
    "Classeurs": "book-open",
    "Échanges": "arrow-left-right",
    "Progression": "trophy",
    "Réglages": "settings",
}
DELAI_VERIFICATION = 3000
ETATS = {
    "ok": ("VERT", "Enregistré"),
    "erreur": ("ROUGE", "Pas enregistré"),
    "hors_ligne": ("ROUGE", "Hors ligne"),
}


class CarteJoueur(QFrame):
    def __init__(self, pseudo, parent=None):
        super().__init__(parent)
        self.setObjectName("carte_joueur")
        self.etat = "ok"
        self.avatar = Avatar(pseudo or "?", 34)
        self.nom = QLabel(pseudo or "Hors ligne")
        self.nom.setObjectName("pseudo")
        self.texte_etat = QLabel("")
        self.texte_etat.setObjectName("aide")
        self.bouton = QPushButton("")
        self.bouton.setObjectName("icone")
        self.bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton.setToolTip("Menu du compte")
        icones.lier(self.bouton, "chevrons-up-down", 16, "TEXTE_DOUX", "OR")

        textes = QVBoxLayout()
        textes.setSpacing(1)
        textes.addWidget(self.nom)
        textes.addWidget(self.texte_etat)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 6, 8)
        layout.setSpacing(10)
        layout.addWidget(self.avatar)
        layout.addLayout(textes, stretch=1)
        layout.addWidget(self.bouton)

        theme.signaux().change.connect(self.afficher_etat)

    def definir_etat(self, etat):
        self.etat = etat
        self.afficher_etat()

    def afficher_etat(self):
        couleur, texte = ETATS[self.etat]
        self.texte_etat.setText(f'<span style="color:{getattr(theme, couleur)}">●</span>&nbsp;{texte}')


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
        fermer = QPushButton("")
        fermer.setObjectName("fermer")
        icones.lier(fermer, "x", 16, "TEXTE_DOUX", "OR")
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
        self.classeurs = Classeurs(user_id)
        self.pseudo = None
        self.verification_manuelle = False
        erreur_chargement = ""
        try:
            self.pseudo = supabase_client.lire_pseudo(user_id)
            self.collection.charger()
        except supabase_client.ErreurSupabase as erreur:
            erreur_chargement = str(erreur)
        if self.collection.chargee:
            self.classeurs.charger()
        else:
            self.classeurs.erreur = f"Classeurs indisponibles : {erreur_chargement}"

        self.page_catalogue = PageCatalogue(self.collection, self.classeurs)
        self.page_collection = PageCollection(self.collection, self.classeurs)
        self.page_classeurs = PageClasseurs(self.collection, self.classeurs)
        self.page_echanges = PageEchanges(self.collection, self.pseudo)
        self.page_progression = PageProgression(self.collection)
        self.page_reglages = PageReglages(self.pseudo)

        self.pages = QStackedWidget()
        self.groupe_menu = QButtonGroup(self)
        self.boutons = {}

        barre = QWidget()
        barre.setObjectName("barre_laterale")
        barre.setFixedWidth(232)
        layout_barre = QVBoxLayout(barre)
        layout_barre.setContentsMargins(12, 18, 12, 14)
        layout_barre.setSpacing(3)

        image_logo = QLabel()
        image_logo.setPixmap(self.image_logo())
        nom_logo = QLabel("RIFTBOUND")
        nom_logo.setObjectName("logo")
        sous_logo = QLabel("COLLECTION")
        sous_logo.setObjectName("logo_sous")
        textes_logo = QVBoxLayout()
        textes_logo.setSpacing(0)
        textes_logo.addWidget(nom_logo)
        textes_logo.addWidget(sous_logo)
        ligne_logo = QHBoxLayout()
        ligne_logo.setContentsMargins(6, 0, 0, 18)
        ligne_logo.setSpacing(11)
        ligne_logo.addWidget(image_logo)
        ligne_logo.addLayout(textes_logo, stretch=1)
        layout_barre.addLayout(ligne_logo)

        layout_barre.addWidget(self.ajouter_page("Catalogue", self.page_catalogue, False))
        layout_barre.addWidget(self.ajouter_page("Ma collection", self.page_collection, True))
        layout_barre.addWidget(self.ajouter_page("Classeurs", self.page_classeurs, True))
        separateur = Separateur()
        separateur.setContentsMargins(0, 0, 0, 0)
        layout_barre.addSpacing(6)
        layout_barre.addWidget(separateur)
        layout_barre.addSpacing(6)
        layout_barre.addWidget(self.ajouter_page("Échanges", self.page_echanges, True))
        layout_barre.addWidget(self.ajouter_page("Progression", self.page_progression, True))
        layout_barre.addStretch()
        layout_barre.addWidget(self.ajouter_page("Réglages", self.page_reglages, False))

        texte_theme = QLabel("Thème")
        texte_theme.setObjectName("sous_titre")
        ligne_theme = QHBoxLayout()
        ligne_theme.setContentsMargins(12, 8, 0, 10)
        ligne_theme.setSpacing(10)
        ligne_theme.addWidget(texte_theme)
        ligne_theme.addWidget(ChoixTheme(), stretch=1)
        layout_barre.addLayout(ligne_theme)

        self.carte_joueur = CarteJoueur(self.pseudo)
        self.carte_joueur.definir_etat("ok" if self.collection.chargee else "hors_ligne")
        layout_barre.addWidget(self.carte_joueur)

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
        self.telechargement.image_prete.connect(self.page_classeurs.vue.image_telechargee)
        self.telechargement.image_prete.connect(self.page_catalogue.barre_filtres.icone_telechargee)
        self.page_catalogue.set_affiche.connect(self.telechargement.prioriser)

        self.page_reglages.mise_a_jour_demandee.connect(self.mettre_a_jour_catalogue)
        self.page_reglages.deconnexion_demandee.connect(self.se_deconnecter)
        self.page_collection.catalogue_demande.connect(lambda: self.aller_a("Catalogue"))
        self.carte_joueur.bouton.clicked.connect(self.ouvrir_menu_compte)
        self.collection.envoi_echoue.connect(self.envoi_echoue)
        self.collection.envoi_reussi.connect(lambda carte_id: self.carte_joueur.definir_etat("ok"))
        self.classeurs.envoi_echoue.connect(self.envoi_classeur_echoue)
        self.classeurs.envoi_reussi.connect(lambda: self.carte_joueur.definir_etat("ok"))
        self.classeurs.message.connect(lambda texte: self.statusBar().showMessage(texte, 6000))
        self.classeurs.ouverture_demandee.connect(self.ouvrir_classeur)

        self.verification = VerificationMiseAJour(self)
        self.verification.resultat.connect(self.verification_terminee)
        self.page_reglages.verification_demandee.connect(self.verification.verifier)
        QTimer.singleShot(DELAI_VERIFICATION, self.verification.verifier)

        if catalogue.nombre_cartes() == 0:
            self.mettre_a_jour_catalogue()
        else:
            self.preparer_catalogue()

    def image_logo(self):
        ratio = self.devicePixelRatioF() or 1
        image = QPixmap(str(ICONE)).scaled(
            round(36 * ratio),
            round(36 * ratio),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image.setDevicePixelRatio(ratio)
        return image

    def ajouter_page(self, texte, page, besoin_collection):
        index = self.pages.addWidget(page)
        bouton = BoutonMenu(texte, ICONES_PAGES[texte])
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

    def ouvrir_menu_compte(self):
        menu = theme.creer_menu(self)
        reglages = menu.addAction(icones.icone("settings", 16), "Réglages")
        sous_menu = theme.creer_menu(menu)
        sous_menu.setTitle("Thème")
        sous_menu.setIcon(icones.icone("palette", 16))
        groupe = QActionGroup(sous_menu)
        for valeur, nom_icone, texte in THEMES:
            action = sous_menu.addAction(texte)
            action.setCheckable(True)
            action.setChecked(theme.choix() == valeur)
            action.triggered.connect(lambda _=False, choix=valeur: theme.choisir(choix))
            groupe.addAction(action)
        menu.addMenu(sous_menu)
        verifier = menu.addAction(icones.icone("refresh-cw", 16), "Vérifier les mises à jour")
        menu.addSeparator()
        deconnexion = menu.addAction(icones.icone("log-out", 16, "ROUGE", "ROUGE"), "Se déconnecter")
        bouton = self.carte_joueur.bouton
        hauteur = menu.sizeHint().height()
        choix = menu.exec(bouton.mapToGlobal(QPoint(bouton.width() - menu.sizeHint().width(), -hauteur - 6)))
        menu.deleteLater()
        if choix == reglages:
            self.aller_a("Réglages")
        elif choix == verifier:
            self.verification_manuelle = True
            self.page_reglages.verifier()
        elif choix == deconnexion:
            self.se_deconnecter()

    def verification_terminee(self, etat, version, page):
        self.page_reglages.afficher_verification(etat, version, page)
        if etat == "nouvelle":
            self.bandeau.afficher(version, page)
        elif etat == "a_jour" and self.verification_manuelle:
            self.statusBar().showMessage("Tu as la dernière version.", 5000)
        self.verification_manuelle = False

    def envoi_echoue(self, carte_id, erreur):
        self.carte_joueur.definir_etat("erreur")
        carte = catalogue.lire_carte(carte_id)
        nom = carte["nom"] if carte is not None else carte_id
        self.statusBar().showMessage(f"⚠ {nom} : pas enregistré. {erreur}", 15000)

    def envoi_classeur_echoue(self, erreur):
        self.carte_joueur.definir_etat("erreur")
        self.statusBar().showMessage(f"⚠ Classeur pas enregistré. {erreur}", 15000)

    def ouvrir_classeur(self, classeur_id, pochette):
        self.aller_a("Classeurs")
        self.page_classeurs.montrer(classeur_id, pochette)

    def enregistrer_en_attente(self):
        self.page_catalogue.zone.enregistrer_maintenant()
        self.page_collection.zone.enregistrer_maintenant()
        self.page_classeurs.enregistrer_maintenant()

    def terminer_envois(self):
        self.enregistrer_en_attente()
        collection_ok = self.collection.attendre_envois()
        classeurs_ok = self.classeurs.attendre_envois()
        if not (collection_ok and classeurs_ok):
            QMessageBox.warning(
                self,
                "Collection",
                "Certains changements n'ont pas pu être enregistrés. Vérifie ta connexion Internet.",
            )
        self.collection.arreter()
        self.classeurs.arreter()

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
