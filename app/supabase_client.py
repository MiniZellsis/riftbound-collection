import os

import httpx
import keyring
from dotenv import load_dotenv
from postgrest import ReturnMethod
from supabase import AuthApiError, AuthError, ClientOptions, PostgrestAPIError, create_client

from app.infos import DOSSIER_APPLI

load_dotenv(DOSSIER_APPLI / ".env")
URL = os.environ.get("SUPABASE_URL", "")
CLE = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
DELAI_MAX = 15

_client = None
if URL and CLE:
    _client = create_client(URL, CLE, options=ClientOptions(postgrest_client_timeout=DELAI_MAX))

MESSAGE_RESEAU = "Impossible de joindre le serveur. Vérifie ta connexion Internet."
MESSAGE_REGLAGES = (
    "Les réglages du serveur sont introuvables (fichier .env). "
    "Réinstalle l'appli, ou ajoute le fichier .env à côté de main.py."
)
MESSAGES_INSCRIPTION = {
    "user_already_exists": "Un compte existe déjà avec cette adresse e-mail. Connecte-toi.",
    "email_exists": "Un compte existe déjà avec cette adresse e-mail. Connecte-toi.",
    "weak_password": "Ce mot de passe est trop faible. Choisis-en un plus long, avec des lettres et des chiffres.",
    "email_address_invalid": "Cette adresse e-mail n'est pas valide.",
    "validation_failed": "Cette adresse e-mail n'est pas valide.",
    "signup_disabled": "Les inscriptions sont fermées pour l'instant.",
    "email_address_not_authorized": (
        "Le serveur ne peut pas envoyer le mail de confirmation à cette adresse. "
        "Préviens l'auteur du logiciel."
    ),
    "over_email_send_rate_limit": "Trop d'inscriptions en peu de temps. Réessaie dans une heure.",
    "over_request_rate_limit": "Trop d'essais en peu de temps. Réessaie dans quelques minutes.",
}
LIGNES_PAR_PAGE = 1000
SERVICE_COFFRE = "RiftboundCollection"
NOM_JETON = "refresh_token"

_rester_connecte = False


class ErreurSupabase(Exception):
    pass


def _sauver_jeton(jeton):
    try:
        keyring.set_password(SERVICE_COFFRE, NOM_JETON, jeton)
    except Exception:
        pass


def _lire_jeton():
    try:
        return keyring.get_password(SERVICE_COFFRE, NOM_JETON)
    except Exception:
        return None


def _oublier_jeton():
    try:
        keyring.delete_password(SERVICE_COFFRE, NOM_JETON)
    except Exception:
        pass


def _session_modifiee(evenement, session):
    if _rester_connecte and session and evenement in ("SIGNED_IN", "TOKEN_REFRESHED"):
        _sauver_jeton(session.refresh_token)


if _client is not None:
    _client.auth.on_auth_state_change(_session_modifiee)


def _verifier_reglages():
    if _client is None:
        raise ErreurSupabase(MESSAGE_REGLAGES)


def _executer(requete):
    try:
        return requete.execute()
    except httpx.HTTPError:
        raise ErreurSupabase(MESSAGE_RESEAU)
    except PostgrestAPIError as erreur:
        if erreur.code == "PGRST301":
            raise ErreurSupabase("Ta session a expiré. Déconnecte-toi puis reconnecte-toi.")
        raise ErreurSupabase(f"Erreur de la base : {erreur.message}")


def se_connecter(email, mot_de_passe, rester_connecte):
    global _rester_connecte
    _verifier_reglages()
    _rester_connecte = rester_connecte
    if not rester_connecte:
        _oublier_jeton()
    try:
        reponse = _client.auth.sign_in_with_password({
            "email": email,
            "password": mot_de_passe,
        })
    except AuthApiError as erreur:
        if erreur.code == "invalid_credentials":
            raise ErreurSupabase("E-mail ou mot de passe incorrect.")
        if erreur.code == "email_not_confirmed":
            raise ErreurSupabase("Confirme d'abord ton e-mail (lien reçu par mail).")
        raise ErreurSupabase(erreur.message)
    except (AuthError, httpx.HTTPError):
        raise ErreurSupabase(MESSAGE_RESEAU)
    return reponse.user.id


