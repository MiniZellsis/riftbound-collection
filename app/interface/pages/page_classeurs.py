from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.classeurs import capacite, contenu_pile, decrire_position, par_page, position
from app.donnees.decks import besoins
from app.interface import icones, theme
from app.interface.composants.elements import EtatVide, ListeChoix, Onglets, Segments, Titre
from app.interface.composants.fenetres_classeur import FenetreChoixCarte, FenetreClasseur, FenetreRemplir
from app.interface.composants.panneau_carte import LARGEUR, PanneauCarte
from app.interface.composants.vue_classeur import VueClasseur
from app.interface.composants.zone_cartes import entete_menu

VERSIONS = [("toutes", "Tous"), ("normale", "Normales"), ("foil", "Foils")]
AIDE = "Clique sur une pochette pour la choisir. Glisse une carte pour la déplacer."
AIDE_VIDE = "Ce classeur est vide : « Remplir » y range tes cartes, ou double-clique sur une pochette."


def bouton(texte, nom_icone, nom="", normal="OR_CLAIR"):
    resultat = QPushButton(texte)
    if nom:
        resultat.setObjectName(nom)
    resultat.setCursor(Qt.CursorShape.PointingHandCursor)
    icones.lier(resultat, nom_icone, 15, normal, normal)
    return resultat


def apercu_couverture(couleur, ratio):
    image = QPixmap(round(18 * ratio), round(22 * ratio))
    image.setDevicePixelRatio(ratio)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    teinte = QColor(couleur)
    peintre.setPen(QPen(teinte.darker(160), 1))
    peintre.setBrush(teinte)
    peintre.drawRoundedRect(QRectF(1.5, 0.5, 16, 21), 3, 3)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(teinte.darker(140))
    peintre.drawRect(QRectF(1.5, 0.5, 3.5, 21))
    peintre.setBrush(QColor(theme.OR_HAUT))
    peintre.drawEllipse(QPointF(10.5, 11), 2, 2)
    peintre.end()
    return image


class DessinPochetteVide(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 210)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        hauteur = min(self.height() - 20, (self.width() - 40) * 1.4)
        zone = QRectF(0, 0, hauteur / 1.4, hauteur)
        zone.moveCenter(QPointF(self.width() / 2, self.height() / 2))
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(theme.couleur("FOND", 150 if theme.mode() == "sombre" else 90))
        peintre.drawRoundedRect(zone.adjusted(-5, -5, 5, 5), 14, 14)
        stylo = QPen(theme.couleur("TEXTE_ETEINT", 90), 1.4)
        stylo.setDashPattern([4, 4])
        peintre.setPen(stylo)
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRoundedRect(zone.adjusted(6, 6, -6, -6), 10, 10)
        peintre.drawPixmap(QPointF(zone.center().x() - 16, zone.center().y() - 16), icones.pixmap("plus", theme.TEXTE_ETEINT, 32))


class PanneauVide(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panneau")
        self.setFixedWidth(LARGEUR)
        self.code = QLabel("")
        self.code.setObjectName("code_carte")
        self.fermer = QPushButton("")
        self.fermer.setObjectName("fermer")
        self.fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fermer.setToolTip("Fermer (Échap)")
        icones.lier(self.fermer, "x", 17, "TEXTE_DOUX", "TEXTE")
        haut = QHBoxLayout()
        haut.addWidget(self.code)
        haut.addStretch()
        haut.addWidget(self.fermer)
        titre = Titre("Pochette vide", "nom_carte")
        texte = QLabel("Choisis une carte à mettre ici, ou glisse une carte depuis une autre pochette.")
        texte.setObjectName("aide")
        texte.setWordWrap(True)
        self.placer = QPushButton("Placer une carte")
        self.placer.setObjectName("principal")
        self.placer.setCursor(Qt.CursorShape.PointingHandCursor)
        icones.lier(self.placer, "plus", 15, "ENCRE", "ENCRE")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 20)
        layout.setSpacing(12)
        layout.addLayout(haut)
        layout.addWidget(DessinPochetteVide(), stretch=1)
        layout.addWidget(titre)
        layout.addWidget(texte)
        layout.addSpacing(6)
        layout.addWidget(self.placer)


