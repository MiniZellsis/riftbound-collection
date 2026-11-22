# Riftbound Collection

Riftbound Collection est un logiciel gratuit pour Windows qui sert à gérer ta collection de cartes **Riftbound**.

- Parcours tout le catalogue, set par set, avec les images des cartes.
- Note combien d'exemplaires tu as de chaque carte, en version normale ou foil.
- Retrouve vite une carte grâce à la recherche et aux filtres (domaine, rareté, type).
- Suis ta progression dans chaque set.
- Indique tes doubles et les cartes que tu cherches, pour trouver des échanges avec les autres joueurs.

Ta collection est enregistrée en ligne : tu la retrouves sur n'importe quel PC où tu te connectes.

## Installer

1. Va sur la page des [versions](https://github.com/MiniZellsis/riftbound-collection/releases/latest).
2. Télécharge le fichier `RiftboundCollection-Setup-….exe`.
3. Lance-le et suis les étapes. Pas besoin d'être administrateur du PC.

Au premier lancement, Windows peut afficher « Windows a protégé votre ordinateur ». C'est normal pour un petit logiciel indépendant : clique sur « Informations complémentaires », puis sur « Exécuter quand même ».

## Premier lancement

- Clique sur **Pas encore de compte ? Créer un compte**. Entre ton adresse e-mail, choisis un pseudo (les autres joueurs le verront) et un mot de passe d'au moins 6 caractères.
- Si tu reçois un mail de confirmation, clique sur le lien qu'il contient, puis reviens dans le logiciel pour te connecter. Pense à regarder dans tes spams.
- Coche « Rester connecté » pour ne pas retaper ton mot de passe à chaque fois.
- La première fois, le logiciel télécharge le catalogue et les images des cartes. Ça peut prendre quelques minutes, ensuite tout est gardé sur ton PC.

## Utilisation

- **Clic sur une carte :** ouvre son détail à droite. Tu peux y indiquer combien tu en as, combien sont à échanger, et si tu la recherches. Tout est enregistré tout seul.
- **Clic droit sur une carte :** ajoute ou retire un exemplaire en un clic.
- **Curseur en haut à droite :** change la taille des cartes.
- Les cartes que tu n'as pas sont affichées en pâle.
- Les cartes Rare, Epic et Showcase n'existent qu'en foil : elles sont comptées en foil automatiquement.

### Classeurs

- **Nouveau classeur :** choisis le même format que ton vrai classeur (pochettes par page et capacité) et sa couleur.
- **Remplir :** le logiciel range tes cartes dans l'ordre (set, puis numéro). Tu peux aussi garder une pochette vide pour chaque carte qui te manque.
- **Variantes :** par défaut, les arts alternatifs et les signatures vont dans la même pochette que la carte de base (OGN 030a et OGN 030b avec OGN 030). La pochette montre alors une petite pile, et le détail affiche une ligne **Versions** pour passer de l'une à l'autre. Tu peux aussi choisir « Dans leur propre pochette ».
- Une variante rangée à la main dans une autre pochette sort de la pile. Les cartes surnumérotées (OGN 299 / 298) gardent leur propre pochette.
- **À la suite des cartes rangées :** seules les cartes qui ne sont pas encore dans le classeur sont ajoutées.
- **À la main :** double-clic sur une pochette vide pour y placer une carte, glisser-déposer pour déplacer une carte, Suppr pour vider une pochette.
- Le nombre sur une pochette (×2, ×3) est celui de ta collection : rien à saisir deux fois.
- Dans le détail d'une carte, la partie **Dans mes classeurs** dit où elle est rangée (page, rangée, colonne). « Voir » ouvre le classeur à la bonne page.
- **Les cartes d'arènes** sont tournées pour tenir debout dans les pochettes et dans les grilles.

### Decks

- **Nouveau deck :** choisis d'abord la légende (elle donne les domaines du deck), puis ajoute les cartes depuis « Ajouter » (double-clic). Le champion choisi est pris tout seul parmi les champions de ta légende.
- **Importer :** colle une liste copiée sur un site de decks (Piltover Archive, les « Top Decks » de Riot…) ou un code de deck. Le logiciel dit quelles lignes il n'a pas reconnues.
- **Règles :** le logiciel vérifie le deck (40 cartes avec le champion, 12 runes, 3 arènes de noms différents, 3 exemplaires au plus, domaines de la légende, réserve de 8 cartes au plus). Il prévient, mais ne bloque rien.
- **Stats :** la courbe de coût et le nombre d'unités, de sorts et d'équipements.
- **À sortir :** où sont les cartes du deck dans tes classeurs, dans l'ordre des pages. « Voir » ouvre le classeur avec les cartes du deck entourées en or (tu peux aussi choisir le deck dans la liste « Surligner un deck » de la page Classeurs).
- **Manquantes :** les cartes qui te manquent (toutes versions comprises). Un bouton les marque comme recherchées, pour les échanges.
- **Monté :** quand tu montes le deck avec tes vraies cartes, coche « Monté ». Ses cartes sont alors signalées dans tes classeurs (petit badge) et dans le détail des cartes (partie **Dans mes decks**).
- Clic droit sur une carte du catalogue ou de ta collection → **Ajouter à un deck**.

### Raccourcis clavier

| Touches | Action |
|---|---|
| Ctrl+F | Rechercher une carte |
| Ctrl+1 à Ctrl+7 | Changer de page |
| Flèches | Passer d'une carte ou d'une pochette à l'autre |
| Page préc. / Page suiv. | Tourner les pages d'un classeur |
| Suppr | Vider la pochette choisie |
| Échap | Fermer le détail d'une carte |

## Mises à jour

Au démarrage, le logiciel vérifie s'il existe une nouvelle version. Si oui, un bandeau te propose de la télécharger : installe-la par-dessus l'ancienne, ta collection ne bouge pas.

Tu peux aussi vérifier à la main dans **Réglages**, partie **À propos**.

## Un problème ?

- Le catalogue est vide ou incomplet : va dans **Réglages** et clique sur **Mettre à jour le catalogue**.
- Le logiciel affiche une erreur : les détails sont enregistrés dans le fichier `erreurs.log`. Pour le trouver, va dans **Réglages**, puis **Ouvrir le dossier**. Tu peux joindre ce fichier quand tu signales le problème dans l'onglet [Issues](https://github.com/MiniZellsis/riftbound-collection/issues).

## Désinstaller

Va dans les **Paramètres de Windows**, puis **Applications**, et désinstalle **Riftbound Collection**. Ta collection reste enregistrée en ligne.

## Mentions

Données des cartes : Riftcodex. Images des cartes : Riot Games.

Riftbound Collection n'est pas approuvé par Riot Games et ne reflète pas les opinions de Riot Games ni de quiconque officiellement impliqué dans la production ou la gestion des propriétés de Riot Games. Riot Games et toutes les propriétés associées sont des marques commerciales ou des marques déposées de Riot Games, Inc.
