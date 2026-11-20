from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import inventaire

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def lignes():
    return inventaire.lire_inventaire(FIXTURES / "inventaire-2026-03-03.csv")


def test_la_date_vient_du_nom_du_fichier(lignes):
    assert (lignes["date_inventaire"] == pd.Timestamp("2026-03-03")).all()


def test_refuse_un_nom_de_fichier_sans_date():
    with pytest.raises(ValueError, match="inventaire-AAAA-MM-JJ"):
        inventaire.date_du_fichier(Path("comptage.csv"))


def test_refuse_des_colonnes_inattendues(tmp_path):
    chemin = tmp_path / "inventaire-2026-03-03.csv"
    chemin.write_text("ean;qte\n2000000000046;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Colonnes attendues"):
        inventaire.lire_inventaire(chemin)


def test_signale_les_lignes_fautives_avec_leur_raison(lignes):
    rejetees = inventaire.lignes_rejetees(lignes)
    assert list(zip(rejetees["code_barres"], rejetees["raison"])) == [
        ("2000000000047", "code-barres invalide"),
        ("2000000000411", "quantité illisible"),
    ]


def test_refuse_une_quantite_negative_ou_decimale():
    lignes = pd.DataFrame({"code_barres": ["2000000000046"] * 3, "quantite": ["-2", "1,5", ""]})
    assert len(inventaire.lignes_rejetees(lignes)) == 3


def test_additionne_le_rayon_et_la_reserve(lignes):
    stock = inventaire.stock_compte(lignes).set_index("code_barres")["quantite_comptee"]
    # 12 en rayon, puis 5 en réserve (saisi avec une espace, retirée à la lecture).
    assert stock["2000000000046"] == 17


def test_le_stock_ecarte_les_lignes_fautives_mais_garde_un_zero(lignes):
    stock = inventaire.stock_compte(lignes).set_index("code_barres")["quantite_comptee"]
    assert "2000000000047" not in stock.index
    # « 1O » est écarté, la ligne à 0 est gardée : le produit a été vu, en rupture.
    assert stock["2000000000411"] == 0
    assert stock.sum() == 17 + 6 + 2 + 0
