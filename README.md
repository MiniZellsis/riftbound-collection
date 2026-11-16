# Riftbound Collection

Logiciel Windows pour gérer sa collection de cartes Riftbound.

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

Résultat :

- `dist/RiftboundCollection/` : l'appli prête à lancer ;
- `dist/RiftboundCollection-Setup-<version>.exe` : l'installateur à partager.

Le script refuse de continuer si le `.env` contient une clé secrète. Seules `SUPABASE_URL` et la clé publique `SUPABASE_PUBLISHABLE_KEY` sont mises dans l'appli.

## Publier une nouvelle version

1. Changer `VERSION` dans `app/infos.py` (par exemple `1.0.1`).
2. `python construire.py`
3. Sur GitHub : Releases, puis « Draft a new release », tag `v1.0.1`, et joindre l'installateur.

Au démarrage, l'appli compare sa version avec la dernière release du dépôt et propose le téléchargement s'il y en a une plus récente.
