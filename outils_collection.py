from flask_login import current_user

from models import Carte, Possession, Recherche, db

STATUTS = {
    "possedees": "Possédées",
    "manquantes": "Manquantes",
    "echange": "À échanger",
    "recherchees": "Recherchées",
}


def trouver_possession(carte_id, foil):
    return db.session.scalar(
        db.select(Possession).filter_by(
            utilisateur_id=current_user.id, carte_id=carte_id, foil=foil
        )
    )


def trouver_recherche(carte_id, foil):
    return db.session.scalar(
        db.select(Recherche).filter_by(
            utilisateur_id=current_user.id, carte_id=carte_id, foil=foil
        )
    )


def enregistrer_possession(carte_id, foil, quantite, a_echanger):
    possession = trouver_possession(carte_id, foil)

    if quantite == 0:
        if possession is not None:
            db.session.delete(possession)
        return

    # Première fois : on crée la ligne
    if possession is None:
        possession = Possession(
            utilisateur_id=current_user.id, carte_id=carte_id, foil=foil
        )
        db.session.add(possession)

    possession.quantite = quantite
    possession.a_echanger = a_echanger


def enregistrer_recherche(carte_id, foil, quantite):
    recherche = trouver_recherche(carte_id, foil)

    if quantite == 0:
        if recherche is not None:
            db.session.delete(recherche)
        return

    if recherche is None:
        recherche = Recherche(
            utilisateur_id=current_user.id, carte_id=carte_id, foil=foil
        )
        db.session.add(recherche)

    recherche.quantite = quantite


def condition_statut(statut):
    """Renvoie la condition SQL qui correspond au filtre "Ma collection"."""
    mes_cartes = db.select(Possession.carte_id).where(
        Possession.utilisateur_id == current_user.id
    )

    if statut == "possedees":
        return Carte.id.in_(mes_cartes)
    if statut == "manquantes":
        return Carte.id.not_in(mes_cartes)
    if statut == "echange":
        return Carte.id.in_(mes_cartes.where(Possession.a_echanger > 0))
    if statut == "recherchees":
        return Carte.id.in_(
            db.select(Recherche.carte_id).where(
                Recherche.utilisateur_id == current_user.id
            )
        )
    return None


def quantites_possedees(carte_ids):
    """Pour une liste de cartes, renvoie {carte_id: {"normale": 2, "foil": 1}}."""
    lignes = db.session.execute(
        db.select(Possession.carte_id, Possession.foil, Possession.quantite).where(
            Possession.utilisateur_id == current_user.id,
            Possession.carte_id.in_(carte_ids),
        )
    ).all()

    resultat = {}
    for carte_id, foil, quantite in lignes:
        compte = resultat.setdefault(carte_id, {"normale": 0, "foil": 0})
        if foil:
            compte["foil"] = quantite
        else:
            compte["normale"] = quantite
    return resultat


def statistiques():
    mes_possessions = Possession.utilisateur_id == current_user.id

    def somme(colonne, *conditions):
        valeur = db.session.scalar(db.select(db.func.sum(colonne)).where(*conditions))
        return valeur or 0

    return {
        "exemplaires": somme(Possession.quantite, mes_possessions),
        "differentes": db.session.scalar(
            db.select(db.func.count(Possession.carte_id.distinct())).where(
                mes_possessions
            )
        ),
        "foils": somme(Possession.quantite, mes_possessions, Possession.foil),
        "a_echanger": somme(Possession.a_echanger, mes_possessions),
        "recherchees": somme(
            Recherche.quantite, Recherche.utilisateur_id == current_user.id
        ),
    }


def progression_par_set():
    totaux = db.session.execute(
        db.select(Carte.set_code, Carte.set_nom, db.func.count(Carte.id))
        .group_by(Carte.set_code, Carte.set_nom)
        .order_by(Carte.set_nom)
    ).all()

    possedees = dict(
        db.session.execute(
            db.select(Carte.set_code, db.func.count(Carte.id.distinct()))
            .join(Possession, Possession.carte_id == Carte.id)
            .where(Possession.utilisateur_id == current_user.id)
            .group_by(Carte.set_code)
        ).all()
    )

    resultat = []
    for code, nom, total in totaux:
        nombre = possedees.get(code, 0)
        resultat.append(
            {
                "code": code,
                "nom": nom,
                "possedees": nombre,
                "total": total,
                "pourcentage": round(nombre * 100 / total),
            }
        )
    return resultat