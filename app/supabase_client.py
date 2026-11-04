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


class ErreurSupabase(Exception):
    """Une erreur avec un message lisible, prêt à afficher dans une fenêtre."""


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
    try:
        reponse = (
            _client.table("profils")
            .select("pseudo")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except httpx.HTTPError:
        raise ErreurSupabase(MESSAGE_RESEAU)
    except PostgrestAPIError as erreur:
        raise ErreurSupabase(f"Erreur de la base : {erreur.message}")
    return reponse.data["pseudo"]


def resume_collection():
    """Renvoie (nombre de cartes différentes, nombre total de cartes)."""
    try:
        # Le RLS ne renvoie que les lignes de l'utilisateur connecté
        reponse = _client.table("collection").select("quantite").execute()
    except httpx.HTTPError:
        raise ErreurSupabase(MESSAGE_RESEAU)
    except PostgrestAPIError as erreur:
        raise ErreurSupabase(f"Erreur de la base : {erreur.message}")
    lignes = reponse.data
    total = sum(ligne["quantite"] for ligne in lignes)
    return len(lignes), total