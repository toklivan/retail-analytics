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


def test_carte_de_chaleur():
    # Deux heures, dont 0 h 30 après minuit ; le dimanche n'a jamais été ouvert.
    table = pd.DataFrame({18: [45000.0] * 6 + [None], 24: [0.0] * 5 + [70000.0, None]}, index=range(7))
    axe = graphiques.carte_de_chaleur(table).axes[0]
    image = axe.images[0].get_array()
    # Une case par jour et par heure, en euros.
    assert image.shape == (7, 2)
    assert image[5, 1] == 700
    # La case du dimanche reste vide : elle n'est pas tracée à 0 €.
    assert image.mask[6, 0]
    assert [etiquette.get_text() for etiquette in axe.get_xticklabels()] == ["18 h", "0 h"]
    assert axe.get_yticklabels()[6].get_text() == "dimanche"
