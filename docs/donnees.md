# Stratégie de données

Ce document explique d'où viennent les données du projet, comment elles sont organisées, et pourquoi le dépôt ne contient que des données fictives.

## 1. Partir des questions, pas des données

On ne collecte pas tout « au cas où ». Chaque source entre dans le projet au moment où une question du commerçant en a besoin :

| Question | Données nécessaires | Arrivée |
|---|---|---|
| Qu'est-ce qui se vend, et combien ça rapporte en chiffre d'affaires ? | Ventes | v0.1 à v0.2 |
| Quand se passe-t-il quelque chose ? | Ventes horodatées | v0.4 |
| Qu'est-ce que j'ai en rayon ? | Inventaire | v0.5 |
| Combien m'a coûté ce que j'ai acheté ? | Factures fournisseurs | v0.6 |
| Quels rayons font vraiment la marge ? | Ventes, factures, inventaire, coût par lot | v0.7 |
| Dois-je changer mon prix de vente ? | Historique des lots, prix de vente | v0.8 |
| Qu'est-ce qui va manquer ? | Stock par lot, rythme des ventes | v0.9 |
| Combien ai-je gagné ce mois-ci ? | Relevé bancaire, paiements, mouvements d'espèces | v0.10 |

## 2. Trois niveaux de données

| Niveau | Où | Suivi par Git | Rôle |
|---|---|---|---|
| Réel | `data/raw/` | Non | Vérifier en local que l'outil tient face aux vraies données |
| Fictif | `data/fictif/` (généré), `data/exemple/` (petit extrait) | Extrait seulement | Faire tourner et montrer le projet |
| Tests | `tests/fixtures/` | Oui | Quelques lignes écrites à la main, une règle métier par fichier |

Le jeu fictif complet n'est pas versionné : il se régénère en une commande, à l'identique grâce à une graine aléatoire fixe. Un extrait d'une semaine est versionné pour qu'un visiteur puisse voir à quoi ressemblent les données sans rien installer.

Quand les données réelles révèlent un défaut nouveau (une colonne en plus, un format de date différent), ce défaut est reproduit dans le générateur et couvert par un test. Le réel nourrit le fictif, jamais l'inverse.

## 3. Une source, un adaptateur

Chaque source a son module de lecture, appelé adaptateur. Il transforme le format de la source en un format interne unique. Le reste du code (nettoyage, indicateurs, alertes) ne sait pas d'où viennent les données.

| Source | Format | Arrivée |
|---|---|---|
| Générateur fictif | Mêmes fichiers que les exports de la caisse, puis inventaires et factures | v0.1 |
| Ventes détaillées | Rapport « Orders » de la Caisse Pro SumUp | v0.1 |
| Journées de caisse | Rapport « Drawers » | v0.1 |
| Totaux par journée et par taux de TVA | Rapport « Accounting » | Contrôle dès v0.1 |
| Ventes par produit | Rapport « Product Sales » | Contrôle dès v0.1 |
| Inventaire | Fichier de comptage (section 6) | v0.5 |
| Achats | Photo ou scan des factures et tickets, PDF, facture électronique, export fournisseur, saisie manuelle en dernier recours (section 8) | v0.6 |
| Mouvements d'espèces | Rapport « Cashbook » | v0.10 |
| Relevé bancaire | CSV ou OFX | v0.10 |
| API de la caisse | JSON | v1.1 |

C'est ce découpage qui permet de passer de l'export manuel à la connexion directe sans réécrire les calculs : seul l'adaptateur change.

## 4. Les exports réels de la caisse

La structure de chaque export a été relevée sur une journée réelle. Aucune valeur réelle n'est reprise ici.

### Format commun

- Séparateur point-virgule, toutes les valeurs entre guillemets, encodage UTF-8.
- Noms de colonnes en anglais (`Closing Date`, `Sales incl Tax`…), traduits à la lecture.
- Montants en texte avec virgule décimale (`"12,40"`), sans symbole €.
- Dates au format `AAAA-MM-JJ HH:MM:SS`, ou `AAAA-MM-JJ` pour les rapports par journée.
- Des colonnes constantes (nom et identifiant du magasin, devise) retirées dès la lecture.
- Chaque rapport se décline en plusieurs fichiers : totaux, paiements, TVA, remboursements, annulations, dépenses, compte client, transferts entre moyens de paiement. Les fichiers vides gardent leur ligne d'en-tête.

### « Orders » : le détail des ventes

