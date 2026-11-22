from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.decks import (
    TAILLE_PRINCIPAL,
    analyser,
    besoins,
    courbe,
    est_champion,
    normaliser,
    separer,
)
from app.donnees.images import ARRONDI, charger_miniature
from app.interface import icones, theme
from app.interface.composants.deck import (
    ListeDeck,
    PanneauAjout,
    PanneauManquantes,
    PanneauSortir,
    PanneauStats,
)
from app.interface.composants.elements import EtatVide, Interrupteur, Onglets, Segments, Titre
from app.interface.composants.fenetres_deck import FenetreImportDeck, FenetreNomDeck
from app.interface.composants.panneau_carte import LARGEUR
from app.interface.pages.page_classeurs import bouton

VUES = [("ajouter", "Ajouter"), ("stats", "Stats"), ("sortir", "À sortir"), ("manquantes", "Manquantes")]
TAILLE_LEGENDE = QSize(38, 53)


def image_legende(carte, ratio):
    taille = QSize(round(TAILLE_LEGENDE.width() * ratio), round(TAILLE_LEGENDE.height() * ratio))
    image = charger_miniature(carte["image_url"], taille) if carte is not None else None
    if image is not None:
        resultat = QPixmap.fromImage(image)
        resultat.setDevicePixelRatio(ratio)
        return resultat
    resultat = QPixmap(taille)
    resultat.setDevicePixelRatio(ratio)
    resultat.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(resultat)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(theme.couleur("BORDURE"))
    peintre.setBrush(QColor(theme.SURFACE_HAUTE))
    rayon = TAILLE_LEGENDE.width() * ARRONDI * 2
    peintre.drawRoundedRect(1, 1, TAILLE_LEGENDE.width() - 2, TAILLE_LEGENDE.height() - 2, rayon, rayon)
    peintre.end()
    return resultat


