"""
Tout ce qui parle à Supabase passe par ce fichier.
Les fenêtres n'appellent jamais Supabase directement : elles appellent
ces fonctions. Si un jour on change de service, seul ce fichier bouge.
"""
import os

import httpx
from dotenv import load_dotenv
from supabase import AuthApiError, AuthError, PostgrestAPIError, create_client

# Lit SUPABASE_URL et SUPABASE_PUBLISHABLE_KEY dans le fichier .env
load_dotenv()
_client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_PUBLISHABLE_KEY"],
)

MESSAGE_RESEAU = "Impossible de joindre le serveur. Vérifie ta connexion Internet."
LIGNES_PAR_PAGE = 1000  # Supabase renvoie 1000 lignes maximum par requête


class ErreurSupabase(Exception):
    """Une erreur avec un message lisible, prêt à afficher dans une fenêtre."""


def _executer(requete):
    """Envoie une requête à la base et traduit les erreurs en français."""
    try:
        return requete.execute()
    except httpx.HTTPError:
        raise ErreurSupabase(MESSAGE_RESEAU)
    except PostgrestAPIError as erreur:
        if erreur.code == "PGRST301":  # jeton de connexion expiré ou invalide
            raise ErreurSupabase("Ta session a expiré. Déconnecte-toi puis reconnecte-toi.")
        raise ErreurSupabase(f"Erreur de la base : {erreur.message}")


def se_connecter(email, mot_de_passe):
    """Connecte l'utilisateur et renvoie son identifiant (uuid)."""
    try:
        reponse = _client.auth.sign_in_with_password({
            "email": email,
            "password": mot_de_passe,
        })
    except AuthApiError as erreur:
        # Supabase renvoie un code précis : on le traduit en français
        if erreur.code == "invalid_credentials":
            raise ErreurSupabase("E-mail ou mot de passe incorrect.")
        if erreur.code == "email_not_confirmed":
            raise ErreurSupabase("Confirme d'abord ton e-mail (lien reçu par mail).")
        raise ErreurSupabase(erreur.message)
    except (AuthError, httpx.HTTPError):
        # Pas d'Internet, serveur en pause ou injoignable
        raise ErreurSupabase(MESSAGE_RESEAU)
    return reponse.user.id


def se_deconnecter():
    """Ferme la session. Même sans Internet, on oublie le jeton localement."""
    try:
        _client.auth.sign_out()
    except (AuthError, httpx.HTTPError):
        pass


def lire_pseudo(user_id):
    """Renvoie le pseudo de l'utilisateur."""
    reponse = _executer(
        _client.table("profils").select("pseudo").eq("id", user_id).single()
    )
    return reponse.data["pseudo"]


def lire_collection():
    """Toutes les lignes de collection de l'utilisateur connecté."""
    # Pas besoin de filtrer sur user_id : le RLS ne renvoie que nos lignes.
    # Supabase s'arrête à 1000 lignes par réponse, donc on lit page par page.
    lignes = []
    debut = 0
    while True:
        reponse = _executer(
            _client.table("collection")
            .select("carte_id, foil, quantite, a_echanger, recherche")
            .order("id")  # un ordre fixe, sinon des lignes pourraient sauter d'une page à l'autre
            .range(debut, debut + LIGNES_PAR_PAGE - 1)
        )
        lignes += reponse.data
        if len(reponse.data) < LIGNES_PAR_PAGE:
            return lignes
        debut += LIGNES_PAR_PAGE


def enregistrer_versions(user_id, carte_id, versions):
    """
    Ajoute ou met à jour des versions d'une carte (normale et/ou foil).
    Chaque version est un dictionnaire : foil, quantite, a_echanger, recherche.
    """
    lignes = [{"user_id": user_id, "carte_id": carte_id, **version} for version in versions]
    # upsert = insert, ou update si la ligne (user_id, carte_id, foil) existe déjà
    _executer(
        _client.table("collection").upsert(lignes, on_conflict="user_id,carte_id,foil")
    )


def supprimer_version(carte_id, foil):
    """Supprime la ligne d'une version (le RLS limite la suppression à nos lignes)."""
    _executer(
        _client.table("collection").delete().eq("carte_id", carte_id).eq("foil", foil)
    )