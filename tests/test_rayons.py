from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import nettoyage, rayons, sumup

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ventes():
    propres = nettoyage.nettoyer(sumup.lire_export(FIXTURES / "sumup"))
    correspondances = rayons.lire_correspondances(FIXTURES / "correspondances.csv")
    return rayons.rattacher_rayons(propres["ventes"], correspondances)


def test_chaque_vente_connue_recoit_son_rayon(ventes):
    par_libelle = ventes.set_index("libelle")["rayon"]
    assert par_libelle["Baguette"] == "Boulangerie"
    assert par_libelle["Bière blonde 33cl"] == "Alcools"


def test_un_libelle_inconnu_n_est_pas_devine(ventes):
    assert ventes.set_index("libelle")["rayon"].isna()["Produit mystère"]
    inconnus = rayons.libelles_inconnus(ventes)
    assert list(inconnus.index) == ["Produit mystère"]
    assert inconnus.loc["Produit mystère", "ca_ht"] == 167


def test_part_du_ca_non_rattachee(ventes):
    # 1,67 € sur 8,99 € de CA HT.
    assert rayons.part_ca_non_rattachee(ventes) == pytest.approx(167 / 899)


def test_part_non_rattachee_sans_vente():
    vide = pd.DataFrame({"montant_ht": pd.Series(dtype="int64"), "rayon": pd.Series(dtype=str)})
    assert rayons.part_ca_non_rattachee(vide) == 0.0


def test_accepte_une_correspondance_repetee_a_l_identique():
    table = pd.DataFrame({"libelle": ["Baguette", "Baguette"], "rayon": ["Boulangerie", "Boulangerie"]})
    assert len(rayons.valider_correspondances(table)) == 1


def test_refuse_un_libelle_range_dans_deux_rayons():
    table = pd.DataFrame({"libelle": ["Croissant", "Croissant"], "rayon": ["Boulangerie", "Snacking"]})
    with pytest.raises(ValueError, match="Croissant"):
        rayons.valider_correspondances(table)


def test_refuse_un_libelle_sans_rayon():
    table = pd.DataFrame({"libelle": ["Croissant"], "rayon": [None]})
    with pytest.raises(ValueError, match="Croissant"):
        rayons.valider_correspondances(table)
