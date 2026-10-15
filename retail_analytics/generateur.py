"""Générateur du jeu de données fictif, au format des exports de la Caisse Pro SumUp.

Il simule le magasin jour par jour, puis écrit les fichiers comme le
back-office les exporte : un export par mois, chacun reprenant le dernier
jour du mois précédent. La graine fixe rend le jeu identique à chaque lancement.

Les montants sont calculés en centimes entiers pour éviter les erreurs
d'arrondi des nombres décimaux.
"""

import json
import random
import uuid
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from retail_analytics.catalogue import SAISONS, lister_produits

GRAINE = 2026
DEBUT = date(2026, 1, 1)
FIN = date(2026, 10, 14)
JOURS_FERMES = {date(2026, 1, 1), date(2026, 5, 1), date(2026, 7, 14), date(2026, 8, 15)}
JOUR_PANNE = date(2026, 3, 17)
SEMAINE_EXEMPLE = (date(2026, 6, 8), date(2026, 6, 14))
NOMBRE_LIBELLES_INCONNUS = 5

MAGASIN = "Épicerie Exemple"
ID_MAGASIN = "10000"
VENDEUR = "Caisse 1"
DEVISE = "EUR"
FOND_DE_CAISSE = 15000
CARTE, ESPECES, PLATEFORME = "Card", "Cash", "LIVRAISON_APP"

# Nombre moyen de tickets selon le jour de la semaine (lundi = 0).
TICKETS_PAR_JOUR = [85, 90, 95, 95, 115, 130, 100]
# Poids de chaque heure d'ouverture ; 24 représente la demi-heure après minuit.
POIDS_HEURES = {9: 3, 10: 4, 11: 5, 12: 7, 13: 5, 14: 3, 15: 3, 16: 4, 17: 6,
                18: 9, 19: 10, 20: 9, 21: 7, 22: 5, 23: 4, 24: 2}
# Nombre d'articles différents par ticket : beaucoup de petits paniers.
POIDS_ARTICLES = {1: 45, 2: 25, 3: 13, 4: 8, 5: 4, 6: 2, 7: 1, 8: 1, 10: 1}
POIDS_QUANTITES = {1: 80, 2: 12, 3: 4, 4: 2, 6: 2}

ENTETES_PRODUITS = ["Store", "Store ID", "Opening Date", "Closing Date", "Order ID", "Currency",
                    "Product", "SKU", "Quantity", "Gift card code", "Price incl Tax", "Discount",
                    "Sales incl Tax", "Sales excl Tax", "Tax Amount"]
ENTETES_TICKETS = ["Store", "Store ID", "Opening Date", "Closing Date", "Order ID", "Currency",
                   "Custom Order ID", "Order Name", "Opened by Seller", "Closed on Table",
                   "# Customers", "Order Duration", "Order Status", "Sales incl Tax",
                   "Sales excl Tax", "Total Tax Amount", "Total Payments"]
ENTETES_PAIEMENTS = ["Store", "Store ID", "Opening Date", "Closing Date", "Order ID", "Currency",
                     "Payment Method", "Payments Amount"]
ENTETES_JOURNEES = ["Store", "Store ID", "Opening Date", "Closing Date", "Drawer ID", "Currency",
                    "# Orders", "# Customers", "Sales incl Tax", "Sales excl Tax",
                    "Total Tax Amount", "Initial Cash", "Final Cash", "Total Discounts",
                    "Total Canceled", "Total Payments", "Total Expenses", "Total Customer Account"]


# --- Petits outils ---------------------------------------------------------

def tirer(rng, poids):
    """Tire une clé d'un dictionnaire {valeur: poids}."""
    return rng.choices(list(poids), weights=list(poids.values()))[0]


