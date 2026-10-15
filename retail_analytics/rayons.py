"""Rattachement de chaque vente à un rayon, par la table de correspondance.

Un libellé absent de la table n'est jamais deviné : son rayon reste vide,
il est listé, et la part du chiffre d'affaires qu'il représente est signalée.
"""

import pandas as pd


def lire_correspondances(chemin):
    """Lit la table libellé -> rayon (`libelle;rayon`) et la valide."""
    correspondances = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
    return valider_correspondances(correspondances)


def valider_correspondances(correspondances):
    """Refuse une table où un libellé n'a pas de rayon ou en a plusieurs."""
    sans_rayon = correspondances[correspondances["rayon"].isna()]
    if not sans_rayon.empty:
        raise ValueError(f"Libellés sans rayon : {list(sans_rayon['libelle'])}")
    # drop_duplicates retire les répétitions identiques ; s'il reste un libellé en double,
    # c'est qu'il est rangé dans deux rayons différents.
    uniques = correspondances.drop_duplicates()
    en_double = uniques[uniques["libelle"].duplicated()]
    if not en_double.empty:
        raise ValueError(f"Libellés rangés dans plusieurs rayons : {list(en_double['libelle'])}")
    return uniques.reset_index(drop=True)


def rattacher_rayons(ventes, correspondances):
    """Ajoute la colonne `rayon` aux ventes ; elle reste vide pour un libellé inconnu."""
    return ventes.merge(correspondances[["libelle", "rayon"]], on="libelle", how="left")


def libelles_inconnus(ventes):
    """Libellés vendus mais absents de la table, du plus gros chiffre d'affaires au plus petit."""
    inconnues = ventes[ventes["rayon"].isna()]
    resume = inconnues.groupby("libelle").agg(nombre_lignes=("libelle", "count"),
                                              ca_ht=("montant_ht", "sum"))
    return resume.sort_values("ca_ht", ascending=False)


def part_ca_non_rattachee(ventes):
    """Part du chiffre d'affaires HT sans rayon, entre 0 et 1 (0 si aucune vente)."""
    total = ventes["montant_ht"].sum()
    if total == 0:
        return 0.0
    return ventes.loc[ventes["rayon"].isna(), "montant_ht"].sum() / total
