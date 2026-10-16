"""Adaptateur des exports de la Caisse Pro SumUp.

Il lit les fichiers exportés depuis le back-office et rend cinq tables au
format interne (voir docs/donnees.md, section 5) : ventes, tickets, paiements,
journées, et les périodes couvertes par les exports. Les colonnes sont traduites, les montants convertis en centimes
entiers, les dates en vraies dates. Le reste du code ne voit jamais le format
SumUp : passer à l'API ne changera que ce module.

L'adaptateur ne nettoie rien : un ticket présent dans deux exports y est
encore deux fois. Le dédoublonnage est le travail du module de nettoyage.
"""

from pathlib import Path

import pandas as pd

# Colonnes gardées pour chaque fichier : nom SumUp -> nom interne.
COLONNES_VENTES = {"Order ID": "id_ticket", "Closing Date": "date_heure", "Product": "libelle",
                   "Quantity": "quantite", "Price incl Tax": "prix_unitaire_ttc",
                   "Sales incl Tax": "montant_ttc", "Sales excl Tax": "montant_ht"}
COLONNES_TICKETS = {"Order ID": "id_ticket", "Order Name": "numero_ticket", "Closing Date": "date_heure",
                    "Sales incl Tax": "montant_ttc", "Sales excl Tax": "montant_ht"}
COLONNES_PAIEMENTS = {"Order ID": "id_ticket", "Payment Method": "moyen_paiement",
                      "Payments Amount": "montant_ttc"}
COLONNES_JOURNEES = {"Drawer ID": "id_journee", "Opening Date": "ouverture", "Closing Date": "fermeture",
                     "# Orders": "nombre_tickets", "Sales incl Tax": "ca_ttc", "Sales excl Tax": "ca_ht",
                     "Total Discounts": "remises_ttc"}

# Moyens de paiement SumUp -> nom interne. Un libellé absent de cette table est
# gardé tel quel : il n'est pas deviné, et les indicateurs le signalent.
MOYENS_PAIEMENT = {"Cash": "especes", "Card": "carte", "UBER_EATS": "plateforme"}

FORMAT_DATE = "%Y-%m-%d %H:%M:%S"


# --- Conversions (sans fichier, donc testables directement) -----------------

def en_centimes(colonne):
    """'12,40' -> 1240. Un montant illisible arrête la lecture : on n'invente jamais de valeur."""
    # pd.to_numeric convertit du texte en nombre ; errors="coerce" met NaN (« pas un nombre »)
    # là où la conversion échoue, ce qui permet de lister les valeurs fautives.
    euros = pd.to_numeric(colonne.str.replace(",", ".", regex=False), errors="coerce")
    verifier_lisible(colonne, euros)
    return (euros * 100).round().astype("int64")


def en_entiers(colonne):
    """'3' -> 3. Une quantité illisible ou décimale arrête la lecture."""
    nombres = pd.to_numeric(colonne, errors="coerce")
    verifier_lisible(colonne, nombres.where(nombres == nombres.round()))
    return nombres.astype("int64")


def en_dates(colonne):
    """'2026-03-02 18:30:00' -> date et heure. Une date mal formée arrête la lecture."""
    return pd.to_datetime(colonne, format=FORMAT_DATE)


def verifier_lisible(texte, nombres):
    """Lève une erreur qui cite les valeurs que la conversion n'a pas su lire."""
    illisibles = texte[nombres.isna()]
    if not illisibles.empty:
        exemples = list(illisibles.unique()[:5])
        raise ValueError(f"Valeurs illisibles dans la colonne « {texte.name} » : {exemples}")


