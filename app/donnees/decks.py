import re
import unicodedata
import uuid

from PySide6.QtCore import Signal

from app.donnees import catalogue, supabase_client
from app.donnees.synchronisation import Synchronisation

NOM_MAX = 60
ZONES = ["legende", "champion", "principal", "arenes", "runes", "reserve"]
NOMS_ZONES = {
    "legende": "Légende",
    "champion": "Champion choisi",
    "principal": "Deck principal",
    "arenes": "Arènes",
    "runes": "Runes",
    "reserve": "Réserve",
}
ZONES_DU_DECK = ("champion", "principal")
ZONES_LIMITEES = ("champion", "principal", "reserve")
TAILLE_PRINCIPAL = 40
TAILLE_RUNES = 12
NOMBRE_ARENES = 3
RESERVE_MAX = 8
EXEMPLAIRES_MAX = 3
SIGNATURES_MAX = 3
COUT_MAX_COURBE = 7
TYPES = [("Unit", "Unités"), ("Spell", "Sorts"), ("Gear", "Équipements")]
MESSAGE_TABLES = (
    "Le serveur n'a pas encore les tables des decks. Lance une fois le script "
    "supabase/4_decks.sql dans Supabase (SQL Editor), puis redémarre l'appli."
)


def normaliser(texte):
    texte = unicodedata.normalize("NFKD", texte or "")
    texte = "".join(lettre for lettre in texte if not unicodedata.combining(lettre))
    texte = texte.lower().replace("’", "'").replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", texte).strip()


def separer(texte):
    return [morceau.strip() for morceau in (texte or "").split(",") if morceau.strip()]


def est_legende(carte):
    return carte["type"] == "Legend"


def est_arene(carte):
    return carte["type"] == "Battlefield"


def est_rune(carte):
    return carte["type"] == "Rune"


def est_champion(carte):
    return "champion" in (carte["supertype"] or "").lower()


def est_signature(carte):
    return "signature" in (carte["supertype"] or "").lower()


def nom_champion(carte):
    if "," in carte["nom"]:
        return carte["nom"].split(",")[0].strip()
    etiquettes = separer(carte["tags"])
    return etiquettes[0] if etiquettes else carte["nom"]


def champions_de_legende(legende):
    noms = {normaliser(etiquette) for etiquette in separer(legende["tags"])}
    if "," in legende["nom"]:
        noms.add(normaliser(legende["nom"].split(",")[0]))
    return noms


def champion_compatible(legende, carte):
    return legende is None or normaliser(nom_champion(carte)) in champions_de_legende(legende)


def signature_compatible(legende, carte):
    if legende is None:
        return True
    champions = champions_de_legende(legende)
    return any(normaliser(etiquette) in champions for etiquette in separer(carte["tags"]))


def zone_naturelle(carte):
    if est_legende(carte):
        return "legende"
    if est_arene(carte):
        return "arenes"
    if est_rune(carte):
        return "runes"
    return "principal"


def legende_du_deck(contenu, cartes):
    for (zone, carte_id), _ in sorted(contenu.items()):
        if zone == "legende" and carte_id in cartes:
            return cartes[carte_id]
    return None


def zone_pour(carte, contenu, cartes):
    zone = zone_naturelle(carte)
    if zone != "principal" or not est_champion(carte):
        return zone
    if any(zone_carte == "champion" for zone_carte, _ in contenu):
        return zone
    if champion_compatible(legende_du_deck(contenu, cartes), carte):
        return "champion"
    return zone


def totaux(contenu):
    resultat = dict.fromkeys(ZONES, 0)
    for (zone, _), quantite in contenu.items():
        resultat[zone] += quantite
    return resultat


def pluriel(nombre, mot):
    return f"{nombre} {mot}{'s' if nombre > 1 else ''}"


