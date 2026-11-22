import re
import sqlite3
from contextlib import contextmanager

from app.infos import CHEMIN_BASE, DOSSIER_ICONES, DOSSIER_IMAGES, DOSSIER_MINIATURES

CODE_SIMPLE = re.compile(r"[a-z]+-(\d+)-(\d+)")
CODE_COMPLET = re.compile(r"([a-z]+)-([^-]+)-(\d+)")
CHIFFRES = re.compile(r"\d+")
RARETES_TOUJOURS_FOIL = ("Rare", "Epic", "Showcase")
SETS_SANS_FOIL = ("OGS",)
COLONNES_AJOUTEES = {
    "cout": "integer",
    "puissance": "integer",
    "supertype": "text",
    "tags": "text",
}


@contextmanager
def ouvrir_base():
    base = sqlite3.connect(CHEMIN_BASE)
    base.row_factory = sqlite3.Row
    try:
        with base:
            yield base
    finally:
        base.close()


def creer_base():
    DOSSIER_IMAGES.mkdir(parents=True, exist_ok=True)
    DOSSIER_MINIATURES.mkdir(parents=True, exist_ok=True)
    DOSSIER_ICONES.mkdir(parents=True, exist_ok=True)
    with ouvrir_base() as base:
        base.execute("""
            create table if not exists cartes (
                carte_id       text primary key,
                code           text not null,
                nom            text not null,
                set_code       text not null,
                set_nom        text,
                numero         integer,
                rarete         text,
                type           text,
                domaines       text,
                image_url      text,
                art_alternatif integer not null default 0,
                signature      integer not null default 0,
                surnumerotee   integer not null default 0,
                tcgplayer_id   text,
                cout           integer,
                puissance      integer,
                supertype      text,
                tags           text
            )
        """)
        presentes = {ligne["name"] for ligne in base.execute("pragma table_info(cartes)")}
        for nom, genre in COLONNES_AJOUTEES.items():
            if nom not in presentes:
                base.execute(f"alter table cartes add column {nom} {genre}")


def donnees_incompletes():
    with ouvrir_base() as base:
        return base.execute("select exists (select 1 from cartes where tags is null)").fetchone()[0] == 1


def _convertir(item):
    classement = item.get("classification") or {}
    infos_set = item.get("set") or {}
    media = item.get("media") or {}
    meta = item.get("metadata") or {}
    attributs = item.get("attributes") or {}
    return {
        "carte_id": item["id"],
        "code": item["riftbound_id"],
        "nom": item["name"],
        "set_code": (infos_set.get("set_id") or "").upper(),
        "set_nom": infos_set.get("label"),
        "numero": item.get("collector_number"),
        "rarete": classement.get("rarity"),
        "type": classement.get("type"),
        "domaines": ", ".join(classement.get("domain") or []),
        "image_url": media.get("image_url"),
        "art_alternatif": bool(meta.get("alternate_art")),
        "signature": bool(meta.get("signature")),
        "surnumerotee": bool(meta.get("overnumbered")),
        "tcgplayer_id": item.get("tcgplayer_id"),
        "cout": attributs.get("energy"),
        "puissance": attributs.get("might"),
        "supertype": classement.get("supertype"),
        "tags": ", ".join(item.get("tags") or []),
    }


def enregistrer_cartes(items):
    lignes = [_convertir(item) for item in items]
    with ouvrir_base() as base:
        base.executemany("""
            insert or replace into cartes (
                carte_id, code, nom, set_code, set_nom, numero, rarete, type,
                domaines, image_url, art_alternatif, signature, surnumerotee,
                tcgplayer_id, cout, puissance, supertype, tags
            ) values (
                :carte_id, :code, :nom, :set_code, :set_nom, :numero, :rarete, :type,
                :domaines, :image_url, :art_alternatif, :signature, :surnumerotee,
                :tcgplayer_id, :cout, :puissance, :supertype, :tags
            )
        """, lignes)

        base.execute("""
            delete from cartes
            where tcgplayer_id is null
              and exists (
                  select 1 from cartes as autre
                  where autre.code = cartes.code
                    and autre.image_url = cartes.image_url
                    and autre.tcgplayer_id is not null
              )
        """)


