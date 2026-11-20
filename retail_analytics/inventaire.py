"""Lecture et validation d'un comptage d'inventaire.

Le fichier `inventaire-AAAA-MM-JJ.csv` contient une ligne par scan : `code_barres;quantite`.
Un même code peut revenir plusieurs fois (le rayon, puis la réserve) : les quantités
s'additionnent. Une ligne fautive est écartée et signalée, sans bloquer le reste du comptage.
"""

import re

import pandas as pd

from retail_analytics.codes_barres import code_barres_valide


def date_du_fichier(chemin):
    """Date du comptage, lue dans le nom du fichier : `inventaire-2026-10-14.csv` -> 14/10/2026."""
    trouve = re.fullmatch(r"inventaire-(\d{4}-\d{2}-\d{2})\.csv", chemin.name)
    if trouve is None:
        raise ValueError(f"Nom de fichier inattendu, il faut inventaire-AAAA-MM-JJ.csv : {chemin.name}")
    return pd.Timestamp(trouve.group(1))


def lire_inventaire(chemin):
    """Lignes du comptage, telles que saisies, avec la date de l'inventaire.

    Tout est lu en texte : la validation décide ensuite de ce qui est un code et un nombre.
    """
    lignes = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8", keep_default_na=False)
    attendues = ["code_barres", "quantite"]
    if list(lignes.columns) != attendues:
        raise ValueError(f"Colonnes attendues {attendues}, trouvées {list(lignes.columns)}")
    # strip retire les espaces autour, qu'une saisie à la main laisse parfois.
    lignes = lignes.apply(lambda colonne: colonne.str.strip())
    return lignes.assign(date_inventaire=date_du_fichier(chemin))


def quantites_lues(lignes):
    """Quantité de chaque ligne en nombre, vide si ce n'est pas un entier positif ou nul."""
    # isdigit n'accepte que des chiffres : « 1O », « -2 » ou « 1,5 » sont refusés.
    return pd.to_numeric(lignes["quantite"].where(lignes["quantite"].str.isdigit()))


def lignes_rejetees(lignes):
    """Lignes écartées, avec la raison : code-barres invalide ou quantité illisible."""
    code_faux = ~lignes["code_barres"].map(code_barres_valide)
    quantite_fausse = quantites_lues(lignes).isna()
    raisons = pd.Series("", index=lignes.index)
    raisons[quantite_fausse] = "quantité illisible"
    raisons[code_faux] = "code-barres invalide"
    rejetees = lignes.assign(raison=raisons)[code_faux | quantite_fausse]
    return rejetees[["code_barres", "quantite", "raison"]]


def stock_compte(lignes):
    """Quantité comptée par code-barres, lignes fautives écartées, doublons additionnés."""
    valides = lignes.drop(lignes_rejetees(lignes).index).assign(quantite=quantites_lues)
    stock = valides.groupby(["date_inventaire", "code_barres"], as_index=False)["quantite"].sum()
    return stock.rename(columns={"quantite": "quantite_comptee"}).astype({"quantite_comptee": "int64"})
