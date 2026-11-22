import queue
import threading
import uuid

from PySide6.QtCore import QObject, Qt, Signal

from app import journal
from app.donnees import catalogue, supabase_client

ATTENTE_FERMETURE = 10
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


def cartes_a_ranger(cartes, groupe, domaine, avec_variantes):
    resultat = []
    for carte in cartes:
        nom_groupe = catalogue.groupe_set(carte["set_nom"])
        if groupe and nom_groupe != groupe:
            continue
        if domaine and domaine not in (carte["domaines"] or "").split(", "):
            continue
        if not avec_variantes and nom_groupe != catalogue.NOM_PROMOS and not catalogue.est_de_base(carte["code"]):
            continue
        resultat.append(carte)
    return resultat


def contenu_automatique(cartes, collection, avec_manquantes, foils_a_part):
    contenu = []
    for carte in cartes:
        carte_id = carte["carte_id"]
        normales = collection.version(carte_id, False)["quantite"]
        foils = collection.version(carte_id, True)["quantite"]
        if normales + foils == 0:
            if avec_manquantes:
                contenu.append((carte_id, "toutes"))
        elif foils_a_part and normales and foils:
            contenu.append((carte_id, "normale"))
            contenu.append((carte_id, "foil"))
        else:
            contenu.append((carte_id, "toutes"))
    return contenu


class Classeurs(QObject):
    change = Signal()
    envoi_reussi = Signal()
    envoi_echoue = Signal(str)
    envoi_fini = Signal(str)
    message = Signal(str)
    ouverture_demandee = Signal(str, int)

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.liste = []
        self.contenus = {}
        self.chargee = False
        self.erreur = ""
        self.a_recharger = False
        self.file = queue.Queue()
        self.condition = threading.Condition()
        self.restants = 0
        self.echecs_non_vus = 0
        self.envoi_fini.connect(self.fin_envoi, Qt.ConnectionType.QueuedConnection)
        threading.Thread(target=self.envoyer, daemon=True).start()

    def charger(self):
        try:
            self.appliquer(*supabase_client.lire_classeurs())
        except supabase_client.TableAbsente:
            self.erreur = MESSAGE_TABLES
        except supabase_client.ErreurSupabase as erreur:
            self.erreur = f"Classeurs indisponibles : {erreur}"
        except Exception as exception:
            journal.noter_erreur(type(exception), exception, exception.__traceback__)
            self.erreur = "Classeurs indisponibles : erreur inattendue (détails dans erreurs.log)."
        self.change.emit()
        return self.chargee

    def appliquer(self, classeurs, pochettes):
        self.liste = [dict(classeur) for classeur in classeurs]
        self.contenus = {classeur["id"]: {} for classeur in self.liste}
        for ligne in pochettes:
            contenu = self.contenus.get(ligne["classeur_id"])
            if contenu is not None:
                contenu[ligne["pochette"]] = {"carte_id": ligne["carte_id"], "version": ligne["version"]}
        self.erreur = ""
        self.chargee = True

    def resynchroniser(self):
        with self.condition:
            occupe = self.restants > 0
        if not self.a_recharger or occupe:
            return
        try:
            donnees = supabase_client.lire_classeurs()
        except supabase_client.ErreurSupabase:
            return
        self.a_recharger = False
        self.appliquer(*donnees)
        self.change.emit()

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
        resultat = []
        for classeur in self.liste:
            for pochette, element in sorted(self.contenus[classeur["id"]].items()):
                if element["carte_id"] == carte_id:
                    resultat.append((classeur, pochette))
        return resultat

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
        self.change.emit()
        return classeur

    def modifier(self, classeur_id, **champs):
        classeur = self.classeur(classeur_id)
        classeur.update(champs)
        self.ajouter_envoi(("classeur", dict(classeur)))
        self.change.emit()

    def supprimer(self, classeur_id):
        self.liste = [classeur for classeur in self.liste if classeur["id"] != classeur_id]
        self.contenus.pop(classeur_id, None)
        self.ajouter_envoi(("supprimer_classeur", classeur_id))
        self.change.emit()

    def placer(self, classeur_id, pochette, carte_id, version="toutes"):
        self.contenus[classeur_id][pochette] = {"carte_id": carte_id, "version": version}
        self.ajouter_envoi(("pochettes", [self.ligne(classeur_id, pochette)]))
        self.change.emit()

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
        self.change.emit()

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
        self.change.emit()

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
        self.change.emit()
        return len(elements)

    def ajouter_envoi(self, *etapes):
        with self.condition:
            self.restants += 1
        self.file.put(list(etapes))

    def envoyer(self):
        while True:
            etapes = self.file.get()
            if etapes is None:
                return
            erreur = ""
            try:
                for operation, argument in etapes:
                    if operation == "classeur":
                        supabase_client.enregistrer_classeur(self.user_id, argument)
                    elif operation == "supprimer_classeur":
                        supabase_client.supprimer_classeur(argument)
                    elif operation == "pochettes":
                        supabase_client.enregistrer_pochettes(argument)
                    elif operation == "vider":
                        supabase_client.supprimer_pochettes(*argument)
            except supabase_client.ErreurSupabase as exception:
                erreur = str(exception)
            except Exception as exception:
                journal.noter_erreur(type(exception), exception, exception.__traceback__)
                erreur = "erreur inattendue (détails dans erreurs.log)"
            with self.condition:
                self.restants -= 1
                if erreur:
                    self.echecs_non_vus += 1
                self.condition.notify_all()
            try:
                self.envoi_fini.emit(erreur)
            except RuntimeError:
                return

    def fin_envoi(self, erreur):
        if erreur:
            with self.condition:
                self.echecs_non_vus -= 1
            self.a_recharger = True
            self.envoi_echoue.emit(erreur)
        with self.condition:
            termine = self.restants == 0
        if not termine:
            return
        if self.a_recharger:
            self.resynchroniser()
        elif not erreur:
            self.envoi_reussi.emit()

    def attendre_envois(self):
        with self.condition:
            termine = self.condition.wait_for(lambda: self.restants == 0, timeout=ATTENTE_FERMETURE)
            return termine and self.echecs_non_vus == 0

    def arreter(self):
        self.file.put(None)