def nouvel_identifiant(rng):
    """Identifiant au format des exports (UUID en majuscules), reproductible grâce à rng."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4)).upper()


def ht_depuis_ttc(ttc_centimes, taux):
    """Montant HT en centimes, arrondi au centime le plus proche (0,5 vers le haut)."""
    ht = Decimal(ttc_centimes) / (1 + Decimal(str(taux)))
    return int(ht.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def montant(centimes):
    """12340 -> '123,40', comme dans les exports."""
    return f"{centimes / 100:.2f}".replace(".", ",")


def horodatage(moment):
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def duree(secondes):
    return f"{secondes // 3600:02d}:{secondes // 60 % 60:02d}:{secondes % 60:02d}"


# --- Simulation du magasin --------------------------------------------------

def poids_du_mois(produits, mois):
    """Poids de tirage de chaque produit pour un mois donné : popularité × saison."""
    return [p["popularite"] * SAISONS[p["saison"]][mois - 1] for p in produits]


def creer_ligne(rng, produit):
    """Une ligne de ticket. Une touche libre (prix None) reçoit un prix tapé à la main."""
    if produit["prix_ttc"] is None:
        prix = rng.randint(80, 650) if produit["rayon"] == "Fruits et légumes" else rng.randint(100, 1500)
        quantite = 1
    else:
        prix = round(produit["prix_ttc"] * 100)
        quantite = tirer(rng, POIDS_QUANTITES)
    ttc = prix * quantite
    return {"libelle": produit["libelle"], "quantite": quantite, "prix": prix,
            "ttc": ttc, "ht": ht_depuis_ttc(ttc, produit["taux_tva"])}


def choisir_paiements(rng, total):
    """Liste des paiements (moyen, centimes) d'un ticket. Un ticket à 0 € n'a aucun paiement."""
    if total == 0:
        return []
    tirage = rng.random()
    if tirage < 0.03:
        return [(PLATEFORME, total)]
    if tirage < 0.05 and total >= 300:
        especes = 100 * rng.randint(1, (total - 1) // 100)
        return [(CARTE, total - especes), (ESPECES, especes)]
    if tirage < 0.35:
        return [(ESPECES, total)]
    return [(CARTE, total)]


def creer_ticket(rng, produits, poids, cloture, offert):
    """Un ticket clos à `cloture`. Un ticket offert est soldé à 0 € par une remise totale."""
    nombre = 3 + rng.randint(0, 7) if offert else tirer(rng, POIDS_ARTICLES)
    choisis = []
    while len(choisis) < nombre:
        produit = rng.choices(produits, weights=poids)[0]
        if produit not in choisis:
            choisis.append(produit)
    lignes = [creer_ligne(rng, p) for p in choisis]
    if offert:
        for ligne in lignes:
            ligne["ttc"] = ligne["ht"] = 0
    secondes = rng.randint(15, 240)
    return {
        "id": nouvel_identifiant(rng),
        "ouverture": cloture - timedelta(seconds=secondes),
        "cloture": cloture,
        "duree": secondes,
        "lignes": lignes,
        "offert": offert,
        "paiements": choisir_paiements(rng, sum(l["ttc"] for l in lignes)),
    }


def heure_de_cloture(rng, jour, ouverture, fermeture):
    """Un instant de la journée, tiré selon l'affluence de chaque heure."""
    while True:
        heure = tirer(rng, POIDS_HEURES)
        moment = datetime.combine(jour, time(0)) + timedelta(hours=heure, seconds=rng.randint(0, 3599))
        if ouverture + timedelta(minutes=1) < moment < fermeture - timedelta(minutes=1):
            return moment


def simuler_journee(rng, jour, produits):
    """Une journée de caisse et ses tickets. La fermeture a lieu après minuit."""
    ouverture = datetime.combine(jour, time(8, 50)) + timedelta(seconds=rng.randint(0, 900))
    fermeture = datetime.combine(jour + timedelta(days=1), time(0, 15)) + timedelta(seconds=rng.randint(0, 1800))
    poids = poids_du_mois(produits, jour.month)
    nombre = round(TICKETS_PAR_JOUR[jour.weekday()] * rng.uniform(0.85, 1.15))
    clotures = [heure_de_cloture(rng, jour, ouverture, fermeture) for _ in range(nombre)]
    tickets = [creer_ticket(rng, produits, poids, c, offert=False) for c in clotures]
    if rng.random() < 0.3:
        tickets.append(creer_ticket(rng, produits, poids, heure_de_cloture(rng, jour, ouverture, fermeture), offert=True))
    tickets.sort(key=lambda t: t["cloture"])
    for numero, ticket in enumerate(tickets, start=1):
        ticket["numero"] = f"A{numero}"
    journee = {"id": nouvel_identifiant(rng), "ouverture": ouverture, "fermeture": fermeture, "tickets": tickets}
    return journee


