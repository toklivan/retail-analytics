# Journal des versions

Toutes les évolutions notables du projet sont consignées ici. Les numéros de version suivent le [versionnage sémantique](https://semver.org/lang/fr/) : `MAJEUR.MINEUR.CORRECTIF`.

## [Non publié]

### Ajouté

- Commande `indicateurs` : chiffre d'affaires TTC et HT, tickets payants et offerts, par mois de journée commerciale
- Encaissements par moyen de paiement (espèces, carte, plateforme de livraison), avec signalement des moyens inconnus

### Modifié

- Les ventes par plateforme de livraison sont comptées dans le chiffre d'affaires et distinguées par leur moyen de paiement

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