| Fichier | Une ligne par | Rôle |
|---|---|---|
| `products` | Article d'un ticket, avec sa quantité | Source principale des ventes |
| `totals` | Ticket | Contrôle, numéro et durée du ticket |
| `payments` | Paiement (un ticket peut en avoir plusieurs) | Contrôle, puis rapprochement bancaire |
| `tax` | Ticket et taux de TVA | Contrôle |
| `refunded-products` | Article remboursé | Retours, format à confirmer sur un jour avec remboursement |
| `canceled` | Article annulé | Exclu du chiffre d'affaires, compté et signalé |

Les fichiers sont reliés par `Order ID`, identifiant unique du ticket. L'heure de la vente est la date de clôture du ticket. Les montants HT et de TVA sont fournis ligne par ligne : on les lit, on ne les recalcule pas.

### « Drawers » : les journées de caisse

Une ligne par ouverture de caisse, avec sa date d'ouverture, sa date de fermeture et un identifiant. Un ticket appartient à la journée de caisse pendant laquelle il a été clos. C'est ce qui définit la `journee_commerciale`.

### « Product Sales » : les ventes par produit

Une ligne par produit vendu sur la période : quantité, prix d'achat, ventes TTC et HT, TVA, marge brute. Il sert de contrôle des quantités et des montants.

**Son prix d'achat et sa marge ne sont jamais utilisés.** Le prix d'achat est un champ unique par produit, saisi à la main dans la caisse. Pour qu'il soit juste, il faudrait le modifier à chaque changement de prix fournisseur, au moment exact où le dernier article de l'ancien lot est vendu. Sur plusieurs centaines de références, personne ne le fait. Ce chiffre est au mieux approximatif, au pire faux. Calculer le vrai coût de chaque vente est précisément l'objet de ce projet (section 7).

### « Accounting » : les totaux comptables

Totaux par journée commerciale : chiffre d'affaires TTC et HT, remises, remboursements, paiements par moyen, ventilation par taux de TVA. La date indiquée est celle de la journée commerciale, pas du calendrier.

### « Cashbook » : le livre de caisse

Chaque entrée et sortie d'espèces, avec le solde du tiroir après l'opération. Les retraits d'espèces y apparaissent comme des ajustements. Utile en v0.10 pour suivre les espèces jusqu'à la banque.

### Ce que les exports ne donnent pas

- **Le code-barres.** La colonne `SKU` d'Orders est vide. Le SKU n'est pas le code-barres : c'est une référence interne que le commerçant invente s'il le souhaite. Le code-barres, lui, est imprimé par le fabricant. La caisse connaît les codes-barres, mais aucun export ne les contient. Dans les ventes, un produit n'est identifié que par son libellé.
- **Le taux de TVA par produit.** La colonne `Tax Rate` d'Orders est vide. Le taux se déduit du rapport TTC / HT, mais l'arrondi au centime le fausse sur les petits montants (un article à 0,20 € TTC donne un taux apparent de 17,6 %). Méthode retenue : on cumule les ventes d'un produit sur plusieurs jours, on calcule le rapport sur le total, puis on le ramène au taux légal le plus proche (5,5 %, 10 % ou 20 %). Les totaux par taux du rapport Accounting servent de contrôle.
- **Un catalogue complet.** Le back-office ne permet pas d'exporter la liste de tous les produits. On ne connaît un produit que s'il s'est vendu sur la période exportée. D'où l'inventaire (section 6).
- **Un coût d'achat fiable.** Voir Product Sales ci-dessus.

### Les pièges relevés

- **La journée ne s'arrête pas à minuit.** Un export par date calendaire contient des tickets d'après minuit qui appartiennent à la journée de la veille. Leur numérotation suit celle de la soirée.
- **Les numéros de ticket ne sont pas uniques.** La numérotation (`A1`, `A2`…) repart à chaque journée. Seul `Order ID` identifie un ticket.
- **Des articles offerts.** Certains tickets sont soldés à 0 € par une remise totale : les articles ont un prix catalogue, un montant encaissé nul, et aucun paiement. Leur valeur se retrouve dans le total des remises de la journée de caisse. Ils sont exclus du chiffre d'affaires mais sortent bien du stock.
- **Des touches génériques** : un produit vendu par famille ou à l'unité, sans code-barres. Elles passent par la table de correspondance.
- **Des paiements en plusieurs fois** : une partie en carte, le reste en espèces. Le moyen de paiement appartient au ticket, pas à l'article.
- **Une plateforme de livraison** apparaît comme moyen de paiement. Ces ventes portent une commission et doivent être distinguées des ventes en magasin.
- **Des lignes en double** dans le fichier des totaux d'Accounting. Le nettoyage dédoublonne avant tout calcul.
- **La remise n'apparaît pas ligne par ligne** dans Orders (colonne à zéro) alors que la journée de caisse en totalise. Les remises se repèrent par l'écart entre prix catalogue et montant encaissé.

