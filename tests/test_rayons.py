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


def test_lit_une_table_sans_colonne_code_barres(tmp_path):
    chemin = tmp_path / "correspondances.csv"
    chemin.write_text("libelle;rayon\nBaguette;Boulangerie\n", encoding="utf-8")
    table = rayons.lire_correspondances(chemin)
    assert table["code_barres"].isna().all()


def test_garde_les_zeros_en_tete_d_un_code_barres(tmp_path):
    chemin = tmp_path / "correspondances.csv"
    chemin.write_text("libelle;rayon;code_barres\nCafé;Épicerie sucrée;0012345678905\n", encoding="utf-8")
    assert rayons.lire_correspondances(chemin).loc[0, "code_barres"] == "0012345678905"


def test_refuse_un_code_barres_invalide():
    table = pd.DataFrame({"libelle": ["Cola 33cl"], "rayon": ["Boissons"], "code_barres": ["2000000000047"]})
    with pytest.raises(ValueError, match="2000000000047"):
        rayons.valider_correspondances(table)


def test_refuse_un_code_barres_range_dans_deux_rayons():
    table = pd.DataFrame({"libelle": ["Cola 33cl", "Chips 150g"], "rayon": ["Boissons", "Épicerie salée"],
                          "code_barres": ["2000000000046", "2000000000046"]})
    with pytest.raises(ValueError, match="2000000000046"):
        rayons.valider_correspondances(table)


def test_accepte_un_produit_renomme_et_un_produit_qui_change_de_code():
    table = pd.DataFrame({"libelle": ["Cola 33cl", "Cola canette 33cl", "Chips 150g", "Chips 150g"],
                          "rayon": ["Boissons", "Boissons", "Épicerie salée", "Épicerie salée"],
                          "code_barres": ["2000000000046", "2000000000046", "2000000000411", "2000000000428"]})
    assert len(rayons.valider_correspondances(table)) == 4


def test_un_libelle_a_deux_codes_ne_double_pas_ses_ventes():
    ventes = pd.DataFrame({"libelle": ["Chips 150g"], "montant_ht": [180]})
    table = pd.DataFrame({"libelle": ["Chips 150g", "Chips 150g"], "rayon": ["Épicerie salée"] * 2,
                          "code_barres": ["2000000000411", "2000000000428"]})
    assert len(rayons.rattacher_rayons(ventes, table)) == 1
