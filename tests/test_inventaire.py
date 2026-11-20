from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import inventaire
from retail_analytics.__main__ import dernier_inventaire
from retail_analytics.catalogue import code_barres_fictif

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


# Un petit magasin écrit à la main : un produit renommé en caisse (Cola), un produit
# qui a changé de code-barres (Chips), une nouveauté jamais vendue (Pesto), un oubli
# de comptage (Miel), un produit sans code-barres (Baguette).
COLA, CHIPS_ANCIEN, CHIPS, PESTO, MIEL, INCONNU = (code_barres_fictif(n) for n in [1, 2, 3, 4, 5, 999])


@pytest.fixture
def correspondances():
    return pd.DataFrame([
        ("Baguette", "Boulangerie", None),
        ("Cola 33cl", "Boissons", COLA),
        ("Cola canette 33cl", "Boissons", COLA),
        ("Chips 150g", "Épicerie salée", CHIPS_ANCIEN),
        ("Chips 150g", "Épicerie salée", CHIPS),
        ("Sauce pesto 190g", "Épicerie salée", PESTO),
        ("Miel 250g", "Épicerie sucrée", MIEL),
    ], columns=["libelle", "rayon", "code_barres"])


@pytest.fixture
def stock():
    return pd.DataFrame({"date_inventaire": pd.Timestamp("2026-03-03"),
                         "code_barres": [COLA, CHIPS, PESTO, INCONNU], "quantite_comptee": [10, 4, 2, 3]})


@pytest.fixture
def ventes():
    return pd.DataFrame({"libelle": ["Cola 33cl", "Chips 150g", "Miel 250g", "Miel 250g", "Baguette", "Produit mystère"],
                         "montant_ht": [500, 300, 450, 450, 200, 100],
                         "journee_commerciale": pd.Timestamp("2026-03-02")})


def test_un_produit_renomme_garde_ses_deux_libelles_sur_une_ligne(stock, correspondances):
    rattache = inventaire.stock_rattache(stock, correspondances)
    assert len(rattache) == len(stock)
    assert rattache.set_index("code_barres").loc[COLA, "libelle"] == "Cola 33cl / Cola canette 33cl"


def test_un_code_inconnu_n_est_pas_devine(stock, correspondances):
    rattache = inventaire.stock_rattache(stock, correspondances)
    assert list(inventaire.codes_inconnus(rattache)["code_barres"]) == [INCONNU]


def test_compte_mais_jamais_vendu(stock, correspondances, ventes):
    rattache = inventaire.stock_rattache(stock, correspondances)
    # Le Cola compte comme vendu par son ancien libellé.
    assert list(inventaire.comptes_jamais_vendus(rattache, ventes, correspondances)["libelle"]) == ["Sauce pesto 190g"]


def test_vendu_mais_jamais_compte(stock, correspondances, ventes):
    oublis = inventaire.vendus_jamais_comptes(ventes, correspondances, stock)
    # Les chips sont comptées sous leur nouveau code ; la baguette, sans code, n'est pas un oubli.
    assert oublis[["libelle", "ca_ht"]].values.tolist() == [["Miel 250g", 900]]


def test_vendu_sans_code_barres(correspondances, ventes):
    sans_code = inventaire.vendus_sans_code_barres(ventes, correspondances)
    assert sans_code[["libelle", "ca_ht"]].values.tolist() == [["Baguette", 200]]


def test_garde_les_ventes_jusqu_au_jour_de_l_inventaire_inclus():
    ventes = pd.DataFrame({"journee_commerciale": pd.to_datetime(["2026-03-02", "2026-03-03", "2026-03-04"])})
    gardees = inventaire.ventes_jusqu_a(ventes, pd.Timestamp("2026-03-03"))
    assert list(gardees["journee_commerciale"].dt.day) == [2, 3]


def test_prend_l_inventaire_le_plus_recent(tmp_path):
    for nom in ["inventaire-2026-10-14.csv", "inventaire-2026-03-03.csv", "stock-2026-12-31.csv"]:
        (tmp_path / nom).write_text("code_barres;quantite\n", encoding="utf-8")
    assert dernier_inventaire(tmp_path).name == "inventaire-2026-10-14.csv"


def test_signale_un_dossier_sans_inventaire(tmp_path):
    with pytest.raises(SystemExit, match="Aucun fichier inventaire"):
        dernier_inventaire(tmp_path)
