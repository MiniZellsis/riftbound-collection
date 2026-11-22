import uuid

from PySide6.QtCore import Signal

from app.donnees import catalogue, supabase_client
from app.donnees.synchronisation import Synchronisation

FORMATS = [(2, 2), (3, 3), (4, 3), (4, 4)]
COTE_MAX = 6
PAGES_MAX = 400
NOM_MAX = 40
MESSAGE_TABLES = (
    "Le serveur n'a pas encore les tables des classeurs. Lance une fois le script "
    "supabase/3_classeurs.sql dans Supabase (SQL Editor), puis redémarre l'appli."
)


def par_page(classeur):
    return classeur["colonnes"] * classeur["lignes"]


def capacite(classeur):
    return par_page(classeur) * classeur["pages"]


def position(classeur, pochette):
    page, reste = divmod(pochette, par_page(classeur))
    ligne, colonne = divmod(reste, classeur["colonnes"])
    return page + 1, ligne + 1, colonne + 1


def decrire_position(classeur, pochette):
    page, ligne, colonne = position(classeur, pochette)
    return f"page {page}, rangée {ligne}, colonne {colonne}"


def quantites(collection, carte_id, version):
    normales = collection.version(carte_id, False)["quantite"]
    foils = collection.version(carte_id, True)["quantite"]
    if version == "normale":
        return normales, False
    if version == "foil":
        return foils, foils > 0
    return normales + foils, foils > 0


def cartes_a_ranger(cartes, groupe, domaine, avec_surnumerotees):
    resultat = []
    for carte in cartes:
        nom_groupe = catalogue.groupe_set(carte["set_nom"])
        if groupe and nom_groupe != groupe:
            continue
        if domaine and domaine not in (carte["domaines"] or "").split(", "):
            continue
        if (
            not avec_surnumerotees
            and nom_groupe != catalogue.NOM_PROMOS
            and catalogue.est_surnumerotee(carte["code"])
        ):
            continue
        resultat.append(carte)
    return resultat


def contenu_automatique(cartes, collection, avec_manquantes, foils_a_part, membres=None):
    membres = membres or {}
    contenu = []
    vues = set()
    for carte in cartes:
        if carte["carte_id"] in vues:
            continue
        groupe = membres.get(carte["carte_id"], [carte["carte_id"]])
        vues.update(groupe)
        representant = groupe[0]
        normales = sum(collection.version(carte_id, False)["quantite"] for carte_id in groupe)
        foils = sum(collection.version(carte_id, True)["quantite"] for carte_id in groupe)
        if normales + foils == 0:
            if avec_manquantes:
                contenu.append((representant, "toutes"))
        elif foils_a_part and normales and foils:
            contenu.append((representant, "normale"))
            contenu.append((representant, "foil"))
        else:
            contenu.append((representant, "toutes"))
    return contenu


def variantes_empilees(cartes, collection, membres, representants):
    nombre = 0
    for carte in cartes:
        groupe = membres.get(carte["carte_id"])
        if (
            groupe
            and groupe[0] != carte["carte_id"]
            and groupe[0] in representants
            and collection.quantite(carte["carte_id"]) > 0
        ):
            nombre += 1
    return nombre


def contenu_pile(collection, pile, version):
    total = 0
    foil = False
    devant = None
    possedees = 0
    for carte_id in pile:
        quantite, avec_foil = quantites(collection, carte_id, version)
        if quantite:
            total += quantite
            foil = foil or avec_foil
            possedees += 1
            if devant is None:
                devant = carte_id
    if devant is None and pile:
        devant = pile[0]
    return total, foil, devant, possedees


