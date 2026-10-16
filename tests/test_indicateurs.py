from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import indicateurs, nettoyage, sumup

FIXTURES = Path(__file__).parent / "fixtures" / "sumup"
MARS = pd.Period("2026-03")


@pytest.fixture
def propres():
    return nettoyage.nettoyer(sumup.lire_export(FIXTURES))


def test_le_mois_est_celui_de_la_journee_commerciale():
    # Ticket de 0 h 10 le 1er avril, dans la journée ouverte le 31 mars : il compte en mars.
    tickets = pd.DataFrame({"journee_commerciale": pd.to_datetime(["2026-03-31"]),
                            "montant_ttc": [200], "montant_ht": [167]})
    assert list(indicateurs.chiffre_affaires(tickets).index) == [MARS]


def test_chiffre_affaires_du_mois(propres):
    mars = indicateurs.chiffre_affaires(propres["tickets"]).loc[MARS]
    assert mars["ca_ttc"] == 1030
    assert mars["ca_ht"] == 899
    assert mars["tickets_payants"] == 3
    # Le ticket T3, dont l'article a été offert, est compté à part.
    assert mars["tickets_offerts"] == 1


def test_un_ticket_sans_journee_n_est_pas_ecarte_en_silence():
    tickets = pd.DataFrame({"journee_commerciale": pd.to_datetime(["2026-03-02", None]),
                            "montant_ttc": [350, 200], "montant_ht": [332, 167]})
    ca = indicateurs.chiffre_affaires(tickets)
    assert len(ca) == 2
    assert ca["ca_ttc"].sum() == 550


def test_ventes_par_moyen_de_paiement(propres):
    mars = indicateurs.ventes_par_moyen(propres["paiements"], propres["tickets"]).loc[MARS]
    # T1 en carte (3,50 €), T2 en carte (2,80 €) et en espèces (2,00 €), T4 par la plateforme.
    assert mars.to_dict() == {"especes": 200, "carte": 630, "plateforme": 200}


def test_les_moyens_de_paiement_font_le_chiffre_d_affaires_ttc(propres):
    moyens = indicateurs.ventes_par_moyen(propres["paiements"], propres["tickets"])
    ca = indicateurs.chiffre_affaires(propres["tickets"])
    assert moyens.sum(axis=1).loc[MARS] == ca.loc[MARS, "ca_ttc"]


def test_un_moyen_de_paiement_inconnu_a_sa_colonne_et_il_est_signale(propres):
    paiements = propres["paiements"]
    paiements.loc[paiements["id_ticket"] == "T4", "moyen_paiement"] = "TITRE_RESTO"
    moyens = indicateurs.ventes_par_moyen(paiements, propres["tickets"])
    assert list(moyens.columns) == ["especes", "carte", "plateforme", "TITRE_RESTO"]
    assert moyens.loc[MARS, "plateforme"] == 0
    inconnus = indicateurs.moyens_inconnus(paiements)
    assert inconnus.loc["TITRE_RESTO"].to_dict() == {"nombre_paiements": 1, "montant_ttc": 200}


def test_aucun_moyen_inconnu_dans_les_fixtures(propres):
    assert indicateurs.moyens_inconnus(propres["paiements"]).empty


def test_un_ticket_paye_en_partie_par_la_plateforme_est_une_livraison():
    tickets = pd.DataFrame({"id_ticket": ["T1", "T2"]})
    paiements = pd.DataFrame({"id_ticket": ["T1", "T2", "T2"],
                              "moyen_paiement": ["carte", "carte", "plateforme"]})
    canaux = indicateurs.canal_des_tickets(tickets, paiements)
    assert list(canaux["canal"]) == ["magasin", "livraison"]


def test_panier_moyen_par_canal(propres):
    paniers = indicateurs.panier_moyen(propres["tickets"], propres["paiements"])
    # Magasin : T1 (3,50 €) et T2 (4,80 €) ; T3, offert, n'est pas compté. Livraison : T4 (2,00 €).
    assert paniers.loc[(MARS, "magasin")].to_dict() == {"nombre_tickets": 2, "ca_ttc": 830, "panier_moyen": 415}
    assert paniers.loc[(MARS, "livraison")].to_dict() == {"nombre_tickets": 1, "ca_ttc": 200, "panier_moyen": 200}


def test_le_panier_moyen_est_arrondi_au_centime():
    tickets = pd.DataFrame({"id_ticket": ["T1", "T2", "T3"], "montant_ttc": [100, 100, 101],
                            "journee_commerciale": pd.to_datetime(["2026-03-02"] * 3)})
    paiements = pd.DataFrame({"id_ticket": ["T1", "T2", "T3"], "moyen_paiement": ["carte"] * 3})
    assert indicateurs.panier_moyen(tickets, paiements).loc[(MARS, "magasin"), "panier_moyen"] == 100


def test_un_mois_sans_livraison_n_a_pas_de_panier_livraison():
    tickets = pd.DataFrame({"id_ticket": ["T1"], "montant_ttc": [350],
                            "journee_commerciale": pd.to_datetime(["2026-03-02"])})
    paiements = pd.DataFrame({"id_ticket": ["T1"], "moyen_paiement": ["especes"]})
    paniers = indicateurs.panier_moyen(tickets, paiements)
    assert list(paniers.index) == [(MARS, "magasin")]
