from app import supabase_client


def version_vide(version):
    return (
        version["quantite"] == 0
        and version["a_echanger"] == 0
        and not version["recherche"]
    )


class Collection:
    def __init__(self, user_id):
        self.user_id = user_id
        self.versions = {}
        self.chargee = False

    def charger(self):
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
        vide = {"foil": foil, "quantite": 0, "a_echanger": 0, "recherche": False}
        return self.versions.get((carte_id, foil), vide)

    def quantite(self, carte_id):
        return self.version(carte_id, False)["quantite"] + self.version(carte_id, True)["quantite"]

    def a_une_foil(self, carte_id):
        return self.version(carte_id, True)["quantite"] > 0

    def enregistrer(self, carte_id, versions):
        a_garder = [v for v in versions if not version_vide(v)]
        a_supprimer = [
            v for v in versions
            if version_vide(v) and (carte_id, v["foil"]) in self.versions
        ]

        if a_garder:
            supabase_client.enregistrer_versions(self.user_id, carte_id, a_garder)
        for version in a_supprimer:
            supabase_client.supprimer_version(carte_id, version["foil"])

        for version in versions:
            cle = (carte_id, version["foil"])
            if version_vide(version):
                self.versions.pop(cle, None)
            else:
                self.versions[cle] = dict(version)

    def modifier(self, carte_id, foil, **changements):
        version = dict(self.version(carte_id, foil))
        version.update(changements)
        version["quantite"] = max(0, min(version["quantite"], 99))
        version["a_echanger"] = max(0, min(version["a_echanger"], version["quantite"]))
        self.enregistrer(carte_id, [version])

    def correspond(self, carte_id, statut):
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
        return True

    def statistiques(self):
        par_carte = {}
        for (carte_id, foil), version in self.versions.items():
            par_carte[carte_id] = par_carte.get(carte_id, 0) + version["quantite"]
        total = sum(par_carte.values())
        differentes = sum(1 for quantite in par_carte.values() if quantite > 0)
        return total, differentes

    def chiffres_cles(self):
        total, differentes = self.statistiques()
        foils = sum(v["quantite"] for (carte_id, foil), v in self.versions.items() if foil)
        a_echanger = sum(v["a_echanger"] for v in self.versions.values())
        recherchees = len({carte_id for (carte_id, foil), v in self.versions.items() if v["recherche"]})
        return {
            "total": total,
            "differentes": differentes,
            "foils": foils,
            "a_echanger": a_echanger,
            "recherchees": recherchees,
        }
