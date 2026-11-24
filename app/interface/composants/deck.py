from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.classeurs import position
from app.donnees.decks import (
    COUT_MAX_COURBE,
    NOMBRE_ARENES,
    NOMS_ZONES,
    RESERVE_MAX,
    TAILLE_PRINCIPAL,
    TAILLE_RUNES,
    TYPES,
    ZONES,
    normaliser,
    separer,
)
from app.donnees.images import fichier_miniature
from app.interface import icones, theme
from app.interface.composants.elements import Filet, ListeChoix, Titre
from app.interface.composants.grille_cartes import GrilleCartes
from app.interface.composants.panneau_carte import Compteur

LARGEUR_GRILLE = 96
TYPES_AJOUT = [
    (None, "Tous les types"),
    ("Legend", "Légendes"),
    ("Unit", "Unités"),
    ("Spell", "Sorts"),
    ("Gear", "Équipements"),
    ("Battlefield", "Arènes"),
    ("Rune", "Runes"),
]
CIBLES = {"legende": 1, "champion": 1, "arenes": NOMBRE_ARENES, "runes": TAILLE_RUNES}
VIDES = {
    "legende": "Pas encore de légende : choisis-en une dans « Ajouter ».",
    "champion": "Pas encore de champion : ajoute un champion de ta légende.",
    "principal": "Ajoute des cartes depuis « Ajouter » (double-clic).",
    "arenes": "Ajoute 3 arènes.",
    "runes": "Ajoute 12 runes des domaines de ta légende.",
    "reserve": "Optionnelle : 8 cartes au plus. Clic droit sur une carte → « Mettre en réserve ».",
}


def apercu(carte):
    fichier = fichier_miniature(carte["image_url"]) if carte["image_url"] else None
    texte = f"<b>{carte['nom']}</b><br>{catalogue.code_affiche(carte, True)}"
    if fichier is not None and fichier.exists():
        return f'<img src="{fichier.as_posix()}" width="200"><br>{texte}'
    return texte


def vider(disposition):
    while disposition.count():
        element = disposition.takeAt(0)
        if element.widget() is not None:
            element.widget().hide()
            element.widget().deleteLater()
        elif element.layout() is not None:
            vider(element.layout())


def defilement(contenu):
    zone = QScrollArea()
    zone.setObjectName("defilement")
    zone.setWidgetResizable(True)
    zone.setFrameShape(QScrollArea.Shape.NoFrame)
    zone.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    zone.viewport().setAutoFillBackground(False)
    contenu.setObjectName("contenu_defilement")
    zone.setWidget(contenu)
    return zone


