from pathlib import Path

import pandas as pd

from retail_analytics import nettoyage, sumup

FIXTURES = Path(__file__).parent / "fixtures" / "sumup"


def journees_exemple():
    return pd.DataFrame({
        "id_journee": ["J1", "J2"],
        "ouverture": pd.to_datetime(["2026-03-02 08:55", "2026-03-03 09:00"]),
        "fermeture": pd.to_datetime(["2026-03-03 00:20", "2026-03-04 00:30"]),
    })


def tickets_a(*heures):
    return pd.DataFrame({"id_ticket": [f"T{n}" for n in range(len(heures))],
                         "date_heure": pd.to_datetime(list(heures))})


def test_dedoublonner_garde_le_premier_export():
    paiements = pd.DataFrame({
        "id_ticket": ["T1", "T1", "T2"],
        "montant_ttc": [350, 350, 200],
        "export": ["2026-01-01_2026-01-31", "2026-01-31_2026-02-28", "2026-01-31_2026-02-28"],
    })
    propres = nettoyage.dedoublonner(paiements, "id_ticket")
    assert list(propres["id_ticket"]) == ["T1", "T2"]
    assert "export" not in propres.columns


def test_dedoublonner_garde_deux_paiements_identiques_d_un_meme_ticket():
    paiements = pd.DataFrame({"id_ticket": ["T1", "T1"], "montant_ttc": [200, 200],
                              "export": ["2026-03-02_2026-03-03"] * 2})
    assert len(nettoyage.dedoublonner(paiements, "id_ticket")) == 2


def test_un_ticket_d_apres_minuit_appartient_a_la_journee_de_la_veille():
    tickets = nettoyage.rattacher_journees(tickets_a("2026-03-03 00:10"), journees_exemple())
    assert tickets.loc[0, "id_journee"] == "J1"
    assert tickets.loc[0, "journee_commerciale"] == pd.Timestamp("2026-03-02")


def test_un_ticket_hors_de_toute_journee_n_est_pas_rattache():
    # Avant la première ouverture, puis entre la fermeture de J1 et l'ouverture de J2.
    tickets = nettoyage.rattacher_journees(tickets_a("2026-03-02 08:00", "2026-03-03 05:00"),
                                           journees_exemple())
    assert tickets["id_journee"].isna().all()
    assert tickets["journee_commerciale"].isna().all()
    assert len(nettoyage.tickets_sans_journee(tickets)) == 2


def test_marquer_offerts():
    ventes = pd.DataFrame({"prix_unitaire_ttc": [190, 110, 0], "montant_ttc": [0, 110, 0]})
    assert list(nettoyage.marquer_offerts(ventes)["offert"]) == [True, False, False]


def test_nettoyer_produit_la_table_des_ventes_du_modele():
    propres = nettoyage.nettoyer(sumup.lire_export(FIXTURES))
    ventes = propres["ventes"]
    assert list(ventes.columns) == nettoyage.COLONNES_VENTES
    assert list(ventes.loc[ventes["offert"], "libelle"]) == ["Chips nature 150g"]
    mystere = ventes.set_index("libelle").loc["Produit mystère"]
    assert mystere["numero_ticket"] == "A4"
    assert mystere["journee_commerciale"] == pd.Timestamp("2026-03-02")
    assert nettoyage.tickets_sans_journee(propres["tickets"]).empty