class PageDecks(QWidget):
    def __init__(self, collection, classeurs, decks, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.classeurs = classeurs
        self.decks = decks
        self.ids = []
        self.a_montrer = None
        self.manquantes = []

        self.bouton_importer = bouton("Importer", "clipboard-paste")
        self.bouton_importer.setToolTip("Créer un deck à partir d'une liste ou d'un code copié sur un site")
        self.bouton_nouveau = bouton("Nouveau deck", "plus", "principal", "ENCRE")
        entete = QHBoxLayout()
        entete.addWidget(Titre("Decks"))
        entete.addStretch()
        entete.addWidget(self.bouton_importer)
        entete.addSpacing(6)
        entete.addWidget(self.bouton_nouveau)

        self.onglets = Onglets()
        self.onglets.currentChanged.connect(self.afficher_deck)

        self.legende = QLabel()
        self.legende.setFixedSize(TAILLE_LEGENDE)
        self.infos = QLabel("")
        self.infos.setObjectName("sous_titre")
        self.infos.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.etat = QPushButton("")
        self.etat.setObjectName("lien")
        self.etat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.etat.setToolTip("Voir les règles du deck")
        self.monte = Interrupteur()
        self.monte.setToolTip(
            "Le deck est monté avec tes vraies cartes : elles sont signalées dans tes classeurs "
            "et dans le détail des cartes."
        )
        texte_monte = QLabel("Monté")
        texte_monte.setToolTip(self.monte.toolTip())
        self.bouton_renommer = bouton("Renommer", "pencil")
        self.bouton_supprimer = QPushButton("")
        self.bouton_supprimer.setObjectName("icone")
        self.bouton_supprimer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_supprimer.setToolTip("Supprimer le deck")
        icones.lier(self.bouton_supprimer, "trash-2", 17, "TEXTE_DOUX", "ROUGE")
        ligne_infos = QHBoxLayout()
        ligne_infos.setSpacing(12)
        ligne_infos.addWidget(self.legende)
        ligne_infos.addWidget(self.infos, stretch=1)
        ligne_infos.addWidget(self.etat)
        ligne_infos.addSpacing(10)
        ligne_infos.addWidget(texte_monte)
        ligne_infos.addWidget(self.monte)
        ligne_infos.addSpacing(10)
        ligne_infos.addWidget(self.bouton_renommer)
        ligne_infos.addWidget(self.bouton_supprimer)

        self.liste = ListeDeck()
        self.ajout = PanneauAjout(collection, decks)
        self.stats = PanneauStats()
        self.sortir = PanneauSortir()
        self.manquant = PanneauManquantes()
        self.vues = Segments(VUES)
        self.pile = QStackedWidget()
        for vue in (self.ajout, self.stats, self.sortir, self.manquant):
            self.pile.addWidget(vue)
        cote = QFrame()
        cote.setObjectName("panneau")
        cote.setFixedWidth(LARGEUR)
        disposition_cote = QVBoxLayout(cote)
        disposition_cote.setContentsMargins(14, 14, 12, 12)
        disposition_cote.setSpacing(12)
        disposition_cote.addWidget(self.vues, alignment=Qt.AlignmentFlag.AlignHCenter)
        disposition_cote.addWidget(self.pile, stretch=1)

        corps = QHBoxLayout()
        corps.setSpacing(18)
        corps.addWidget(self.liste, stretch=1)
        corps.addWidget(cote)

        self.contenu_deck = QWidget()
        disposition = QVBoxLayout(self.contenu_deck)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(12)
        disposition.addLayout(ligne_infos)
        disposition.addLayout(corps, stretch=1)

        self.vide = EtatVide()
        self.vide.action.connect(self.nouveau)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 24, 16)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(self.onglets)
        layout.addWidget(self.contenu_deck, stretch=1)
        layout.addWidget(self.vide, stretch=1)

        self.decks.change.connect(self.actualiser)
        self.bouton_nouveau.clicked.connect(self.nouveau)
        self.bouton_importer.clicked.connect(self.importer)
        self.bouton_renommer.clicked.connect(self.renommer)
        self.bouton_supprimer.clicked.connect(self.supprimer)
        self.monte.toggled.connect(self.changer_monte)
        self.etat.clicked.connect(lambda: self.choisir_vue("stats"))
        self.vues.change.connect(lambda: self.choisir_vue(self.vues.valeur()))
        self.liste.quantite_changee.connect(self.changer_quantite)
        self.liste.menu_demande.connect(self.ouvrir_menu)
        self.ajout.ajout_demande.connect(self.ajouter)
        self.sortir.voir_demande.connect(self.voir_dans_classeur)
        self.manquant.marquer_demande.connect(self.marquer_recherchees)
        theme.signaux().change.connect(self.afficher_infos)

        self.actualiser()

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.decks.resynchroniser()
            self.afficher_deck()

    def deck_id(self):
        return self.onglets.tabData(self.onglets.currentIndex())

    def deck(self):
        return self.decks.deck(self.deck_id()) if self.deck_id() else None

    def choisir_vue(self, valeur):
        self.vues.definir(valeur)
        self.pile.setCurrentIndex([code for code, _ in VUES].index(valeur))

    def actualiser(self):
        disponible = self.decks.chargee
        self.bouton_nouveau.setEnabled(disponible)
        self.bouton_importer.setEnabled(disponible)
        if not disponible:
            self.vide.definir("Decks indisponibles", self.decks.erreur, "", "circle-alert")
            self.onglets.hide()
            self.contenu_deck.hide()
            self.vide.show()
            return
        ids = [deck["id"] for deck in self.decks.liste]
        courant = self.a_montrer or self.deck_id()
        self.a_montrer = None
        self.onglets.blockSignals(True)
        if ids != self.ids:
            while self.onglets.count():
                self.onglets.removeTab(0)
            for deck in self.decks.liste:
                self.onglets.setTabData(self.onglets.addTab(deck["nom"]), deck["id"])
            self.ids = ids
        for index, deck in enumerate(self.decks.liste):
            if self.onglets.tabText(index) != deck["nom"]:
                self.onglets.setTabText(index, deck["nom"])
            nombres = analyser(self.decks.contenu(deck["id"]), self.decks.cartes())
            self.onglets.definir_nombre(index, nombres["principal"])
        if courant in ids:
            self.onglets.setCurrentIndex(ids.index(courant))
        self.onglets.blockSignals(False)
        if not ids:
            self.vide.definir(
                "Aucun deck pour l'instant",
                "Crée un deck en choisissant sa légende, puis ajoute tes cartes. "
                "Tu peux aussi importer une liste copiée sur un site de decks.",
                "Créer un deck",
                "layers",
            )
        self.vide.setVisible(not ids)
        self.onglets.setVisible(bool(ids))
        self.contenu_deck.setVisible(bool(ids))
        self.afficher_deck()

    def afficher_deck(self):
        deck = self.deck()
        if deck is None:
            return
        cartes = self.decks.cartes()
        contenu = self.decks.contenu(deck["id"])
        analyse = analyser(contenu, cartes)
        besoins_deck = besoins(contenu, cartes)
        manques = {}
        self.manquantes = []
        for cle, besoin in besoins_deck.items():
            if besoin["carte_id"] not in cartes:
                continue
            possedees = self.decks.possedees(self.collection, besoin["carte_id"])
            manque = max(0, besoin["quantite"] - possedees)
            if manque:
                manques[cle] = manque
                self.manquantes.append((cartes[besoin["carte_id"]], manque, possedees))
        self.analyse = analyse
        self.liste.definir(contenu, cartes, manques, analyse)
        colonnes, types = courbe(contenu, cartes)
        self.stats.definir(colonnes, types, analyse)
        self.afficher_sortir(besoins_deck, deck)
        self.manquant.definir(self.manquantes)
        self.manquant.bouton.setEnabled(self.collection.chargee)
        self.monte.definir(bool(deck["monte"]))
        self.ajout.definir_legende(analyse["legende"])
        self.afficher_infos()

    def afficher_sortir(self, besoins_deck, deck):
        cartes = self.decks.cartes()
        places = {}
        hors_classeur = []
        for besoin in besoins_deck.values():
            carte = cartes.get(besoin["carte_id"])
            if carte is None:
                continue
            trouves = set()
            for impression in self.decks.impressions(besoin["carte_id"]):
                for classeur, pochette, _ in self.classeurs.emplacements(impression):
                    trouves.add((classeur["id"], pochette))
            for classeur_id, pochette in trouves:
                places.setdefault(classeur_id, []).append((pochette, carte, besoin["quantite"]))
            if not trouves and self.decks.possedees(self.collection, besoin["carte_id"]) > 0:
                hors_classeur.append((carte, besoin["quantite"]))
        ordre = [
            (classeur, sorted(places[classeur["id"]], key=lambda ligne: ligne[0]))
            for classeur in self.classeurs.liste
            if classeur["id"] in places
        ]
        hors_classeur.sort(key=lambda ligne: ligne[0]["nom"])
        self.sortir.definir(ordre, hors_classeur, bool(deck["monte"]), not besoins_deck)

    def afficher_infos(self):
        deck = self.deck()
        if deck is None or not hasattr(self, "analyse"):
            return
        analyse = self.analyse
        legende = analyse["legende"]
        self.legende.setPixmap(image_legende(legende, self.devicePixelRatioF()))
        if legende is not None:
            domaines = " · ".join(separer(legende["domaines"]))
            titre = f'<span style="color:{theme.TEXTE}; font-weight:600">{legende["nom"]}</span>'
            details = f"{titre}  ·  {domaines}" if domaines else titre
        else:
            details = "Pas encore de légende"
        nombres = analyse["nombres"]
        details += (
            f"  ·  Deck {analyse['principal']}/{TAILLE_PRINCIPAL}"
            f"  ·  Runes {nombres['runes']}/12  ·  Arènes {nombres['arenes']}/3"
        )
        if nombres["reserve"]:
            details += f"  ·  Réserve {nombres['reserve']}"
        self.infos.setText(details)
        problemes = len(analyse["problemes"])
        if problemes:
            self.etat.setText(f"{problemes} point{'s' if problemes > 1 else ''} à revoir")
            icones.lier(self.etat, "triangle-alert", 15, "OR_CLAIR", "OR_CLAIR")
        else:
            self.etat.setText("Prêt à jouer")
            icones.lier(self.etat, "circle-check", 15, "VERT", "VERT")

    def changer_quantite(self, zone, carte_id, quantite):
        deck = self.deck()
        if deck is not None:
            self.decks.definir(deck["id"], zone, carte_id, quantite)

    def ajouter(self, carte_id):
        deck = self.deck()
        if deck is None:
            return
        zone = self.decks.ajouter(deck["id"], carte_id)
        carte = self.decks.cartes().get(carte_id)
        if carte is not None and zone is not None:
            noms = {"legende": "comme légende", "champion": "comme champion choisi", "arenes": "aux arènes",
                    "runes": "aux runes", "principal": "au deck principal"}
            self.decks.message.emit(f"{carte['nom']} ajoutée {noms.get(zone, '')}.")

    def ouvrir_menu(self, zone, carte_id, position):
        deck = self.deck()
        carte = self.decks.cartes().get(carte_id)
        if deck is None or carte is None:
            return
        menu = theme.creer_menu(self)
        champion = reserve = remettre = retirer = None
        if zone == "principal" and est_champion(carte):
            champion = menu.addAction(icones.icone("crown", 16), "Choisir comme champion")
        if zone in ("principal", "champion"):
            reserve = menu.addAction(icones.icone("layers", 16), "Mettre un exemplaire en réserve")
        if zone == "reserve":
            remettre = menu.addAction(icones.icone("layers", 16), "Remettre un exemplaire dans le deck")
        if not menu.isEmpty():
            menu.addSeparator()
        retirer = menu.addAction(icones.icone("trash-2", 16, "ROUGE", "ROUGE"), "Retirer du deck")
        choix = menu.exec(position)
        menu.deleteLater()
        if choix is None:
            return
        if choix == champion:
            self.decks.choisir_champion(deck["id"], zone, carte_id)
        elif choix == reserve:
            self.decks.changer_zone(deck["id"], zone, carte_id, "reserve")
        elif choix == remettre:
            self.decks.changer_zone(deck["id"], zone, carte_id, "principal")
        elif choix == retirer:
            self.decks.definir(deck["id"], zone, carte_id, 0)

    def changer_monte(self, coche):
        deck = self.deck()
        if deck is not None and bool(deck["monte"]) != coche:
            self.decks.modifier(deck["id"], monte=coche)
            if coche:
                self.decks.message.emit(f"« {deck['nom']} » est monté : ses cartes sont signalées dans tes classeurs.")

    def voir_dans_classeur(self, classeur_id, pochette):
        deck = self.deck()
        if deck is not None:
            self.decks.surlignage_demande.emit(deck["id"], classeur_id, pochette)

    def marquer_recherchees(self):
        nombre = 0
        for carte, _, _ in self.manquantes:
            foil = catalogue.toujours_foil(carte)
            if not self.collection.version(carte["carte_id"], foil)["recherche"]:
                if self.collection.modifier(carte["carte_id"], foil, recherche=True):
                    nombre += 1
        if nombre:
            self.decks.message.emit(
                f"{nombre} carte{'s' if nombre > 1 else ''} marquée{'s' if nombre > 1 else ''} comme recherchée"
                f"{'s' if nombre > 1 else ''} : elles comptent maintenant dans les échanges."
            )
        else:
            self.decks.message.emit("Ces cartes étaient déjà marquées comme recherchées.")

    def nouveau(self):
        fenetre = FenetreNomDeck(
            "Nouveau deck",
            "Donne un nom à ton deck. Tu choisiras ensuite sa légende, puis ses cartes.",
            "Créer",
            parent=self,
        )
        if fenetre.exec():
            deck = self.decks.creer(fenetre.resultat())
            self.a_montrer = deck["id"]
            self.actualiser()
            self.choisir_vue("ajouter")
        fenetre.deleteLater()

    def importer(self):
        fenetre = FenetreImportDeck(self.decks, self)
        if fenetre.exec():
            nom, contenu = fenetre.resultat()
            deck = self.decks.creer(nom, contenu)
            self.a_montrer = deck["id"]
            self.actualiser()
            self.choisir_vue("stats")
            total = sum(contenu.values())
            self.decks.message.emit(f"Deck « {nom} » importé : {total} cartes.")
        fenetre.deleteLater()

    def renommer(self):
        deck = self.deck()
        if deck is None:
            return
        fenetre = FenetreNomDeck("Renommer le deck", "", "Renommer", deck["nom"], self)
        if fenetre.exec() and fenetre.resultat() != deck["nom"]:
            self.decks.modifier(deck["id"], nom=fenetre.resultat())
        fenetre.deleteLater()

    def supprimer(self):
        deck = self.deck()
        if deck is None:
            return
        reponse = QMessageBox.question(
            self,
            "Supprimer le deck",
            f"Supprimer le deck « {deck['nom']} » ?\n\nTes cartes restent dans ta collection et dans tes classeurs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reponse == QMessageBox.StandardButton.Yes:
            self.decks.supprimer(deck["id"])

    def montrer(self, deck_id):
        if deck_id in self.ids:
            self.onglets.setCurrentIndex(self.ids.index(deck_id))

    def cartes_du_deck(self, deck_id):
        cartes = self.decks.cartes()
        return {normaliser(cartes[carte_id]["nom"]) for _, carte_id in self.decks.contenu(deck_id) if carte_id in cartes}
