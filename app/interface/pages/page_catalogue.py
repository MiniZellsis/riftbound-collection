from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from app.donnees import catalogue
from app.interface import theme
from app.interface.composants.barre_filtres import BarreFiltres
from app.interface.composants.elements import Onglets, Titre
from app.interface.composants.grille_cartes import ReglageTaille
from app.interface.composants.zone_cartes import ZoneCartes

class PageCatalogue(QWidget):
    set_affiche = Signal(list)

    def __init__(self, collection, classeurs=None, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.sets = {}

        self.onglets = Onglets()
        self.zone = ZoneCartes(collection, classeurs)
        self.grille = self.zone.grille
        self.reglage = ReglageTaille(self.grille)

        entete = QHBoxLayout()
        entete.addWidget(Titre("Catalogue"))
        entete.addStretch()
        entete.addWidget(self.reglage)

        self.texte_progression = QLabel("")
        self.texte_progression.setObjectName("sous_titre")
        self.barre_progression = QProgressBar()
        self.barre_progression.setObjectName("fine")
        self.barre_progression.setTextVisible(False)
        self.barre_progression.setMinimumWidth(160)
        self.pourcentage = QLabel("")
        self.pourcentage.setObjectName("pourcentage")

        ligne_progression = QHBoxLayout()
        ligne_progression.setSpacing(14)
        ligne_progression.addWidget(self.texte_progression)
        ligne_progression.addWidget(self.barre_progression, stretch=1)
        ligne_progression.addWidget(self.pourcentage)

        self.barre_filtres = BarreFiltres()
        self.compteur = QLabel("")
        self.compteur.setObjectName("aide")
        ligne_filtres = QHBoxLayout()
        ligne_filtres.setSpacing(12)
        ligne_filtres.addWidget(self.barre_filtres, stretch=1)
        ligne_filtres.addWidget(self.compteur)

        self.haut = QWidget()
        layout_haut = QVBoxLayout(self.haut)
        layout_haut.setContentsMargins(0, 2, 0, 4)
        layout_haut.setSpacing(16)
        layout_haut.addLayout(ligne_progression)
        layout_haut.addLayout(ligne_filtres)
        self.haut.hide()
        self.zone.afficher([], ("Chargement du catalogue…", "", "", "library-big"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 24, 12)
        layout.setSpacing(12)
        layout.addLayout(entete)
        layout.addWidget(self.onglets)
        layout.addWidget(self.haut)
        layout.addWidget(self.zone, stretch=1)

        self.onglets.currentChanged.connect(self.changer_set)
        self.barre_filtres.filtres_changes.connect(self.afficher_cartes)
        self.zone.collection_modifiee.connect(self.actualiser_progression)
        self.zone.etat_vide.action.connect(self.barre_filtres.effacer)
        theme.signaux().change.connect(self.actualiser_progression)

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.reglage.synchroniser()
            self.actualiser_progression()

    def charger(self):
        self.sets = {}
        for carte in catalogue.lister_cartes():
            self.sets.setdefault(catalogue.groupe_set(carte["set_nom"]), []).append(carte)

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
        for index in range(self.onglets.count()):
            nom = self.onglets.tabData(index)
            nombre = sum(1 for carte in self.sets[nom] if self.correspond(carte, filtres))
            self.onglets.definir_nombre(index, nombre)

        cartes = [carte for carte in self.cartes_du_set() if self.correspond(carte, filtres)]
        self.compteur.setText(f"{len(cartes)} carte{'s' if len(cartes) > 1 else ''}")
        self.actualiser_progression()

        if not self.sets:
            vide = ("Le catalogue est vide", "Mets-le à jour depuis la page Réglages.", "", "library-big")
        else:
            vide = (
                "Aucune carte ne correspond à tes filtres",
                "Le nombre à côté du nom de chaque set montre où il y en a.",
                "Effacer les filtres",
                "search",
            )
        self.zone.afficher(cartes, vide)
        self.haut.setVisible(bool(self.sets))

    def actualiser_progression(self):
        cartes = self.cartes_du_set()
        possedees = sum(1 for carte in cartes if self.collection.quantite(carte["carte_id"]) > 0)
        de_base = [carte for carte in cartes if catalogue.est_de_base(carte["code"])]
        base_possedees = sum(1 for carte in de_base if self.collection.quantite(carte["carte_id"]) > 0)

        fort = f"color: {theme.TEXTE}; font-weight: 600"
        separateur = f'<span style="color: {theme.TEXTE_ETEINT}">&nbsp;&nbsp;·&nbsp;&nbsp;</span>'
        if self.nom_set() == catalogue.NOM_PROMOS or not de_base:
            texte = f'<span style="{fort}">{possedees} / {len(cartes)}</span> cartes possédées'
            valeur, total = possedees, len(cartes)
        else:
            texte = (
                f'<span style="{fort}">{base_possedees} / {len(de_base)}</span> cartes de base'
                f"{separateur}{possedees} / {len(cartes)} avec les variantes"
            )
            valeur, total = base_possedees, len(de_base)
        self.texte_progression.setText(texte)
        self.barre_progression.setRange(0, max(total, 1))
        self.barre_progression.setValue(valeur)
        self.pourcentage.setText(f"{round(100 * valeur / total) if total else 0} %")
