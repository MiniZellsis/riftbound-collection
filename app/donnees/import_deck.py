import re

from app.donnees.decks import (
    champion_compatible,
    cle_numero,
    est_champion,
    normaliser,
    zone_naturelle,
)

ENTETES = {
    "legend": "legende",
    "legende": "legende",
    "champion legend": "legende",
    "legende champion": "legende",
    "champion": "champion",
    "chosen champion": "champion",
    "champion choisi": "champion",
    "main": "principal",
    "main deck": "principal",
    "maindeck": "principal",
    "deck": "principal",
    "deck principal": "principal",
    "cards": "principal",
    "battlefields": "arenes",
    "battlefield": "arenes",
    "arenes": "arenes",
    "arene": "arenes",
    "runes": "runes",
    "rune": "runes",
    "rune pool": "runes",
    "rune deck": "runes",
    "sideboard": "reserve",
    "side": "reserve",
    "side deck": "reserve",
    "reserve": "reserve",
}
QUANTITE_AVANT = re.compile(r"^(\d{1,2})\s*[xX×]?\s+(.+)$")
QUANTITE_APRES = re.compile(r"^(.+?)\s+[xX×]\s*(\d{1,2})$")
CODE_DANS_TEXTE = re.compile(r"\b([A-Za-z]{2,4})[-\s]((?:[Rr]|[Ss][Pp])?\d{1,3}[a-zA-Z*]?)(?:\s*/\s*\d+)?\b")
CODE_DECK = re.compile(r"^[A-Za-z2-7]{16,}$")
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
SETS = ["OGN", "OGS", "ARC", "SFD", "UNL", "VEN", "RAD"]
VARIANTES = {0: "", 1: "a", 2: "s", 3: "b"}
FORMAT = 1
VERSION_MAX = 6


class CodeIllisible(Exception):
    pass


class Lecteur:
    def __init__(self, octets):
        self.octets = octets
        self.position = 0

    def octet(self):
        if self.position >= len(self.octets):
            raise CodeIllisible("code trop court")
        valeur = self.octets[self.position]
        self.position += 1
        return valeur

    def nombre(self):
        resultat = 0
        decalage = 0
        while True:
            valeur = self.octet()
            resultat |= (valeur & 0x7F) << decalage
            if not valeur & 0x80:
                return resultat
            decalage += 7


def base32(texte):
    octets = bytearray()
    tampon = 0
    bits = 0
    for lettre in texte.upper():
        valeur = ALPHABET.find(lettre)
        if valeur < 0:
            raise CodeIllisible(f"caractère inconnu : {lettre}")
        tampon = (tampon << 5) | valeur
        bits += 5
        while bits >= 8:
            bits -= 8
            octets.append((tampon >> bits) & 0xFF)
    return bytes(octets)


def numero_carte(lecteur, marque):
    if marque is None:
        return f"{lecteur.nombre():03d}"
    drapeau = lecteur.octet()
    valeur = lecteur.nombre()
    if drapeau == 0:
        return f"{valeur:03d}"
    if drapeau == 1:
        return f"R{valeur:02d}"
    if drapeau == 2:
        return f"SP{valeur}"
    raise CodeIllisible(f"marque de numéro inconnue : {drapeau}")


def reference(lecteur, marque):
    numero_set = lecteur.octet()
    variante = lecteur.octet()
    if numero_set >= len(SETS) or variante not in VARIANTES:
        raise CodeIllisible("set ou variante inconnus")
    return f"{SETS[numero_set]}-{numero_carte(lecteur, marque)}{VARIANTES[variante]}"


def section_fixe(lecteur, maximum, version):
    cartes = []
    for nombre in range(maximum, 0, -1):
        for _ in range(lecteur.nombre()):
            taille = lecteur.nombre()
            numero_set = lecteur.octet()
            variante = lecteur.octet()
            if numero_set >= len(SETS) or variante not in VARIANTES:
                raise CodeIllisible("set ou variante inconnus")
            for _ in range(taille):
                numero = numero_carte(lecteur, True if version >= 4 else None)
                cartes.append((f"{SETS[numero_set]}-{numero}{VARIANTES[variante]}", nombre))
    return cartes


def section_libre(lecteur, marque):
    cartes = []
    for _ in range(lecteur.nombre()):
        nombre = lecteur.nombre()
        for _ in range(lecteur.nombre()):
            taille = lecteur.nombre()
            numero_set = lecteur.octet()
            variante = lecteur.octet()
            if numero_set >= len(SETS) or variante not in VARIANTES:
                raise CodeIllisible("set ou variante inconnus")
            for _ in range(taille):
                numero = numero_carte(lecteur, marque)
                cartes.append((f"{SETS[numero_set]}-{numero}{VARIANTES[variante]}", nombre))
    return cartes