def nombre_cartes():
    with ouvrir_base() as base:
        return base.execute("select count(*) from cartes").fetchone()[0]


def lister_cartes():
    with ouvrir_base() as base:
        return base.execute("""
            select carte_id, code, nom, set_code, set_nom, numero, rarete, type,
                   domaines, image_url, cout, supertype, tags
            from cartes
            order by set_nom like '%Promotional%', set_code, numero, code
        """).fetchall()


def lire_carte(carte_id):
    with ouvrir_base() as base:
        return base.execute(
            "select * from cartes where carte_id = :carte_id", {"carte_id": carte_id}
        ).fetchone()


def toujours_foil(carte):
    return carte["rarete"] in RARETES_TOUJOURS_FOIL and carte["set_code"] not in SETS_SANS_FOIL


def cartes_toujours_foil():
    with ouvrir_base() as base:
        lignes = base.execute("select carte_id, rarete, set_code from cartes").fetchall()
    return {ligne["carte_id"] for ligne in lignes if toujours_foil(ligne)}


NOM_PROMOS = "Promos"


def groupe_set(set_nom):
    return NOM_PROMOS if "Promotional" in (set_nom or "") else set_nom


def code_affiche(carte, avec_total=False):
    code = carte["code"] or ""
    morceaux = CODE_COMPLET.fullmatch(code)
    if morceaux is None:
        return code.upper()
    texte = f"{morceaux.group(1).upper()} {morceaux.group(2)}"
    if avec_total:
        texte += f" / {morceaux.group(3)}"
    return texte


def numero_court(carte):
    morceaux = CODE_COMPLET.fullmatch(carte["code"] or "")
    return morceaux.group(2) if morceaux else code_affiche(carte)


def decouper_code(code):
    morceaux = CODE_COMPLET.fullmatch(code or "")
    if morceaux is None:
        return None
    chiffres = CHIFFRES.match(morceaux.group(2))
    if chiffres is None:
        return None
    return morceaux.group(1), int(chiffres.group()), morceaux.group(2)[chiffres.end():], int(morceaux.group(3))


def est_variante(code):
    morceaux = decouper_code(code)
    return morceaux is not None and morceaux[2] != ""


def est_surnumerotee(code):
    morceaux = decouper_code(code)
    return morceaux is not None and morceaux[1] > morceaux[3]


def groupes_numeros(cartes):
    groupes = {}
    for carte in cartes:
        morceaux = decouper_code(carte["code"])
        if morceaux is not None:
            cle = (groupe_set(carte["set_nom"]), carte["set_code"], morceaux[0], morceaux[1])
            groupes.setdefault(cle, []).append(carte)
    membres = {}
    for groupe in groupes.values():
        if len(groupe) < 2:
            continue
        groupe.sort(key=lambda carte: (est_variante(carte["code"]), carte["code"]))
        identifiants = [carte["carte_id"] for carte in groupe]
        for carte_id in identifiants:
            membres[carte_id] = identifiants
    return membres


def est_de_base(code):
    morceaux = CODE_SIMPLE.fullmatch(code)
    return bool(morceaux) and int(morceaux.group(1)) <= int(morceaux.group(2))


def cartes_par_set():
    with ouvrir_base() as base:
        lignes = base.execute("""
            select set_nom, carte_id, code from cartes
            order by set_nom like '%Promotional%', set_code, numero
        """).fetchall()
    sets = {}
    for ligne in lignes:
        sets.setdefault(ligne["set_nom"], []).append(
            (ligne["carte_id"], est_de_base(ligne["code"]))
        )
    return sets