def simuler_magasin(rng, produits):
    """Toutes les journées de caisse de la période, sauf jours fermés et jour de panne."""
    journees = []
    jour = DEBUT
    while jour <= FIN:
        if jour not in JOURS_FERMES and jour != JOUR_PANNE:
            journees.append(simuler_journee(rng, jour, produits))
        jour += timedelta(days=1)
    return journees


# --- Écriture des exports ---------------------------------------------------

def ecrire_csv(chemin, entetes, lignes):
    """Écrit un fichier au format SumUp : point-virgule, guillemets, CRLF, pas de saut final."""
    texte = "\r\n".join(";".join(f'"{v}"' for v in ligne) for ligne in [entetes] + lignes)
    chemin.write_text(texte, encoding="utf-8", newline="")


def lignes_export(journees, debut, fin):
    """Lignes des quatre fichiers d'un export couvrant les jours calendaires debut à fin.

    Comme le vrai back-office : Orders contient les tickets clos pendant la période,
    Drawers les caisses ouvertes pendant la période.
    """
    commun = [MAGASIN, ID_MAGASIN]
    produits, tickets, paiements, caisses = [], [], [], []
    for journee in journees:
        if debut <= journee["ouverture"].date() <= fin:
            caisses.append(ligne_journee(commun, journee))
        for t in journee["tickets"]:
            if not debut <= t["cloture"].date() <= fin:
                continue
            dates = commun + [horodatage(t["ouverture"]), horodatage(t["cloture"]), t["id"], DEVISE]
            ttc = sum(l["ttc"] for l in t["lignes"])
            ht = sum(l["ht"] for l in t["lignes"])
            for l in t["lignes"]:
                produits.append(dates + [l["libelle"], "", l["quantite"], "", montant(l["prix"]), "0,00",
                                         montant(l["ttc"]), montant(l["ht"]), montant(l["ttc"] - l["ht"])])
            tickets.append(dates + ["", t["numero"], VENDEUR, "", 1, duree(t["duree"]), "CLOSE",
                                    montant(ttc), montant(ht), montant(ttc - ht), montant(ttc)])
            for moyen, somme in t["paiements"]:
                paiements.append(dates + [moyen, montant(somme)])
    return produits, tickets, paiements, caisses


def ligne_journee(commun, journee):
    tickets = journee["tickets"]
    lignes = [l for t in tickets for l in t["lignes"]]
    ttc = sum(l["ttc"] for l in lignes)
    ht = sum(l["ht"] for l in lignes)
    remises = sum(l["prix"] * l["quantite"] for t in tickets if t["offert"] for l in t["lignes"])
    especes = sum(s for t in tickets for m, s in t["paiements"] if m == ESPECES)
    return commun + [horodatage(journee["ouverture"]), horodatage(journee["fermeture"]), journee["id"],
                     DEVISE, len(tickets), len(tickets), montant(ttc), montant(ht), montant(ttc - ht),
                     montant(FOND_DE_CAISSE), montant(FOND_DE_CAISSE + especes), montant(remises),
                     "0,00", montant(ttc), "0,00", "0,00"]


def ecrire_export(dossier, journees, debut, fin):
    """Écrit les fichiers d'un export, nommés comme ceux du back-office."""
    dossier.mkdir(parents=True, exist_ok=True)
    periode = f"{debut.isoformat()}_{fin.isoformat()}"
    produits, tickets, paiements, caisses = lignes_export(journees, debut, fin)
    ecrire_csv(dossier / f"orders-report-products-{periode}.csv", ENTETES_PRODUITS, produits)
    ecrire_csv(dossier / f"orders-report-totals-{periode}.csv", ENTETES_TICKETS, tickets)
    ecrire_csv(dossier / f"orders-report-payments-{periode}.csv", ENTETES_PAIEMENTS, paiements)
    ecrire_csv(dossier / f"drawers-report-totals-{periode}.csv", ENTETES_JOURNEES, caisses)


