from PySide6.QtCore import QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.classeurs import decrire_position, position, quantites
from app.donnees.collection import version_vide
from app.donnees.decks import NOMS_ZONES
from app.donnees.images import (
    DELAI_MAX,
    LARGEUR_GRANDE,
    arrondir,
    fichier_grand,
    fichier_icone,
    fichier_miniature,
    url_redimensionnee,
)
from app.interface import icones, theme
from app.interface.composants.elements import Filet, Flux, Interrupteur, Segments, Statut, Titre
from app.interface.composants.image_carte import ImageCarte

COULEURS = dict(theme.DOMAINES + theme.RARETES)
DELAI_SAUVEGARDE = 700
LARGEUR = 372
HAUTEUR_LIGNE = 24
EMPLACEMENTS_MONTRES = 3


def menu_ranger(menu, classeurs, carte_id):
    deja = {}
    for classeur, pochette, _ in classeurs.emplacements(carte_id):
        deja.setdefault(classeur["id"], pochette)
    actions = {}
    for classeur in classeurs.liste:
        texte = classeur["nom"]
        libre = classeurs.premiere_libre(classeur["id"])
        if classeur["id"] in deja:
            texte += f"  ·  déjà page {position(classeur, deja[classeur['id']])[0]}"
        elif libre is None:
            texte += "  ·  plein"
        action = menu.addAction(texte)
        action.setEnabled(classeur["id"] not in deja and libre is not None)
        actions[action] = classeur["id"]
    return actions


def ranger(classeurs, classeur_id, carte_id):
    pochette = classeurs.ranger(classeur_id, carte_id)
    classeur = classeurs.classeur(classeur_id)
    carte = catalogue.lire_carte(carte_id)
    if pochette is not None and carte is not None:
        classeurs.message.emit(
            f"{carte['nom']} rangée dans « {classeur['nom']} » : {decrire_position(classeur, pochette)}."
        )


def menu_decks(menu, decks, carte_id):
    actions = {}
    utilisations = {deck["id"]: quantite for deck, quantite in decks.utilisations(carte_id)}
    for deck in decks.liste:
        texte = deck["nom"]
        if deck["id"] in utilisations:
            texte += f"  ·  déjà ×{utilisations[deck['id']]}"
        actions[menu.addAction(texte)] = deck["id"]
    return actions


def ajouter_au_deck(decks, deck_id, carte_id):
    zone = decks.ajouter(deck_id, carte_id)
    deck = decks.deck(deck_id)
    carte = decks.cartes().get(carte_id)
    if zone is not None and deck is not None and carte is not None:
        decks.message.emit(f"{carte['nom']} ajoutée au deck « {deck['nom']} » ({NOMS_ZONES[zone].lower()}).")


def image_icone(nom, ratio):
    fichier = fichier_icone(nom)
    image = QPixmap(str(fichier)) if fichier.exists() else QPixmap()
    if not image.isNull():
        image = image.scaledToHeight(round(15 * ratio), Qt.TransformationMode.SmoothTransformation)
        image.setDevicePixelRatio(ratio)
        return image
    image = QPixmap(round(10 * ratio), round(10 * ratio))
    image.setDevicePixelRatio(ratio)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor(COULEURS.get(nom, theme.TEXTE_DOUX)))
    peintre.drawEllipse(QRectF(1, 1, 8, 8))
    peintre.end()
    return image


def etiquette(nom, texte=""):
    element = QLabel(texte)
    element.setObjectName(nom)
    element.setFixedHeight(HAUTEUR_LIGNE)
    return element


