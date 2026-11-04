from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from app import catalogue, supabase_client


class FenetreEchanges(QDialog):
    def __init__(self, collection, pseudo, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.pseudo = pseudo
        self.cartes = {carte["carte_id"]: carte for carte in catalogue.lister_cartes()}
        self.setWindowTitle("Échanges")
        self.resize(900, 550)

        self.champ_contact = QLineEdit()
        self.champ_contact.setPlaceholderText("Ex. Discord : ton_pseudo")
        self.champ_contact.setMaxLength(100)
        self.bouton_contact = QPushButton("Enregistrer")
        self.bouton_contact.clicked.connect(self.enregistrer_contact)
        self.champ_contact.textEdited.connect(self.contact_modifie)

        ligne_contact = QHBoxLayout()
        ligne_contact.addWidget(QLabel("Ton contact :"))
        ligne_contact.addWidget(self.champ_contact, stretch=1)
        ligne_contact.addWidget(self.bouton_contact)

        aide_contact = QLabel("Il n'est montré qu'aux joueurs avec qui un échange est possible.")
        self.resume = QLabel("")
        self.resume.setWordWrap(True)
        self.erreur = QLabel("")
        self.erreur.setObjectName("erreur")
        self.erreur.setWordWrap(True)

        self.tableau_joueurs = self.creer_tableau(
            ["Joueur", "Contact", "Il te propose", "Il te cherche", "Total"]
        )
        self.tableau_recevoir = self.creer_tableau(
            ["Joueur", "Carte", "Set", "Version", "Disponibles"]
        )
        self.tableau_donner = self.creer_tableau(
            ["Joueur", "Carte", "Set", "Version", "Tu en proposes"]
        )

        onglets = QTabWidget()
        onglets.addTab(self.tableau_joueurs, "Par joueur")
        onglets.addTab(self.tableau_recevoir, "Je peux recevoir")
        onglets.addTab(self.tableau_donner, "Je peux donner")

        self.bouton_copier = QPushButton("Copier ma liste pour Discord")
        self.bouton_copier.clicked.connect(self.copier_liste)
        bouton_actualiser = QPushButton("Actualiser")
        bouton_actualiser.clicked.connect(self.charger)
        bouton_fermer = QPushButton("Fermer")
        bouton_fermer.clicked.connect(self.accept)

        ligne_boutons = QHBoxLayout()
        ligne_boutons.addWidget(self.bouton_copier)
        ligne_boutons.addStretch()
        ligne_boutons.addWidget(bouton_actualiser)
        ligne_boutons.addWidget(bouton_fermer)

        layout = QVBoxLayout(self)
        layout.addLayout(ligne_contact)
        layout.addWidget(aide_contact)
        layout.addSpacing(10)
        layout.addWidget(self.resume)
        layout.addWidget(self.erreur)
        layout.addWidget(onglets)
        layout.addLayout(ligne_boutons)

        self.charger()

    def creer_tableau(self, entetes):
        tableau = QTableWidget(0, len(entetes))
        tableau.setHorizontalHeaderLabels(entetes)
        tableau.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tableau.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tableau.verticalHeader().hide()
        tableau.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return tableau

    def remplir(self, tableau, lignes, colonne_tri, ordre):
        tableau.setSortingEnabled(False)
        tableau.setRowCount(len(lignes))
        for i, valeurs in enumerate(lignes):
            for j, valeur in enumerate(valeurs):
                case = QTableWidgetItem()
                case.setData(Qt.ItemDataRole.DisplayRole, valeur)
                tableau.setItem(i, j, case)
        tableau.setSortingEnabled(True)
        tableau.sortItems(colonne_tri, ordre)

    def decrire(self, carte_id, foil):
        carte = self.cartes.get(carte_id)
        version = "Foil" if foil else "Normale"
        if carte is None:
            return [carte_id, "?", version]
        return [carte["nom"], f"{carte['set_nom']} n°{carte['numero']}", version]

    def charger(self):
        self.erreur.setText("")
        try:
            self.champ_contact.setText(supabase_client.lire_contact())
            echanges = supabase_client.lire_echanges()
        except supabase_client.ErreurSupabase as erreur:
            self.erreur.setText(str(erreur))
            echanges = []

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

        if echanges:
            self.resume.setText(
                f"{len(recevoir)} carte(s) à recevoir et {len(donner)} à donner, "
                f"avec {len(joueurs)} joueur(s)."
            )
        else:
            self.resume.setText(
                "Aucun échange possible pour l'instant. Dans la fenêtre d'une carte, coche "
                "« Recherchée » pour celles qui te manquent et indique combien tu en as "
                "« À échanger » pour tes doubles."
            )

    def contact_modifie(self):
        self.bouton_contact.setText("Enregistrer")

    def enregistrer_contact(self):
        try:
            supabase_client.modifier_contact(
                self.collection.user_id, self.champ_contact.text().strip()
            )
        except supabase_client.ErreurSupabase as erreur:
            self.erreur.setText(str(erreur))
            return
        self.erreur.setText("")
        self.bouton_contact.setText("Enregistré")

    def copier_liste(self):
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