### Les contrôles qui tiennent

Sur la journée étudiée, au centime près :
- la somme des lignes d'un ticket est égale au total du ticket ;
- la somme des paiements d'un ticket est égale au total du ticket ;
- la somme HT des lignes est égale à celle du fichier de TVA et à celle de Product Sales ;
- la valeur catalogue des articles offerts est égale aux remises de la journée de caisse ;
- les totaux par taux de TVA de la journée de caisse sont égaux à ceux d'Accounting.

Ces égalités deviennent des garde-fous du nettoyage : si l'une d'elles casse, le programme le dit au lieu de produire des chiffres faux.

## 5. Le modèle de données cible

Le modèle complet est défini dès le départ, mais chaque table n'est construite que dans la version qui en a besoin. Les noms sont en français et en `snake_case`.

### `ventes` (v0.1) : une ligne par article d'un ticket

| Colonne | Contenu |
|---|---|
| `id_ticket` | Identifiant unique du ticket (`Order ID`) |
| `numero_ticket` | Numéro affiché (`A12`), unique seulement dans sa journée |
| `date_heure` | Date et heure de clôture du ticket |
| `journee_commerciale` | Journée de caisse à laquelle le ticket appartient |
| `libelle` | Libellé du produit à la caisse |
| `quantite` | Nombre d'unités |
| `prix_unitaire_ttc` | Prix catalogue unitaire |
| `montant_ttc` | Montant encaissé |
| `montant_ht` | Montant hors taxes, fourni par l'export |
| `offert` | Vrai si l'article a été soldé à 0 € |

### `journees` (v0.1)

`id_journee`, `ouverture`, `fermeture`, `nombre_tickets`, `ca_ttc`, `ca_ht`, `remises_ttc`.

### `produits` (v0.1, complétée en v0.5)

| Colonne | Contenu |
|---|---|
| `libelle` | Nom du produit à la caisse, clé des ventes |
| `rayon` | Rayon de rattachement, par la table de correspondance |
| `taux_tva` | Déduit des ventes cumulées, ramené au taux légal |
| `code_barres` | EAN-13, renseigné par l'inventaire en v0.5 ; vide pour un produit sans code-barres |

### `correspondances` (v0.1, étendue en v0.5 et v0.6)

Relie un libellé de caisse, un code-barres ou une référence fournisseur à un produit et à un rayon. Elle s'enrichit au fil du temps : tout libellé inconnu est listé pour être rattaché à la main, jamais deviné.

### `inventaires` (v0.5)

`date_inventaire`, `code_barres`, `libelle`, `quantite_comptee`.

### `achats` (v0.6) : une ligne par document d'achat

| Colonne | Contenu |
|---|---|
| `id_achat` | Identifiant interne |
| `type_document` | Facture électronique, facture papier, ticket de caisse, sans justificatif |
| `fournisseur` | Fournisseur ou lieu d'achat |
| `date_achat` | Date de la facture ou du ticket |
| `numero_document` | Numéro de facture ou de ticket, vide si sans justificatif |
| `total_declare` | Total écrit sur le document, saisi pour contrôle |
| `prix_saisis_en` | HT ou TTC, selon ce qu'affiche le document |
| `source` | Photo, PDF, facture électronique, export fournisseur, saisie manuelle |
| `statut` | Brouillon ou validé ; seul un achat validé crée des lots |
| `photo` | Chemin vers l'image ou le PDF du justificatif, si elle existe |

### `lignes_achat` (v0.6) : une ligne par article d'un achat

`id_achat`, `reference_fournisseur`, `code_barres`, `libelle_document`, `libelle` (produit rattaché), `quantite_colis`, `unites_par_colis`, `unites_gratuites`, `prix_colis`, `remise`, `montant_ht`, `taux_tva`.

### `lots` (v0.7)

Une ligne par entrée en stock : une ligne d'achat ou le stock de départ d'un inventaire.

| Colonne | Contenu |
|---|---|
| `id_lot` | Identifiant du lot |
| `libelle` | Produit concerné |
| `date_entree` | Date de livraison, ou date de l'inventaire de départ |
| `origine` | Ligne d'achat ou inventaire |
| `quantite_entree` | Unités entrées |
| `cout_unitaire_ht` | Coût réel d'une unité, remises et gratuités déduites |
| `quantite_restante` | Unités pas encore sorties |