class Info(QFrame):
    def __init__(self, nom, parent=None):
        super().__init__(parent)
        self.setObjectName(nom)
        self.setFixedHeight(HAUTEUR_LIGNE)
        self.icone = QLabel()
        self.texte = QLabel()
        layout = QHBoxLayout(self)
        marge = 10 if nom == "puce_domaine" else 0
        layout.setContentsMargins(marge, 0, marge, 0)
        layout.setSpacing(6)
        layout.addWidget(self.icone)
        layout.addWidget(self.texte)

    def definir(self, texte):
        self.texte.setText(texte)
        self.icone.setPixmap(image_icone(texte, self.devicePixelRatioF()) if texte else QPixmap())
        self.setVisible(bool(texte))


class Compteur(QWidget):
    change = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valeur = 0
        self.moins = QPushButton("")
        self.moins.setObjectName("rond")
        icones.lier(self.moins, "minus", 13, "TEXTE", "TEXTE")
        self.plus = QPushButton("")
        self.plus.setObjectName("rond_or")
        icones.lier(self.plus, "plus", 13, "OR_CLAIR", "OR_CLAIR")
        for bouton in (self.moins, self.plus):
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            bouton.setAutoRepeat(True)
        self.texte = QLabel("0")
        self.texte.setObjectName("nombre_compteur")
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte.setFixedWidth(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.moins)
        layout.addWidget(self.texte)
        layout.addWidget(self.plus)

        self.moins.clicked.connect(self.diminuer)
        self.plus.clicked.connect(self.augmenter)

    def diminuer(self):
        self.change.emit(self.valeur - 1)

    def augmenter(self):
        self.change.emit(self.valeur + 1)

    def definir(self, valeur, maximum):
        self.valeur = valeur
        self.texte.setText(str(valeur))
        self.moins.setEnabled(valeur > 0)
        self.plus.setEnabled(valeur < maximum)