def entete(texte, compte="", etat="aide"):
    ligne = QHBoxLayout()
    ligne.setSpacing(10)
    ligne.addWidget(Titre(texte, "titre_section"))
    ligne.addWidget(Filet(), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
    if compte:
        nombre = QLabel(compte)
        nombre.setObjectName(etat)
        ligne.addWidget(nombre)
    return ligne


def aide(texte):
    etiquette = QLabel(texte)
    etiquette.setObjectName("aide")
    etiquette.setWordWrap(True)
    return etiquette


class LigneCliquable(QFrame):
    clique = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ligne_deck")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clique.emit()


class LigneCarte(QFrame):
    quantite_changee = Signal(str, str, int)
    menu_demande = Signal(str, str, QPoint)

    def __init__(self, carte, zone, quantite, manque, maximum, parent=None):
        super().__init__(parent)
        self.setObjectName("ligne_deck")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.zone = zone
        self.carte_id = carte["carte_id"]

        cout = QLabel("" if carte["cout"] is None else str(carte["cout"]))
        cout.setObjectName("cout_deck" if carte["cout"] is not None else "cout_vide")
        cout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cout.setFixedSize(24, 24)
        nom = QLabel(carte["nom"])
        nom.setObjectName("nom_deck")
        nom.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        code = QLabel(catalogue.code_affiche(carte))
        code.setObjectName("aide")
        etat = QLabel()
        if manque:
            etat.setText(f"il en manque {manque}")
            etat.setObjectName("manque_deck")
            etat.setToolTip("Pas assez d'exemplaires dans ta collection (toutes versions comprises)")
        else:
            icones.lier_image(etat, "circle-check", 15, "VERT")
            etat.setToolTip("Tu as assez d'exemplaires")
        self.compteur = Compteur()
        self.compteur.definir(quantite, maximum)
        self.compteur.change.connect(lambda valeur: self.quantite_changee.emit(self.zone, self.carte_id, valeur))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(10)
        layout.addWidget(cout)
        layout.addWidget(nom, stretch=1)
        layout.addWidget(code)
        layout.addSpacing(4)
        layout.addWidget(etat)
        layout.addWidget(self.compteur)
        self.setToolTip(apercu(carte))

    def contextMenuEvent(self, event):
        self.menu_demande.emit(self.zone, self.carte_id, event.globalPos())


class ListeDeck(QScrollArea):
    quantite_changee = Signal(str, str, int)
    menu_demande = Signal(str, str, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("defilement")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        contenu = QWidget()
        contenu.setObjectName("contenu_defilement")
        self.disposition = QVBoxLayout(contenu)
        self.disposition.setContentsMargins(0, 0, 12, 12)
        self.disposition.setSpacing(2)
        self.setWidget(contenu)

    def definir(self, contenu, cartes, manques, analyse):
        position_defilement = self.verticalScrollBar().value()
        vider(self.disposition)
        nombres = analyse["nombres"]
        montres = set()
        for zone in ZONES:
            if zone == "principal":
                total = analyse["principal"]
                compte = f"{total} / {TAILLE_PRINCIPAL}"
                etat = "succes" if total == TAILLE_PRINCIPAL else "erreur" if total > TAILLE_PRINCIPAL else "aide"
            elif zone == "reserve":
                compte = f"{nombres[zone]} / {RESERVE_MAX}"
                etat = "erreur" if nombres[zone] > RESERVE_MAX else "aide"
            else:
                cible = CIBLES[zone]
                compte = f"{nombres[zone]} / {cible}"
                etat = "succes" if nombres[zone] == cible else "erreur" if nombres[zone] > cible else "aide"
            if zone != "legende":
                self.disposition.addSpacing(14)
            self.disposition.addLayout(entete(NOMS_ZONES[zone], compte, etat))
            self.disposition.addSpacing(4)
            lignes = [
                (cartes[carte_id], quantite)
                for (zone_carte, carte_id), quantite in contenu.items()
                if zone_carte == zone and carte_id in cartes
            ]
            if not lignes:
                self.disposition.addWidget(aide(VIDES[zone]))
                continue
            lignes.sort(key=lambda element: (
                element[0]["cout"] if element[0]["cout"] is not None else 99,
                element[0]["nom"],
            ))
            if zone == "principal":
                groupes = [(code, texte, [ligne for ligne in lignes if ligne[0]["type"] == code]) for code, texte in TYPES]
                autres = [ligne for ligne in lignes if ligne[0]["type"] not in dict(TYPES)]
                if autres:
                    groupes.append((None, "Autres", autres))
            else:
                groupes = [(None, "", lignes)]
            for _, texte, lignes_groupe in groupes:
                if not lignes_groupe:
                    continue
                if texte:
                    sous_titre = QLabel(f"{texte}  ·  {sum(quantite for _, quantite in lignes_groupe)}")
                    sous_titre.setObjectName("sous_groupe_deck")
                    self.disposition.addWidget(sous_titre)
                for carte, quantite in lignes_groupe:
                    cle = normaliser(carte["nom"])
                    manque = manques.get(cle, 0) if cle not in montres else 0
                    montres.add(cle)
                    maximum = 1 if zone in ("legende", "champion") else 99
                    ligne = LigneCarte(carte, zone, quantite, manque, maximum)
                    ligne.quantite_changee.connect(self.quantite_changee)
                    ligne.menu_demande.connect(self.menu_demande)
                    self.disposition.addWidget(ligne)
        self.disposition.addStretch()
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(position_defilement))


class CourbeCouts(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.colonnes = [0] * (COUT_MAX_COURBE + 1)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def definir(self, colonnes):
        self.colonnes = list(colonnes)
        self.setToolTip("\n".join(
            f"Coût {self.etiquette(cout)} : {nombre} carte{'s' if nombre > 1 else ''}"
            for cout, nombre in enumerate(self.colonnes)
        ))
        self.update()

    def etiquette(self, cout):
        return f"{cout}+" if cout == COUT_MAX_COURBE else str(cout)

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        nombre = len(self.colonnes)
        haut, bas = 20, 22
        hauteur_utile = self.height() - haut - bas
        largeur = self.width() / nombre
        maximum = max(self.colonnes) or 1
        petite = QFont(self.font())
        petite.setPixelSize(12)
        grasse = QFont(petite)
        grasse.setWeight(QFont.Weight.Bold)
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.drawLine(QPointF(0, self.height() - bas + 0.5), QPointF(self.width(), self.height() - bas + 0.5))
        for cout, valeur in enumerate(self.colonnes):
            x = cout * largeur
            barre = QRectF(x + largeur * 0.18, 0, largeur * 0.64, 0)
            hauteur = hauteur_utile * valeur / maximum
            barre.setTop(self.height() - bas - hauteur)
            barre.setBottom(self.height() - bas)
            if valeur:
                degrade = QLinearGradient(barre.topLeft(), barre.bottomLeft())
                degrade.setColorAt(0, theme.couleur("OR_HAUT"))
                degrade.setColorAt(1, theme.couleur("OR_BAS"))
                peintre.setPen(Qt.PenStyle.NoPen)
                peintre.setBrush(degrade)
                peintre.drawRoundedRect(barre, 4, 4)
                peintre.setFont(grasse)
                peintre.setPen(theme.couleur("TEXTE"))
                peintre.drawText(QRectF(x, barre.top() - 18, largeur, 16), Qt.AlignmentFlag.AlignCenter, str(valeur))
            peintre.setFont(petite)
            peintre.setPen(theme.couleur("TEXTE_DOUX"))
            peintre.drawText(QRectF(x, self.height() - bas + 4, largeur, bas - 4), Qt.AlignmentFlag.AlignCenter, self.etiquette(cout))


class PanneauStats(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.courbe = CourbeCouts()
        self.types = aide("")
        self.regles = QVBoxLayout()
        self.regles.setSpacing(6)
        contenu = QWidget()
        disposition = QVBoxLayout(contenu)
        disposition.setContentsMargins(2, 4, 10, 10)
        disposition.setSpacing(10)
        disposition.addLayout(entete("Courbe de coût"))
        disposition.addWidget(self.courbe)
        disposition.addWidget(self.types)
        disposition.addSpacing(8)
        disposition.addLayout(entete("Règles du deck"))
        disposition.addLayout(self.regles)
        disposition.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(defilement(contenu))

    def definir(self, colonnes, types, analyse):
        self.courbe.definir(colonnes)
        morceaux = [f"{types[code]} {texte.lower()}" for code, texte in TYPES]
        legende = analyse["legende"]
        if legende is not None:
            domaines = " et ".join(separer(legende["domaines"]))
            morceaux.append(f"domaines : {domaines}" if domaines else "")
        self.types.setText("  ·  ".join(morceau for morceau in morceaux if morceau))
        vider(self.regles)
        problemes = analyse["problemes"]
        if not problemes:
            self.regles.addLayout(self.ligne_regle("circle-check", "VERT", "Deck complet : il respecte les règles des tournois."))
        for probleme in problemes:
            self.regles.addLayout(self.ligne_regle("triangle-alert", "OR_CLAIR", probleme))

    def ligne_regle(self, nom_icone, couleur, texte):
        ligne = QHBoxLayout()
        ligne.setSpacing(8)
        icone = QLabel()
        icone.setAlignment(Qt.AlignmentFlag.AlignTop)
        icones.lier_image(icone, nom_icone, 15, couleur)
        etiquette = QLabel(texte)
        etiquette.setWordWrap(True)
        ligne.addWidget(icone, alignment=Qt.AlignmentFlag.AlignTop)
        ligne.addWidget(etiquette, stretch=1)
        return ligne


class PanneauAjout(QWidget):
    ajout_demande = Signal(str)

    def __init__(self, collection, decks, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.decks = decks
        self.identite = None
        self.rempli = False
        self.recherche = QLineEdit()
        self.recherche.setObjectName("recherche")
        self.recherche.setPlaceholderText("Nom ou code")
        self.recherche.setClearButtonEnabled(True)
        loupe = self.recherche.addAction(icones.icone("search", 16), QLineEdit.ActionPosition.LeadingPosition)
        icones.lier(loupe, "search", 16, "TEXTE_DOUX", "TEXTE_DOUX")
        self.type = ListeChoix(TYPES_AJOUT)
        self.miennes = QCheckBox("Mes cartes")
        self.domaines = QCheckBox("Domaines du deck")
        self.domaines.setChecked(True)
        self.domaines.setToolTip("Seulement les cartes que ta légende permet")
        cases = QHBoxLayout()
        cases.setSpacing(14)
        cases.addWidget(self.miennes)
        cases.addWidget(self.domaines)
        cases.addStretch()
        self.indication = aide("Double-clic sur une carte pour l'ajouter au deck.")
        self.grille = GrilleCartes(collection)
        self.grille.largeur = LARGEUR_GRILLE
        self.grille.ajuster_colonnes()
        self.grille.carte_choisie.connect(self.ajout_demande)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.recherche)
        layout.addWidget(self.type)
        layout.addLayout(cases)
        layout.addWidget(self.indication)
        layout.addWidget(self.grille, stretch=1)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(200)
        self.minuteur.timeout.connect(self.filtrer)
        self.recherche.textChanged.connect(self.minuteur.start)
        self.type.change.connect(self.filtrer)
        self.miennes.toggled.connect(self.filtrer)
        self.domaines.toggled.connect(self.filtrer)

    def definir_legende(self, legende):
        identite = set(separer(legende["domaines"])) if legende is not None else None
        changement = identite != self.identite or not self.rempli
        self.identite = identite
        self.domaines.setEnabled(legende is not None)
        if not changement:
            return
        if legende is None:
            self.type.definir("Legend")
            self.indication.setText("Commence par la légende : elle donne les domaines du deck. Double-clic pour l'ajouter.")
        else:
            if self.type.valeur == "Legend":
                self.type.definir(None)
            self.indication.setText("Double-clic sur une carte pour l'ajouter au deck.")
        self.filtrer()

    def filtrer(self):
        texte = normaliser(self.recherche.text())
        code = self.recherche.text().strip().lower()
        genre = self.type.valeur
        cartes = []
        for carte in self.decks.cartes().values():
            if genre and carte["type"] != genre:
                continue
            if carte["type"] not in dict(TYPES_AJOUT):
                continue
            if self.miennes.isChecked() and self.collection.quantite(carte["carte_id"]) == 0:
                continue
            if (
                self.domaines.isChecked()
                and self.identite is not None
                and not set(separer(carte["domaines"])) <= self.identite
            ):
                continue
            if texte and texte not in normaliser(carte["nom"]) and code not in carte["code"]:
                continue
            cartes.append(carte)
        self.rempli = True
        self.grille.precharger(cartes)
        self.grille.afficher(cartes)


class PanneauSortir(QWidget):
    voir_demande = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        contenu = QWidget()
        self.disposition = QVBoxLayout(contenu)
        self.disposition.setContentsMargins(2, 4, 10, 10)
        self.disposition.setSpacing(2)
        self.resume = aide("")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.resume)
        layout.addWidget(defilement(contenu), stretch=1)

    def definir(self, places, hors_classeur, monte, vide):
        vider(self.disposition)
        if vide:
            self.resume.setText("Ajoute des cartes au deck pour savoir où les prendre.")
            self.disposition.addStretch()
            return
        if monte:
            self.resume.setText("Ce deck est monté : ses cartes sont signalées dans tes classeurs.")
        else:
            self.resume.setText("Les cartes du deck, dans l'ordre des pages. Clique sur une ligne pour l'ouvrir dans le classeur.")
        for classeur, lignes in places:
            premiere = lignes[0][0]
            voir = QPushButton("Voir")
            voir.setObjectName("lien")
            voir.setCursor(Qt.CursorShape.PointingHandCursor)
            voir.setToolTip("Ouvrir le classeur avec les cartes du deck en surbrillance")
            voir.clicked.connect(lambda _=False, classeur_id=classeur["id"], pochette=premiere: self.voir_demande.emit(classeur_id, pochette))
            ligne_titre = entete(classeur["nom"])
            ligne_titre.addWidget(voir)
            self.disposition.addSpacing(10)
            self.disposition.addLayout(ligne_titre)
            for pochette, carte, besoin in lignes:
                page, rangee, colonne = position(classeur, pochette)
                ligne = LigneCliquable()
                ligne.setToolTip(apercu(carte))
                ligne.clique.connect(lambda classeur_id=classeur["id"], pochette=pochette: self.voir_demande.emit(classeur_id, pochette))
                endroit = QLabel(f"p. {page} · r. {rangee} · c. {colonne}")
                endroit.setObjectName("emplacement")
                endroit.setFixedWidth(96)
                nom = QLabel(carte["nom"])
                nom.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                nombre = QLabel(f"×{besoin}")
                nombre.setObjectName("nombre_deck")
                disposition = QHBoxLayout(ligne)
                disposition.setContentsMargins(8, 5, 8, 5)
                disposition.setSpacing(8)
                disposition.addWidget(endroit)
                disposition.addWidget(nom, stretch=1)
                disposition.addWidget(nombre)
                self.disposition.addWidget(ligne)
        if hors_classeur:
            self.disposition.addSpacing(10)
            self.disposition.addLayout(entete("Pas dans un classeur"))
            for carte, besoin in hors_classeur:
                ligne = QFrame()
                ligne.setObjectName("ligne_deck")
                ligne.setToolTip(apercu(carte))
                nom = QLabel(carte["nom"])
                nom.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                nombre = QLabel(f"×{besoin}")
                nombre.setObjectName("nombre_deck")
                disposition = QHBoxLayout(ligne)
                disposition.setContentsMargins(8, 5, 8, 5)
                disposition.addWidget(nom, stretch=1)
                disposition.addWidget(nombre)
                self.disposition.addWidget(ligne)
        if not places and not hors_classeur:
            self.disposition.addWidget(aide("Aucune carte de ce deck n'est dans ta collection pour l'instant."))
        self.disposition.addStretch()


class PanneauManquantes(QWidget):
    marquer_demande = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        contenu = QWidget()
        self.disposition = QVBoxLayout(contenu)
        self.disposition.setContentsMargins(2, 4, 10, 10)
        self.disposition.setSpacing(2)
        self.resume = aide("")
        self.bouton = QPushButton("Marquer comme recherchées")
        self.bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton.setToolTip("Les cartes manquantes passent en « Recherchée » : elles apparaissent dans les échanges")
        icones.lier(self.bouton, "heart", 15, "OR_CLAIR", "OR_CLAIR")
        self.bouton.clicked.connect(self.marquer_demande)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.resume)
        layout.addWidget(defilement(contenu), stretch=1)
        layout.addWidget(self.bouton)

    def definir(self, manquantes):
        vider(self.disposition)
        total = sum(manque for _, manque, _ in manquantes)
        self.bouton.setVisible(bool(manquantes))
        if not manquantes:
            self.resume.setText("Tu as toutes les cartes de ce deck.")
            self.disposition.addStretch()
            return
        self.resume.setText(
            f"Il te manque <b>{total}</b> carte{'s' if total > 1 else ''} "
            f"({len(manquantes)} différente{'s' if len(manquantes) > 1 else ''}), toutes versions comprises."
        )
        for carte, manque, possedees in manquantes:
            ligne = QFrame()
            ligne.setObjectName("ligne_deck")
            ligne.setToolTip(apercu(carte))
            nom = QLabel(carte["nom"])
            nom.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            detail = QLabel(f"tu en as {possedees}" if possedees else "aucune")
            detail.setObjectName("aide")
            nombre = QLabel(f"−{manque}")
            nombre.setObjectName("manque_deck")
            disposition = QHBoxLayout(ligne)
            disposition.setContentsMargins(8, 5, 8, 5)
            disposition.setSpacing(8)
            disposition.addWidget(nom, stretch=1)
            disposition.addWidget(detail)
            disposition.addWidget(nombre)
            self.disposition.addWidget(ligne)
        self.disposition.addStretch()
