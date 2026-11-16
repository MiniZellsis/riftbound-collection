# Développement

- Interface : PySide6 (Qt)
- Comptes et collection en ligne : Supabase
- Données des cartes : API Riftcodex

## Lancer depuis le code

1. `pip install -r requirements.txt`
2. Mettre un fichier `.env` à côté de `main.py`, avec `SUPABASE_URL` et `SUPABASE_PUBLISHABLE_KEY`.
3. `python main.py`

## Fabriquer l'installateur (Windows)

1. Installer Inno Setup 6.3 ou plus récent : https://jrsoftware.org/isdl.php
2. `pip install -r requirements-construction.txt`
3. `python construire.py`

Résultat dans `dist/` : le dossier `RiftboundCollection` (l'appli) et `RiftboundCollection-Setup-<version>.exe` (l'installateur).

Le script refuse de continuer si le `.env` contient une clé secrète. Seules `SUPABASE_URL` et la clé publique `SUPABASE_PUBLISHABLE_KEY` sont mises dans l'appli.

## Inscriptions (réglages Supabase)

Dans le tableau de bord Supabase, partie Authentication :

- « Allow new users to sign up » doit être activé.
- « Confirm email » activé : chaque nouveau joueur reçoit un mail de confirmation. Il faut alors un service d'e-mail à soi (Custom SMTP), car celui fourni par Supabase n'envoie qu'aux membres de l'équipe du projet, et 2 mails par heure au plus. Mettre aussi la Site URL (URL Configuration) sur la page GitHub du projet : c'est là qu'arrive le joueur après avoir cliqué sur le lien.
- « Confirm email » désactivé : le compte marche tout de suite, sans mail.

L'appli gère les deux cas : sans confirmation, elle ouvre directement la collection après l'inscription.

## Publier une nouvelle version

1. Changer `VERSION` dans `app/infos.py` (par exemple `1.0.1`).
2. `python construire.py`
3. Sur GitHub : Releases, « Draft a new release », tag `v1.0.1`, joindre l'installateur.