class PanneauCarte(QFrame):
    ferme = Signal()
    modifiee = Signal(str)

    def __init__(self, collection, classeurs=None, decks=None, parent=None):
        super().__init__(parent)
        self.setObjectName("panneau")
        self.setFixedWidth(LARGEUR)
        self.collection = collection
        self.classeurs = classeurs
        self.decks = decks
        self.carte = None
        self.seule_foil = False
        self.versions = {}
        self.compteurs = {}
        self.interrupteurs = {}
        self.lignes = {}
        self.pile = []
        self.version_pile = "toutes"
        self.choix_pile = None
        self.reseau = QNetworkAccessManager(self)
        self.reponse = None

        self.code = QLabel("")
        self.code.setObjectName("code_carte")
        bouton_fermer = QPushButton("")
        bouton_fermer.setObjectName("fermer")
        icones.lier(bouton_fermer, "x", 17, "TEXTE_DOUX", "TEXTE")
        bouton_fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton_fermer.setToolTip("Fermer (Échap)")
        bouton_fermer.clicked.connect(self.ferme)
        haut = QHBoxLayout()
        haut.addWidget(self.code)
        haut.addStretch()
        haut.addWidget(bouton_fermer)

        self.zone_pile = QWidget()
        self.ligne_pile = QHBoxLayout(self.zone_pile)
        self.ligne_pile.setContentsMargins(0, 0, 0, 0)
        self.ligne_pile.setSpacing(10)
        titre_pile = QLabel("Versions")
        titre_pile.setObjectName("entete_tableau")
        titre_pile.setToolTip("Les versions de cette carte rangées dans la même pochette")
        self.ligne_pile.addWidget(titre_pile)
        self.ligne_pile.addStretch()
        self.zone_pile.hide()

        self.image = ImageCarte()
        self.nom = QLabel("")
        self.nom.setObjectName("nom_carte")
        self.nom.setWordWrap(True)

        self.rarete = Info("meta_carte")
        self.separateur_type = etiquette("meta_sep", "·")
        self.type = etiquette("meta_carte")
        self.separateur_domaines = etiquette("meta_sep", "·")
        self.domaines = [Info("puce_domaine") for _ in range(3)]
        self.version = etiquette("puce_version")
        meta = Flux(8, 6)
        for element in (self.rarete, self.separateur_type, self.type, self.separateur_domaines, *self.domaines, self.version):
            meta.addWidget(element)

        section = QHBoxLayout()
        section.setSpacing(10)
        section.addWidget(Titre("Dans ma collection", "titre_section"))
        section.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        tableau = QGridLayout()
        tableau.setHorizontalSpacing(8)
        tableau.setVerticalSpacing(6)
        tableau.setColumnStretch(0, 1)
        for colonne, texte in enumerate(["Exemplaires", "À l'échange", "Recherchée"], start=1):
            entete = QLabel(texte)
            entete.setObjectName("entete_tableau")
            tableau.addWidget(entete, 0, colonne, alignment=Qt.AlignmentFlag.AlignCenter)
        self.creer_ligne(tableau, 1, False, "Normale", None)
        self.creer_ligne(tableau, 2, True, "Foil", "sparkles")

        self.info_foil = QLabel("Cette carte n'existe qu'en foil.")
        self.info_foil.setObjectName("aide")
        self.info_foil.hide()

        self.statut = Statut()
        self.message = QLabel("")
        self.message.setObjectName("erreur")
        self.message.setWordWrap(True)
        self.message.hide()

        self.section_classeurs = QWidget()
        self.bouton_ranger = QPushButton("")
        self.bouton_ranger.setObjectName("icone")
        self.bouton_ranger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_ranger.setToolTip("Ranger dans un classeur")
        icones.lier(self.bouton_ranger, "book-plus", 16, "OR_CLAIR", "OR_CLAIR")
        self.bouton_ranger.clicked.connect(self.ouvrir_menu_ranger)
        entete_classeurs = QHBoxLayout()
        entete_classeurs.setSpacing(10)
        entete_classeurs.addWidget(Titre("Dans mes classeurs", "titre_section"))
        entete_classeurs.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        entete_classeurs.addWidget(self.bouton_ranger)
        self.lignes_classeurs = QVBoxLayout()
        self.lignes_classeurs.setSpacing(2)
        disposition_classeurs = QVBoxLayout(self.section_classeurs)
        disposition_classeurs.setContentsMargins(0, 0, 0, 0)
        disposition_classeurs.setSpacing(4)
        disposition_classeurs.addLayout(entete_classeurs)
        disposition_classeurs.addLayout(self.lignes_classeurs)
        self.section_classeurs.hide()

        self.section_decks = QWidget()
        self.bouton_deck = QPushButton("")
        self.bouton_deck.setObjectName("icone")
        self.bouton_deck.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_deck.setToolTip("Ajouter à un deck")
        icones.lier(self.bouton_deck, "layers", 16, "OR_CLAIR", "OR_CLAIR")
        self.bouton_deck.clicked.connect(self.ouvrir_menu_decks)
        entete_decks = QHBoxLayout()
        entete_decks.setSpacing(10)
        entete_decks.addWidget(Titre("Dans mes decks", "titre_section"))
        entete_decks.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        entete_decks.addWidget(self.bouton_deck)
        self.lignes_decks = QVBoxLayout()
        self.lignes_decks.setSpacing(2)
        disposition_decks = QVBoxLayout(self.section_decks)
        disposition_decks.setContentsMargins(0, 0, 0, 0)
        disposition_decks.setSpacing(4)
        disposition_decks.addLayout(entete_decks)
        disposition_decks.addLayout(self.lignes_decks)
        self.section_decks.hide()

        self.bouton_prix = QPushButton("Voir le prix sur TCGplayer")
        self.bouton_prix.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_prix.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        icones.lier(self.bouton_prix, "external-link", 15, "OR_CLAIR", "OR_CLAIR")
        self.bouton_prix.clicked.connect(self.ouvrir_tcgplayer)

        contenu = QWidget()
        contenu.setObjectName("contenu_defilement")
        layout = QVBoxLayout(contenu)
        layout.setContentsMargins(20, 6, 16, 12)
        layout.setSpacing(12)
        layout.addLayout(haut)
        layout.addWidget(self.zone_pile)
        layout.addWidget(self.image, stretch=1)
        layout.addWidget(self.nom)
        layout.addLayout(meta)
        layout.addSpacing(4)
        layout.addLayout(section)
        layout.addLayout(tableau)
        layout.addWidget(self.info_foil)
        layout.addWidget(self.statut)
        layout.addWidget(self.message)
        layout.addWidget(self.section_classeurs)
        layout.addWidget(self.section_decks)
        layout.addStretch()
        layout.addWidget(self.bouton_prix)

        defilement = QScrollArea()
        defilement.setObjectName("defilement")
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QScrollArea.Shape.NoFrame)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        defilement.viewport().setAutoFillBackground(False)
        defilement.setWidget(contenu)

        cadre = QVBoxLayout(self)
        cadre.setContentsMargins(0, 8, 4, 8)
        cadre.addWidget(defilement)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(DELAI_SAUVEGARDE)
        self.minuteur.timeout.connect(self.enregistrer)

        self.minuteur_etat = QTimer(self)
        self.minuteur_etat.setSingleShot(True)
        self.minuteur_etat.setInterval(2500)
        self.minuteur_etat.timeout.connect(self.effacer_statut)

        self.collection.envoi_reussi.connect(self.envoi_reussi)
        self.collection.envoi_echoue.connect(self.envoi_echoue)
        if self.classeurs is not None:
            self.classeurs.change.connect(self.afficher_classeurs)
        if self.decks is not None:
            self.decks.change.connect(self.afficher_decks)

    def creer_ligne(self, tableau, ligne, foil, texte, nom_icone):
        quantite = Compteur()
        a_echanger = Compteur()
        recherche = Interrupteur()
        quantite.change.connect(lambda valeur: self.changer(foil, "quantite", valeur))
        a_echanger.change.connect(lambda valeur: self.changer(foil, "a_echanger", valeur))
        recherche.toggled.connect(lambda coche: self.changer(foil, "recherche", coche))

        libelle = QWidget()
        disposition = QHBoxLayout(libelle)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(6)
        if nom_icone:
            icone = QLabel()
            icones.lier_image(icone, nom_icone, 15, "OR_CLAIR")
            disposition.addWidget(icone)
        nom = QLabel(texte)
        nom.setObjectName("libelle_ligne")
        disposition.addWidget(nom)
        disposition.addStretch()

        tableau.addWidget(libelle, ligne, 0)
        tableau.addWidget(quantite, ligne, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        tableau.addWidget(a_echanger, ligne, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        tableau.addWidget(recherche, ligne, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.compteurs[foil] = (quantite, a_echanger)
        self.interrupteurs[foil] = recherche
        self.lignes[foil] = (libelle, quantite, a_echanger, recherche)

    def afficher(self, carte_id):
        if carte_id not in self.pile:
            self.definir_pile([])
        if self.carte is not None and self.carte["carte_id"] == carte_id:
            return
        self.enregistrer_maintenant()
        self.carte = catalogue.lire_carte(carte_id)
        self.seule_foil = catalogue.toujours_foil(self.carte)
        self.code.setText(catalogue.code_affiche(self.carte, True))
        self.nom.setText(self.carte["nom"].upper())
        self.afficher_meta()
        self.bouton_prix.setEnabled(bool(self.carte["tcgplayer_id"]))
        self.effacer_statut()
        self.message.hide()
        self.recharger()
        self.afficher_classeurs()
        self.afficher_decks()
        self.charger_image()
        if self.choix_pile is not None:
            self.choix_pile.definir(carte_id)

    def definir_pile(self, pile, version="toutes"):
        pile = list(pile) if len(pile) > 1 else []
        if pile != self.pile:
            if self.choix_pile is not None:
                self.ligne_pile.removeWidget(self.choix_pile)
                self.choix_pile.hide()
                self.choix_pile.deleteLater()
                self.choix_pile = None
            self.pile = pile
            if pile:
                choix = [(carte_id, catalogue.numero_court(catalogue.lire_carte(carte_id))) for carte_id in pile]
                self.choix_pile = Segments(choix)
                for carte_id, bouton in self.choix_pile.boutons.items():
                    bouton.setProperty("numero", bouton.text())
                    bouton.setToolTip(f"Voir {catalogue.code_affiche(catalogue.lire_carte(carte_id))}")
                self.choix_pile.change.connect(self.choisir_dans_pile)
                self.ligne_pile.insertWidget(1, self.choix_pile)
            self.zone_pile.setVisible(bool(pile))
        self.version_pile = version
        if self.choix_pile is not None and self.carte is not None:
            self.choix_pile.definir(self.carte["carte_id"])
        self.afficher_pile()

    def choisir_dans_pile(self):
        carte_id = self.choix_pile.valeur()
        if carte_id:
            self.afficher(carte_id)

    def afficher_pile(self):
        if self.choix_pile is None:
            return
        for carte_id, bouton in self.choix_pile.boutons.items():
            quantite = quantites(self.collection, carte_id, self.version_pile)[0]
            numero = bouton.property("numero")
            bouton.setText(f"{numero}  ×{quantite}" if quantite else numero)

    def afficher_classeurs(self):
        utile = (
            self.carte is not None
            and self.classeurs is not None
            and self.classeurs.chargee
            and bool(self.classeurs.liste)
        )
        self.section_classeurs.setVisible(utile)
        if not utile:
            return
        while self.lignes_classeurs.count():
            element = self.lignes_classeurs.takeAt(0)
            if element.widget() is not None:
                element.widget().hide()
                element.widget().deleteLater()
        emplacements = self.classeurs.emplacements(self.carte["carte_id"])
        for classeur, pochette, empilee in emplacements[:EMPLACEMENTS_MONTRES]:
            self.lignes_classeurs.addWidget(self.ligne_classeur(classeur, pochette, empilee))
        reste = len(emplacements) - EMPLACEMENTS_MONTRES
        if reste > 0:
            self.lignes_classeurs.addWidget(etiquette("aide", f"et {reste} autre{'s' if reste > 1 else ''} pochette{'s' if reste > 1 else ''}"))
        if not emplacements:
            texte = QLabel("Cette carte n'est dans aucun classeur.")
            texte.setObjectName("aide")
            self.lignes_classeurs.addWidget(texte)

    def ligne_classeur(self, classeur, pochette, empilee=False):
        ligne = QWidget()
        disposition = QHBoxLayout(ligne)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(8)
        icone = QLabel()
        icones.lier_image(icone, "map-pin", 14, "OR_CLAIR")
        description = f"<b>{classeur['nom']}</b> · {decrire_position(classeur, pochette)}"
        if empilee:
            element = self.classeurs.contenu(classeur["id"]).get(pochette)
            voisine = catalogue.lire_carte(element["carte_id"]) if element else None
            if voisine is not None:
                description += f", avec {catalogue.code_affiche(voisine)}"
        texte = QLabel(description)
        texte.setObjectName("emplacement")
        texte.setWordWrap(True)
        voir = QPushButton("Voir")
        voir.setObjectName("lien")
        voir.setCursor(Qt.CursorShape.PointingHandCursor)
        voir.setToolTip("Ouvrir le classeur à cette page")
        voir.clicked.connect(lambda: self.classeurs.ouverture_demandee.emit(classeur["id"], pochette))
        disposition.addWidget(icone, alignment=Qt.AlignmentFlag.AlignTop)
        disposition.addWidget(texte, stretch=1)
        disposition.addWidget(voir, alignment=Qt.AlignmentFlag.AlignTop)
        return ligne

    def afficher_decks(self):
        utile = (
            self.carte is not None
            and self.decks is not None
            and self.decks.chargee
            and bool(self.decks.liste)
        )
        self.section_decks.setVisible(utile)
        if not utile:
            return
        while self.lignes_decks.count():
            element = self.lignes_decks.takeAt(0)
            if element.widget() is not None:
                element.widget().hide()
                element.widget().deleteLater()
        utilisations = self.decks.utilisations(self.carte["carte_id"])
        for deck, quantite in utilisations:
            self.lignes_decks.addWidget(self.ligne_deck(deck, quantite))
        if not utilisations:
            texte = QLabel("Cette carte n'est dans aucun deck.")
            texte.setObjectName("aide")
            self.lignes_decks.addWidget(texte)

    def ligne_deck(self, deck, quantite):
        ligne = QWidget()
        disposition = QHBoxLayout(ligne)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(8)
        icone = QLabel()
        icones.lier_image(icone, "layers", 14, "OR_CLAIR")
        description = f"<b>{deck['nom']}</b> · {quantite} exemplaire{'s' if quantite > 1 else ''}"
        if deck["monte"]:
            description += " · monté"
        texte = QLabel(description)
        texte.setObjectName("emplacement")
        texte.setWordWrap(True)
        voir = QPushButton("Voir")
        voir.setObjectName("lien")
        voir.setCursor(Qt.CursorShape.PointingHandCursor)
        voir.setToolTip("Ouvrir le deck")
        voir.clicked.connect(lambda: self.decks.ouverture_demandee.emit(deck["id"]))
        disposition.addWidget(icone, alignment=Qt.AlignmentFlag.AlignTop)
        disposition.addWidget(texte, stretch=1)
        disposition.addWidget(voir, alignment=Qt.AlignmentFlag.AlignTop)
        return ligne

    def ouvrir_menu_decks(self):
        if self.carte is None:
            return
        menu = theme.creer_menu(self)
        actions = menu_decks(menu, self.decks, self.carte["carte_id"])
        choix = menu.exec(self.bouton_deck.mapToGlobal(self.bouton_deck.rect().bottomLeft()))
        menu.deleteLater()
        if choix in actions:
            ajouter_au_deck(self.decks, actions[choix], self.carte["carte_id"])

    def ouvrir_menu_ranger(self):
        if self.carte is None:
            return
        menu = theme.creer_menu(self)
        actions = menu_ranger(menu, self.classeurs, self.carte["carte_id"])
        choix = menu.exec(self.bouton_ranger.mapToGlobal(self.bouton_ranger.rect().bottomLeft()))
        menu.deleteLater()
        if choix in actions:
            ranger(self.classeurs, actions[choix], self.carte["carte_id"])

    def afficher_meta(self):
        carte = self.carte
        rarete = carte["rarete"] or ""
        type_carte = carte["type"] or ""
        domaines = [domaine for domaine in (carte["domaines"] or "").split(", ") if domaine]
        self.rarete.definir(rarete)
        self.type.setText(type_carte)
        self.type.setVisible(bool(type_carte))
        self.separateur_type.setVisible(bool(rarete and type_carte))
        self.separateur_domaines.setVisible(bool(domaines) and bool(rarete or type_carte))
        for rang, element in enumerate(self.domaines):
            element.definir(domaines[rang] if rang < len(domaines) else "")
        version = self.texte_version()
        self.version.setText(version)
        self.version.setVisible(bool(version))

    def texte_version(self):
        versions = []
        if self.carte["art_alternatif"]:
            versions.append("Art alternatif")
        if self.carte["signature"]:
            versions.append("Signature")
        if self.carte["surnumerotee"]:
            versions.append("Surnumérotée")
        return " · ".join(versions)

    def recharger(self):
        if self.carte is None:
            return
        carte_id = self.carte["carte_id"]
        self.versions = {
            False: dict(self.collection.version(carte_id, False)),
            True: dict(self.collection.version(carte_id, True)),
        }
        normale_visible = not self.seule_foil or not version_vide(self.versions[False])
        for widget in self.lignes[False]:
            widget.setVisible(normale_visible)
        self.info_foil.setVisible(self.seule_foil)
        self.afficher_valeurs()
        if not self.collection.chargee:
            self.message.setText("Collection indisponible : vérifie ta connexion, puis reconnecte-toi.")
            self.message.show()

    def afficher_valeurs(self):
        for foil, (quantite, a_echanger) in self.compteurs.items():
            version = self.versions[foil]
            quantite.definir(version["quantite"], 99)
            a_echanger.definir(version["a_echanger"], version["quantite"])
            interrupteur = self.interrupteurs[foil]
            if interrupteur.isChecked() != version["recherche"]:
                interrupteur.definir(version["recherche"])
            for controle in (quantite, a_echanger, interrupteur):
                controle.setEnabled(self.collection.chargee)
        self.image.definir_foil(self.seule_foil or self.versions[True]["quantite"] > 0)

    def changer(self, foil, champ, valeur):
        version = self.versions[foil]
        version[champ] = valeur
        version["a_echanger"] = min(version["a_echanger"], version["quantite"])
        self.afficher_valeurs()
        self.effacer_statut()
        self.minuteur.start()

    def effacer_statut(self):
        self.minuteur_etat.stop()
        self.statut.definir(None)

    def enregistrer_maintenant(self):
        if self.minuteur.isActive():
            self.minuteur.stop()
            self.enregistrer()

    def enregistrer(self):
        carte_id = self.carte["carte_id"]
        if not self.collection.enregistrer(carte_id, [self.versions[False], self.versions[True]]):
            return
        self.message.hide()
        self.minuteur_etat.stop()
        self.statut.definir("envoi", "Enregistrement…")
        self.modifiee.emit(carte_id)
        self.afficher_pile()

    def montre(self, carte_id):
        return self.carte is not None and self.carte["carte_id"] == carte_id

    def envoi_reussi(self, carte_id):
        if self.montre(carte_id) and self.statut.etat == "envoi":
            self.statut.definir("ok", "Enregistré")
            self.minuteur_etat.start()

    def envoi_echoue(self, carte_id, erreur):
        if not self.montre(carte_id):
            return
        self.effacer_statut()
        self.message.setText(f"Pas enregistré : {erreur}")
        self.message.show()
        if not self.minuteur.isActive():
            self.recharger()

    def ouvrir_tcgplayer(self):
        url = f"https://www.tcgplayer.com/product/{self.carte['tcgplayer_id']}"
        QDesktopServices.openUrl(QUrl(url))

    def charger_image(self):
        if self.reponse is not None:
            self.reponse.abort()
        url = self.carte["image_url"]
        if not url:
            self.image.definir(None)
            return
        if fichier_grand(url).exists():
            self.image.definir(QImage(str(fichier_grand(url))))
            return

        miniature = QImage(str(fichier_miniature(url)))
        self.image.definir(None if miniature.isNull() else arrondir(miniature))
        requete = QNetworkRequest(url_redimensionnee(url, LARGEUR_GRANDE, "webp"))
        requete.setTransferTimeout(DELAI_MAX)
        reponse = self.reseau.get(requete)
        self.reponse = reponse
        reponse.finished.connect(lambda: self.image_recue(reponse, url))

    def image_recue(self, reponse, url):
        reponse.deleteLater()
        if reponse is self.reponse:
            self.reponse = None
        if reponse.error() != QNetworkReply.NetworkError.NoError:
            return
        donnees = reponse.readAll()
        image = QImage()
        if image.loadFromData(donnees):
            fichier_grand(url).write_bytes(bytes(donnees))
            if self.carte is not None and self.carte["image_url"] == url:
                self.image.definir(image)
