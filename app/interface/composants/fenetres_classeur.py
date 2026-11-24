from math import ceil

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue
from app.donnees.classeurs import (
    COTE_MAX,
    FORMATS,
    NOM_MAX,
    PAGES_MAX,
    capacite,
    cartes_a_ranger,
    contenu_automatique,
    par_page,
    variantes_empilees,
)
from app.interface import icones, theme
from app.interface.composants.elements import ChampNombre, ListeChoix, Segments, Titre
from app.interface.composants.grille_cartes import ROLE_CARTE_ID, GrilleCartes

PAGES_DEFAUT = 40
LARGEUR_CHOIX = 118


def libelle(texte):
    element = QLabel(texte)
    element.setObjectName("libelle")
    return element


def aide(texte):
    element = QLabel(texte)
    element.setObjectName("aide")
    element.setWordWrap(True)
    return element


def choix_sets(cartes, premier):
    groupes = dict.fromkeys(catalogue.groupe_set(carte["set_nom"]) for carte in cartes)
    return [(None, premier)] + [(groupe, groupe) for groupe in groupes]


class FenetreDialogue(QDialog):
    def __init__(self, titre, sous_titre, texte_bouton, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setModal(True)
        self.titre = Titre(titre, "titre_connexion")
        self.sous_titre = QLabel(sous_titre)
        self.sous_titre.setObjectName("sous_titre")
        self.sous_titre.setWordWrap(True)
        self.contenu = QVBoxLayout()
        self.contenu.setSpacing(10)
        self.erreur = QLabel("")
        self.erreur.setObjectName("erreur")
        self.erreur.setWordWrap(True)
        self.erreur.hide()

        self.bouton_annuler = QPushButton("Annuler")
        self.bouton_annuler.setObjectName("discret")
        self.bouton_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_annuler.clicked.connect(self.reject)
        self.bouton_valider = QPushButton(texte_bouton)
        self.bouton_valider.setObjectName("principal")
        self.bouton_valider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_valider.setDefault(True)
        self.bouton_valider.clicked.connect(self.valider)
        boutons = QHBoxLayout()
        boutons.addStretch()
        boutons.addWidget(self.bouton_annuler)
        boutons.addWidget(self.bouton_valider)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(8)
        layout.addWidget(self.titre)
        layout.addWidget(self.sous_titre)
        layout.addSpacing(10)
        layout.addLayout(self.contenu, stretch=1)
        layout.addWidget(self.erreur)
        layout.addSpacing(8)
        layout.addLayout(boutons)

    def montrer_erreur(self, texte):
        self.erreur.setText(texte)
        self.erreur.setVisible(bool(texte))

    def valider(self):
        self.accept()


class TuileFormat(QAbstractButton):
    def __init__(self, colonnes, lignes, texte="", parent=None):
        super().__init__(parent)
        self.colonnes = colonnes
        self.lignes = lignes
        self.texte = texte
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(96, 110)

    def definir(self, colonnes, lignes):
        self.colonnes = colonnes
        self.lignes = lignes
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        choisie = self.isChecked()
        if choisie:
            bord = theme.couleur("OR")
            fond = theme.voile()
        else:
            bord = theme.couleur("TEXTE_ETEINT" if self.underMouse() else "BORDURE")
            fond = theme.couleur("SURFACE")
        peintre.setPen(QPen(bord, 1.2))
        peintre.setBrush(fond)
        peintre.drawRoundedRect(QRectF(self.rect()).adjusted(0.6, 0.6, -0.6, -0.6), 10, 10)

        page = QRectF(0, 0, 46, 60)
        page.moveCenter(QPointF(self.width() / 2, 40))
        peintre.setPen(QPen(theme.couleur("BORDURE"), 1))
        peintre.setBrush(theme.couleur("FOND"))
        peintre.drawRoundedRect(page, 4, 4)
        marge, ecart = 4, 2
        largeur = (page.width() - 2 * marge - (self.colonnes - 1) * ecart) / self.colonnes
        hauteur = (page.height() - 2 * marge - (self.lignes - 1) * ecart) / self.lignes
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(theme.couleur("OR" if choisie else "TEXTE_ETEINT", 230 if choisie else 140))
        for ligne in range(self.lignes):
            for colonne in range(self.colonnes):
                peintre.drawRoundedRect(
                    QRectF(
                        page.left() + marge + colonne * (largeur + ecart),
                        page.top() + marge + ligne * (hauteur + ecart),
                        largeur,
                        hauteur,
                    ),
                    1.5,
                    1.5,
                )

        police = QFont(self.font())
        police.setPixelSize(12)
        police.setWeight(QFont.Weight.DemiBold if choisie else QFont.Weight.Medium)
        peintre.setFont(police)
        peintre.setPen(theme.couleur("OR_CLAIR" if choisie else "TEXTE_DOUX"))
        texte = self.texte or f"{self.colonnes * self.lignes} pochettes"
        peintre.drawText(QRectF(0, 76, self.width(), 16), Qt.AlignmentFlag.AlignHCenter, texte)
        police.setPixelSize(11)
        police.setWeight(QFont.Weight.Normal)
        peintre.setFont(police)
        peintre.setPen(theme.couleur("TEXTE_ETEINT"))
        peintre.drawText(QRectF(0, 91, self.width(), 14), Qt.AlignmentFlag.AlignHCenter, f"{self.colonnes} × {self.lignes}")


class PastilleCouleur(QAbstractButton):
    def __init__(self, valeur, texte, couleur, parent=None):
        super().__init__(parent)
        self.valeur = valeur
        self.couleur = QColor(couleur)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(texte)
        self.setFixedSize(34, 34)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        centre = QPointF(self.width() / 2, self.height() / 2)
        if self.isChecked():
            peintre.setPen(QPen(theme.couleur("OR"), 2))
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            peintre.drawEllipse(centre, 15, 15)
        elif self.underMouse():
            peintre.setPen(QPen(theme.couleur("TEXTE_ETEINT"), 1.5))
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            peintre.drawEllipse(centre, 15, 15)
        peintre.setPen(QPen(self.couleur.darker(150), 1))
        peintre.setBrush(self.couleur)
        peintre.drawEllipse(centre, 11, 11)


class FenetreClasseur(FenetreDialogue):
    def __init__(self, classeur=None, minimum=0, parent=None):
        modification = classeur is not None
        super().__init__(
            "Modifier le classeur" if modification else "Nouveau classeur",
            "Choisis le même format que ton vrai classeur : pochettes par page et nombre de cartes.",
            "Enregistrer" if modification else "Créer le classeur",
            parent,
        )
        self.minimum = minimum
        self.pages_voulues = classeur["pages"] if modification else PAGES_DEFAUT

        self.nom = QLineEdit()
        self.nom.setPlaceholderText("Ex. Origins, Decks Fury…")
        self.nom.setMaxLength(NOM_MAX)

        self.groupe_formats = QButtonGroup(self)
        self.groupe_formats.setExclusive(True)
        self.tuiles = []
        ligne_formats = QHBoxLayout()
        ligne_formats.setSpacing(10)
        for colonnes, lignes in FORMATS:
            tuile = TuileFormat(colonnes, lignes)
            self.groupe_formats.addButton(tuile)
            self.tuiles.append(tuile)
            ligne_formats.addWidget(tuile)
        self.tuile_autre = TuileFormat(3, 4, "Autre")
        self.groupe_formats.addButton(self.tuile_autre)
        ligne_formats.addWidget(self.tuile_autre)
        ligne_formats.addStretch()

        self.colonnes = ChampNombre(1, COTE_MAX)
        self.lignes = ChampNombre(1, COTE_MAX)
        self.autre = QWidget()
        ligne_autre = QHBoxLayout(self.autre)
        ligne_autre.setContentsMargins(0, 2, 0, 0)
        ligne_autre.setSpacing(10)
        ligne_autre.addWidget(QLabel("Colonnes"))
        ligne_autre.addWidget(self.colonnes)
        ligne_autre.addSpacing(16)
        ligne_autre.addWidget(QLabel("Rangées"))
        ligne_autre.addWidget(self.lignes)
        ligne_autre.addStretch()

        self.capacite = ChampNombre(1, PAGES_MAX * 9, 18, "cartes")
        self.detail = aide("")
        ligne_capacite = QHBoxLayout()
        ligne_capacite.setSpacing(14)
        ligne_capacite.addWidget(self.capacite)
        ligne_capacite.addWidget(self.detail, stretch=1)

        self.groupe_couleurs = QButtonGroup(self)
        self.groupe_couleurs.setExclusive(True)
        self.pastilles = {}
        ligne_couleurs = QHBoxLayout()
        ligne_couleurs.setSpacing(4)
        for valeur, texte, couleur in theme.COUVERTURES:
            pastille = PastilleCouleur(valeur, texte, couleur)
            self.groupe_couleurs.addButton(pastille)
            self.pastilles[valeur] = pastille
            ligne_couleurs.addWidget(pastille)
        ligne_couleurs.addStretch()

        self.contenu.addWidget(libelle("Nom"))
        self.contenu.addWidget(self.nom)
        self.contenu.addSpacing(8)
        self.contenu.addWidget(libelle("Pochettes par page"))
        self.contenu.addLayout(ligne_formats)
        self.contenu.addWidget(self.autre)
        self.contenu.addSpacing(8)
        self.contenu.addWidget(libelle("Capacité"))
        self.contenu.addLayout(ligne_capacite)
        self.contenu.addSpacing(8)
        self.contenu.addWidget(libelle("Couleur"))
        self.contenu.addLayout(ligne_couleurs)
        if modification and minimum:
            self.contenu.addSpacing(4)
            self.contenu.addWidget(aide(
                "Si tu changes le format, les cartes gardent leur ordre et se répartissent sur les nouvelles pages."
            ))

        if modification:
            self.nom.setText(classeur["nom"])
            format_actuel = (classeur["colonnes"], classeur["lignes"])
            if format_actuel in FORMATS:
                self.tuiles[FORMATS.index(format_actuel)].setChecked(True)
            else:
                self.tuile_autre.setChecked(True)
            self.colonnes.definir(classeur["colonnes"])
            self.lignes.definir(classeur["lignes"])
            self.pastilles.get(classeur["couleur"], self.pastilles[theme.COUVERTURES[0][0]]).setChecked(True)
        else:
            self.tuiles[FORMATS.index((3, 3))].setChecked(True)
            self.colonnes.definir(3)
            self.lignes.definir(4)
            self.pastilles[theme.COUVERTURES[0][0]].setChecked(True)

        self.groupe_formats.buttonClicked.connect(self.format_change)
        self.colonnes.change.connect(self.format_change)
        self.lignes.change.connect(self.format_change)
        self.capacite.change.connect(self.capacite_changee)
        self.format_change()
        self.setMinimumWidth(600)
        self.nom.setFocus()

    def format(self):
        if self.tuile_autre.isChecked():
            return self.colonnes.valeur(), self.lignes.valeur()
        for tuile in self.tuiles:
            if tuile.isChecked():
                return tuile.colonnes, tuile.lignes
        return FORMATS[1]

    def format_change(self, *arguments):
        self.autre.setVisible(self.tuile_autre.isChecked())
        self.tuile_autre.definir(self.colonnes.valeur(), self.lignes.valeur())
        colonnes, lignes = self.format()
        nombre = colonnes * lignes
        minimum = max(nombre, ceil(self.minimum / nombre) * nombre)
        self.capacite.blockSignals(True)
        self.capacite.definir_limites(minimum, PAGES_MAX * nombre, 2 * nombre)
        self.capacite.definir(max(minimum, self.pages_voulues * nombre))
        self.capacite.blockSignals(False)
        self.afficher_detail()

    def capacite_changee(self, valeur):
        colonnes, lignes = self.format()
        self.pages_voulues = ceil(valeur / (colonnes * lignes))
        self.afficher_detail()

    def pages(self):
        colonnes, lignes = self.format()
        return max(1, ceil(self.capacite.valeur() / (colonnes * lignes)))

    def afficher_detail(self):
        colonnes, lignes = self.format()
        pages = self.pages()
        feuilles = ceil(pages / 2)
        texte = f"{pages} pages, soit {feuilles} feuille{'s' if feuilles > 1 else ''} recto verso"
        if pages * colonnes * lignes != self.capacite.valeur():
            texte += f" ({pages * colonnes * lignes} pochettes)"
        if self.minimum:
            texte += f". Déjà {self.minimum} pochettes utilisées."
        self.detail.setText(texte)

    def couleur(self):
        for valeur, pastille in self.pastilles.items():
            if pastille.isChecked():
                return valeur
        return theme.COUVERTURES[0][0]

    def resultat(self):
        colonnes, lignes = self.format()
        return {
            "nom": self.nom.text().strip(),
            "colonnes": colonnes,
            "lignes": lignes,
            "pages": self.pages(),
            "couleur": self.couleur(),
        }

    def valider(self):
        if not self.nom.text().strip():
            self.montrer_erreur("Donne un nom au classeur.")
            self.nom.setFocus()
            return
        self.accept()


class FenetreRemplir(FenetreDialogue):
    def __init__(self, collection, classeurs, classeur, parent=None):
        super().__init__(
            "Remplir le classeur",
            "Les cartes sont rangées dans l'ordre du catalogue : set, puis numéro. "
            "Tu pourras ensuite les déplacer à la main.",
            "Remplir",
            parent,
        )
        self.collection = collection
        self.classeurs = classeurs
        self.classeur = classeur
        self.cartes = catalogue.lister_cartes()
        self.deja = len(classeurs.contenu(classeur["id"]))

        self.set = ListeChoix(choix_sets(self.cartes, "Tous les sets"))
        self.domaine = ListeChoix([(None, "Tous les domaines")] + [(nom, nom) for nom, _ in theme.DOMAINES])
        ligne_choix = QHBoxLayout()
        ligne_choix.setSpacing(10)
        ligne_choix.addWidget(self.set, stretch=1)
        ligne_choix.addWidget(self.domaine, stretch=1)

        self.miennes = QCheckBox("Seulement les cartes que j'ai")
        self.miennes.setChecked(True)
        aide_miennes = aide("Décoche pour garder aussi une pochette, vide, à chaque carte qui te manque.")
        aide_miennes.setContentsMargins(26, 0, 0, 0)
        self.surnumerotees = QCheckBox("Inclure les cartes surnumérotées (ex. OGN 299 / 298)")
        self.surnumerotees.setChecked(True)

        self.variantes = Segments([("pile", "Avec la carte de base"), ("a_part", "Dans leur propre pochette")])
        ligne_variantes = QHBoxLayout()
        ligne_variantes.addWidget(self.variantes)
        ligne_variantes.addStretch()
        aide_variantes = aide("Exemple : OGN 030a et OGN 030b vont dans la même pochette que OGN 030.")

        self.foils = Segments([("ensemble", "Avec les normales"), ("a_part", "Dans une pochette à part")])
        ligne_foils = QHBoxLayout()
        ligne_foils.addWidget(self.foils)
        ligne_foils.addStretch()

        self.placement = Segments([("suite", "À la suite des cartes rangées"), ("remplacer", "Tout remplacer")])
        ligne_placement = QHBoxLayout()
        ligne_placement.addWidget(self.placement)
        ligne_placement.addStretch()

        self.resume = QLabel("")
        self.resume.setWordWrap(True)
        self.resume.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.resume.setMinimumHeight(self.resume.fontMetrics().lineSpacing() * 5 + 6)
        cadre_resume = QFrame()
        cadre_resume.setObjectName("resume_remplir")
        disposition_resume = QVBoxLayout(cadre_resume)
        disposition_resume.setContentsMargins(14, 10, 14, 10)
        disposition_resume.addWidget(self.resume)

        self.contenu.addWidget(libelle("Cartes à ranger"))
        self.contenu.addLayout(ligne_choix)
        self.contenu.addSpacing(2)
        self.contenu.addWidget(self.miennes)
        self.contenu.addWidget(aide_miennes)
        self.contenu.addWidget(self.surnumerotees)
        self.contenu.addSpacing(8)
        self.contenu.addWidget(libelle("Variantes (arts alternatifs, signatures)"))
        self.contenu.addLayout(ligne_variantes)
        self.contenu.addWidget(aide_variantes)
        self.contenu.addSpacing(8)
        self.contenu.addWidget(libelle("Foils"))
        self.contenu.addLayout(ligne_foils)
        if self.deja:
            self.contenu.addSpacing(8)
            self.contenu.addWidget(libelle("Où les mettre"))
            self.contenu.addLayout(ligne_placement)
        self.contenu.addSpacing(10)
        self.contenu.addWidget(cadre_resume)

        for element in (self.set, self.domaine, self.variantes, self.foils, self.placement):
            element.change.connect(self.actualiser)
        self.miennes.toggled.connect(self.actualiser)
        self.surnumerotees.toggled.connect(self.actualiser)
        self.setMinimumWidth(620)
        self.actualiser()

    def remplacer(self):
        return not self.deja or self.placement.valeur() == "remplacer"

    def depart(self):
        return 0 if self.remplacer() else self.classeurs.derniere(self.classeur["id"]) + 1

    def calculer(self):
        cartes = cartes_a_ranger(self.cartes, self.set.valeur, self.domaine.valeur, self.surnumerotees.isChecked())
        membres = self.classeurs.groupes() if self.variantes.valeur() == "pile" else {}
        elements = contenu_automatique(
            cartes, self.collection, not self.miennes.isChecked(), self.foils.valeur() == "a_part", membres
        )
        deja = 0
        if not self.remplacer():
            if membres:
                rangees = self.classeurs.cartes_du_classeur(self.classeur["id"])
            else:
                rangees = {element["carte_id"] for element in self.classeurs.contenu(self.classeur["id"]).values()}
            restants = [element for element in elements if element[0] not in rangees]
            deja = len({carte_id for carte_id, _ in elements}) - len({carte_id for carte_id, _ in restants})
            elements = restants
        empilees = variantes_empilees(cartes, self.collection, membres, {carte_id for carte_id, _ in elements})
        return elements, deja, empilees

    def elements(self):
        return self.calculer()[0]

    def actualiser(self):
        elements, deja, empilees = self.calculer()
        nombre = len(elements)
        depart = self.depart()
        places = max(0, capacite(self.classeur) - depart)
        self.bouton_valider.setEnabled(nombre > 0 and places > 0)
        if nombre == 0:
            if deja:
                self.resume.setText("Toutes ces cartes sont déjà rangées dans ce classeur.")
            else:
                self.resume.setText("Aucune carte ne correspond à ces choix.")
            return
        rangees = min(nombre, places)
        lignes = []
        if rangees:
            premiere = depart // par_page(self.classeur) + 1
            derniere = (depart + rangees - 1) // par_page(self.classeur) + 1
            pages = f"page {premiere}" if premiere == derniere else f"pages {premiere} à {derniere}"
            lignes.append(f"<b>{nombre}</b> pochette{'s' if nombre > 1 else ''} à remplir : {pages}.")
        if empilees:
            pluriel = "s" if empilees > 1 else ""
            lignes.append(f"{empilees} variante{pluriel} rangée{pluriel} avec leur carte de base.")
        if deja:
            pluriel = "s" if deja > 1 else ""
            lignes.append(f"{deja} carte{pluriel} déjà dans ce classeur : pas ajoutée{pluriel} une deuxième fois.")
        if nombre > places:
            manque = nombre - places
            lignes.append(
                f'<span style="color:{theme.ROUGE}">Il manque {manque} pochette{"s" if manque > 1 else ""} : '
                "les dernières cartes ne seront pas rangées. Agrandis le classeur avec « Modifier ».</span>"
            )
        if self.deja and self.remplacer():
            lignes.append(
                f"Les {self.deja} pochettes déjà remplies seront vidées (ta collection ne change pas)."
            )
        self.resume.setText("<br>".join(lignes))


class FenetreChoixCarte(FenetreDialogue):
    def __init__(self, collection, sous_titre, parent=None):
        super().__init__("Choisir une carte", sous_titre, "Placer la carte", parent)
        self.collection = collection
        self.cartes = catalogue.lister_cartes()
        self.carte_id = None

        self.recherche = QLineEdit()
        self.recherche.setObjectName("recherche")
        self.recherche.setPlaceholderText("Rechercher une carte (nom ou code)")
        self.recherche.setClearButtonEnabled(True)
        loupe = self.recherche.addAction(QIcon(), QLineEdit.ActionPosition.LeadingPosition)
        icones.lier(loupe, "search", 16, "TEXTE_DOUX", "TEXTE_DOUX")
        self.set = ListeChoix(choix_sets(self.cartes, "Tous les sets"))
        self.set.setMinimumWidth(180)
        self.miennes = QCheckBox("Seulement mes cartes")
        self.miennes.setChecked(True)
        self.nombre = aide("")
        self.nombre.setWordWrap(False)
        ligne = QHBoxLayout()
        ligne.setSpacing(10)
        ligne.addWidget(self.recherche, stretch=1)
        ligne.addWidget(self.set)
        ligne.addSpacing(6)
        ligne.addWidget(self.miennes)
        ligne.addSpacing(6)
        ligne.addWidget(self.nombre)

        self.grille = GrilleCartes(collection)
        self.grille.largeur = LARGEUR_CHOIX
        self.grille.ajuster_colonnes()
        self.grille.currentItemChanged.connect(self.selection_changee)
        self.grille.carte_choisie.connect(self.choisir)

        self.contenu.addLayout(ligne)
        self.contenu.addWidget(self.grille, stretch=1)

        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(200)
        self.minuteur.timeout.connect(self.filtrer)
        self.recherche.textChanged.connect(self.minuteur.start)
        self.set.change.connect(self.filtrer)
        self.miennes.toggled.connect(self.filtrer)

        self.bouton_valider.setEnabled(False)
        self.resize(980, 700)
        self.filtrer()
        self.recherche.setFocus()

    def filtrer(self):
        texte = self.recherche.text().strip().lower()
        groupe = self.set.valeur
        cartes = []
        for carte in self.cartes:
            if groupe and catalogue.groupe_set(carte["set_nom"]) != groupe:
                continue
            if self.miennes.isChecked() and self.collection.quantite(carte["carte_id"]) == 0:
                continue
            if texte and texte not in carte["nom"].lower() and texte not in carte["code"].lower():
                continue
            cartes.append(carte)
        self.grille.precharger(cartes)
        self.grille.afficher(cartes)
        self.nombre.setText(f"{len(cartes)} carte{'s' if len(cartes) > 1 else ''}")
        self.selection_changee()

    def selection_changee(self, *arguments):
        element = self.grille.currentItem()
        self.bouton_valider.setEnabled(element is not None and element.isSelected())

    def choisir(self, carte_id):
        self.carte_id = carte_id
        self.accept()

    def valider(self):
        element = self.grille.currentItem()
        if element is not None:
            self.choisir(element.data(ROLE_CARTE_ID))

    def sizeHint(self):
        return QSize(980, 700)
