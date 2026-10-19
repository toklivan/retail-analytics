"""Graphiques du rapport mensuel.

Chaque fonction prend un tableau d'indicateurs et rend une figure matplotlib,
sans lire de fichier ni rien afficher. Les montants arrivent en centimes et
sont tracés en euros.

On crée les figures avec `Figure` plutôt qu'avec `pyplot` : pyplot garde
chaque figure dans une liste globale et suppose un écran pour l'afficher.
Une `Figure` créée directement est un objet Python ordinaire, libéré quand
on ne s'en sert plus.
"""

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from retail_analytics.affichage import mois_fr, nombre

# Le mois détaillé en couleur foncée, le reste en couleur claire.
COULEUR_MOIS = "#1f4e79"
COULEUR_AUTRE = "#a9bcd0"


def en_euros(centimes):
    """Centimes -> euros, pour les tracés."""
    return centimes / 100


def axe_en_euros(axe):
    """Graduations de l'axe des montants au format « 12 000 € »."""
    # FuncFormatter applique notre fonction à chaque graduation de l'axe.
    axe.set_major_formatter(FuncFormatter(lambda valeur, _: f"{nombre(int(valeur))} €"))


def nom_de_rayon(rayon):
    """Les ventes sans rayon ont un nom lisible plutôt qu'une case vide."""
    return "non rattaché" if pd.isna(rayon) else rayon


def evolution_ca(ca_par_mois, complets, mois):
    """Barres du CA HT de chaque mois ; le mois détaillé en foncé, un mois incomplet hachuré.

    `ca_par_mois` est le tableau de `indicateurs.chiffre_affaires`. La ligne des
    tickets sans journée n'a pas de mois : elle n'est pas tracée.
    """
    # notna garde les lignes dont le mois est connu.
    ca = ca_par_mois[ca_par_mois.index.notna()]
    figure = Figure(figsize=(8, 3.5))
    axe = figure.add_subplot()
    positions = range(len(ca))
    couleurs = [COULEUR_MOIS if m == mois else COULEUR_AUTRE for m in ca.index]
    barres = axe.bar(positions, en_euros(ca["ca_ht"]), color=couleurs)
    # zip parcourt les deux listes ensemble : chaque barre avec son mois.
    for barre, m in zip(barres, ca.index):
        if not complets.get(m, False):
            barre.set_hatch("//")
            axe.annotate("incomplet", (barre.get_x() + barre.get_width() / 2, barre.get_height()),
                         ha="center", va="bottom", fontsize=8)
    axe.set_xticks(list(positions), [mois_fr(m) for m in ca.index], rotation=45, ha="right")
    axe_en_euros(axe.yaxis)
    axe.set_title("Chiffre d'affaires HT par mois")
    axe.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    return figure


def rayons(comparaison, mois):
    """Barres horizontales du CA HT par rayon : le mois et, à côté, le mois précédent.

    `comparaison` est le tableau de `indicateurs.comparer_au_mois_precedent`,
    trié du plus gros rayon au plus petit ; le plus gros est tracé en haut.
    """
    figure = Figure(figsize=(8, 1 + 0.5 * len(comparaison)))
    axe = figure.add_subplot()
    positions = range(len(comparaison))
    epaisseur = 0.4
    axe.barh([p - epaisseur / 2 for p in positions], en_euros(comparaison["actuel"]), height=epaisseur,
             color=COULEUR_MOIS, label=mois_fr(mois))
    axe.barh([p + epaisseur / 2 for p in positions], en_euros(comparaison["precedent"]), height=epaisseur,
             color=COULEUR_AUTRE, label=mois_fr(mois - 1))
    axe.set_yticks(list(positions), [nom_de_rayon(r) for r in comparaison.index])
    # Sans inversion, la première ligne du tableau serait tracée en bas.
    axe.invert_yaxis()
    axe_en_euros(axe.xaxis)
    axe.set_title("Chiffre d'affaires HT par rayon")
    axe.legend(loc="lower right")
    axe.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    return figure


def premiers_produits(par_produit, nombre_produits=10):
    """Barres horizontales du CA HT des premiers produits du mois, le plus gros en haut.

    `par_produit` est trié du plus gros CA au plus petit, comme le rend
    `indicateurs.ventes_par_produit`.
    """
    premiers = par_produit.head(nombre_produits)
    figure = Figure(figsize=(8, 1 + 0.4 * len(premiers)))
    axe = figure.add_subplot()
    positions = range(len(premiers))
    axe.barh(positions, en_euros(premiers["ca_ht"]), color=COULEUR_MOIS)
    axe.set_yticks(list(positions), list(premiers.index))
    axe.invert_yaxis()
    axe_en_euros(axe.xaxis)
    axe.set_title(f"Les {len(premiers)} premiers produits, CA HT")
    axe.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    return figure
