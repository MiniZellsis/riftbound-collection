"""
Test de Supabase : inscription, connexion, ajout d'une carte et test d'attaque.
Lancer avec :  python test_supabase.py
"""
import getpass
import os
import uuid

from dotenv import load_dotenv
from supabase import AuthApiError, PostgrestAPIError, create_client

# Lit SUPABASE_URL et SUPABASE_PUBLISHABLE_KEY dans le fichier .env
load_dotenv()
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_PUBLISHABLE_KEY"],
)

# Une vraie carte Riftcodex (son riftbound_id), juste pour le test
CARTE_TEST = "ogs-009-024"


def inscription():
    email = input("E-mail (celui de ton compte Supabase) : ").strip()
    pseudo = input("Pseudo (3 à 20 caractères) : ").strip()
    # getpass masque la saisie : rien ne s'affiche quand tu tapes, c'est normal
    mot_de_passe = getpass.getpass("Mot de passe (6 caractères minimum) : ")

    # Le pseudo part dans les "métadonnées" du compte.
    # Le trigger creer_profil() le récupère pour remplir la table profils.
    supabase.auth.sign_up({
        "email": email,
        "password": mot_de_passe,
        "options": {"data": {"pseudo": pseudo}},
    })
    print("\nCompte créé ! Ouvre le mail de confirmation et clique sur le lien.")
    print("Ensuite, relance le script et choisis 2.")


def connexion():
    email = input("E-mail : ").strip()
    mot_de_passe = getpass.getpass("Mot de passe : ")
    reponse = supabase.auth.sign_in_with_password({
        "email": email,
        "password": mot_de_passe,
    })
    # À partir d'ici, la bibliothèque envoie le jeton de connexion
    # avec chaque requête : Supabase sait qui parle.
    return reponse.user


def tester_collection(utilisateur):
    # 1. Lire son profil
    profil = (
        supabase.table("profils")
        .select("pseudo")
        .eq("id", utilisateur.id)
        .single()
        .execute()
    )
    print(f"\nConnecté en tant que {profil.data['pseudo']}")

    # 2. Ajouter la carte de test (ou la mettre à jour si elle existe déjà)
    supabase.table("collection").upsert(
        {
            "user_id": utilisateur.id,
            "carte_id": CARTE_TEST,
            "foil": False,
            "quantite": 2,
            "a_echanger": 1,
            "recherche": False,
        },
        on_conflict="user_id,carte_id,foil",
    ).execute()

    # 3. Relire sa collection
    cartes = supabase.table("collection").select("*").execute()
    print(f"Ta collection contient {len(cartes.data)} ligne(s) :")
    for carte in cartes.data:
        print(
            f"  - {carte['carte_id']} | foil : {carte['foil']} | "
            f"quantité : {carte['quantite']} | à échanger : {carte['a_echanger']}"
        )

    # 4. Test d'attaque : écrire dans la collection de quelqu'un d'autre
    print("\nTest d'attaque : ajout d'une carte chez un autre joueur...")
    faux_joueur = str(uuid.uuid4())
    try:
        supabase.table("collection").insert(
            {"user_id": faux_joueur, "carte_id": CARTE_TEST, "quantite": 99}
        ).execute()
        print("  PROBLÈME : l'attaque a réussi, le RLS ne protège pas la table !")
    except PostgrestAPIError as erreur:
        print(f"  Bloqué par la base, c'est bon : {erreur.message}")

    # 5. Se déconnecter, puis essayer de lire la collection
    supabase.auth.sign_out()
    print("\nDéconnecté. Lecture de la collection sans être connecté...")
    try:
        supabase.table("collection").select("*").execute()
        print("  PROBLÈME : on a pu lire la table sans être connecté !")
    except PostgrestAPIError as erreur:
        print(f"  Refusé, c'est bon : {erreur.message}")


def main():
    print("1 = créer un compte")
    print("2 = se connecter et tester")
    choix = input("Ton choix : ").strip()

    try:
        if choix == "1":
            inscription()
        elif choix == "2":
            utilisateur = connexion()
            tester_collection(utilisateur)
        else:
            print("Choix inconnu.")
    except AuthApiError as erreur:
        # Erreurs de compte : mauvais mot de passe, e-mail non confirmé...
        print(f"\nErreur de compte : {erreur.message}")
        if "Database error" in erreur.message:
            print("Ton pseudo est sûrement déjà pris, trop court ou trop long.")


main()