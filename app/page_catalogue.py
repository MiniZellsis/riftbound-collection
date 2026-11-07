from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QTabBar, QVBoxLayout, QWidget

from app import catalogue
from app.barre_filtres import BarreFiltres
from app.grille_cartes import ReglageTaille
from app.zone_cartes import ZoneCartes

NOM_PROMOS = "Promos"


class PageCatalogue(QWidget):
    set_affiche = Signal(list)

    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.sets = {}

        self.onglets = QTabBar()
        self.onglets.setDrawBase(False)
        self.onglets.setExpanding(False)
        self.zone = ZoneCartes(collection)
        self.grille = self.zone.grille
        self.reglage = ReglageTaille(self.grille)

        entete = QHBoxLayout()
        entete.addWidget(self.onglets)
        entete.addStretch()
        entete.addWidget(self.reglage)

        self.texte_progression = QLabel("")
        self.barre_progression = QProgressBar()
        self.barre_progression.setObjectName("fine")
        self.barre_progression.setTextVisible(False)
        self.barre_progression.setFixedWidth(200)
        self.compteur = QLabel("")
        self.compteur.setObjectName("sous_titre")

        ligne_progression = QHBoxLayout()
        ligne_progression.addWidget(self.texte_progression)
        ligne_progression.addSpacing(10)
        ligne_progression.addWidget(self.barre_progression)
        ligne_progression.addStretch()
        ligne_progression.addWidget(self.compteur)

        self.barre_filtres = BarreFiltres()

        self.haut = QWidget()
        layout_haut = QVBoxLayout(self.haut)
        layout_haut.setContentsMargins(0, 0, 0, 0)
        layout_haut.setSpacing(14)
        layout_haut.addLayout(ligne_progression)
        layout_haut.addWidget(self.barre_filtres)
        self.haut.hide()
        self.zone.afficher([], "Chargement du catalogue...")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 12)
        layout.setSpacing(10)
        layout.addLayout(entete)
        layout.addWidget(self.haut)
        layout.addWidget(self.zone, stretch=1)

        self.onglets.currentChanged.connect(self.changer_set)
        self.barre_filtres.filtres_changes.connect(self.afficher_cartes)
        self.zone.collection_modifiee.connect(self.actualiser_progression)

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.reglage.synchroniser()
            self.actualiser_progression()

    def charger(self):
        self.sets = {}
        for carte in catalogue.lister_cartes():
            if "Promotional" in (carte["set_nom"] or ""):
                nom = NOM_PROMOS
            else:
                nom = carte["set_nom"]
            self.sets.setdefault(nom, []).append(carte)

        dernier = QSettings().value("set_choisi", "")
        self.onglets.blockSignals(True)
        while self.onglets.count():
            self.onglets.removeTab(0)
        for nom in self.sets:
            index = self.onglets.addTab(nom)
            self.onglets.setTabData(index, nom)
            if nom == dernier:
                self.onglets.setCurrentIndex(index)
        self.onglets.blockSignals(False)
        self.changer_set()

    def nom_set(self):
        return self.onglets.tabData(self.onglets.currentIndex())

    def cartes_du_set(self):
        return self.sets.get(self.nom_set(), [])

    def changer_set(self):
        if self.nom_set():
            QSettings().setValue("set_choisi", self.nom_set())
        cartes = self.cartes_du_set()
        self.grille.precharger(cartes)
        self.set_affiche.emit(cartes)
        self.afficher_cartes()

    def correspond(self, carte, filtres):
        texte = filtres["texte"]
        if texte and texte not in carte["nom"].lower() and texte not in carte["code"].lower():
            return False
        if filtres["raretes"] and carte["rarete"] not in filtres["raretes"]:
            return False
        if filtres["types"] and carte["type"] not in filtres["types"]:
            return False
        domaines = carte["domaines"].split(", ")
        if filtres["domaines"] and not any(d in filtres["domaines"] for d in domaines):
            return False
        statuts = filtres["statuts"]
        if statuts and not any(self.collection.correspond(carte["carte_id"], s) for s in statuts):
            return False
        return True

    def afficher_cartes(self):
        filtres = self.barre_filtres.filtres()
        actifs = self.barre_filtres.actifs()
        for index in range(self.onglets.count()):
            nom = self.onglets.tabData(index)
            if actifs:
                nombre = sum(1 for carte in self.sets[nom] if self.correspond(carte, filtres))
                self.onglets.setTabText(index, f"{nom} ({nombre})")
            else:
                self.onglets.setTabText(index, nom)

        cartes = [carte for carte in self.cartes_du_set() if self.correspond(carte, filtres)]
        self.compteur.setText(f"{len(cartes)} carte(s) affichée(s)")
        self.actualiser_progression()

        if not self.sets:
            message = "Le catalogue est vide. Mets-le à jour depuis la page Réglages."
        else:
            message = (
                "Aucune carte de ce set ne correspond à tes filtres.\n"
                "Les nombres entre parenthèses, dans les onglets, montrent où en trouver."
            )
        self.zone.afficher(cartes, message)
        self.haut.setVisible(bool(self.sets))

    def actualiser_progression(self):
        cartes = self.cartes_du_set()
        possedees = sum(1 for carte in cartes if self.collection.quantite(carte["carte_id"]) > 0)
        de_base = [carte for carte in cartes if catalogue.est_de_base(carte["code"])]
        base_possedees = sum(1 for carte in de_base if self.collection.quantite(carte["carte_id"]) > 0)

        if self.nom_set() == NOM_PROMOS or not de_base:
            self.texte_progression.setText(f"{possedees} / {len(cartes)} cartes possédées")
            self.barre_progression.setRange(0, max(len(cartes), 1))
            self.barre_progression.setValue(possedees)
        else:
            self.texte_progression.setText(
                f"{base_possedees} / {len(de_base)} cartes de base  ·  "
                f"{possedees} / {len(cartes)} avec les variantes"
            )
            self.barre_progression.setRange(0, len(de_base))
            self.barre_progression.setValue(base_possedees)