def decoder(code):
    lecteur = Lecteur(base32(code.strip()))
    entete = lecteur.octet()
    if entete >> 4 != FORMAT:
        raise CodeIllisible("format inconnu")
    version = entete & 0x0F
    if version > VERSION_MAX:
        raise CodeIllisible("code fait par une version plus récente du format")
    if version >= 5:
        marque = lecteur.octet()
        if marque > 1:
            raise CodeIllisible("marque inconnue")
        marque = True if marque == 1 else None
        principal = section_libre(lecteur, marque)
        reserve = section_libre(lecteur, marque)
    else:
        marque = True if version >= 4 else None
        principal = section_fixe(lecteur, 12, version)
        reserve = section_fixe(lecteur, 3, version) if version >= 2 else []
    champion = None
    if version >= 3 and lecteur.octet() == 1:
        champion = reference(lecteur, marque)
    legendes = []
    if version >= 6:
        legendes = [reference(lecteur, marque) for _ in range(lecteur.nombre())]
    return principal, reserve, champion, legendes


def code_vers_cle(code):
    set_code, numero = code.split("-", 1)
    return cle_numero(set_code, numero)


class Resultat:
    def __init__(self):
        self.contenu = {}
        self.inconnues = []
        self.erreur = ""

    def ajouter(self, zone, carte_id, quantite):
        self.contenu[(zone, carte_id)] = self.contenu.get((zone, carte_id), 0) + quantite


def zone_de(carte, zone_annoncee):
    naturelle = zone_naturelle(carte)
    if naturelle != "principal":
        return naturelle
    if zone_annoncee in ("champion", "principal", "reserve"):
        return zone_annoncee
    return "principal"


def trouver(texte, decks):
    noms = decks.noms()
    codes = decks.codes()
    texte = texte.strip()
    for morceaux in CODE_DANS_TEXTE.finditer(texte):
        cle = cle_numero(morceaux.group(1), morceaux.group(2))
        if cle in codes:
            return codes[cle]
    sans_parentheses = re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", texte).strip()
    for essai in (texte, sans_parentheses):
        trouvees = noms.get(normaliser(essai))
        if trouvees:
            return trouvees[0]
    return None


def lire_quantite(ligne):
    morceaux = QUANTITE_AVANT.match(ligne)
    if morceaux:
        return int(morceaux.group(1)), morceaux.group(2)
    morceaux = QUANTITE_APRES.match(ligne)
    if morceaux:
        return int(morceaux.group(2)), morceaux.group(1)
    return None, ligne


def lire_liste(texte, decks):
    resultat = Resultat()
    cartes = decks.cartes()
    zone = None
    for brute in texte.splitlines():
        ligne = brute.strip().lstrip("-•*").strip()
        if not ligne or ligne.startswith(("#", "//")):
            continue
        entete = normaliser(re.sub(r"\(.*?\)", "", ligne.rstrip(":")))
        if entete in ENTETES and not QUANTITE_AVANT.match(ligne):
            zone = ENTETES[entete]
            continue
        quantite, reste = lire_quantite(ligne)
        if quantite is None or quantite == 0:
            if ligne.endswith(":"):
                continue
            resultat.inconnues.append(ligne)
            continue
        carte_id = trouver(reste, decks)
        if carte_id is None:
            resultat.inconnues.append(ligne)
            continue
        resultat.ajouter(zone_de(cartes[carte_id], zone), carte_id, quantite)
    completer_champion(resultat, decks)
    return resultat


def lire_code(code, decks):
    resultat = Resultat()
    try:
        principal, reserve, champion, legendes = decoder(code)
    except CodeIllisible as erreur:
        resultat.erreur = f"Code de deck illisible ({erreur})."
        return resultat
    cartes = decks.cartes()
    codes = decks.codes()
    for zone_annoncee, liste in (("principal", principal), ("reserve", reserve)):
        for code_carte, quantite in liste:
            carte_id = codes.get(code_vers_cle(code_carte))
            if carte_id is None:
                resultat.inconnues.append(f"{quantite} {code_carte}")
                continue
            resultat.ajouter(zone_de(cartes[carte_id], zone_annoncee), carte_id, quantite)
    for code_carte in legendes:
        carte_id = codes.get(code_vers_cle(code_carte))
        if carte_id is None:
            resultat.inconnues.append(f"1 {code_carte}")
        else:
            resultat.ajouter("legende", carte_id, 1)
    if champion is not None:
        carte_id = codes.get(code_vers_cle(champion))
        if carte_id is None:
            resultat.inconnues.append(f"1 {champion}")
        else:
            prendre_champion(resultat, carte_id)
    completer_champion(resultat, decks)
    return resultat


def prendre_champion(resultat, carte_id):
    contenu = resultat.contenu
    if any(zone == "champion" for zone, _ in contenu):
        return
    presentes = contenu.get(("principal", carte_id), 0)
    if presentes > 1:
        contenu[("principal", carte_id)] = presentes - 1
    elif presentes == 1:
        del contenu[("principal", carte_id)]
    contenu[("champion", carte_id)] = 1


def completer_champion(resultat, decks):
    contenu = resultat.contenu
    if any(zone == "champion" for zone, _ in contenu):
        return
    cartes = decks.cartes()
    legende = next((cartes[carte_id] for zone, carte_id in sorted(contenu) if zone == "legende"), None)
    for zone, carte_id in sorted(contenu):
        carte = cartes[carte_id]
        if zone == "principal" and est_champion(carte) and champion_compatible(legende, carte):
            prendre_champion(resultat, carte_id)
            return


def lire(texte, decks):
    texte = texte.strip()
    if CODE_DECK.fullmatch(texte):
        return lire_code(texte, decks)
    return lire_liste(texte, decks)
