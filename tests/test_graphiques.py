import pandas as pd
from matplotlib.colors import to_rgba

from retail_analytics import graphiques

SEPTEMBRE = pd.Period("2026-09")


def ca_par_mois():
    # La ligne au mois vide est celle des tickets sans journée connue.
    index = pd.PeriodIndex(["2026-08", "2026-09", "2026-10", None], freq="M", name="mois")
    return pd.DataFrame({"ca_ht": [2000000, 2100000, 900000, 500]}, index=index)


def test_une_barre_par_mois_connu():
    figure = graphiques.evolution_ca(ca_par_mois(), pd.Series({SEPTEMBRE: True}), SEPTEMBRE)
    barres = figure.axes[0].patches
    assert len(barres) == 3
    # Tracé en euros : 2 100 000 centimes font 21 000 €.
    assert barres[1].get_height() == 21000


def test_le_mois_du_rapport_est_en_fonce_et_un_mois_incomplet_hachure():
    complets = pd.Series({pd.Period("2026-08"): True, SEPTEMBRE: True, pd.Period("2026-10"): False})
    aout, septembre, octobre = graphiques.evolution_ca(ca_par_mois(), complets, SEPTEMBRE).axes[0].patches
    assert septembre.get_facecolor() == to_rgba(graphiques.COULEUR_MOIS)
    assert aout.get_facecolor() == to_rgba(graphiques.COULEUR_AUTRE)
    assert octobre.get_hatch() == "//"
    assert not aout.get_hatch()


def test_les_ventes_sans_rayon_ont_un_nom():
    comparaison = pd.DataFrame({"precedent": [100, 50], "actuel": [120, 40]}, index=["Boissons", None])
    axe = graphiques.rayons(comparaison, SEPTEMBRE).axes[0]
    assert [etiquette.get_text() for etiquette in axe.get_yticklabels()] == ["Boissons", "non rattaché"]


def test_dix_produits_au_plus():
    par_produit = pd.DataFrame({"ca_ht": range(1500, 0, -100)}, index=[f"Produit {n}" for n in range(15)])
    assert len(graphiques.premiers_produits(par_produit).axes[0].patches) == 10
