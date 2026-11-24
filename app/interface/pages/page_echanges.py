from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.donnees import catalogue, supabase_client
from app.interface import icones
from app.interface.composants.elements import Carte, EtatVide, Onglets, Titre

ONGLETS = ["Par joueur", "Je peux recevoir", "Je peux donner"]

TUILES = [
    ("recevoir", "cartes à recevoir"),
    ("donner", "cartes à donner"),
    ("joueurs", "joueurs"),
]

AUCUN_ECHANGE = (
    "Aucun échange possible pour l'instant",
    "Ouvre une carte et active « Recherchée » pour celles qui te manquent, puis indique "
    "combien tu en as « À l'échange » pour tes doubles. Les joueurs qui correspondent "
    "apparaîtront ici.",
    "",
    "arrow-left-right",
)


class PageEchanges(QWidget):
    def __init__(self, collection, pseudo, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.pseudo = pseudo
        self.cartes = {}
        self.chiffres = {}

        titre = Titre("Échanges")
        self.bouton_copier = QPushButton("Copier ma liste pour Discord")
        self.bouton_copier.clicked.connect(self.copier_liste)
        icones.lier(self.bouton_copier, "copy", 15, "OR_CLAIR", "OR_CLAIR")
        bouton_actualiser = QPushButton("Actualiser")
        bouton_actualiser.clicked.connect(self.actualiser)
        icones.lier(bouton_actualiser, "refresh-cw", 15, "OR_CLAIR", "OR_CLAIR")

        entete = QHBoxLayout()
        entete.addWidget(titre)
        entete.addStretch()
        entete.addWidget(self.bouton_copier)
        entete.addWidget(bouton_actualiser)

        presentation = QLabel(
            "Les joueurs qui ont les cartes que tu recherches, et ceux qui cherchent tes doubles."
        )
        presentation.setObjectName("sous_titre")

        self.champ_contact = QLineEdit()
        self.champ_contact.setPlaceholderText("Ex. Discord : ton_pseudo")
        self.champ_contact.setMaxLength(100)
        self.bouton_contact = QPushButton("Enregistrer")
        self.bouton_contact.setObjectName("principal")
        self.bouton_contact.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_contact.clicked.connect(self.enregistrer_contact)
        self.champ_contact.textEdited.connect(self.contact_modifie)

        ligne_contact = QHBoxLayout()
        ligne_contact.setSpacing(10)
        ligne_contact.addWidget(self.champ_contact, stretch=1)
        ligne_contact.addWidget(self.bouton_contact)
        aide_contact = QLabel("Il n'est montré qu'aux joueurs avec qui un échange est possible.")
        aide_contact.setObjectName("aide")

        carte_contact = Carte("Ton contact", "user-round")
        carte_contact.contenu.addLayout(ligne_contact)
        carte_contact.contenu.addWidget(aide_contact)

        ligne_haut = QHBoxLayout()
        ligne_haut.setSpacing(12)
        ligne_haut.addWidget(carte_contact, stretch=1)
        for cle, legende in TUILES:
            ligne_haut.addWidget(self.creer_tuile(cle, legende))

        self.erreur = QLabel("")
        self.erreur.setObjectName("erreur")
        self.erreur.setWordWrap(True)
        self.erreur.hide()

        self.tableau_joueurs = self.creer_tableau(
            ["Joueur", "Contact", "Il te propose", "Il te cherche", "Total"]
        )
        self.tableau_recevoir = self.creer_tableau(
            ["Joueur", "Carte", "Set", "Version", "Disponibles"]
        )
        self.tableau_donner = self.creer_tableau(
            ["Joueur", "Carte", "Set", "Version", "Tu en proposes"]
        )

        self.onglets = Onglets()
        self.pile = QStackedWidget()
        for texte, tableau in zip(ONGLETS, (self.tableau_joueurs, self.tableau_recevoir, self.tableau_donner)):
            self.onglets.addTab(texte)
            self.pile.addWidget(tableau)
        self.onglets.currentChanged.connect(self.pile.setCurrentIndex)

        self.vide = EtatVide()
        self.vide.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 24, 12)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(presentation)
        layout.addSpacing(4)
        layout.addLayout(ligne_haut)
        layout.addWidget(self.erreur)
        layout.addWidget(self.onglets)
        layout.addWidget(self.pile, stretch=1)
        layout.addWidget(self.vide, stretch=1)

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.actualiser()

    def creer_tuile(self, cle, legende):
        tuile = QFrame()
        tuile.setObjectName("tuile")
        tuile.setMinimumWidth(150)
        chiffre = QLabel("0")
        chiffre.setObjectName("chiffre")
        texte = QLabel(legende)
        texte.setObjectName("sous_titre")
        layout = QVBoxLayout(tuile)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        layout.addStretch()
        layout.addWidget(chiffre)
        layout.addWidget(texte)
        layout.addStretch()
        self.chiffres[cle] = chiffre
        return tuile

    def creer_tableau(self, entetes):
        tableau = QTableWidget(0, len(entetes))
        tableau.setHorizontalHeaderLabels(entetes)
        tableau.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tableau.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tableau.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tableau.setShowGrid(False)
        tableau.setWordWrap(False)
        tableau.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tableau.verticalHeader().hide()
        tableau.verticalHeader().setDefaultSectionSize(40)
        entete = tableau.horizontalHeader()
        entete.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        entete.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        entete.setHighlightSections(False)
        return tableau

    def remplir(self, tableau, lignes, colonne_tri, ordre):
        tableau.setSortingEnabled(False)
        tableau.setRowCount(len(lignes))
        gras = QFont(tableau.font())
        gras.setWeight(QFont.Weight.DemiBold)
        for i, valeurs in enumerate(lignes):
            for j, valeur in enumerate(valeurs):
                case = QTableWidgetItem()
                case.setData(Qt.ItemDataRole.DisplayRole, valeur)
                if j == 0:
                    case.setFont(gras)
                tableau.setItem(i, j, case)
        tableau.setSortingEnabled(True)
        tableau.sortItems(colonne_tri, ordre)

    def decrire(self, carte_id, foil):
        carte = self.cartes.get(carte_id)
        version = "Foil" if foil else "Normale"
        if carte is None:
            return [carte_id, "?", version]
        return [carte["nom"], f"{carte['set_nom']} · {catalogue.code_affiche(carte)}", version]

    def montrer_erreur(self, texte):
        self.erreur.setText(texte)
        self.erreur.setVisible(bool(texte))

    def actualiser(self):
        self.cartes = {carte["carte_id"]: carte for carte in catalogue.lister_cartes()}
        self.montrer_erreur("")
        probleme = ""
        try:
            self.champ_contact.setText(supabase_client.lire_contact())
            echanges = supabase_client.lire_echanges()
        except supabase_client.ErreurSupabase as erreur:
            probleme = str(erreur)
            echanges = []
        self.bouton_contact.setText("Enregistrer")

        recevoir = [e for e in echanges if e["sens"] == "recevoir"]
        donner = [e for e in echanges if e["sens"] == "donner"]

        self.remplir(
            self.tableau_recevoir,
            [[e["pseudo"], *self.decrire(e["carte_id"], e["foil"]), e["nombre"]] for e in recevoir],
            0,
            Qt.SortOrder.AscendingOrder,
        )
        self.remplir(
            self.tableau_donner,
            [[e["pseudo"], *self.decrire(e["carte_id"], e["foil"]), e["nombre"]] for e in donner],
            0,
            Qt.SortOrder.AscendingOrder,
        )

        joueurs = {}
        for e in echanges:
            joueur = joueurs.setdefault(
                e["pseudo"], {"contact": e["contact"] or "-", "recevoir": 0, "donner": 0}
            )
            joueur[e["sens"]] += 1
        self.remplir(
            self.tableau_joueurs,
            [
                [pseudo, j["contact"], j["recevoir"], j["donner"], j["recevoir"] + j["donner"]]
                for pseudo, j in joueurs.items()
            ],
            4,
            Qt.SortOrder.DescendingOrder,
        )

        self.chiffres["recevoir"].setText(str(len(recevoir)))
        self.chiffres["donner"].setText(str(len(donner)))
        self.chiffres["joueurs"].setText(str(len(joueurs)))
        for index, nombre in enumerate((len(joueurs), len(recevoir), len(donner))):
            self.onglets.definir_nombre(index, nombre)

        if probleme:
            self.vide.definir(
                "Impossible de charger les échanges",
                f"{probleme} Vérifie ta connexion, puis clique sur Actualiser.",
                "",
                "circle-alert",
            )
        else:
            self.vide.definir(*AUCUN_ECHANGE)
        for element in (self.onglets, self.pile):
            element.setVisible(bool(echanges))
        self.vide.setVisible(not echanges)

    def contact_modifie(self):
        self.bouton_contact.setText("Enregistrer")

    def enregistrer_contact(self):
        try:
            supabase_client.modifier_contact(
                self.collection.user_id, self.champ_contact.text().strip()
            )
        except supabase_client.ErreurSupabase as erreur:
            self.montrer_erreur(str(erreur))
            return
        self.montrer_erreur("")
        self.bouton_contact.setText("Enregistré")

    def copier_liste(self):
        if not self.cartes:
            self.cartes = {carte["carte_id"]: carte for carte in catalogue.lister_cartes()}
        ordre = {carte_id: position for position, carte_id in enumerate(self.cartes)}
        versions = sorted(
            self.collection.versions.items(),
            key=lambda element: (ordre.get(element[0][0], len(ordre)), element[0][1]),
        )

        a_echanger = []
        recherchees = []
        for (carte_id, foil), version in versions:
            nom, set_et_numero, type_version = self.decrire(carte_id, foil)
            texte = f"{nom}{' (foil)' if foil else ''} - {set_et_numero}"
            if version["a_echanger"] > 0:
                a_echanger.append(f"- {version['a_echanger']}x {texte}")
            if version["recherche"]:
                recherchees.append(f"- {texte}")

        lignes = [f"Liste d'échange Riftbound de {self.pseudo}", "", "À échanger :"]
        lignes += a_echanger or ["- rien pour l'instant"]
        lignes += ["", "Recherchées :"]
        lignes += recherchees or ["- rien pour l'instant"]

        QApplication.clipboard().setText("\n".join(lignes))
        self.bouton_copier.setText("Copié !")
        QTimer.singleShot(2000, self, self.remettre_bouton_copier)

    def remettre_bouton_copier(self):
        self.bouton_copier.setText("Copier ma liste pour Discord")