class PageClasseurs(QWidget):
    def __init__(self, collection, classeurs, decks=None, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.classeurs = classeurs
        self.decks = decks
        self.cartes = {}
        self.ids = []
        self.a_montrer = None

        self.bouton_nouveau = bouton("Nouveau classeur", "book-plus", "principal", "ENCRE")
        self.bouton_nouveau.clicked.connect(self.nouveau)
        entete = QHBoxLayout()
        entete.addWidget(Titre("Classeurs"))
        entete.addStretch()
        entete.addWidget(self.bouton_nouveau)

        self.onglets = Onglets()
        self.onglets.currentChanged.connect(self.changer_classeur)

        self.couverture = QLabel()
        self.infos = QLabel("")
        self.infos.setObjectName("sous_titre")
        self.infos.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.bouton_remplir = bouton("Remplir", "wand-sparkles")
        self.bouton_remplir.setToolTip("Ranger automatiquement des cartes dans ce classeur")
        self.bouton_modifier = bouton("Modifier", "pencil")
        self.bouton_modifier.setToolTip("Nom, format, capacité et couleur")
        self.bouton_supprimer = QPushButton("")
        self.bouton_supprimer.setObjectName("icone")
        self.bouton_supprimer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_supprimer.setToolTip("Supprimer le classeur")
        icones.lier(self.bouton_supprimer, "trash-2", 17, "TEXTE_DOUX", "ROUGE")
        ligne_infos = QHBoxLayout()
        ligne_infos.setSpacing(10)
        ligne_infos.addWidget(self.couverture)
        ligne_infos.addWidget(self.infos, stretch=1)
        self.choix_deck = ListeChoix([(None, "Surligner un deck…")])
        self.choix_deck.setFixedWidth(210)
        self.choix_deck.setToolTip("Montre où sont les cartes d'un deck, pour les sortir vite du classeur")
        self.choix_deck.setVisible(decks is not None)
        ligne_infos.addWidget(self.choix_deck)
        ligne_infos.addSpacing(6)
        ligne_infos.addWidget(self.bouton_remplir)
        ligne_infos.addWidget(self.bouton_modifier)
        ligne_infos.addWidget(self.bouton_supprimer)

        self.vue = VueClasseur(collection, classeurs)
        self.vue.decks = decks
        self.panneau = PanneauCarte(collection, classeurs, decks)
        self.panneau_vide = PanneauVide()
        self.cote = QStackedWidget()
        self.cote.setFixedWidth(LARGEUR)
        self.cote.addWidget(self.panneau)
        self.cote.addWidget(self.panneau_vide)
        self.cote.hide()
        corps = QHBoxLayout()
        corps.setSpacing(16)
        corps.addWidget(self.vue, stretch=1)
        corps.addWidget(self.cote)

        self.icone_pochette = QLabel()
        icones.lier_image(self.icone_pochette, "map-pin", 15, "OR_CLAIR")
        self.texte_pochette = QLabel("")
        self.texte_pochette.setObjectName("texte_pochette")
        self.texte_pochette.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.versions = Segments(VERSIONS)
        self.versions.setToolTip("Exemplaires comptés dans cette pochette")
        self.bouton_placer = bouton("Placer une carte", "plus")
        self.bouton_changer = bouton("Changer", "replace")
        self.bouton_vider = bouton("Vider", "eraser", "discret", "TEXTE_DOUX")
        self.bouton_vider.setToolTip("Vider la pochette (Suppr)")
        self.texte_pages = QLabel("")
        self.texte_pages.setObjectName("aide")
        self.curseur = QSlider(Qt.Orientation.Horizontal)
        self.curseur.setFixedWidth(150)
        self.curseur.setCursor(Qt.CursorShape.PointingHandCursor)
        barre = QHBoxLayout()
        barre.setSpacing(10)
        barre.addWidget(self.icone_pochette)
        barre.addWidget(self.texte_pochette, stretch=1)
        barre.addWidget(self.versions)
        barre.addWidget(self.bouton_placer)
        barre.addWidget(self.bouton_changer)
        barre.addWidget(self.bouton_vider)
        barre.addSpacing(18)
        barre.addWidget(self.texte_pages)
        barre.addWidget(self.curseur)

        self.contenu_classeur = QWidget()
        disposition = QVBoxLayout(self.contenu_classeur)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(12)
        disposition.addLayout(ligne_infos)
        disposition.addLayout(corps, stretch=1)
        disposition.addLayout(barre)

        self.vide = EtatVide()
        self.vide.action.connect(self.nouveau)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 24, 12)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(self.onglets)
        layout.addWidget(self.contenu_classeur, stretch=1)
        layout.addWidget(self.vide, stretch=1)

        self.classeurs.change.connect(self.actualiser)
        self.vue.pochette_choisie.connect(self.pochette_choisie)
        self.vue.pochette_activee.connect(self.activer)
        self.vue.deplacement_demande.connect(self.deplacer)
        self.vue.menu_demande.connect(self.ouvrir_menu)
        self.vue.suppression_demandee.connect(self.vider)
        self.vue.double_page_changee.connect(self.afficher_pages)
        self.curseur.valueChanged.connect(self.vue.aller)
        self.versions.change.connect(self.changer_version)
        self.bouton_placer.clicked.connect(lambda: self.choisir_carte(self.vue.choisie))
        self.bouton_changer.clicked.connect(lambda: self.choisir_carte(self.vue.choisie))
        self.bouton_vider.clicked.connect(lambda: self.vider(self.vue.choisie))
        self.bouton_remplir.clicked.connect(self.remplir)
        self.bouton_modifier.clicked.connect(self.modifier)
        self.bouton_supprimer.clicked.connect(self.supprimer)
        self.panneau.ferme.connect(self.fermer_cote)
        self.panneau.modifiee.connect(self.vue.update)
        self.panneau_vide.fermer.clicked.connect(self.fermer_cote)
        self.panneau_vide.placer.clicked.connect(lambda: self.choisir_carte(self.vue.choisie))
        theme.signaux().change.connect(self.afficher_infos)
        self.choix_deck.change.connect(self.surligner)
        if decks is not None:
            decks.change.connect(self.actualiser_decks)
            self.actualiser_decks()

        raccourci = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        raccourci.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        raccourci.activated.connect(self.fermer_cote)

        self.actualiser()

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.charger_cartes()
            self.classeurs.resynchroniser()
            self.afficher_classeur()

    def charger_cartes(self):
        if len(self.cartes) != catalogue.nombre_cartes():
            self.cartes = {carte["carte_id"]: carte for carte in catalogue.lister_cartes()}

    def classeur_id(self):
        return self.onglets.tabData(self.onglets.currentIndex())

    def classeur(self):
        return self.classeurs.classeur(self.classeur_id()) if self.classeur_id() else None

    def actualiser(self):
        if not self.classeurs.chargee:
            self.vide.definir("Classeurs indisponibles", self.classeurs.erreur, "", "circle-alert")
            self.bouton_nouveau.setEnabled(False)
            for element in (self.onglets, self.contenu_classeur):
                element.hide()
            self.vide.show()
            return
        self.bouton_nouveau.setEnabled(True)
        ids = [classeur["id"] for classeur in self.classeurs.liste]
        courant = self.a_montrer or self.classeur_id()
        self.a_montrer = None
        self.onglets.blockSignals(True)
        if ids != self.ids:
            while self.onglets.count():
                self.onglets.removeTab(0)
            for classeur in self.classeurs.liste:
                self.onglets.setTabData(self.onglets.addTab(classeur["nom"]), classeur["id"])
            self.ids = ids
        for index, classeur in enumerate(self.classeurs.liste):
            if self.onglets.tabText(index) != classeur["nom"]:
                self.onglets.setTabText(index, classeur["nom"])
            self.onglets.definir_nombre(index, len(self.classeurs.contenu(classeur["id"])))
        if courant in ids:
            self.onglets.setCurrentIndex(ids.index(courant))
        self.onglets.blockSignals(False)

        if not ids:
            self.vide.definir(
                "Aucun classeur pour l'instant",
                "Crée un classeur au même format que ton vrai classeur : nombre de pochettes par page "
                "et capacité. L'appli pourra ensuite le remplir pour toi.",
                "Créer un classeur",
                "book-open",
            )
        self.vide.setVisible(not ids)
        self.onglets.setVisible(bool(ids))
        self.contenu_classeur.setVisible(bool(ids))
        self.afficher_classeur()

    def changer_classeur(self):
        self.fermer_cote()
        self.afficher_classeur()

    def afficher_classeur(self):
        classeur = self.classeur()
        if classeur is None:
            self.vue.definir(None, {}, {}, "")
            return
        self.charger_cartes()
        self.vue.definir(
            classeur,
            self.classeurs.contenu(classeur["id"]),
            self.cartes,
            theme.couleur_couverture(classeur["couleur"]),
        )
        self.afficher_infos()
        self.curseur.blockSignals(True)
        self.curseur.setRange(0, max(0, self.vue.nombre_doubles_pages() - 1))
        self.curseur.setValue(self.vue.double_page)
        self.curseur.blockSignals(False)
        self.afficher_pages()
        self.afficher_pochette()

    def afficher_infos(self):
        classeur = self.classeur()
        if classeur is None:
            return
        self.couverture.setPixmap(apercu_couverture(theme.couleur_couverture(classeur["couleur"]), self.devicePixelRatioF()))
        remplies = len(self.classeurs.contenu(classeur["id"]))
        self.infos.setText(
            f"{par_page(classeur)} pochettes par page ({classeur['colonnes']} × {classeur['lignes']})"
            f"  ·  {classeur['pages']} pages"
            f'  ·  <span style="color:{theme.TEXTE}; font-weight:600">{remplies} / {capacite(classeur)}</span> pochettes remplies'
        )

    def afficher_pages(self):
        if self.classeur() is None:
            return
        self.curseur.blockSignals(True)
        self.curseur.setValue(self.vue.double_page)
        self.curseur.blockSignals(False)
        total = self.classeur()["pages"]
        numeros = [str(numero) for numero, _ in self.vue.zones_pages if numero]
        self.texte_pages.setText(f"{'–'.join(numeros)} / {total}" if numeros else "")
        self.texte_pages.setToolTip("Pages affichées / nombre de pages")

    def afficher_pochette(self):
        classeur = self.classeur()
        pochette = self.vue.choisie
        element = self.classeurs.contenu(classeur["id"]).get(pochette) if classeur else None
        choisie = classeur is not None and pochette >= 0
        self.icone_pochette.setVisible(choisie)
        self.bouton_placer.setVisible(choisie and element is None)
        self.bouton_changer.setVisible(element is not None)
        self.bouton_vider.setVisible(element is not None)
        carte = self.cartes.get(element["carte_id"]) if element else None
        seule_foil = carte is not None and catalogue.toujours_foil(carte)
        self.versions.setVisible(element is not None and not seule_foil)
        if element is not None:
            self.versions.definir(element["version"])
        if not choisie:
            vide = classeur is not None and not self.classeurs.contenu(classeur["id"])
            self.texte_pochette.setText(AIDE_VIDE if vide else AIDE)
            return
        page, ligne, colonne = position(classeur, pochette)
        endroit = f"<b>Page {page}</b> · rangée {ligne} · colonne {colonne}"
        if element is None:
            self.texte_pochette.setText(f"{endroit}  —  pochette vide")
        else:
            nom = carte["nom"] if carte is not None else element["carte_id"]
            pile = self.classeurs.pile(classeur["id"], pochette)
            if len(pile) > 1:
                nom += f"  ·  {len(pile)} versions"
            self.texte_pochette.setText(f"{endroit}  —  {nom}")
            montree = self.panneau.carte["carte_id"] if self.panneau.carte is not None else None
            if self.cote.isVisible() and self.cote.currentWidget() is self.panneau and montree in pile:
                self.panneau.definir_pile(pile, element["version"])
        self.panneau_vide.code.setText(f"PAGE {page} · RANGÉE {ligne} · COLONNE {colonne}")

    def montrer_detail(self, pochette):
        classeur = self.classeur()
        element = self.classeurs.contenu(classeur["id"]).get(pochette) if classeur and pochette >= 0 else None
        if element is None:
            return False
        pile = self.classeurs.pile(classeur["id"], pochette)
        self.panneau.afficher(contenu_pile(self.collection, pile, element["version"])[2])
        self.panneau.definir_pile(pile, element["version"])
        self.cote.setCurrentWidget(self.panneau)
        self.cote.show()
        return True

    def pochette_choisie(self, pochette):
        self.afficher_pochette()
        if self.montrer_detail(pochette):
            return
        if pochette >= 0 and self.cote.isVisible():
            self.cote.setCurrentWidget(self.panneau_vide)
        elif pochette < 0:
            self.fermer_cote()

    def fermer_cote(self):
        self.panneau.enregistrer_maintenant()
        self.cote.hide()

    def activer(self, pochette):
        classeur = self.classeur()
        if classeur is None:
            return
        if pochette in self.classeurs.contenu(classeur["id"]):
            self.pochette_choisie(pochette)
        else:
            self.choisir_carte(pochette)

    def choisir_carte(self, pochette):
        classeur = self.classeur()
        if classeur is None or pochette < 0:
            return
        fenetre = FenetreChoixCarte(
            self.collection,
            f"Pour la pochette de « {classeur['nom']} », {decrire_position(classeur, pochette)}.",
            self,
        )
        if fenetre.exec() and fenetre.carte_id:
            element = self.classeurs.contenu(classeur["id"]).get(pochette)
            version = element["version"] if element and element["carte_id"] == fenetre.carte_id else "toutes"
            self.classeurs.placer(classeur["id"], pochette, fenetre.carte_id, version)
            self.vue.choisir(-1)
            self.vue.choisir(pochette)
        fenetre.deleteLater()

    def vider(self, pochette):
        classeur = self.classeur()
        if classeur is not None and pochette >= 0:
            self.classeurs.vider(classeur["id"], [pochette])
            self.pochette_choisie(pochette)

    def deplacer(self, depart, arrivee):
        classeur = self.classeur()
        if classeur is not None:
            self.classeurs.deplacer(classeur["id"], depart, arrivee)

    def changer_version(self):
        classeur = self.classeur()
        pochette = self.vue.choisie
        element = self.classeurs.contenu(classeur["id"]).get(pochette) if classeur else None
        version = self.versions.valeur()
        if element is not None and version != element["version"]:
            self.classeurs.placer(classeur["id"], pochette, element["carte_id"], version)

    def ouvrir_menu(self, pochette, position_menu):
        classeur = self.classeur()
        if classeur is None:
            return
        element = self.classeurs.contenu(classeur["id"]).get(pochette)
        menu = theme.creer_menu(self)
        versions = {}
        detail = changer = vider = placer = None
        if element is None:
            placer = menu.addAction(icones.icone("plus", 16), "Placer une carte…")
        else:
            carte = catalogue.lire_carte(element["carte_id"])
            if carte is not None:
                menu.addAction(entete_menu(menu, carte))
                menu.addSeparator()
            detail = menu.addAction(icones.icone("panel-right-open", 16), "Voir le détail")
            changer = menu.addAction(icones.icone("replace", 16), "Changer de carte…")
            if carte is not None and not catalogue.toujours_foil(carte):
                sous_menu = theme.creer_menu(menu)
                sous_menu.setTitle("Exemplaires comptés")
                sous_menu.setIcon(icones.icone("layers", 16))
                for valeur, texte in VERSIONS:
                    action = sous_menu.addAction(texte)
                    action.setCheckable(True)
                    action.setChecked(element["version"] == valeur)
                    versions[action] = valeur
                menu.addMenu(sous_menu)
            menu.addSeparator()
            vider = menu.addAction(icones.icone("eraser", 16, "ROUGE", "ROUGE"), "Vider la pochette")
        choix = menu.exec(position_menu)
        menu.deleteLater()
        if choix is None:
            return
        if choix in (placer, changer):
            self.choisir_carte(pochette)
        elif choix == detail:
            self.montrer_detail(pochette)
        elif choix == vider:
            self.vider(pochette)
        elif choix in versions:
            self.classeurs.placer(classeur["id"], pochette, element["carte_id"], versions[choix])

    def nouveau(self):
        fenetre = FenetreClasseur(parent=self)
        if fenetre.exec():
            classeur = self.classeurs.creer(**fenetre.resultat())
            self.a_montrer = classeur["id"]
            self.actualiser()
            self.remplir()
        fenetre.deleteLater()

    def modifier(self):
        classeur = self.classeur()
        if classeur is None:
            return
        fenetre = FenetreClasseur(classeur, self.classeurs.derniere(classeur["id"]) + 1, self)
        if fenetre.exec():
            self.classeurs.modifier(classeur["id"], **fenetre.resultat())
        fenetre.deleteLater()

    def remplir(self):
        classeur = self.classeur()
        if classeur is None:
            return
        fenetre = FenetreRemplir(self.collection, self.classeurs, classeur, self)
        if fenetre.exec():
            deja = len(self.classeurs.contenu(classeur["id"]))
            if deja and fenetre.remplacer():
                reponse = QMessageBox.question(
                    self,
                    "Tout remplacer",
                    f"Vider les {deja} pochettes remplies de « {classeur['nom']} », puis le remplir à nouveau ?\n\n"
                    "Ton rangement actuel sera perdu. Ta collection ne change pas.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reponse != QMessageBox.StandardButton.Yes:
                    fenetre.deleteLater()
                    return
            depart = fenetre.depart()
            nombre = self.classeurs.remplir(classeur["id"], fenetre.elements(), depart, fenetre.remplacer())
            self.vue.aller(self.vue.double_page_de(depart))
            self.classeurs.message.emit(f"{nombre} pochette{'s' if nombre > 1 else ''} remplie{'s' if nombre > 1 else ''} dans « {classeur['nom']} ».")
        fenetre.deleteLater()

    def supprimer(self):
        classeur = self.classeur()
        if classeur is None:
            return
        reponse = QMessageBox.question(
            self,
            "Supprimer le classeur",
            f"Supprimer le classeur « {classeur['nom']} » ?\n\n"
            "Seul le rangement est supprimé : tes cartes restent dans ta collection.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reponse == QMessageBox.StandardButton.Yes:
            self.fermer_cote()
            self.classeurs.supprimer(classeur["id"])

    def montrer(self, classeur_id, pochette):
        if classeur_id not in self.ids:
            return
        self.onglets.setCurrentIndex(self.ids.index(classeur_id))
        self.vue.montrer(pochette)
        self.vue.setFocus()

    def enregistrer_maintenant(self):
        self.panneau.enregistrer_maintenant()

    def actualiser_decks(self):
        if self.decks is None:
            return
        choix = [(None, "Surligner un deck…")]
        if self.decks.chargee:
            choix += [(deck["id"], f"Deck : {deck['nom']}") for deck in self.decks.liste]
        self.choix_deck.definir_choix(choix)
        self.surligner()

    def surligner(self):
        deck = self.decks.deck(self.choix_deck.valeur) if self.decks is not None and self.choix_deck.valeur else None
        if deck is None:
            self.vue.surligner({})
            return
        cartes = self.decks.cartes()
        besoins_deck = besoins(self.decks.contenu(deck["id"]), cartes)
        self.vue.surligner({cle: besoin["quantite"] for cle, besoin in besoins_deck.items()}, deck["nom"])

    def surligner_deck(self, deck_id, classeur_id, pochette):
        self.actualiser_decks()
        self.choix_deck.definir(deck_id)
        self.surligner()
        self.montrer(classeur_id, pochette)

    def sizeHint(self):
        return QSize(1100, 760)
