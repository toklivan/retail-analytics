from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import controles, indicateurs, nettoyage, rapport, rayons, sumup

FIXTURES = Path(__file__).parent / "fixtures"
MARS = pd.Period("2026-03")
LE_19_OCTOBRE = pd.Timestamp("2026-10-19")


@pytest.fixture
def propres():
    propres = nettoyage.nettoyer(sumup.lire_export(FIXTURES / "sumup"))
    correspondances = rayons.lire_correspondances(FIXTURES / "correspondances.csv")
    propres["ventes"] = rayons.rattacher_rayons(propres["ventes"], correspondances)
    return propres


def construire(propres, mois=MARS, resultats=None):
    if resultats is None:
        resultats = controles.controler(propres)
    complets = indicateurs.mois_complets(propres["periodes"])
    return rapport.construire_rapport(propres, resultats, mois, complets, LE_19_OCTOBRE)


def comparaison(rayons_et_montants):
    """Tableau au format de `comparer_au_mois_precedent`, depuis {rayon: (précédent, actuel)}."""
    tableau = pd.DataFrame(rayons_et_montants.values(), index=list(rayons_et_montants), columns=["precedent", "actuel"])
    # Comme dans comparer_au_mois_precedent : pas d'évolution quand le mois précédent est à 0.
    precedent = tableau["precedent"].where(tableau["precedent"] != 0)
    return tableau.assign(evolution=(tableau["actuel"] - tableau["precedent"]) / precedent)


PRODUITS = pd.DataFrame({"ca_ht": [600, 400]}, index=["Pastis 70cl", "Baguette"])


def test_les_rayons_sont_classes_sur_l_ecart_en_euros():
    # Divers double (+50 €), Boissons ne prend que 20 % (+200 €) : c'est Boissons qui compte.
    points = rapport.points_a_retenir(comparaison({"Boissons": (100000, 120000), "Divers": (5000, 10000)}),
                                      PRODUITS, pd.Period("2026-09"), comparable=True)
    assert points[0] == "Le rayon Boissons progresse le plus : +200,00 € HT par rapport à 08/2026 (+20,0 %)."


def test_le_rayon_qui_recule_le_plus():
    points = rapport.points_a_retenir(comparaison({"Boissons": (100000, 120000), "Alcools": (50000, 40000)}),
                                      PRODUITS, pd.Period("2026-09"), comparable=True)
    assert points[1] == "Le rayon Alcools recule le plus : -100,00 € HT par rapport à 08/2026 (-20,0 %)."


def test_les_ventes_sans_rayon_ne_sont_pas_classees():
    points = rapport.points_a_retenir(comparaison({None: (0, 90000), "Boissons": (100000, 101000)}),
                                      PRODUITS, pd.Period("2026-09"), comparable=True)
    assert points[0].startswith("Le rayon Boissons progresse le plus")


def test_sans_rayon_en_baisse_pas_de_phrase_de_baisse():
    points = rapport.points_a_retenir(comparaison({"Boissons": (100000, 120000)}), PRODUITS,
                                      pd.Period("2026-09"), comparable=True)
    assert not any("recule" in point for point in points)


def test_un_rayon_nouveau_n_a_pas_de_pourcentage():
    points = rapport.points_a_retenir(comparaison({"Boissons": (0, 5000)}), PRODUITS,
                                      pd.Period("2026-09"), comparable=True)
    assert points[0] == "Le rayon Boissons progresse le plus : +50,00 € HT par rapport à 08/2026."


def test_pas_de_comparaison_si_un_mois_est_incomplet():
    points = rapport.points_a_retenir(comparaison({"Boissons": (100000, 120000)}), PRODUITS,
                                      pd.Period("2026-09"), comparable=False)
    assert points[0].startswith("Pas de comparaison par rayon avec 08/2026")
    assert not any("progresse" in point for point in points)


def test_le_produit_numero_un_et_sa_part():
    points = rapport.points_a_retenir(comparaison({}), PRODUITS, pd.Period("2026-09"), comparable=True)
    assert points == ["Produit n°1 : Pastis 70cl, avec 6,00 € HT, soit 60,0 % du CA HT du mois."]


def test_le_rapport_porte_le_mois_la_periode_et_la_date(propres):
    page = construire(propres)
    assert "<title>Rapport de ventes, mars 2026</title>" in page
    assert "du 01/03/2026 au 31/03/2026" in page
    assert "Rapport établi le 19/10/2026" in page


def test_le_rapport_reprend_les_indicateurs_du_mois(propres):
    page = construire(propres)
    # CA TTC et CA HT des fixtures, voir test_indicateurs.
    assert "10,30 €" in page
    assert "8,99 €" in page


def test_un_mois_incomplet_est_annonce_en_tete(propres):
    # Les fixtures ne couvrent que les 2 et 3 mars.
    assert "Mars 2026 est incomplet" in construire(propres)


def test_un_controle_en_ecart_est_annonce_en_tete(propres):
    resultats = controles.controler(propres)
    resultats["totaux des journées"] = pd.DataFrame({"ecart": [100]})
    page = construire(propres, resultats=resultats)
    assert "Contrôles en écart sur l&#x27;ensemble des exports : totaux des journées." in page


def test_un_libelle_inconnu_apparait_dans_la_fiabilite(propres):
    page = construire(propres)
    fiabilite = page[page.index("Fiabilité des données"):]
    assert "Produit mystère" in fiabilite


def test_un_libelle_est_echappe(propres):
    ventes = propres["ventes"]
    ventes.loc[ventes["libelle"] == "Produit mystère", "libelle"] = "Thé <menthe> & co"
    page = construire(propres)
    assert "Thé &lt;menthe&gt; &amp; co" in page
    assert "<menthe>" not in page


def test_un_mois_sans_vente_est_refuse(propres):
    with pytest.raises(ValueError, match="Aucune vente en 04/2026"):
        construire(propres, mois=pd.Period("2026-04"))


def test_la_classe_a_est_limitee_et_le_reste_resume():
    par_produit = pd.DataFrame({"rayon": "Alcools", "ca_ht": [500, 300, 100, 100], "quantite": 1,
                                "part": [0.5, 0.3, 0.1, 0.1], "part_cumulee": [0.5, 0.8, 0.9, 1.0],
                                "classe": ["A", "A", "A", "B"]},
                               index=["Whisky 70cl", "Pastis 70cl", "Vodka 70cl", "Rhum 70cl"])
    section = rapport.section_produits(par_produit, MARS, nombre_affiches=2)
    assert "Pastis 70cl" in section.split("<h3>Les premiers")[1]
    assert "Vodka 70cl" not in section.split("<h3>Les premiers")[1]
    assert "Et 1 autre(s) produit(s) en classe A, qui font 10,0 % du CA HT." in section
