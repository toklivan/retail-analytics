# Retail Analytics

Un outil d'analyse et de pilotage pour un commerce d'alimentation de proximité. Il part des données que le commerce produit déjà (les ventes de la caisse, les factures des fournisseurs, le relevé bancaire) et les transforme en réponses concrètes : quels rayons font la marge, quand un fournisseur augmente ses prix, ce qui va manquer en rayon, ce que le mois a réellement rapporté.

**État : en construction.** La première version (v0.1.0) est en cours. Ce qui fonctionne déjà est listé dans [État actuel](#état-actuel). Le reste est décrit dans la [feuille de route](ROADMAP.md).

## Pourquoi ce projet

J'ai tenu un commerce d'alimentation de proximité pendant une dizaine d'années. La caisse enregistre chaque vente, les factures arrivent chaque semaine, la banque envoie son relevé chaque mois. Les données sont là. Ce qui manque, c'est le temps de les croiser.

Résultat : on sait à peu près quels rayons rapportent, on remarque une hausse fournisseur quand elle est grosse, et on découvre en fin d'année ce que le commerce a vraiment gagné.

Même la marge affichée par la caisse est approximative. Elle repose sur un prix d'achat unique par produit, à corriger à la main à chaque changement de tarif, au moment précis où l'ancien stock est écoulé. Sur des centaines de références, personne ne le fait. Ce projet calcule le coût réel de chaque vente à partir des livraisons, lot par lot.

Ce projet part des questions que je me posais en boutique :

- Quels rayons font la marge, et lesquels ne font que du chiffre ?
- Quels produits pèsent vraiment, et lesquels prennent de la place pour rien ?
- Ce fournisseur a changé son prix : promo temporaire ou vraie hausse ? Dois-je changer mon prix de vente ?
- Qu'est-ce qui va manquer en rayon, et qu'est-ce qui dort en réserve ?
- Ce mois-ci, combien le commerce a-t-il réellement gagné ?
- À quelles heures et quels jours il se passe quelque chose ?

## Où va le projet

```mermaid
flowchart LR
    A[Ventes de la caisse] --> O(Retail Analytics)
    I[Inventaire] --> O
    B[Factures et tickets en photo] --> O
    C[Relevé bancaire] --> O
    O --> D[Indicateurs et rapport mensuel]
    O --> E[Alertes de prix et de stock]
    O --> F[Tableau de pilotage]
```

Le projet avance par phases. Chaque phase ajoute une source de données, et chaque source débloque de nouvelles réponses.

| Phase | Source ajoutée | Ce que l'outil sait faire à la fin de la phase | Versions | État |
|---|---|---|---|---|
| 1. Comprendre les ventes | Exports de caisse | Chiffre d'affaires par rayon et par produit, classement ABC, comparaison mensuelle, analyse par jour et par heure, rapport mensuel | v0.1 à v0.4 | En cours |
| 2. Le stock, les coûts et la marge | Inventaire, factures et tickets d'achat pris en photo | Stock par lots, coût réel de chaque vente (premier entré, premier sorti), marge par rayon, alertes de hausse avec prix de vente suggéré, distinction des promotions, démarque, alertes de rupture | v0.5 à v0.9 | Prévu |
| 3. Piloter les finances | Relevé bancaire, livre de caisse | Tableau de pilotage mensuel : chiffre d'affaires, marge, charges, résultat estimé, trésorerie | v0.10 | Prévu |
| 4. Devenir un produit | Connexion directe à la caisse | Tableau de bord, démo en ligne, ventes récupérées automatiquement | v1.0 à v1.2 | Prévu |

Chaque version est livrable, testée et taguée. Le détail version par version est dans [ROADMAP.md](ROADMAP.md), les changements livrés dans [CHANGELOG.md](CHANGELOG.md).

## État actuel

Version en cours : **v0.1.0, les fondations**.

- [ ] Générateur de données fictives (ventes et journées de caisse de janvier à mi-octobre 2026)
- [ ] Lecture et nettoyage des ventes, avec contrôles de cohérence
- [ ] Rattachement de chaque produit à un rayon
- [ ] Tests automatisés et intégration continue

## Données

Les données réelles d'un commerce ne sont jamais publiées. Le dépôt utilise uniquement un jeu de données fictif, produit par un script qui reproduit la structure d'un vrai export de caisse, ses défauts et les phénomènes du métier : saisonnalité, heures de pointe, promotions, hausses de prix fournisseurs. Les produits, prix et quantités sont inventés.

La stratégie complète est décrite dans [docs/donnees.md](docs/donnees.md).

## Technique

Python, pandas, matplotlib, pytest, GitHub Actions.

## Auteur

Livan, étudiant à 42 Marseille, en reconversion vers le développement et la data après dix ans de commerce.
