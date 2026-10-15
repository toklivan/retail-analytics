from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import sumup

FIXTURES = Path(__file__).parent / "fixtures" / "sumup"


@pytest.fixture
def export():
    # Une « fixture » pytest : une valeur préparée une fois et passée aux tests qui la demandent.
    return sumup.lire_export(FIXTURES)


def test_lit_les_quatre_tables(export):
    assert len(export["ventes"]) == 5
    assert len(export["tickets"]) == 4
    assert len(export["paiements"]) == 4
    assert len(export["journees"]) == 1


def test_traduit_les_colonnes(export):
    assert list(export["ventes"].columns) == ["id_ticket", "date_heure", "libelle", "quantite",
                                              "prix_unitaire_ttc", "montant_ttc", "montant_ht", "export"]
    assert list(export["journees"].columns) == ["id_journee", "ouverture", "fermeture", "nombre_tickets",
                                                "ca_ttc", "ca_ht", "remises_ttc", "export"]


def test_convertit_montants_quantites_et_dates(export):
    baguette = export["ventes"].iloc[0]
    assert baguette["quantite"] == 2
    assert baguette["prix_unitaire_ttc"] == 110
    assert baguette["montant_ttc"] == 220
    assert baguette["montant_ht"] == 209
    assert baguette["date_heure"] == pd.Timestamp("2026-03-02 10:00:00")
    assert export["journees"].iloc[0]["remises_ttc"] == 190


def test_garde_le_ticket_d_apres_minuit_a_sa_vraie_date(export):
    ticket = export["tickets"].set_index("id_ticket").loc["T4"]
    assert ticket["date_heure"] == pd.Timestamp("2026-03-03 00:10:00")


def test_en_centimes_lit_les_montants_negatifs_et_nuls():
    textes = pd.Series(["12,40", "0,00", "-1,10", "0,07"])
    assert list(sumup.en_centimes(textes)) == [1240, 0, -110, 7]


def test_en_centimes_refuse_un_montant_illisible():
    with pytest.raises(ValueError, match="12 euros"):
        sumup.en_centimes(pd.Series(["1,00", "12 euros"], name="Sales incl Tax"))


def test_en_entiers_refuse_une_quantite_decimale():
    with pytest.raises(ValueError, match="1,5"):
        sumup.en_entiers(pd.Series(["2", "1,5"], name="Quantity"))


def test_signale_une_colonne_absente():
    brut = pd.DataFrame({"Order ID": ["T1"]})
    with pytest.raises(ValueError, match="Payment Method"):
        sumup.preparer_paiements(brut)


def test_signale_un_dossier_sans_export(tmp_path):
    # tmp_path : dossier temporaire vide fourni par pytest, effacé après le test.
    with pytest.raises(FileNotFoundError):
        sumup.lire_export(tmp_path)


def test_met_bout_a_bout_plusieurs_exports(tmp_path):
    for periode in ["2026-03-01_2026-03-02", "2026-03-02_2026-03-03"]:
        source = FIXTURES / "orders-report-products-2026-03-02_2026-03-03.csv"
        (tmp_path / f"orders-report-products-{periode}.csv").write_bytes(source.read_bytes())
    brut = sumup.lire_fichiers(tmp_path, "orders-report-products")
    assert len(brut) == 10
    assert sorted(brut["export"].unique()) == ["2026-03-01_2026-03-02", "2026-03-02_2026-03-03"]
