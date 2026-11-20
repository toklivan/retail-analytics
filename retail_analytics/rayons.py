"""Rattachement de chaque vente à un rayon, par la table de correspondance.

Un libellé absent de la table n'est jamais deviné : son rayon reste vide,
il est listé, et la part du chiffre d'affaires qu'il représente est signalée.
"""

import pandas as pd

from retail_analytics.codes_barres import code_barres_valide


def lire_correspondances(chemin):
    """Lit la table `libelle;rayon;code_barres` et la valide.

    La colonne `code_barres` est facultative : une table sans elle reste valable,
    ses produits n'ont simplement pas encore de code-barres.
    """
    # dtype=str garde les codes-barres en texte : lu comme un nombre, 0012345678905 perdrait ses zéros.
    correspondances = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
    return valider_correspondances(correspondances)


def valider_correspondances(correspondances):
    """Refuse une table où un libellé n'a pas de rayon ou en a plusieurs, ou dont un code-barres est faux.

    Un libellé peut avoir plusieurs codes-barres (le produit a changé d'EAN) et un
    code-barres plusieurs libellés (le produit a été renommé en caisse), mais
    toujours dans un seul rayon.
    """
    if "code_barres" not in correspondances.columns:
        # assign rend une copie avec la colonne ajoutée, sans modifier la table reçue.
        correspondances = correspondances.assign(code_barres=pd.NA)
    sans_rayon = correspondances[correspondances["rayon"].isna()]
    if not sans_rayon.empty:
        raise ValueError(f"Libellés sans rayon : {list(sans_rayon['libelle'])}")
    # drop_duplicates retire les répétitions identiques ; s'il reste un libellé en double,
    # c'est qu'il est rangé dans deux rayons différents.
    rayons_des_libelles = correspondances[["libelle", "rayon"]].drop_duplicates()
    en_double = rayons_des_libelles[rayons_des_libelles["libelle"].duplicated()]
    if not en_double.empty:
        raise ValueError(f"Libellés rangés dans plusieurs rayons : {list(en_double['libelle'])}")
    codes = correspondances["code_barres"].dropna()
    faux = codes[~codes.map(code_barres_valide)]
    if not faux.empty:
        raise ValueError(f"Codes-barres invalides : {list(faux)}")
    rayons_des_codes = correspondances.dropna(subset=["code_barres"])[["code_barres", "rayon"]].drop_duplicates()
    en_double = rayons_des_codes[rayons_des_codes["code_barres"].duplicated()]
    if not en_double.empty:
        raise ValueError(f"Codes-barres rangés dans plusieurs rayons : {list(en_double['code_barres'])}")
    return correspondances.drop_duplicates().reset_index(drop=True)


def rattacher_rayons(ventes, correspondances):
    """Ajoute la colonne `rayon` aux ventes ; elle reste vide pour un libellé inconnu."""
    # Un libellé à deux codes-barres a deux lignes dans la table : sans drop_duplicates,
    # ses ventes seraient comptées deux fois.
    rayons_des_libelles = correspondances[["libelle", "rayon"]].drop_duplicates()
    return ventes.merge(rayons_des_libelles, on="libelle", how="left")


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