### `sorties` (v0.7)

Une ligne par portion de lot consommée : une vente de six unités à cheval sur deux lots donne deux lignes.

`id_vente`, `id_lot`, `quantite`, `cout_ht`, `type` (vente, offert, casse, écart d'inventaire).

### `decisions_prix` (v0.8)

`date`, `libelle`, `ancien_prix_ttc`, `prix_suggere_ttc`, `decision` (acceptée, modifiée, refusée), `prix_retenu_ttc`.

### `paiements` (v0.10)

`id_ticket`, `date_heure`, `moyen_paiement` (carte, espèces, plateforme de livraison), `montant`.

### `operations_bancaires` (v0.10)

`date_operation`, `libelle`, `montant` (négatif pour un débit), `categorie`.

## 6. Reconnaître un produit

Un même produit porte trois noms : son libellé en caisse, sa référence chez le fournisseur et son code-barres. Les ventes ne donnent que le libellé, les factures surtout le code-barres. Il faut donc une table qui relie les deux :

```
vente (libellé) → référentiel produits (libellé ↔ code-barres) → facture (code-barres)
```

Ce référentiel n'existe dans aucun export. Il se construit pendant l'inventaire (v0.5) : chaque produit compté en rayon est enregistré avec son code-barres, son libellé de caisse et sa quantité. L'inventaire sert donc deux fois : il donne le stock de départ, et il crée le lien entre les ventes et les factures.

Le format d'entrée de l'inventaire et la façon de récupérer le libellé de caisse au moment du comptage sont à décider avant la v0.5. Pistes :
- une application de scan qui exporte un CSV (code-barres, quantité), complétée par le libellé ;
- renseigner le code-barres dans le champ SKU de la caisse, pour qu'il apparaisse ensuite dans chaque export de ventes ;
- vérifier si l'API de la caisse expose le catalogue avec ses codes-barres.

Le libellé reste une clé fragile :
- renommer un produit dans la caisse coupe son historique en deux ;
- deux produits peuvent porter des libellés très proches ;
- un produit qui ne s'est pas vendu sur la période n'apparaît dans aucun export.

Restent aussi les cas où le code-barres ne suffit pas :
- les produits sans code-barres et les touches génériques : ils passent par la table de correspondance ;
- le colisage : la facture peut porter le code du carton, différent de celui de l'unité vendue ;
- les factures qui ne mentionnent que la référence fournisseur ;
- un produit dont l'EAN change (nouveau format, nouvelle recette) alors que c'est le même article en rayon.

Ces cas sont minoritaires, mais ce sont eux qui faussent les marges si on les ignore. D'où deux règles :
- un produit non reconnu n'est jamais rattaché par approximation : il est signalé ;
- chaque rapport indique la part du chiffre d'affaires qu'il n'a pas pu rattacher, pour qu'on sache ce que valent les chiffres.

## 7. Le coût réel : un stock par lots

C'est le cœur du projet. Un même produit peut être en rayon à plusieurs coûts différents : six canettes achetées 2,00 €, puis six autres à 2,10 €. La marge d'une vente dépend du lot dont sort l'article vendu.

### La méthode : premier entré, premier sorti (PEPS)

Chaque entrée en stock crée un lot avec sa quantité et son coût unitaire. Chaque sortie consomme d'abord le lot le plus ancien, puis le suivant quand il est épuisé.

Exemple :

| Événement | Lot à 2,00 € | Lot à 2,10 € | Coût de la sortie |
|---|---|---|---|
| Livraison de 6 à 2,00 € | 6 | | |
| Livraison de 6 à 2,10 € | 6 | 6 | |
| Vente de 4 | 2 | 6 | 4 × 2,00 = 8,00 € |
| Vente de 3 | 0 | 5 | 2 × 2,00 + 1 × 2,10 = 6,10 € |

La deuxième vente est à cheval sur deux lots : elle donne deux lignes dans `sorties`. La marge de chaque vente se calcule ensuite avec ce coût exact, sans aucune saisie dans la caisse.

PEPS suit le mouvement physique d'un rayon bien tenu, où l'on vend d'abord ce qui est arrivé en premier. C'est aussi une méthode de valorisation des stocks admise en comptabilité.

L'autre méthode admise est le coût unitaire moyen pondéré (CUMP) : à chaque livraison, on recalcule un coût moyen unique pour tout le stock du produit. Plus simple, mais elle lisse les hausses de prix et ne dit pas combien d'unités restent à chaque coût. Elle pourra être calculée à côté pour comparaison.

### Le coût unitaire d'un lot

Il se calcule à partir de la ligne d'achat, ramenée à l'unité vendue :

- coût unitaire HT = (montant HT de la ligne) / (colis × unités par colis + unités gratuites)
- les remises et les gratuités (« 10 achetés + 2 offerts ») baissent le coût du lot ; une promotion fournisseur se retrouve donc d'elle-même dans la marge des ventes concernées.

### Les règles

- **Toutes les sorties consomment des lots** : ventes, articles offerts, casse, et écarts constatés à l'inventaire. Un article offert a un coût, même s'il ne rapporte rien.
- **Un retour client remet l'unité en stock**, dans le lot dont elle était sortie.
- **On ne vend jamais à partir de rien sans le dire.** Si une vente arrive alors que le stock connu du produit est épuisé (facture pas encore saisie, inventaire incomplet), la sortie est enregistrée « sans coût », signalée, puis régularisée quand le lot manquant arrive. Le coût n'est jamais inventé.
- **L'inventaire recale le stock.** L'écart entre stock théorique et stock compté est la démarque inconnue. Il consomme les lots comme une sortie.
- **Le stock de départ** n'est connu par aucune facture saisie. Il est soit compté à un inventaire, soit reconstitué (ci-dessous). Ses lots restent marqués « coût estimé ».

### Reconstituer une période passée

Cas d'usage réel : on démarre l'outil en cours d'année. On lui donne toutes les factures depuis le 1er janvier, toutes les ventes depuis le 1er janvier, et un inventaire fait aujourd'hui. Il n'existe pas d'inventaire au 1er janvier.

Pour chaque produit, une seule équation relie ces données :

```
stock au 1er janvier + achats − ventes − offerts − pertes = inventaire d'aujourd'hui
```

Deux inconnues : le stock au 1er janvier et les pertes (DLC dépassées, casse, vol, erreurs de caisse). Une équation ne suffit pas à trouver deux inconnues. L'outil ne peut donc pas séparer exactement « ce qu'il y avait au départ » de « ce qui a disparu ». Mais il peut en tirer des bornes utiles :

```
stock au 1er janvier = inventaire − achats + ventes + offerts + pertes
```

Les pertes sont positives ou nulles. En les supposant nulles, on obtient le stock de départ minimum. Deux cas :

| Produit fictif | Inventaire | Achats | Ventes + offerts | Stock de départ minimum | Lecture |
|---|---|---|---|---|---|
| A | 10 | 120 | 118 | 8 | Au moins 8 unités au 1er janvier, pertes inconnues |
| B | 2 | 60 | 50 | −8 | Impossible : au moins 8 unités ont disparu |

Un minimum négatif ne peut pas être un vrai stock. Il prouve une perte minimale : ici, au moins 8 unités du produit B sont sorties sans passer en caisse. Selon le produit, c'est de la DLC, du vol, une facture saisie en double ou une erreur de rattachement.

**Le cas favorable : un stock de départ connu.** Si la période commence à une ouverture ou une réouverture avec un magasin vide, le stock de départ vaut zéro. Il ne reste plus qu'une inconnue, et l'équation la donne exactement :

```
pertes = achats − ventes − offerts − inventaire
```

Chaque unité vendue vient alors d'une facture de la période : le moteur PEPS connaît le coût de toutes les ventes, sans aucune estimation. Seule la date des pertes reste inconnue. Cette méthode exige toutes les factures depuis le premier achat, y compris celles d'avant l'ouverture et les achats de dépannage payés en caisse ailleurs : une seule unité entrée sans facture fausse la démarque de son produit.

Méthode retenue dans le cas général :
1. Rattacher factures et ventes au même produit, grâce au référentiel de l'inventaire.
2. Calculer pour chaque produit le stock de départ minimum.
3. S'il est positif ou nul, l'utiliser comme stock de départ, valorisé au coût de la première facture de l'année.
4. S'il est négatif, partir de zéro et inscrire l'écart comme démarque minimale.
5. Faire tourner le moteur PEPS sur toute la période.
6. Comparer le stock théorique final à l'inventaire : l'écart restant est la démarque de la période.

Ce qui est fiable :
- le coût de chaque vente dès que les lots achetés cette année ont pris le relais du stock de départ ; en épicerie, la plupart des produits tournent en quelques semaines ;
- la marge par rayon sur l'année, à l'erreur du stock de départ près ;
- la démarque totale par produit sur la période.

Ce qui ne l'est pas :
- la date des pertes : on sait combien a disparu, pas quand ;
- la cause des pertes, sauf si elles sont enregistrées au fil de l'eau (casse et DLC passées en offerts, par exemple) ;
- le coût des produits à rotation lente, dont le stock de départ pèse longtemps.

Le rapport de reconstitution liste les produits par ordre d'anomalie : démarque minimale élevée, taux de perte anormal, produits vendus sans aucune facture, factures sans aucune vente. C'est un résultat utile en soi : il montre où chercher une facture manquante, une erreur de rattachement, ou un problème de vol.

### Ce que les lots rendent possible

- la marge réelle par vente, par produit, par rayon ;
- la valeur exacte du stock à tout moment ;
- les alertes de prix (v0.8) : le dernier lot coûte plus cher que le précédent, et on sait combien d'unités restent à l'ancien prix avant que la hausse touche la marge ;
- la démarque, connue (offerts, casse) et inconnue (inventaire), en euros au coût réel.

## 8. Capter les achats

Tout ce qui entre en stock doit passer par l'outil : factures de grossistes, factures papier, tickets de caisse d'un dépannage en magasin, achats sans aucun justificatif. Un seul achat oublié fausse le stock et la démarque de ses produits.

Le but est de faciliter la vie du commerçant, pas de lui donner de la saisie en plus. La voie principale est donc la photo : on photographie ou on scanne le document, l'outil le lit, on vérifie, on valide. La saisie à la main reste possible, en dernier recours.

L'outil applique ici le même principe qu'aux exports de caisse : un adaptateur par voie d'entrée, et un seul format interne à la sortie, les tables `achats` et `lignes_achat`. Le moteur de coûts ne sait jamais si une ligne vient d'une photo, d'un fichier ou d'une saisie.

### Les voies d'entrée

| Voie | Comment l'outil la traite | Fiabilité | Arrivée |
|---|---|---|---|
| Photo ou scan d'une facture papier ou d'un ticket de caisse | Lecture de l'image, lignes proposées, validation | Bonne si la photo est nette, toujours validée | v0.6 |
| PDF reçu par e-mail | Même lecture que les photos | Bonne, toujours validée | v0.6 |
| Facture électronique (Factur-X et autres formats de la réforme) | Les données sont déjà structurées dans un fichier XML joint à la facture : on les lit directement | Exacte | v0.6 |
| Export de l'historique d'achats depuis l'espace client d'un fournisseur (CSV, Excel) | Une table de correspondance de colonnes par fournisseur | Exacte | v0.6 |
| Saisie manuelle | Les mêmes écrans, avec des lignes vides | Dépend de la saisie | v0.6, en dernier recours |

### Lire une photo

Un ticket de caisse froissé ou une facture remplie à la main ne se lisent pas comme un fichier. Deux familles d'outils existent :

- **la reconnaissance de caractères classique** (OCR) : elle transforme l'image en texte, mais ne comprend pas la mise en page. Elle ne sait pas quelle colonne est le prix et laquelle est la quantité, et elle peine sur le papier thermique et l'écriture manuscrite ;
- **un modèle de langage capable de lire les images** : il comprend la mise en page et rend directement les lignes sous forme de données (article, quantité, prix, total). C'est aujourd'hui la seule approche réaliste pour des documents aussi variés.

Le modèle de langage peut se tromper de façon plausible : lire un 8 pour un 3, ou proposer une ligne qui n'existe pas. Il n'est donc jamais cru sur parole. Le circuit complet :

1. **Lecture** : la photo est lue, le résultat arrive en données structurées.
2. **Contrôles automatiques** : la somme des lignes doit tomber sur le total imprimé, la TVA doit être cohérente, les quantités et les prix doivent être plausibles par rapport aux achats précédents du même produit.
3. **Rattachement** : chaque ligne est reliée à un produit du référentiel. L'outil se souvient des rattachements déjà faits pour ce fournisseur : la deuxième facture d'un même grossiste se rattache presque toute seule.
4. **Validation** : un écran montre la photo à côté des lignes proposées, les lignes douteuses en évidence. Le commerçant corrige ce qui doit l'être et valide. Rien n'entre dans le stock sans cette validation.

Chaque correction enrichit les correspondances : avec le temps, il y a de moins en moins à corriger.

### Ce que la photo impose

- **Un service externe.** Les modèles capables de lire ces images tournent chez un prestataire. Chaque document est envoyé à ce service : des données commerciales sortent du poste. C'est un choix à faire en connaissance de cause, avec le prestataire, son coût par document et sa politique de conservation des données. Une solution entièrement locale (reconnaissance de caractères libre) existe mais lit beaucoup moins bien.
- **Une clé d'accès** stockée dans le fichier `.env` local, jamais dans le dépôt.
- **Des tests sans réseau.** Les tests automatiques ne contactent jamais le service : ils utilisent des réponses enregistrées à partir de documents fictifs.
- **Des photos nettes** : à plat, bien éclairées, document entier. Une photo floue est refusée avec un message clair plutôt que mal lue.

### La saisie manuelle, en dernier recours

Quand la photo ne passe pas (ticket effacé, document absent), on saisit à la main dans les mêmes écrans :

- on saisit ce qu'on a sous les yeux : prix HT ou TTC selon le document. Un ticket de caisse affiche des prix TTC ; l'outil calcule le HT avec le taux de TVA du produit ;
- le produit se choisit dans le référentiel, par son libellé ou son code-barres ;
- le dernier prix payé et le colisage habituel sont proposés ;
- le total du document se saisit aussi : si la somme des lignes ne tombe pas dessus, l'achat reste en brouillon ;
- un achat sans justificatif est accepté, marqué comme tel. Pour le stock et la marge, il compte comme les autres.

Les remises globales d'un ticket (fidélité, bon de réduction) ne sont rattachées à aucun article. Elles sont réparties sur les lignes au prorata de leur montant.

### La réforme de la facture électronique

Depuis le 1er septembre 2026, toutes les entreprises doivent pouvoir recevoir des factures électroniques, par une plateforme agréée. Les grandes entreprises et les entreprises de taille intermédiaire doivent déjà en émettre ; les PME et les micro-entreprises le devront à partir du 1er septembre 2027.

Une facture électronique n'est pas un document à déchiffrer : ses lignes, quantités, prix et taux de TVA sont fournis sous forme de données. C'est le meilleur format possible, et il va devenir la norme. La photo restera nécessaire pour les tickets de caisse et les factures des petits fournisseurs d'ici là.

Limites à connaître :
- le code-barres de chaque article est un champ facultatif ; certains fournisseurs ne donnent que leur propre référence ;
- l'unité facturée (colis, pack, unité) dépend du fournisseur et doit être ramenée à l'unité vendue.

### Les garde-fous communs

Quelle que soit la voie d'entrée :
- **le document doit tomber juste** : la somme des lignes est égale au total du document, et la TVA est cohérente ; sinon l'achat reste en brouillon ;
- **un document n'entre qu'une fois** : le couple fournisseur et numéro de document est unique ; une photo déjà importée est reconnue ; un achat sans justificatif de même fournisseur, même date et même montant est signalé comme doublon possible ;
- **une ligne non reconnue n'est jamais devinée** : elle reste à rattacher à la main ;
- **la première facture d'un nouveau fournisseur** est toujours vérifiée en entier ;
- **rien n'entre dans le stock sans validation** quand le document a été lu à partir d'une image.

## 9. Le jeu de données fictif

Le générateur produit les mêmes fichiers que les exports réels, au même format, avec un nom de magasin et un identifiant inventés. En v0.1 : `Orders` (products, totals, payments) et `Drawers` (totals). Puis un inventaire en v0.5 et des achats en v0.6 : des images de factures et de tickets fictifs avec la lecture attendue, des factures électroniques et des exports de fournisseurs. Il doit produire des données qu'on a envie d'analyser.

**Les défauts relevés dans les vrais exports**
- le format de la section 4 : point-virgule, guillemets, virgule décimale, colonnes en anglais, colonnes constantes ou vides
- des tickets après minuit rattachés à la journée de la veille, avec une numérotation qui se chevauche
- des articles offerts, soldés à 0 € par une remise totale
- des tickets payés en plusieurs fois, des ventes par plateforme de livraison
- des lignes en double dans les totaux
- des libellés inconnus de la table de correspondance
- un jour sans données (caisse en panne), un mois incomplet

**Les phénomènes du métier**
- une ouverture tardive jusqu'après minuit, des pics en fin de journée, des jours plus chargés que d'autres, des jours de fermeture
- beaucoup de petits paniers d'un ou deux articles
- saisonnalité par rayon (boissons fraîches l'été, par exemple)
- trois taux de TVA selon les produits
- environ 95 % des produits avec un code-barres, utilisé à partir de l'inventaire
- des codes-barres fictifs commençant par 20, préfixe réservé à l'usage interne d'un magasin, pour ne jamais tomber sur un vrai produit, avec une clé de contrôle valide
- à partir de la v0.6 : des livraisons régulières avec colisage, des hausses de prix, des promotions fournisseurs, des gratuités, et parfois une vente avant la saisie de la facture correspondante

**Une vérité terrain**

Le générateur connaît le coût réel de chaque unité vendue, puisqu'il invente les livraisons et les ventes. Le moteur PEPS doit retrouver exactement ces coûts : c'est son test principal.

Il invente aussi des pertes cachées (DLC, casse, vol) et un stock au 1er janvier. La reconstitution ne peut pas retrouver ces valeurs exactement ; les tests vérifient qu'elle les encadre correctement : jamais un stock négatif, et une démarque minimale toujours inférieure ou égale aux pertes réelles.

Les autres événements volontairement cachés dans le jeu fictif (une hausse de 8 % sur un produit à une date donnée, une promotion de trois semaines, un produit qui décroche) sont listés dans un fichier à part. Les tests vérifient que l'outil les retrouve. C'est l'avantage d'inventer ses données : on connaît la bonne réponse.

## 10. Définitions

Ces termes sont souvent confondus. Dans ce projet, ils ne le sont jamais.

| Terme | Calcul |
|---|---|
| Chiffre d'affaires HT | Somme des montants HT des lignes de vente |
| Lot | Quantité d'un produit entrée en stock à un même coût unitaire |
| PEPS | Premier entré, premier sorti : chaque sortie consomme le lot le plus ancien |
| CUMP | Coût unitaire moyen pondéré, recalculé à chaque entrée |
| Coût des ventes | Somme des coûts des lots consommés par les ventes |
| Marge brute | CA HT − coût des ventes |
| Taux de marque | Marge brute / CA HT |
| Taux de marge | Marge brute / coût des ventes |
| Coefficient multiplicateur | Prix de vente TTC / coût d'achat HT |
| Journée commerciale | Période entre l'ouverture et la fermeture de la caisse, qui peut dépasser minuit |
| Article offert | Article sorti du magasin avec un montant encaissé nul ; il coûte sans rapporter |
| Démarque connue | Coût des articles offerts et de la casse enregistrée |
| Démarque inconnue | Stock théorique − stock compté à l'inventaire, valorisé au coût des lots |
| Colisage | Nombre d'unités dans un colis facturé |
| Classement ABC | A : produits qui font environ 80 % du total, B : les 15 % suivants, C : le reste |

Exemple : un produit acheté 1,50 € HT, vendu 2,11 € TTC avec une TVA à 5,5 %. Prix de vente HT : 2,00 €. Marge brute : 0,50 €. Taux de marque : 25 %. Taux de marge : 33,3 %. Coefficient : 1,41.

Prix de vente suggéré pour un taux de marque cible : prix HT = coût HT / (1 − taux de marque cible), puis prix TTC = prix HT × (1 + TVA), arrondi au prix commercial supérieur.

## 11. Ce qui n'entre jamais dans le dépôt

- Les exports de caisse, inventaires, factures et relevés réels, et tout ce qui est calculé à partir d'eux
- Les noms de commerce, adresses, numéros d'entreprise, identifiants de magasin ou de caisse, noms de fournisseurs réels, chiffres réels
- Les clés d'accès aux API : elles vivent dans un fichier `.env` local, ignoré par Git. Seul un modèle vide `.env.exemple` est versionné.

## 12. Simplifications connues

- Les montants sont manipulés en nombres décimaux (`float`). Une version comptable travaillerait en centimes entiers ou avec `Decimal` pour éviter les erreurs d'arrondi.
- Le taux de TVA d'un produit est déduit de ses ventes. Un produit vendu une seule fois pour quelques centimes peut être mal classé ; le contrôle par les totaux d'Accounting le signale.
- Les remises globales d'un ticket de caisse sont réparties au prorata des lignes, faute de savoir à quel article elles s'appliquent.
- La reconstitution d'une période passée attribue les pertes à la fin de la période, faute de connaître leur date. Le coût des ventes du début de période dépend d'un stock de départ estimé.
- PEPS suppose qu'on vend d'abord le plus ancien. Si un rayon est mal tourné, le coût calculé et le coût physique peuvent légèrement différer ; l'inventaire corrige les quantités, pas l'ordre réel des sorties.
- Avant la v0.7, aucune marge n'est calculée sur les données réelles : seul le chiffre d'affaires est fiable.
