import time

import requests

from models import Carte, db

URL_API = "https://api.riftcodex.com/cards"
TAILLE_PAGE = 100


def importer_cartes():
    # On charge les cartes déjà en base, pour savoir s'il faut créer ou mettre à jour
    existantes = {c.riftcodex_id: c for c in db.session.scalars(db.select(Carte))}

    page = 1
    nb_nouvelles = 0
    nb_maj = 0

    while True:
        reponse = requests.get(
            URL_API, params={"page": page, "size": TAILLE_PAGE}, timeout=30
        )
        reponse.raise_for_status()  # s'arrête si l'API renvoie une erreur
        donnees = reponse.json()

        for item in donnees["items"]:
            carte = existantes.get(item["id"])
            if carte is None:
                carte = Carte(riftcodex_id=item["id"])
                db.session.add(carte)
                existantes[item["id"]] = carte
                nb_nouvelles += 1
            else:
                nb_maj += 1
            remplir_carte(carte, item)

        db.session.commit()
        print(f"Page {page}/{donnees['pages']} traitée")

        if page >= donnees["pages"]:
            break
        page += 1
        time.sleep(0.5)  # on ne surcharge pas l'API gratuite

    print(f"Terminé : {nb_nouvelles} nouvelles cartes, {nb_maj} mises à jour.")


def remplir_carte(carte, item):
    classement = item.get("classification") or {}
    infos_set = item.get("set") or {}
    media = item.get("media") or {}
    meta = item.get("metadata") or {}

    carte.nom = item["name"]
    carte.riftbound_id = item.get("riftbound_id")
    carte.set_code = (infos_set.get("set_id") or "").upper()
    carte.set_nom = infos_set.get("label")
    carte.numero = item.get("collector_number")
    carte.rarete = classement.get("rarity")
    carte.type_carte = classement.get("type")
    carte.domaines = ", ".join(classement.get("domain") or [])
    carte.image_url = media.get("image_url")
    carte.art_alternatif = bool(meta.get("alternate_art"))
    carte.signature = bool(meta.get("signature"))
    carte.surnumerotee = bool(meta.get("overnumbered"))
    carte.tcgplayer_id = item.get("tcgplayer_id")