def analyser(contenu, cartes):
    nombres = totaux(contenu)
    legende = legende_du_deck(contenu, cartes)
    identite = set(separer(legende["domaines"])) if legende is not None else None
    problemes = []
    if nombres["legende"] == 0:
        problemes.append("Choisis une légende : elle donne les domaines du deck.")
    elif nombres["legende"] > 1:
        problemes.append("Un deck n'a qu'une seule légende.")
    if nombres["champion"] == 0:
        problemes.append("Choisis ton champion : un champion de ta légende.")
    elif nombres["champion"] > 1:
        problemes.append("Un seul champion choisi par deck.")
    principal = nombres["principal"] + nombres["champion"]
    if principal != TAILLE_PRINCIPAL:
        problemes.append(f"Deck principal : {principal} cartes sur {TAILLE_PRINCIPAL} (champion compris).")
    if nombres["runes"] != TAILLE_RUNES:
        problemes.append(f"Runes : {nombres['runes']} sur {TAILLE_RUNES}.")
    if nombres["arenes"] != NOMBRE_ARENES:
        problemes.append(f"Arènes : {nombres['arenes']} sur {NOMBRE_ARENES}.")
    if nombres["reserve"] > RESERVE_MAX:
        problemes.append(f"Réserve : {nombres['reserve']} cartes, {RESERVE_MAX} au plus.")

    exemplaires = {}
    noms_arenes = {}
    signatures = 0
    for (zone, carte_id), quantite in sorted(contenu.items()):
        carte = cartes.get(carte_id)
        if carte is None:
            problemes.append("Une carte du deck n'est plus dans le catalogue.")
            continue
        if zone == "arenes":
            cle = normaliser(carte["nom"])
            noms_arenes[cle] = noms_arenes.get(cle, 0) + quantite
            continue
        if zone in ZONES_LIMITEES:
            cle = normaliser(carte["nom"])
            nom, total = exemplaires.get(cle, (carte["nom"], 0))
            exemplaires[cle] = (nom, total + quantite)
            if est_signature(carte):
                signatures += quantite
                if not signature_compatible(legende, carte):
                    problemes.append(f"« {carte['nom']} » est une carte Signature d'un autre champion.")
        if zone == "champion" and (not est_champion(carte) or not champion_compatible(legende, carte)):
            problemes.append(f"« {carte['nom']} » n'est pas un champion de ta légende.")
        domaines = set(separer(carte["domaines"]))
        if identite is not None and zone != "legende" and not domaines <= identite:
            problemes.append(f"« {carte['nom']} » n'est pas dans les domaines de ta légende.")
    for nom, total in exemplaires.values():
        if total > EXEMPLAIRES_MAX:
            problemes.append(f"« {nom} » : {total} exemplaires, {EXEMPLAIRES_MAX} au plus.")
    if any(total > 1 for total in noms_arenes.values()):
        problemes.append("Tes 3 arènes doivent avoir des noms différents.")
    if signatures > SIGNATURES_MAX:
        problemes.append(f"{signatures} cartes Signature : {SIGNATURES_MAX} au plus.")
    return {"nombres": nombres, "principal": principal, "legende": legende, "problemes": problemes}


def courbe(contenu, cartes):
    colonnes = [0] * (COUT_MAX_COURBE + 1)
    types = dict.fromkeys([code for code, _ in TYPES], 0)
    for (zone, carte_id), quantite in contenu.items():
        carte = cartes.get(carte_id)
        if zone not in ZONES_DU_DECK or carte is None:
            continue
        cout = carte["cout"] if carte["cout"] is not None else 0
        colonnes[min(max(cout, 0), COUT_MAX_COURBE)] += quantite
        if carte["type"] in types:
            types[carte["type"]] += quantite
    return colonnes, types


def besoins(contenu, cartes):
    resultat = {}
    for (zone, carte_id), quantite in sorted(contenu.items(), key=lambda element: ZONES.index(element[0][0])):
        carte = cartes.get(carte_id)
        cle = normaliser(carte["nom"]) if carte is not None else carte_id
        besoin = resultat.setdefault(cle, {"nom": carte["nom"] if carte else carte_id, "carte_id": carte_id, "quantite": 0})
        besoin["quantite"] += quantite
    return resultat


def cle_code(code):
    morceaux = catalogue.CODE_COMPLET.fullmatch(code or "")
    if morceaux is None:
        return None
    return cle_numero(morceaux.group(1), morceaux.group(2))


def cle_numero(set_code, numero):
    morceaux = re.fullmatch(r"(r|sp)?0*(\d+)([a-z*]?)", numero.lower())
    if morceaux is None:
        return None
    suffixe = "s" if morceaux.group(3) == "*" else morceaux.group(3)
    return f"{set_code.lower()}-{morceaux.group(1) or ''}{int(morceaux.group(2))}{suffixe}"


def ordre_impression(carte, rang):
    return (
        catalogue.groupe_set(carte["set_nom"]) == catalogue.NOM_PROMOS,
        catalogue.est_variante(carte["code"]),
        catalogue.est_surnumerotee(carte["code"]),
        rang,
    )