def periodes_mensuelles():
    """Un export par mois ; à partir de février, chacun reprend le dernier jour du mois précédent."""
    periodes = []
    premier_du_mois = date(DEBUT.year, DEBUT.month, 1)
    while premier_du_mois <= FIN:
        mois_suivant = date(premier_du_mois.year + premier_du_mois.month // 12, premier_du_mois.month % 12 + 1, 1)
        debut = max(premier_du_mois - timedelta(days=1), DEBUT)
        fin = min(mois_suivant - timedelta(days=1), FIN)
        periodes.append((debut, fin))
        premier_du_mois = mois_suivant
    return periodes


def ecrire_correspondances(chemin, produits, inconnus):
    """Table libellé -> rayon, où manquent volontairement quelques libellés."""
    lignes = ["libelle;rayon"] + [f"{p['libelle']};{p['rayon']}" for p in produits if p["libelle"] not in inconnus]
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")


# --- Vérité terrain ---------------------------------------------------------

def verite_terrain(journees, periodes, inconnus):
    """Ce que l'outil doit retrouver dans le jeu fictif, calculé sur ce qui a été exporté."""
    exportes = {}
    apparitions = 0
    for debut, fin in periodes:
        for j in journees:
            for t in j["tickets"]:
                if debut <= t["cloture"].date() <= fin:
                    exportes[t["id"]] = t
                    apparitions += 1
    tickets = list(exportes.values())
    lignes = [l for t in tickets for l in t["lignes"]]
    jours_ouverts = {j["ouverture"].date() for j in journees}
    jours_sans_donnees = [DEBUT + timedelta(days=n) for n in range((FIN - DEBUT).days + 1)]
    return {
        "periode": [DEBUT.isoformat(), FIN.isoformat()],
        "jour_panne": JOUR_PANNE.isoformat(),
        "jours_sans_donnees": [d.isoformat() for d in jours_sans_donnees if d not in jours_ouverts],
        "journee_coupee_par_la_fin_de_l_export": FIN.isoformat(),
        "nombre_journees": len(journees),
        "nombre_tickets": len(tickets),
        "nombre_tickets_en_double": apparitions - len(tickets),
        "nombre_tickets_offerts": sum(t["offert"] for t in tickets),
        "nombre_tickets_payes_en_plusieurs_fois": sum(len(t["paiements"]) > 1 for t in tickets),
        "nombre_tickets_plateforme": sum(any(m == PLATEFORME for m, _ in t["paiements"]) for t in tickets),
        "nombre_lignes": len(lignes),
        "ca_ttc_centimes": sum(l["ttc"] for l in lignes),
        "ca_ht_centimes": sum(l["ht"] for l in lignes),
        "libelles_inconnus": sorted(inconnus),
    }


def generer(dossier_fictif=Path("data/fictif"), dossier_exemple=Path("data/exemple")):
    """Génère le jeu complet, son extrait d'une semaine et la vérité terrain."""
    rng = random.Random(GRAINE)
    produits = lister_produits()
    journees = simuler_magasin(rng, produits)
    candidats = [p["libelle"] for p in produits if p["prix_ttc"] is not None]
    inconnus = rng.sample(candidats, NOMBRE_LIBELLES_INCONNUS)

    periodes = periodes_mensuelles()
    for debut, fin in periodes:
        ecrire_export(dossier_fictif / "sumup", journees, debut, fin)
    ecrire_correspondances(dossier_fictif / "correspondances.csv", produits, inconnus)
    verite = verite_terrain(journees, periodes, inconnus)
    texte = json.dumps(verite, indent=2, ensure_ascii=False) + "\n"
    (dossier_fictif / "verite_terrain.json").write_text(texte, encoding="utf-8")

    ecrire_export(dossier_exemple / "sumup", journees, *SEMAINE_EXEMPLE)
    ecrire_correspondances(dossier_exemple / "correspondances.csv", produits, inconnus)
    return verite
