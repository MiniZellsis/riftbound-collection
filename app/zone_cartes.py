from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from app import supabase_client, theme
from app.grille_cartes import ROLE_CARTE_ID, GrilleCartes
from app.panneau_carte import PanneauCarte


class ZoneCartes(QWidget):
    collection_modifiee = Signal()

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.grille = GrilleCartes(collection)
        self.panneau = PanneauCarte(collection)
        self.panneau.hide()

        self.message = QLabel("")
        self.message.setObjectName("sous_titre")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.message.hide()

        gauche = QVBoxLayout()
        gauche.addWidget(self.message, stretch=1)
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

    def afficher(self, cartes, message):
        self.grille.afficher(cartes)
        self.message.setText(message)
        self.message.setVisible(not cartes)
        self.grille.setVisible(bool(cartes))

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

    def ouvrir_menu(self, position):
        element = self.grille.itemAt(position)
        if element is None:
            return
        self.grille.setCurrentItem(element)
        carte_id = element.data(ROLE_CARTE_ID)
        self.panneau.enregistrer_maintenant()
        normale = self.collection.version(carte_id, False)
        foil = self.collection.version(carte_id, True)

        menu = theme.creer_menu(self)
        titre = menu.addAction(element.text())
        titre.setEnabled(False)
        menu.addSeparator()
        ajouter = menu.addAction("Ajouter un exemplaire")
        ajouter_foil = menu.addAction("Ajouter une foil")
        retirer = menu.addAction("Retirer un exemplaire")
        retirer.setEnabled(normale["quantite"] > 0)
        retirer_foil = menu.addAction("Retirer une foil")
        retirer_foil.setEnabled(foil["quantite"] > 0)
        menu.addSeparator()
        recherchee = menu.addAction("Recherchée")
        recherchee.setCheckable(True)
        recherchee.setChecked(normale["recherche"])
        doubles = menu.addAction("Doubles à l'échange")
        doubles.setCheckable(True)
        doubles.setChecked(normale["a_echanger"] > 0)
        doubles.setEnabled(normale["quantite"] > 1 or normale["a_echanger"] > 0)
        menu.addSeparator()
        detail = menu.addAction("Voir le détail")
        if not self.collection.chargee:
            for action in (ajouter, ajouter_foil, retirer, retirer_foil, recherchee, doubles):
                action.setEnabled(False)

        choix = menu.exec(self.grille.viewport().mapToGlobal(position))
        menu.deleteLater()
        if choix is None:
            return
        if choix == detail:
            self.ouvrir(carte_id)
            return

        try:
            if choix == ajouter:
                self.collection.modifier(carte_id, False, quantite=normale["quantite"] + 1)
            elif choix == ajouter_foil:
                self.collection.modifier(carte_id, True, quantite=foil["quantite"] + 1)
            elif choix == retirer:
                self.collection.modifier(carte_id, False, quantite=normale["quantite"] - 1)
            elif choix == retirer_foil:
                self.collection.modifier(carte_id, True, quantite=foil["quantite"] - 1)
            elif choix == recherchee:
                self.collection.modifier(carte_id, False, recherche=recherchee.isChecked())
            elif choix == doubles:
                nombre = normale["quantite"] - 1 if doubles.isChecked() else 0
                self.collection.modifier(carte_id, False, a_echanger=nombre)
        except supabase_client.ErreurSupabase as erreur:
            QMessageBox.warning(self, "Collection", f"Pas enregistré : {erreur}")
            return
        self.panneau.recharger()
        self.carte_modifiee(carte_id)
