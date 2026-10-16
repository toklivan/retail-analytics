# Feuille de route

Chaque version répond à une question que se pose un commerçant. Elle est livrable seule, testée, et laisse le dépôt dans un état propre. L'ordre des versions suit les données : on n'exploite une source que lorsque la précédente est maîtrisée.

Légende : **Livré** · **En cours** · **Prévu**

---

## Phase 1 : comprendre les ventes

Source : les exports de la caisse.

### v0.1.0 : les fondations (Livré)

> Mes données de caisse sont-elles exploitables ?

- Modèle de données documenté pour l'ensemble du projet ([docs/donnees.md](docs/donnees.md))
- Générateur de données fictives : ventes et journées de caisse de janvier à mi-octobre 2026, au format exact des exports et avec leurs défauts
- Lecture et nettoyage des ventes : colonnes traduites, montants convertis, articles offerts repérés, rattachement de chaque ticket à sa journée de caisse
- Contrôles de cohérence : lignes, total du ticket, paiements et totaux de la journée doivent concorder au centime
- Rattachement de chaque produit à un rayon par une table de correspondance
- Part du chiffre d'affaires non rattachée à un rayon, signalée plutôt que devinée
- Tests et intégration continue

Terminé quand : une commande produit un fichier de ventes propre et catégorisé à partir du jeu fictif, et les tests passent en CI.

### v0.2.0 : les indicateurs de vente (En cours)

> Qu'est-ce qui se vend vraiment ?

- Chiffre d'affaires HT et quantités par rayon et par produit
- Panier moyen, nombre de tickets, valeur des articles offerts au prix de vente
- Ventes par moyen de paiement (espèces, carte, plateforme de livraison), panier moyen séparé pour le magasin et la livraison
- Classement ABC des produits sur le chiffre d'affaires
- Comparaison d'un mois sur l'autre, avec signalement des mois incomplets

Pas encore de marge : le coût d'achat saisi dans la caisse n'est pas fiable, et le vrai coût arrive en v0.7.

### v0.3.0 : le rapport mensuel (Prévu)

> Qu'est-ce que je dois retenir de ce mois ?

- Graphiques par rayon et par produit
- Rapport généré en une commande, lisible par un commerçant

### v0.4.0 : le rythme du magasin (Prévu)

> Quand se passe-t-il quelque chose ?

- Ventes et panier moyen par jour de la semaine et par heure
- Carte de chaleur jour × heure

---

## Phase 2 : le stock, les coûts et la marge

Sources : l'inventaire, puis les achats : factures et tickets pris en photo, factures électroniques, exports des fournisseurs.

### v0.5.0 : l'inventaire (Prévu)

> Qu'est-ce que j'ai en rayon, et combien ?

- Import d'un comptage d'inventaire : code-barres, libellé, quantité
- Référentiel produits : chaque libellé de caisse relié à son code-barres et à son rayon
- Liste des produits comptés jamais vendus, et des produits vendus jamais comptés

Décision à prendre avant de commencer : le format de saisie de l'inventaire et la façon de relier le code-barres au libellé de caisse.

### v0.6.0 : les achats en photo (Prévu)

> Je prends ma facture en photo, l'outil fait le reste.

- Photo ou scan d'une facture papier ou d'un ticket de caisse, et PDF reçu par e-mail : lecture du document, lignes proposées sous forme de données
- Contrôles automatiques : total des lignes égal au total du document, TVA cohérente, prix plausibles par rapport aux achats précédents
- Rattachement des lignes aux produits du référentiel, avec mémoire des rattachements par fournisseur
- Écran de validation : la photo à côté des lignes proposées, les lignes douteuses en évidence ; rien n'entre en stock sans validation
- Factures électroniques (Factur-X) lues directement, exports d'historique des fournisseurs importés
- Saisie manuelle en dernier recours, dans les mêmes écrans
- Coût unitaire réel : colisage, remises et gratuités ramenés à l'unité vendue