def message_inscription(erreur):
    if erreur.code in MESSAGES_INSCRIPTION:
        return MESSAGES_INSCRIPTION[erreur.code]
    if "database error saving new user" in (erreur.message or "").lower():
        return "Ce pseudo est déjà pris. Choisis-en un autre."
    if isinstance(erreur, AuthApiError) and 0 < erreur.status < 500:
        return f"Inscription impossible : {erreur.message}"
    return MESSAGE_RESEAU


def creer_compte(email, pseudo, mot_de_passe, rester_connecte):
    global _rester_connecte
    _verifier_reglages()
    _rester_connecte = rester_connecte
    if not rester_connecte:
        _oublier_jeton()
    try:
        reponse = _client.auth.sign_up({
            "email": email,
            "password": mot_de_passe,
            "options": {"data": {"pseudo": pseudo}},
        })
    except AuthError as erreur:
        raise ErreurSupabase(message_inscription(erreur))
    except httpx.HTTPError:
        raise ErreurSupabase(MESSAGE_RESEAU)
    if reponse.user is None:
        raise ErreurSupabase(MESSAGE_RESEAU)
    if reponse.user.identities == []:
        raise ErreurSupabase(MESSAGES_INSCRIPTION["user_already_exists"])
    if reponse.session is None:
        return None
    return reponse.user.id


def reprendre_session():
    global _rester_connecte
    _verifier_reglages()
    jeton = _lire_jeton()
    if not jeton:
        return None
    _rester_connecte = True
    try:
        reponse = _client.auth.refresh_session(jeton)
    except AuthApiError as erreur:
        if erreur.status >= 500:
            raise ErreurSupabase(MESSAGE_RESEAU)
        _rester_connecte = False
        _oublier_jeton()
        return None
    except (AuthError, httpx.HTTPError):
        raise ErreurSupabase(MESSAGE_RESEAU)
    return reponse.user.id


def se_deconnecter():
    global _rester_connecte
    _rester_connecte = False
    _oublier_jeton()
    try:
        _client.auth.sign_out({"scope": "local"})
    except (AuthError, httpx.HTTPError):
        pass


def lire_pseudo(user_id):
    reponse = _executer(
        _client.table("profils").select("pseudo").eq("id", user_id).single()
    )
    return reponse.data["pseudo"]


def _lire_par_pages(fabriquer_requete):
    lignes = []
    debut = 0
    while True:
        reponse = _executer(
            fabriquer_requete().range(debut, debut + LIGNES_PAR_PAGE - 1)
        )
        lignes += reponse.data
        if len(reponse.data) < LIGNES_PAR_PAGE:
            return lignes
        debut += LIGNES_PAR_PAGE


def lire_collection():
    return _lire_par_pages(
        lambda: _client.table("collection")
        .select("carte_id, foil, quantite, a_echanger, recherche")
        .order("id")
    )


def lire_echanges():
    return _lire_par_pages(
        lambda: _client.rpc("echanges_possibles")
        .order("pseudo")
        .order("carte_id")
        .order("foil")
        .order("sens")
    )


def lire_contact():
    return _executer(_client.rpc("mon_contact")).data or ""


def modifier_contact(user_id, contact):
    _executer(
        _client.table("profils")
        .update({"contact": contact or None}, returning=ReturnMethod.minimal)
        .eq("id", user_id)
    )


def enregistrer_versions(user_id, carte_id, versions):
    lignes = [{"user_id": user_id, "carte_id": carte_id, **version} for version in versions]
    _executer(
        _client.table("collection").upsert(lignes, on_conflict="user_id,carte_id,foil")
    )


def supprimer_version(carte_id, foil):
    _executer(
        _client.table("collection").delete().eq("carte_id", carte_id).eq("foil", foil)
    )
