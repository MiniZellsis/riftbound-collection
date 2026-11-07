import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DOSSIER_DONNEES = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RiftboundCollection"
CHEMIN_BASE = DOSSIER_DONNEES / "catalogue.db"
DOSSIER_IMAGES = DOSSIER_DONNEES / "images"
DOSSIER_MINIATURES = DOSSIER_DONNEES / "miniatures"

CODE_SIMPLE = re.compile(r"[a-z]+-(\d+)-(\d+)")


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


def lister_cartes():
    with ouvrir_base() as base:
        return base.execute("""
            select carte_id, code, nom, set_code, set_nom, numero, rarete, type,
                   domaines, image_url
            from cartes
            order by set_nom like '%Promotional%', set_code, numero, code
        """).fetchall()


def lire_carte(carte_id):
    with ouvrir_base() as base:
        return base.execute(
            "select * from cartes where carte_id = :carte_id", {"carte_id": carte_id}
        ).fetchone()


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