# Journal des versions

Toutes les évolutions notables du projet sont consignées ici. Les numéros de version suivent le [versionnage sémantique](https://semver.org/lang/fr/) : `MAJEUR.MINEUR.CORRECTIF`.

## [Non publié]

## [0.3.0] - 2026-10-19

### Ajouté

- Commande `rapport` : rapport mensuel des ventes en une page HTML autonome, graphiques compris, imprimable en PDF depuis le navigateur
- Graphiques du chiffre d'affaires HT par mois, par rayon comparé au mois précédent, et des dix premiers produits
- Points à retenir du mois : rayon qui progresse le plus, rayon qui recule le plus (classés en euros), produit n°1
- Section « Fiabilité des données » : part du chiffre d'affaires sans rayon, libellés à ajouter à la table de correspondance, résultat des contrôles

## [0.2.0] - 2026-10-16

### Ajouté

- Commande `indicateurs` : indicateurs de vente par mois de journée commerciale, et détail d'un mois choisi (option `--mois`)
- Chiffre d'affaires TTC et HT, tickets payants et tickets offerts
- Encaissements par moyen de paiement (espèces, carte, plateforme de livraison), avec signalement des moyens inconnus
- Panier moyen TTC, séparé pour le magasin et la livraison
- Nombre et valeur au prix de vente des articles offerts
- Chiffre d'affaires HT et quantités vendues par rayon et par produit, ventes sans rayon comprises
- Classement ABC des produits sur le chiffre d'affaires d'un mois
- Comparaison du chiffre d'affaires par rayon avec le mois précédent
- Lecture de la période couverte par chaque export, et signalement des mois incomplets

### Modifié

- Les ventes par plateforme de livraison sont comptées dans le chiffre d'affaires et distinguées par leur moyen de paiement
- Le générateur utilise le libellé réel de la plateforme de livraison dans les exports fictifs

## [0.1.0] - 2026-10-15

### Ajouté

- Feuille de route du projet
- Stratégie de données : sources, modèle cible, jeu fictif, confidentialité
- Générateur du jeu fictif au format des exports de caisse (commande `generer`), avec sa vérité terrain et un extrait d'une semaine dans `data/exemple/`
- Lecture des exports Orders et Drawers, montants convertis en centimes
- Nettoyage : doublons entre exports, articles offerts, rattachement des tickets à leur journée de caisse
- Contrôles de cohérence au centime : lignes, paiements, totaux et remises des journées, tickets sans journée
- Rattachement des ventes aux rayons, libellés inconnus et part du chiffre d'affaires non rattachée
- Commande `nettoyer`, qui produit le fichier des ventes propres et catégorisées
- Tests, dont la vérification de la vérité terrain du jeu fictif, et intégration continue