class Classeurs(Synchronisation):
    ouverture_demandee = Signal(str, int)

    titre = "Classeurs"
    message_tables = MESSAGE_TABLES

    def __init__(self, user_id, parent=None):
        super().__init__(user_id, parent)
        self.liste = []
        self.contenus = {}
        self.groupes_numeros = None
        self.index_places = None

    def lire(self):
        return supabase_client.lire_classeurs()

    def appliquer(self, classeurs, pochettes):
        self.liste = [dict(classeur) for classeur in classeurs]
        self.contenus = {classeur["id"]: {} for classeur in self.liste}
        for ligne in pochettes:
            contenu = self.contenus.get(ligne["classeur_id"])
            if contenu is not None:
                contenu[ligne["pochette"]] = {"carte_id": ligne["carte_id"], "version": ligne["version"]}
        self.erreur = ""
        self.chargee = True

    def executer(self, operation, argument):
        if operation == "classeur":
            supabase_client.enregistrer_classeur(self.user_id, argument)
        elif operation == "supprimer_classeur":
            supabase_client.supprimer_classeur(argument)
        elif operation == "pochettes":
            supabase_client.enregistrer_pochettes(argument)
        elif operation == "vider":
            supabase_client.supprimer_pochettes(*argument)

    def signaler(self):
        self.index_places = None
        self.change.emit()

    def groupes(self):
        if self.groupes_numeros is None:
            self.groupes_numeros = catalogue.groupes_numeros(catalogue.lister_cartes())
        return self.groupes_numeros

    def oublier_groupes(self):
        self.groupes_numeros = None
        self.signaler()

    def places(self):
        if self.index_places is None:
            index = {}
            for classeur in self.liste:
                for pochette, element in sorted(self.contenus[classeur["id"]].items()):
                    index.setdefault(element["carte_id"], []).append((classeur["id"], pochette))
            self.index_places = index
        return self.index_places

    def maisons(self, membres):
        places = self.places()
        if membres[0] in places:
            return places[membres[0]]
        for carte_id in membres:
            if carte_id in places:
                return places[carte_id][:1]
        return []

    def pile(self, classeur_id, pochette):
        element = self.contenu(classeur_id).get(pochette)
        if element is None:
            return []
        carte_id = element["carte_id"]
        membres = self.groupes().get(carte_id)
        if not membres or (classeur_id, pochette) not in self.maisons(membres):
            return [carte_id]
        places = self.places()
        return [carte_id] + [autre for autre in membres if autre != carte_id and autre not in places]

    def cartes_du_classeur(self, classeur_id):
        cartes = set()
        for pochette in self.contenu(classeur_id):
            cartes.update(self.pile(classeur_id, pochette))
        return cartes

    def classeur(self, classeur_id):
        return next((classeur for classeur in self.liste if classeur["id"] == classeur_id), None)

    def contenu(self, classeur_id):
        return self.contenus.get(classeur_id, {})

    def derniere(self, classeur_id):
        return max(self.contenu(classeur_id), default=-1)

    def premiere_libre(self, classeur_id):
        contenu = self.contenu(classeur_id)
        for pochette in range(capacite(self.classeur(classeur_id))):
            if pochette not in contenu:
                return pochette
        return None

    def emplacements(self, carte_id):
        directs = self.places().get(carte_id)
        if directs:
            return [(self.classeur(classeur_id), pochette, False) for classeur_id, pochette in directs]
        membres = self.groupes().get(carte_id)
        if not membres:
            return []
        return [(self.classeur(classeur_id), pochette, True) for classeur_id, pochette in self.maisons(membres)]

    def ligne(self, classeur_id, pochette):
        return {"classeur_id": classeur_id, "pochette": pochette, **self.contenus[classeur_id][pochette]}

    def creer(self, nom, colonnes, lignes, pages, couleur):
        classeur = {
            "id": str(uuid.uuid4()),
            "nom": nom,
            "colonnes": colonnes,
            "lignes": lignes,
            "pages": pages,
            "couleur": couleur,
        }
        self.liste.append(classeur)
        self.contenus[classeur["id"]] = {}
        self.ajouter_envoi(("classeur", dict(classeur)))
        self.signaler()
        return classeur

    def modifier(self, classeur_id, **champs):
        classeur = self.classeur(classeur_id)
        classeur.update(champs)
        self.ajouter_envoi(("classeur", dict(classeur)))
        self.signaler()

    def supprimer(self, classeur_id):
        self.liste = [classeur for classeur in self.liste if classeur["id"] != classeur_id]
        self.contenus.pop(classeur_id, None)
        self.ajouter_envoi(("supprimer_classeur", classeur_id))
        self.signaler()

    def placer(self, classeur_id, pochette, carte_id, version="toutes"):
        self.contenus[classeur_id][pochette] = {"carte_id": carte_id, "version": version}
        self.ajouter_envoi(("pochettes", [self.ligne(classeur_id, pochette)]))
        self.signaler()

    def ranger(self, classeur_id, carte_id):
        pochette = self.premiere_libre(classeur_id)
        if pochette is not None:
            self.placer(classeur_id, pochette, carte_id)
        return pochette

    def vider(self, classeur_id, pochettes):
        contenu = self.contenus[classeur_id]
        pochettes = [pochette for pochette in pochettes if pochette in contenu]
        if not pochettes:
            return
        for pochette in pochettes:
            del contenu[pochette]
        self.ajouter_envoi(("vider", (classeur_id, pochettes)))
        self.signaler()

    def deplacer(self, classeur_id, depart, arrivee):
        contenu = self.contenus[classeur_id]
        if depart == arrivee or depart not in contenu:
            return
        element = contenu.pop(depart)
        autre = contenu.get(arrivee)
        contenu[arrivee] = element
        if autre is None:
            self.ajouter_envoi(
                ("pochettes", [self.ligne(classeur_id, arrivee)]),
                ("vider", (classeur_id, [depart])),
            )
        else:
            contenu[depart] = autre
            self.ajouter_envoi(
                ("pochettes", [self.ligne(classeur_id, arrivee), self.ligne(classeur_id, depart)])
            )
        self.signaler()

    def remplir(self, classeur_id, elements, depart, remplacer):
        contenu = self.contenus[classeur_id]
        etapes = []
        if remplacer:
            contenu.clear()
            etapes.append(("vider", (classeur_id, None)))
        places = capacite(self.classeur(classeur_id)) - depart
        elements = elements[:max(0, places)]
        for decalage, (carte_id, version) in enumerate(elements):
            contenu[depart + decalage] = {"carte_id": carte_id, "version": version}
        if elements:
            pochettes = range(depart, depart + len(elements))
            etapes.append(("pochettes", [self.ligne(classeur_id, pochette) for pochette in pochettes]))
        if etapes:
            self.ajouter_envoi(*etapes)
        self.signaler()
        return len(elements)