Décisions à prendre avant de commencer : le service de lecture des images (coût par document, confidentialité, conservation des données) et l'outil des écrans de validation.

### v0.7.0 : le coût réel et la marge (Prévu)

> Quels rayons font vraiment la marge ?

- Stock par lots : chaque livraison crée un lot avec sa quantité et son coût
- Moteur premier entré, premier sorti : chaque vente consomme le lot le plus ancien, au besoin à cheval sur deux lots
- Marge brute, taux de marque et taux de marge par vente, produit et rayon
- Classement ABC sur la marge
- Coût des articles offerts, ventes sans stock connu signalées puis régularisées
- Valeur du stock au coût réel
- Reconstitution d'une période passée : à partir des factures et des ventes depuis le début de l'année et d'un inventaire d'aujourd'hui, stock de départ estimé et démarque minimale par produit
- Rapport des anomalies : produits vendus sans facture, factures sans vente, pertes anormales

Décision à prendre avant de commencer : le stockage persistant des lots (fichiers ou base SQLite), puisqu'ils doivent survivre d'un mois sur l'autre.

### v0.8.0 : les alertes de prix (Prévu)

> Mon fournisseur a changé son prix : est-ce que je change le mien ?

- Détection d'un lot plus cher ou moins cher que le précédent, au-delà d'un seuil
- Nombre d'unités restant à l'ancien prix, pour savoir quand la hausse touchera la marge
- Distinction entre promotion, hausse durable et cas douteux :
  - remise, gratuité ou mention promotionnelle sur la facture : promotion, pas d'alerte
  - baisse isolée suivie d'un retour au prix habituel : promotion reconnue après coup
  - hausse sans remise, confirmée sur deux livraisons : hausse durable, alerte
  - tout le reste : demande de validation
- Prix de vente suggéré pour retrouver le taux de marque cible, arrondi à un prix commercial
- Journal des décisions : suggestion acceptée, modifiée ou refusée

### v0.9.0 : le suivi du stock (Prévu)

> Qu'est-ce qui va manquer, qu'est-ce qui dort ?

- Nouvel inventaire : démarque inconnue en quantité et en euros
- Alertes de rupture à partir du rythme de vente
- Liste des produits dormants et de l'argent qu'ils immobilisent

---

## Phase 3 : piloter les finances

Sources : le relevé bancaire et le livre de caisse.

### v0.10.0 : le pilotage mensuel (Prévu)

> Ce mois-ci, combien le commerce a-t-il gagné ?

- Import du relevé bancaire (CSV ou OFX)
- Classement des opérations : fournisseurs, loyer, énergie, salaires, encaissements carte
- Rapprochement des ventes carte de la caisse avec les virements du prestataire de paiement, pour mesurer les commissions réelles
- Suivi des espèces : du tiroir-caisse au dépôt en banque
- Ventes par plateforme de livraison : chiffre d'affaires, commissions, marge réelle
- Tableau mensuel : chiffre d'affaires, marge, charges, résultat estimé, trésorerie

Limite assumée : c'est un outil de pilotage, pas une comptabilité. Il ne remplace pas l'expert-comptable.

---

## Phase 4 : devenir un produit

### v1.0.0 : l'application (Prévu)

- Tableau de bord interactif couvrant les phases 1 à 3
- Démo en ligne sur le jeu de données fictif

### v1.1.0 : la connexion à la caisse (Prévu)

- Récupération automatique des ventes par l'API du fournisseur de caisse (SumUp en premier), à la place de l'export manuel
- Clés d'accès stockées hors du dépôt

### v1.2.0 : l'envoi des documents (Prévu)

- Photo d'une facture ou d'un ticket prise directement depuis le téléphone, au moment de la livraison
- Dépôt d'un relevé ou d'un comptage d'inventaire depuis le téléphone

---

## Pistes après la v1

- Prévision des ventes par produit et par jour
- Détection des produits en perte de vitesse
- Suggestions de commande à partir du stock et du rythme de vente
