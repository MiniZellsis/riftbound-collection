from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.donnees import catalogue
from app.donnees.collection import version_vide
from app.interface import icones, theme
from app.interface.composants.grille_cartes import ROLE_CARTE_ID, GrilleCartes
from app.interface.composants.panneau_carte import PanneauCarte


def dessin_vide(loupe):
    pixmap = QPixmap(192, 192)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    stylo = QPen(QColor(theme.TEXTE_ETEINT), 2, Qt.PenStyle.DashLine)
    stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
    peintre.setPen(stylo)
    peintre.drawRoundedRect(QRectF(24, 12, 48, 68), 6, 6)
    if loupe:
        peintre.setPen(QPen(QColor(theme.OR), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        peintre.setBrush(QColor(theme.FOND))
        peintre.drawEllipse(QPointF(62, 60), 14, 14)
        peintre.drawLine(QPointF(72, 70), QPointF(84, 82))
    peintre.end()
    return pixmap


class EtatVide(QWidget):
    action = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dessin = QLabel()
        self.dessin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titre = QLabel("")
        self.titre.setObjectName("titre_vide")
        self.titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte = QLabel("")
        self.texte.setObjectName("sous_titre")
        self.texte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte.setWordWrap(True)
        self.texte.setFixedWidth(440)
        self.bouton = QPushButton("")
        self.bouton.setObjectName("principal")
        self.bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton.clicked.connect(self.action)
        self.arguments = None
        theme.signaux().change.connect(self.redessiner)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addStretch(2)
        layout.addWidget(self.dessin)
        layout.addWidget(self.titre)
        layout.addWidget(self.texte, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.bouton, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(3)

    def redessiner(self):
        if self.arguments is not None:
            self.definir(*self.arguments)

    def definir(self, titre, texte="", bouton="", loupe=False):
        self.arguments = (titre, texte, bouton, loupe)
        self.dessin.setPixmap(dessin_vide(loupe))
        self.titre.setText(titre)
        self.texte.setText(texte)
        hauteur = self.texte.heightForWidth(self.texte.width())
        if hauteur > 0:
            self.texte.setFixedHeight(hauteur)
        self.texte.setVisible(bool(texte))
        self.bouton.setText(bouton)
        self.bouton.setVisible(bool(bouton))


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
        titre = menu.addAction(element.text().upper())
        titre.setFont(theme.police_titres(13))
        titre.setEnabled(False)
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
