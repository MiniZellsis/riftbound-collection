import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DOSSIER_DONNEES = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RiftboundCollection"
CHEMIN_BASE = DOSSIER_DONNEES / "catalogue.db"
DOSSIER_IMAGES = DOSSIER_DONNEES / "images"


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
    """Crée les dossiers et la table si besoin (au premier lancement)."""
    DOSSIER_IMAGES.mkdir(parents=True, exist_ok=True)
    with ouvrir_base() as base:
        base.execute("""
            create table if not exists cartes (
                carte_id       text primary key,  -- identifiant Riftcodex
                code           text not null,     -- code imprimé, ex. ogn-001-298
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
                tcgplayer_id   text
            )
        """)


def _convertir(item):
    classement = item.get("classification") or {}
    infos_set = item.get("set") or {}
    media = item.get("media") or {}
    meta = item.get("metadata") or {}
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
    }


def enregistrer_cartes(items):
    lignes = [_convertir(item) for item in items]
    with ouvrir_base() as base:
        base.executemany("""
            insert or replace into cartes (
                carte_id, code, nom, set_code, set_nom, numero, rarete, type,
                domaines, image_url, art_alternatif, signature, surnumerotee,
                tcgplayer_id
            ) values (
                :carte_id, :code, :nom, :set_code, :set_nom, :numero, :rarete, :type,
                :domaines, :image_url, :art_alternatif, :signature, :surnumerotee,
                :tcgplayer_id
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


def lister_cartes(texte="", set_code="", rarete="", domaine="", type_carte=""):
    conditions = []
    if texte:
        conditions.append("(nom like :texte or code like :texte)")
    if set_code:
        conditions.append("set_code = :set_code")
    if rarete:
        conditions.append("rarete = :rarete")
    if domaine:
        conditions.append("domaines like :domaine")
    if type_carte:
        conditions.append("type = :type_carte")
    where = ("where " + " and ".join(conditions)) if conditions else ""

    valeurs = {
        "texte": f"%{texte}%",
        "set_code": set_code,
        "rarete": rarete,
        "domaine": f"%{domaine}%",
        "type_carte": type_carte,
    }
    with ouvrir_base() as base:
        return base.execute(f"""
            select carte_id, nom, set_nom, numero, rarete, image_url
            from cartes
            {where}
            order by set_nom like '%Promotional%', set_code, numero, code
        """, valeurs).fetchall()


ORDRE_RARETES = ["Common", "Uncommon", "Rare", "Epic", "Showcase", "Promo"]


def valeurs_filtres():
    with ouvrir_base() as base:
        sets = base.execute("""
            select distinct set_nom, set_code from cartes
            order by set_nom like '%Promotional%', set_code
        """).fetchall()
        raretes = [ligne["rarete"] for ligne in base.execute("select distinct rarete from cartes")]
        types = [ligne["type"] for ligne in base.execute("select distinct type from cartes order by type")]
        domaines = set()
        for ligne in base.execute("select distinct domaines from cartes"):
            domaines.update(d for d in ligne["domaines"].split(", ") if d)

    raretes_triees = [r for r in ORDRE_RARETES if r in raretes]
    raretes_triees += sorted(r for r in raretes if r and r not in ORDRE_RARETES)

    return {
        "sets": [(ligne["set_nom"], ligne["set_code"]) for ligne in sets],
        "raretes": [(r, r) for r in raretes_triees],
        "domaines": [(d, d) for d in sorted(domaines)],
        "types": [(t, t) for t in types if t],
    }


def lire_carte(carte_id):
    with ouvrir_base() as base:
        return base.execute(
            "select * from cartes where carte_id = :carte_id", {"carte_id": carte_id}
        ).fetchone()