from pathlib import Path

import pytest

from retail_analytics import controles, nettoyage, sumup

FIXTURES = Path(__file__).parent / "fixtures" / "sumup"


@pytest.fixture
def propres():
    return nettoyage.nettoyer(sumup.lire_export(FIXTURES))


def test_les_fixtures_passent_tous_les_controles(propres):
    for nom, ecarts in controles.controler(propres).items():
        assert ecarts.empty, nom


# Les tests suivants cassent volontairement une règle pour vérifier que le contrôle le voit.

def test_signale_un_ticket_dont_les_lignes_ne_font_pas_le_total(propres):
    tickets = propres["tickets"]
    tickets.loc[tickets["id_ticket"] == "T1", "montant_ttc"] = 360
    ecarts = controles.ecarts_lignes_tickets(propres["ventes"], tickets)
    assert list(ecarts.index) == ["T1"]
    assert ecarts.loc["T1", "montant_ttc"] == 360
    assert ecarts.loc["T1", "montant_ttc_calcule"] == 350


def test_signale_un_ticket_sans_paiement(propres):
    paiements = propres["paiements"]
    paiements = paiements[paiements["id_ticket"] != "T4"]
    ecarts = controles.ecarts_paiements_tickets(paiements, propres["tickets"])
    assert list(ecarts.index) == ["T4"]
    assert ecarts.loc["T4", "montant_ttc_calcule"] == 0


def test_signale_une_journee_a_laquelle_il_manque_un_ticket(propres):
    tickets = propres["tickets"]
    tickets = tickets[tickets["id_ticket"] != "T4"]
    ecarts = controles.ecarts_journees(tickets, propres["journees"])
    assert list(ecarts.index) == ["J1"]
    assert ecarts.loc["J1", "nombre_tickets_calcule"] == 3


def test_signale_des_remises_sans_article_offert(propres):
    ventes = propres["ventes"]
    ventes["offert"] = False
    ecarts = controles.ecarts_remises(ventes, propres["tickets"], propres["journees"])
    assert ecarts.loc["J1", "remises_ttc"] == 190
    assert ecarts.loc["J1", "remises_ttc_calcule"] == 0


def test_signale_un_ticket_sans_journee(propres):
    journees = propres["journees"]
    journees["fermeture"] = journees["fermeture"].dt.normalize()
    tickets = nettoyage.rattacher_journees(propres["tickets"].drop(columns=["id_journee",
                                                                           "journee_commerciale"]), journees)
    resultats = controles.controler({**propres, "tickets": tickets, "journees": journees})
    assert list(resultats["tickets sans journée"].index) == ["T4"]
