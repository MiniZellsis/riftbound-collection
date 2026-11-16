import queue
import threading

from PySide6.QtCore import QObject, Qt, Signal

from app import catalogue, journal, supabase_client

ATTENTE_FERMETURE = 10


def version_vide(version):
    return (
        version["quantite"] == 0
        and version["a_echanger"] == 0
        and not version["recherche"]
    )


def version_videe(foil):
    return {"foil": foil, "quantite": 0, "a_echanger": 0, "recherche": False}


class Collection(QObject):
    envoi_reussi = Signal(str)
    envoi_echoue = Signal(str, str)
    envoi_fini = Signal(str, object, object, str)

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.versions = {}
        self.confirmees = {}
        self.en_cours = {}
        self.echecs = {}
        self.chargee = False
        self.file = queue.Queue()
        self.condition = threading.Condition()
        self.restants = 0
        self.echecs_non_vus = 0
        self.envoi_fini.connect(self.fin_envoi, Qt.ConnectionType.QueuedConnection)
        threading.Thread(target=self.envoyer, daemon=True).start()

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
        try:
            self.passer_en_foil(catalogue.cartes_toujours_foil())
        except supabase_client.ErreurSupabase:
            pass
        self.confirmees = {cle: dict(version) for cle, version in self.versions.items()}

    def passer_en_foil(self, toujours_foil):
        normales = [carte_id for carte_id, foil in self.versions if not foil and carte_id in toujours_foil]
        for carte_id in normales:
            normale = self.version(carte_id, False)
            if not version_vide(normale):
                foil = self.version(carte_id, True)
                quantite = min(normale["quantite"] + foil["quantite"], 99)
                fusion = {
                    "foil": True,
                    "quantite": quantite,
                    "a_echanger": min(normale["a_echanger"] + foil["a_echanger"], quantite),
                    "recherche": normale["recherche"] or foil["recherche"],
                }
                supabase_client.enregistrer_versions(self.user_id, carte_id, [version_videe(False), fusion])
                self.versions[(carte_id, False)] = version_videe(False)
                self.versions[(carte_id, True)] = fusion
            supabase_client.supprimer_version(carte_id, False)
            del self.versions[(carte_id, False)]

    def version(self, carte_id, foil):
        return self.versions.get((carte_id, foil), version_videe(foil))

    def quantite(self, carte_id):
        return self.version(carte_id, False)["quantite"] + self.version(carte_id, True)["quantite"]

    def a_une_foil(self, carte_id):
        return self.version(carte_id, True)["quantite"] > 0

    def en_attente(self, carte_id):
        return carte_id in self.en_cours

    def enregistrer(self, carte_id, versions):
        changees = [dict(v) for v in versions if v != self.version(carte_id, v["foil"])]
        if not changees:
            return False
        for version in changees:
            cle = (carte_id, version["foil"])
            if version_vide(version):
                self.versions.pop(cle, None)
            else:
                self.versions[cle] = dict(version)
        a_envoyer = [version for version in changees if not version_vide(version)]
        a_supprimer = [version["foil"] for version in changees if version_vide(version)]
        self.en_cours[carte_id] = self.en_cours.get(carte_id, 0) + 1
        with self.condition:
            self.restants += 1
        self.file.put((carte_id, a_envoyer, a_supprimer))
        return True

    def modifier(self, carte_id, foil, **changements):
        version = dict(self.version(carte_id, foil))
        version.update(changements)
        version["quantite"] = max(0, min(version["quantite"], 99))
        version["a_echanger"] = max(0, min(version["a_echanger"], version["quantite"]))
        return self.enregistrer(carte_id, [version])

    def envoyer(self):
        while True:
            travail = self.file.get()
            if travail is None:
                return
            carte_id, a_envoyer, a_supprimer = travail
            envoyees = []
            supprimees = []
            erreur = ""
            try:
                if a_envoyer:
                    supabase_client.enregistrer_versions(self.user_id, carte_id, a_envoyer)
                    envoyees = a_envoyer
                for foil in a_supprimer:
                    supabase_client.supprimer_version(carte_id, foil)
                    supprimees.append(foil)
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
                self.envoi_fini.emit(carte_id, envoyees, supprimees, erreur)
            except RuntimeError:
                return

    def fin_envoi(self, carte_id, envoyees, supprimees, erreur):
        for version in envoyees:
            self.confirmees[(carte_id, version["foil"])] = dict(version)
        for foil in supprimees:
            self.confirmees.pop((carte_id, foil), None)
        if erreur:
            self.echecs[carte_id] = erreur
            with self.condition:
                self.echecs_non_vus -= 1
        self.en_cours[carte_id] -= 1
        if self.en_cours[carte_id]:
            return
        del self.en_cours[carte_id]
        for foil in (False, True):
            cle = (carte_id, foil)
            if cle in self.confirmees:
                self.versions[cle] = dict(self.confirmees[cle])
            else:
                self.versions.pop(cle, None)
        erreur = self.echecs.pop(carte_id, "")
        if erreur:
            self.envoi_echoue.emit(carte_id, erreur)
        else:
            self.envoi_reussi.emit(carte_id)

    def attendre_envois(self):
        with self.condition:
            termine = self.condition.wait_for(lambda: self.restants == 0, timeout=ATTENTE_FERMETURE)
            return termine and self.echecs_non_vus == 0

    def arreter(self):
        self.file.put(None)

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
