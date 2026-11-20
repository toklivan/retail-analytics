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


# --- Rapprochement avec le référentiel et les ventes ------------------------

def libelles_par_code(correspondances):
    """Libellé et rayon de chaque code-barres du référentiel.

    Un code à plusieurs libellés (produit renommé en caisse) les garde tous, réunis
    par « / », pour que son stock ne soit pas compté deux fois.
    """
    avec_code = correspondances.dropna(subset=["code_barres"])
    # agg applique une fonction par colonne : " / ".join colle les libellés, "first" garde le rayon, unique.
    return avec_code.groupby("code_barres", as_index=False).agg(libelle=("libelle", " / ".join),
                                                                 rayon=("rayon", "first"))


def stock_rattache(stock, correspondances):
    """Stock compté avec libellé et rayon ; ils restent vides pour un code-barres inconnu."""
    return stock.merge(libelles_par_code(correspondances), on="code_barres", how="left")


def codes_inconnus(rattache):
    """Codes-barres comptés mais absents du référentiel, à y ajouter à la main."""
    return rattache[rattache["libelle"].isna()][["code_barres", "quantite_comptee"]]


def codes_vendus(ventes, correspondances):
    """Codes-barres dont au moins un libellé apparaît dans les ventes."""
    vendus = correspondances[correspondances["libelle"].isin(ventes["libelle"])]
    return set(vendus["code_barres"].dropna())


def comptes_jamais_vendus(rattache, ventes, correspondances):
    """Produits connus, comptés en rayon, sans aucune vente."""
    connus = rattache.dropna(subset=["libelle"])
    return connus[~connus["code_barres"].isin(codes_vendus(ventes, correspondances))]


def ca_par_libelle(ventes):
    return ventes.groupby("libelle", as_index=False)["montant_ht"].sum().rename(columns={"montant_ht": "ca_ht"})


def vendus_jamais_comptes(ventes, correspondances, stock):
    """Produits vendus, avec un code-barres connu, dont aucun code n'a été compté.

    Un oubli de comptage ou une rupture : du plus gros chiffre d'affaires HT au plus petit.
    """
    avec_code = correspondances.dropna(subset=["code_barres"])
    # Un libellé est compté si au moins un de ses codes l'est.
    comptes = set(avec_code.loc[avec_code["code_barres"].isin(stock["code_barres"]), "libelle"])
    rayons = avec_code[~avec_code["libelle"].isin(comptes)][["libelle", "rayon"]].drop_duplicates()
    resultat = rayons.merge(ca_par_libelle(ventes), on="libelle")
    return resultat.sort_values("ca_ht", ascending=False, ignore_index=True)


def vendus_sans_code_barres(ventes, correspondances):
    """Produits vendus que le référentiel connaît sans code-barres : ils ne se scannent pas."""
    sans_code = correspondances.groupby("libelle")["code_barres"].count() == 0
    rayons = correspondances[correspondances["libelle"].isin(sans_code[sans_code].index)][["libelle", "rayon"]]
    resultat = rayons.drop_duplicates().merge(ca_par_libelle(ventes), on="libelle")
    return resultat.sort_values("ca_ht", ascending=False, ignore_index=True)


def ventes_jusqu_a(ventes, date_inventaire):
    """Ventes des journées commerciales jusqu'au jour de l'inventaire inclus."""
    return ventes[ventes["journee_commerciale"] <= date_inventaire]
