# Développement

- Interface : PySide6 (Qt)
- Comptes et collection en ligne : Supabase
- Données des cartes : API Riftcodex

## Organisation du projet

```
main.py                    point de départ de l'appli
app/
├── infos.py               nom, version, dépôt GitHub, emplacement des dossiers
├── journal.py             fichier erreurs.log
├── donnees/               tout ce qui lit, télécharge ou enregistre (rien ne s'affiche ici)
│   ├── catalogue.py           base locale des cartes (SQLite) et règles des foils
│   ├── import_catalogue.py    téléchargement du catalogue depuis Riftcodex
│   ├── images.py              images des cartes et icônes officielles
│   ├── collection.py          collection du joueur et sauvegarde en arrière-plan
│   ├── classeurs.py           classeurs, pochettes, remplissage automatique, sauvegarde en arrière-plan
│   ├── supabase_client.py     comptes, connexion et requêtes Supabase
│   └── mises_a_jour.py        vérification des nouvelles versions sur GitHub
└── interface/             tout ce qui s'affiche
    ├── theme.py               couleurs des modes clair et sombre, polices, feuille de style, choix du thème
    ├── icones.py              icônes SVG recolorées selon le thème
    ├── fenetre_connexion.py   connexion et inscription
    ├── fenetre_principale.py  barre latérale et pages
    ├── pages/                 une page par entrée de la barre latérale (page_classeurs.py : les classeurs)
    └── composants/            morceaux réutilisés par les pages (grille, panneau, filtres, effets 3D…)
                               elements.py : titres, cartes, interrupteur, avatar, choix du thème,
                               onglets avec nombre, pastille d'état, état vide, mise en page en flux
ressources/                icône de l'appli, polices (polices/) et icônes (icones/)
supabase/                  scripts SQL du serveur, à lancer dans l'ordre
construction/              fabrication du .exe et de l'installateur
```

Règle à garder : un fichier de `donnees/` n'importe jamais rien de `interface/`.

## Thème, polices et icônes

- Deux palettes dans `app/interface/theme.py` : `sombre` et `clair`. Le choix (Clair, Sombre ou Système) est gardé dans les réglages Windows de l'appli (clé `theme`). « Système » suit le mode de Windows, même pendant que l'appli est ouverte.
- Les widgets dessinés à la main lisent les couleurs au moment de dessiner (`theme.OR`, `theme.couleur("TEXTE", alpha)`…). Pour un dessin gardé en cache, écouter `theme.signaux().change`.
- Polices : Cinzel (titres, gras 800, en majuscules) et Albert Sans (texte), sous licence OFL. Les fichiers de `ressources/polices/` sont des versions à graisse fixe, tirées des polices variables de Google Fonts.
- Icônes : Lucide, licence ISC. Pour en ajouter une, copier son fichier `.svg` depuis lucide.dev dans `ressources/icones/`, puis l'utiliser avec `icones.lier(bouton, "nom")` (elle change de couleur avec le thème).
- Code imprimé d'une carte (« OGN 019 / 298 ») : `catalogue.code_affiche(carte, avec_total)`. Il est tiré du code Riftcodex (`ogn-019-298`).
- Pastilles de la grille : dorée = exemplaires possédés, contour arc-en-ciel = au moins une foil, cœur bleu = carte recherchée mais pas encore possédée.

## Classeurs

- Un classeur a un format (colonnes × rangées par page), un nombre de pages et une couleur. Ses pochettes sont numérotées à partir de 0, page après page : la pochette `n` est en page `n // (colonnes × rangées) + 1`. Changer le format garde l'ordre des cartes.
- Une pochette garde seulement la carte et les exemplaires qu'elle compte (`toutes`, `normale` ou `foil`). Le nombre affiché vient de la collection : rien n'est saisi deux fois. Une carte qu'on n'a pas reste pâle dans sa pochette.
- `classeurs.py` (données) : liste, contenu, créer, modifier, supprimer, placer, déplacer (échange si la pochette d'arrivée est prise), vider, remplir. Chaque changement s'affiche tout de suite et part au serveur dans un fil à part, dans l'ordre. Si un envoi rate, l'appli relit les classeurs du serveur dès qu'elle le peut.
- Interface : `composants/vue_classeur.py` dessine le classeur ouvert (double page, anneaux, glisser-déposer, clavier), `composants/fenetres_classeur.py` contient les fenêtres Nouveau / Modifier, Remplir et Choisir une carte.
- Si les tables n'existent pas sur le serveur, la page Classeurs le dit et demande de lancer `supabase/3_classeurs.sql`.

## Lancer depuis le code

1. `pip install -r requirements.txt`
2. Mettre un fichier `.env` à côté de `main.py`, avec `SUPABASE_URL` et `SUPABASE_PUBLISHABLE_KEY`.
3. `python main.py`

## Recréer le serveur Supabase

Dans un nouveau projet Supabase, ouvrir « SQL Editor » et lancer, une seule fois chacun et dans cet ordre :

1. `supabase/1_tables.sql` : tables, sécurité ligne par ligne, création du profil à l'inscription.
2. `supabase/2_echanges.sql` : contact des joueurs et recherche des échanges.
3. `supabase/3_classeurs.sql` : tables `classeurs` et `classeur_pochettes`, chacun ne voit et ne modifie que ses classeurs.

Une prochaine modification du serveur ira dans un nouveau fichier `4_....sql`. Sur un serveur qui existe déjà, on ne lance que les fichiers nouveaux.

## Inscriptions (réglages Supabase)

Dans le tableau de bord Supabase, partie Authentication :

- « Allow new users to sign up » doit être activé.
- « Confirm email » activé : chaque nouveau joueur reçoit un mail de confirmation. Il faut alors un service d'e-mail à soi (Custom SMTP), car celui fourni par Supabase n'envoie qu'aux membres de l'équipe du projet, et 2 mails par heure au plus. Mettre aussi la Site URL (URL Configuration) sur la page GitHub du projet : c'est là qu'arrive le joueur après avoir cliqué sur le lien.
- « Confirm email » désactivé : le compte marche tout de suite, sans mail.

L'appli gère les deux cas : sans confirmation, elle ouvre directement la collection après l'inscription.

## Fabriquer l'installateur (Windows)

1. Installer Inno Setup 6.3 ou plus récent : https://jrsoftware.org/isdl.php
2. `pip install -r construction/requirements.txt`
3. `python construction/construire.py`

Résultat dans `dist/` : le dossier `RiftboundCollection` (l'appli) et `RiftboundCollection-Setup-<version>.exe` (l'installateur).

Le script refuse de continuer si le `.env` contient une clé secrète. Seules `SUPABASE_URL` et la clé publique `SUPABASE_PUBLISHABLE_KEY` sont mises dans l'appli.

## Publier une nouvelle version

1. Changer `VERSION` dans `app/infos.py` (par exemple `1.0.2`).
2. `python construction/construire.py`
3. Sur GitHub : Releases, « Draft a new release », tag `V1.0.2` (même forme que les précédents), joindre l'installateur.