def indexer(cartes):
    par_nom = {}
    par_code = {}
    alias = {}
    for rang, carte in enumerate(cartes):
        cle = normaliser(carte["nom"])
        par_nom.setdefault(cle, []).append((ordre_impression(carte, rang), carte["carte_id"]))
        code = cle_code(carte["code"])
        if code is not None:
            par_code.setdefault(code, carte["carte_id"])
        if est_legende(carte):
            for etiquette in separer(carte["tags"]):
                alias.setdefault(normaliser(f"{etiquette} {carte['nom']}"), []).append((ordre_impression(carte, rang), carte["carte_id"]))
    noms = {cle: [carte_id for _, carte_id in sorted(liste)] for cle, liste in par_nom.items()}
    for cle, liste in alias.items():
        noms.setdefault(cle, [carte_id for _, carte_id in sorted(liste)])
    return noms, par_code


class Decks(Synchronisation):
    ouverture_demandee = Signal(str)
    surlignage_demande = Signal(str, str, int)

    titre = "Decks"
    message_tables = MESSAGE_TABLES

    def __init__(self, user_id, parent=None):
        super().__init__(user_id, parent)
        self.liste = []
        self.contenus = {}
        self.index_cartes = None
        self.index_noms = None
        self.index_codes = None
        self.cache_montees = None

    def signaler(self):
        self.cache_montees = None
        self.change.emit()

    def lire(self):
        return supabase_client.lire_decks()

    def appliquer(self, decks, cartes):
        self.liste = [dict(deck) for deck in decks]
        self.contenus = {deck["id"]: {} for deck in self.liste}
        for ligne in cartes:
            contenu = self.contenus.get(ligne["deck_id"])
            if contenu is not None and ligne["zone"] in ZONES:
                contenu[(ligne["zone"], ligne["carte_id"])] = ligne["quantite"]
        self.erreur = ""
        self.chargee = True

    def executer(self, operation, argument):
        if operation == "deck":
            supabase_client.enregistrer_deck(self.user_id, argument)
        elif operation == "supprimer_deck":
            supabase_client.supprimer_deck(argument)
        elif operation == "cartes":
            supabase_client.enregistrer_cartes_deck(argument)
        elif operation == "retirer":
            supabase_client.supprimer_cartes_deck(*argument)

    def cartes(self):
        if self.index_cartes is None:
            liste = catalogue.lister_cartes()
            self.index_cartes = {carte["carte_id"]: carte for carte in liste}
            self.index_noms, self.index_codes = indexer(liste)
        return self.index_cartes

    def noms(self):
        self.cartes()
        return self.index_noms

    def codes(self):
        self.cartes()
        return self.index_codes

    def oublier_catalogue(self):
        self.index_cartes = None
        self.index_noms = None
        self.index_codes = None
        self.signaler()

    def impressions(self, carte_id):
        carte = self.cartes().get(carte_id)
        if carte is None:
            return [carte_id]
        return self.noms().get(normaliser(carte["nom"]), [carte_id])

    def possedees(self, collection, carte_id):
        return sum(collection.quantite(autre) for autre in self.impressions(carte_id))

    def deck(self, deck_id):
        return next((deck for deck in self.liste if deck["id"] == deck_id), None)

    def contenu(self, deck_id):
        return self.contenus.get(deck_id, {})

    def ligne(self, deck_id, zone, carte_id):
        return {"deck_id": deck_id, "zone": zone, "carte_id": carte_id, "quantite": self.contenus[deck_id][(zone, carte_id)]}

    def creer(self, nom, contenu=None):
        deck = {"id": str(uuid.uuid4()), "nom": nom, "monte": False}
        self.liste.append(deck)
        self.contenus[deck["id"]] = dict(contenu or {})
        etapes = [("deck", dict(deck))]
        if contenu:
            etapes.append(("cartes", [self.ligne(deck["id"], zone, carte_id) for zone, carte_id in sorted(contenu)]))
        self.ajouter_envoi(*etapes)
        self.signaler()
        return deck

    def modifier(self, deck_id, **champs):
        deck = self.deck(deck_id)
        deck.update(champs)
        self.ajouter_envoi(("deck", dict(deck)))
        self.signaler()

    def supprimer(self, deck_id):
        self.liste = [deck for deck in self.liste if deck["id"] != deck_id]
        self.contenus.pop(deck_id, None)
        self.ajouter_envoi(("supprimer_deck", deck_id))
        self.signaler()

    def definir(self, deck_id, zone, carte_id, quantite):
        contenu = self.contenus[deck_id]
        quantite = max(0, min(quantite, 99))
        if quantite == contenu.get((zone, carte_id), 0):
            return
        if quantite == 0:
            del contenu[(zone, carte_id)]
            self.ajouter_envoi(("retirer", (deck_id, [(zone, carte_id)])))
        else:
            contenu[(zone, carte_id)] = quantite
            self.ajouter_envoi(("cartes", [self.ligne(deck_id, zone, carte_id)]))
        self.signaler()

    def ajouter(self, deck_id, carte_id, nombre=1):
        contenu = self.contenus[deck_id]
        carte = self.cartes().get(carte_id)
        if carte is None:
            return None
        zone = zone_pour(carte, contenu, self.cartes())
        etapes = []
        if zone == "legende":
            anciennes = [cle for cle in contenu if cle[0] == "legende" and cle[1] != carte_id]
            for cle in anciennes:
                del contenu[cle]
            if anciennes:
                etapes.append(("retirer", (deck_id, anciennes)))
            contenu[("legende", carte_id)] = 1
        else:
            contenu[(zone, carte_id)] = min(99, contenu.get((zone, carte_id), 0) + nombre)
        etapes.append(("cartes", [self.ligne(deck_id, zone, carte_id)]))
        self.ajouter_envoi(*etapes)
        self.signaler()
        return zone

    def changer_zone(self, deck_id, zone, carte_id, nouvelle_zone, nombre=1):
        contenu = self.contenus[deck_id]
        presentes = contenu.get((zone, carte_id), 0)
        nombre = min(nombre, presentes)
        if nombre <= 0 or zone == nouvelle_zone:
            return
        etapes = []
        if presentes == nombre:
            del contenu[(zone, carte_id)]
            etapes.append(("retirer", (deck_id, [(zone, carte_id)])))
        else:
            contenu[(zone, carte_id)] = presentes - nombre
            etapes.append(("cartes", [self.ligne(deck_id, zone, carte_id)]))
        contenu[(nouvelle_zone, carte_id)] = contenu.get((nouvelle_zone, carte_id), 0) + nombre
        etapes.append(("cartes", [self.ligne(deck_id, nouvelle_zone, carte_id)]))
        self.ajouter_envoi(*etapes)
        self.signaler()

    def choisir_champion(self, deck_id, zone, carte_id):
        contenu = self.contenus[deck_id]
        actuels = [cle for cle in contenu if cle[0] == "champion"]
        etapes = []
        for cle in actuels:
            quantite = contenu.pop(cle)
            contenu[("principal", cle[1])] = contenu.get(("principal", cle[1]), 0) + quantite
            etapes.append(("retirer", (deck_id, [cle])))
            etapes.append(("cartes", [self.ligne(deck_id, "principal", cle[1])]))
        presentes = contenu.get((zone, carte_id), 0)
        if presentes <= 1:
            contenu.pop((zone, carte_id), None)
            etapes.append(("retirer", (deck_id, [(zone, carte_id)])))
        else:
            contenu[(zone, carte_id)] = presentes - 1
            etapes.append(("cartes", [self.ligne(deck_id, zone, carte_id)]))
        contenu[("champion", carte_id)] = 1
        etapes.append(("cartes", [self.ligne(deck_id, "champion", carte_id)]))
        self.ajouter_envoi(*etapes)
        self.signaler()

    def utilisations(self, carte_id):
        cle = normaliser(self.cartes()[carte_id]["nom"]) if carte_id in self.cartes() else carte_id
        resultat = []
        for deck in self.liste:
            total = 0
            for (_, autre), quantite in self.contenus[deck["id"]].items():
                carte = self.cartes().get(autre)
                if (normaliser(carte["nom"]) if carte is not None else autre) == cle:
                    total += quantite
            if total:
                resultat.append((deck, total))
        return resultat

    def cartes_montees(self):
        if self.cache_montees is None:
            resultat = {}
            for deck in self.liste:
                if not deck["monte"]:
                    continue
                for cle, besoin in besoins(self.contenus[deck["id"]], self.cartes()).items():
                    resultat.setdefault(cle, []).append((deck, besoin["quantite"]))
            self.cache_montees = resultat
        return self.cache_montees
