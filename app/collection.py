"""
La collection du joueur : gardée en mémoire pour afficher vite,
et enregistrée sur Supabase à chaque modification.
"""
from app import supabase_client

# Une "version" = la version normale ou foil d'une carte, avec ses compteurs.
# Exemple : {"foil": False, "quantite": 3, "a_echanger": 1, "recherche": False}


def version_vide(version):
    """Vrai si on n'a rien à retenir : 0 exemplaire, rien à échanger, pas recherchée."""
    return (
        version["quantite"] == 0
        and version["a_echanger"] == 0
        and not version["recherche"]
    )


class Collection:
    def __init__(self, user_id):
        self.user_id = user_id
        self.versions = {}    # (carte_id, foil) -> version
        self.chargee = False  # reste False tant que la lecture sur Supabase n'a pas réussi

    def charger(self):
        """Lit toute la collection sur Supabase. Peut lever ErreurSupabase."""
        self.versions = {}
        for ligne in supabase_client.lire_collection():
            self.versions[(ligne["carte_id"], ligne["foil"])] = {
                "foil": ligne["foil"],
                "quantite": ligne["quantite"],
                "a_echanger": ligne["a_echanger"],
                "recherche": ligne["recherche"],
            }
        self.chargee = True

    def version(self, carte_id, foil):
        """La version normale (foil=False) ou foil d'une carte. Vide si on ne l'a pas."""
        vide = {"foil": foil, "quantite": 0, "a_echanger": 0, "recherche": False}
        return self.versions.get((carte_id, foil), vide)

    def quantite(self, carte_id):
        """Nombre total d'exemplaires, normales + foils."""
        return self.version(carte_id, False)["quantite"] + self.version(carte_id, True)["quantite"]

    def a_une_foil(self, carte_id):
        return self.version(carte_id, True)["quantite"] > 0

    def enregistrer(self, carte_id, versions):
        """
        Envoie les nouvelles versions d'une carte à Supabase, puis met la mémoire à jour.
        Peut lever ErreurSupabase : dans ce cas, la mémoire n'est pas modifiée.
        """
        a_garder = [v for v in versions if not version_vide(v)]
        # On ne supprime que ce qui existe vraiment sur Supabase
        a_supprimer = [
            v for v in versions
            if version_vide(v) and (carte_id, v["foil"]) in self.versions
        ]

        if a_garder:
            supabase_client.enregistrer_versions(self.user_id, carte_id, a_garder)
        for version in a_supprimer:
            supabase_client.supprimer_version(carte_id, version["foil"])

        # Supabase a tout accepté : on recopie les changements en mémoire
        for version in versions:
            cle = (carte_id, version["foil"])
            if version_vide(version):
                self.versions.pop(cle, None)
            else:
                self.versions[cle] = dict(version)

    def correspond(self, carte_id, statut):
        """Vrai si la carte correspond au filtre "Ma collection" choisi."""
        normale = self.version(carte_id, False)
        foil = self.version(carte_id, True)
        if statut == "possedees":
            return self.quantite(carte_id) > 0
        if statut == "manquantes":
            return self.quantite(carte_id) == 0
        if statut == "a_echanger":
            return normale["a_echanger"] + foil["a_echanger"] > 0
        if statut == "recherchees":
            return normale["recherche"] or foil["recherche"]
        return True  # pas de filtre

    def statistiques(self):
        """Renvoie (nombre total de cartes, nombre de cartes différentes)."""
        par_carte = {}
        for (carte_id, foil), version in self.versions.items():
            par_carte[carte_id] = par_carte.get(carte_id, 0) + version["quantite"]
        total = sum(par_carte.values())
        differentes = sum(1 for quantite in par_carte.values() if quantite > 0)
        return total, differentes