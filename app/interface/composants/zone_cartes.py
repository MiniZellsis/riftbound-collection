from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QWidgetAction

from app.donnees import catalogue
from app.donnees.collection import version_vide
from app.interface import icones, theme
from app.interface.composants.elements import EtatVide
from app.interface.composants.grille_cartes import ROLE_CARTE_ID, GrilleCartes
from app.interface.composants.panneau_carte import PanneauCarte


class ZoneCartes(QWidget):
    collection_modifiee = Signal()

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.grille = GrilleCartes(collection)
        self.panneau = PanneauCarte(collection)
        self.panneau.hide()

        self.etat_vide = EtatVide()
        self.etat_vide.hide()

        gauche = QVBoxLayout()
        gauche.addWidget(self.etat_vide, stretch=1)
        gauche.addWidget(self.grille, stretch=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(gauche, stretch=1)
        layout.addWidget(self.panneau)

        self.grille.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grille.customContextMenuRequested.connect(self.ouvrir_menu)
        self.grille.itemClicked.connect(self.element_clique)
        self.grille.currentItemChanged.connect(self.element_courant)
        self.grille.carte_choisie.connect(self.ouvrir)
        self.panneau.ferme.connect(self.fermer_panneau)
        self.panneau.modifiee.connect(self.carte_modifiee)

        raccourci = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        raccourci.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        raccourci.activated.connect(self.fermer_panneau)

        self.collection.envoi_echoue.connect(self.envoi_echoue)

    def afficher(self, cartes, vide):
        self.grille.afficher(cartes)
        self.etat_vide.definir(*vide)
        self.etat_vide.setVisible(not cartes)
        self.grille.setVisible(bool(cartes))

    def envoi_echoue(self, carte_id, erreur):
        self.grille.rafraichir()
        self.collection_modifiee.emit()

    def element_clique(self, element):
        self.ouvrir(element.data(ROLE_CARTE_ID))

    def element_courant(self, element, precedent):
        if element is not None and self.panneau.isVisible():
            self.panneau.afficher(element.data(ROLE_CARTE_ID))

    def ouvrir(self, carte_id):
        self.panneau.afficher(carte_id)
        self.panneau.show()

    def fermer_panneau(self):
        self.panneau.enregistrer_maintenant()
        self.panneau.hide()
        self.grille.clearSelection()

    def carte_modifiee(self, carte_id):
        self.grille.rafraichir()
        self.collection_modifiee.emit()

    def enregistrer_maintenant(self):
        self.panneau.enregistrer_maintenant()

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous() and self.panneau.isVisible():
            self.panneau.recharger()

    def hideEvent(self, event):
        super().hideEvent(event)
        if not event.spontaneous():
            self.panneau.enregistrer_maintenant()

    def entete_menu(self, menu, carte):
        entete = QWidget()
        disposition = QVBoxLayout(entete)
        disposition.setContentsMargins(12, 6, 12, 6)
        disposition.setSpacing(2)
        nom = QLabel(carte["nom"].upper())
        nom.setObjectName("titre_menu")
        morceaux = [catalogue.code_affiche(carte), carte["rarete"], carte["domaines"]]
        details = QLabel(" · ".join(morceau for morceau in morceaux if morceau))
        details.setObjectName("details_menu")
        disposition.addWidget(nom)
        disposition.addWidget(details)
        action = QWidgetAction(menu)
        action.setDefaultWidget(entete)
        action.setEnabled(False)
        return action

    def ouvrir_menu(self, position):
        element = self.grille.itemAt(position)
        if element is None:
            return
        self.grille.setCurrentItem(element)
        carte_id = element.data(ROLE_CARTE_ID)
        self.panneau.enregistrer_maintenant()
        normale = self.collection.version(carte_id, False)
        foil = self.collection.version(carte_id, True)
        carte = catalogue.lire_carte(carte_id)
        seule_foil = carte is not None and catalogue.toujours_foil(carte) and version_vide(normale)
        principale = foil if seule_foil else normale

        menu = theme.creer_menu(self)
        if carte is not None:
            menu.addAction(self.entete_menu(menu, carte))
            menu.addSeparator()
        ajouter = menu.addAction(icones.icone("plus", 16), "Ajouter un exemplaire")
        ajouter_foil = None if seule_foil else menu.addAction(icones.icone("sparkles", 16), "Ajouter une foil")
        retirer = menu.addAction(icones.icone("minus", 16), "Retirer un exemplaire")
        retirer.setEnabled(principale["quantite"] > 0)
        retirer_foil = None
        if not seule_foil:
            retirer_foil = menu.addAction(icones.icone("minus", 16), "Retirer une foil")
            retirer_foil.setEnabled(foil["quantite"] > 0)
        menu.addSeparator()
        recherchee = menu.addAction(icones.icone("heart", 16), "Recherchée")
        recherchee.setCheckable(True)
        recherchee.setChecked(principale["recherche"])
        doubles = menu.addAction(icones.icone("arrow-left-right", 16), "Doubles à l'échange")
        doubles.setCheckable(True)
        doubles.setChecked(principale["a_echanger"] > 0)
        doubles.setEnabled(principale["quantite"] > 1 or principale["a_echanger"] > 0)
        menu.addSeparator()
        detail = menu.addAction(icones.icone("panel-right-open", 16), "Voir le détail")
        if not self.collection.chargee:
            for action in (ajouter, ajouter_foil, retirer, retirer_foil, recherchee, doubles):
                if action is not None:
                    action.setEnabled(False)

        choix = menu.exec(self.grille.viewport().mapToGlobal(position))
        menu.deleteLater()
        if choix is None:
            return
        if choix == detail:
            self.ouvrir(carte_id)
            return

        version_choisie = principale["foil"]
        if choix == ajouter:
            self.collection.modifier(carte_id, version_choisie, quantite=principale["quantite"] + 1)
        elif choix == ajouter_foil:
            self.collection.modifier(carte_id, True, quantite=foil["quantite"] + 1)
        elif choix == retirer:
            self.collection.modifier(carte_id, version_choisie, quantite=principale["quantite"] - 1)
        elif choix == retirer_foil:
            self.collection.modifier(carte_id, True, quantite=foil["quantite"] - 1)
        elif choix == recherchee:
            self.collection.modifier(carte_id, version_choisie, recherche=recherchee.isChecked())
        elif choix == doubles:
            nombre = principale["quantite"] - 1 if doubles.isChecked() else 0
            self.collection.modifier(carte_id, version_choisie, a_echanger=nombre)
        self.panneau.recharger()
        self.carte_modifiee(carte_id)