def traduire(brut, colonnes):
    """Garde les colonnes utiles et leur donne leur nom interne. Signale celles qui manquent.

    La colonne `export`, ajoutée à la lecture, est conservée telle quelle.
    """
    manquantes = [c for c in colonnes if c not in brut.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes de l'export : {manquantes}")
    garder = list(colonnes) + (["export"] if "export" in brut.columns else [])
    return brut[garder].rename(columns=colonnes)


def preparer_ventes(brut):
    ventes = traduire(brut, COLONNES_VENTES)
    ventes["date_heure"] = en_dates(ventes["date_heure"])
    ventes["quantite"] = en_entiers(ventes["quantite"])
    for colonne in ["prix_unitaire_ttc", "montant_ttc", "montant_ht"]:
        ventes[colonne] = en_centimes(ventes[colonne])
    return ventes


def preparer_tickets(brut):
    tickets = traduire(brut, COLONNES_TICKETS)
    tickets["date_heure"] = en_dates(tickets["date_heure"])
    for colonne in ["montant_ttc", "montant_ht"]:
        tickets[colonne] = en_centimes(tickets[colonne])
    return tickets


def preparer_paiements(brut):
    paiements = traduire(brut, COLONNES_PAIEMENTS)
    # replace avec un dictionnaire remplace les valeurs trouvées et laisse les autres intactes.
    paiements["moyen_paiement"] = paiements["moyen_paiement"].replace(MOYENS_PAIEMENT)
    paiements["montant_ttc"] = en_centimes(paiements["montant_ttc"])
    return paiements


def preparer_journees(brut):
    journees = traduire(brut, COLONNES_JOURNEES)
    journees["ouverture"] = en_dates(journees["ouverture"])
    journees["fermeture"] = en_dates(journees["fermeture"])
    journees["nombre_tickets"] = en_entiers(journees["nombre_tickets"])
    for colonne in ["ca_ttc", "ca_ht", "remises_ttc"]:
        journees[colonne] = en_centimes(journees[colonne])
    return journees


# --- Lecture des fichiers ---------------------------------------------------

def lire_fichiers(dossier, prefixe):
    """Lit et met bout à bout tous les fichiers d'un même type (un par export mensuel).

    Chaque ligne garde dans la colonne `export` la période de son fichier
    (`2026-01-31_2026-02-28`) : le nettoyage s'en sert pour retirer les doublons.
    """
    chemins = sorted(Path(dossier).glob(f"{prefixe}-*.csv"))
    if not chemins:
        raise FileNotFoundError(f"Aucun fichier {prefixe}-*.csv dans {dossier}")
    tables = []
    for chemin in chemins:
        # dtype=str : pandas lit tout en texte, sans deviner les types ; la conversion
        # est faite ensuite, colonne par colonne, avec vérification.
        table = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
        table["export"] = chemin.stem.removeprefix(f"{prefixe}-")
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def lire_periodes(dossier):
    """Début et fin de chaque export, lus dans le nom des fichiers de ventes.

    `orders-report-products-2026-01-31_2026-02-28.csv` couvre les tickets clos
    du 31/01/2026 au 28/02/2026 inclus. Un nom mal formé arrête la lecture.
    """
    prefixe = "orders-report-products-"
    noms = [chemin.stem.removeprefix(prefixe) for chemin in sorted(Path(dossier).glob(f"{prefixe}*.csv"))]
    if not noms:
        raise FileNotFoundError(f"Aucun fichier {prefixe}*.csv dans {dossier}")
    # partition coupe le texte au premier « _ » : ('2026-01-31', '_', '2026-02-28').
    bornes = [nom.partition("_") for nom in noms]
    return pd.DataFrame({
        "debut": pd.to_datetime([debut for debut, _, _ in bornes], format="%Y-%m-%d"),
        "fin": pd.to_datetime([fin for _, _, fin in bornes], format="%Y-%m-%d"),
    })


def lire_export(dossier):
    """Les cinq tables internes, lues depuis un dossier d'exports SumUp."""
    return {
        "ventes": preparer_ventes(lire_fichiers(dossier, "orders-report-products")),
        "tickets": preparer_tickets(lire_fichiers(dossier, "orders-report-totals")),
        "paiements": preparer_paiements(lire_fichiers(dossier, "orders-report-payments")),
        "journees": preparer_journees(lire_fichiers(dossier, "drawers-report-totals")),
        "periodes": lire_periodes(dossier),
    }
