"""Le jeu fictif cache des défauts connus ; l'outil doit tous les retrouver."""

import pandas as pd
import pytest

from retail_analytics import generateur, rayons
from retail_analytics.__main__ import preparer


@pytest.fixture(scope="module")
def jeu(tmp_path_factory):
    # scope="module" : le jeu est généré une seule fois pour tous les tests de ce fichier.
    dossier = tmp_path_factory.mktemp("fictif")
    verite = generateur.generer(dossier, tmp_path_factory.mktemp("exemple"))
    ventes, resultats = preparer(dossier / "sumup", dossier / "correspondances.csv")
    return verite, ventes, resultats


def test_retrouve_les_tickets_les_lignes_et_le_ca(jeu):
    verite, ventes, _ = jeu
    assert ventes["id_ticket"].nunique() == verite["nombre_tickets"]
    assert len(ventes) == verite["nombre_lignes"]
    assert ventes["montant_ttc"].sum() == verite["ca_ttc_centimes"]
    assert ventes["montant_ht"].sum() == verite["ca_ht_centimes"]


def test_retrouve_les_tickets_offerts(jeu):
    verite, ventes, _ = jeu
    assert ventes.loc[ventes["offert"], "id_ticket"].nunique() == verite["nombre_tickets_offerts"]


def test_retrouve_les_libelles_inconnus(jeu):
    verite, ventes, _ = jeu
    assert sorted(rayons.libelles_inconnus(ventes).index) == verite["libelles_inconnus"]


def test_retrouve_les_jours_sans_donnees(jeu):
    verite, ventes, _ = jeu
    periode = pd.date_range(*verite["periode"])
    jours_vus = set(ventes["journee_commerciale"])
    manquants = [jour.date().isoformat() for jour in periode if jour not in jours_vus]
    assert manquants == verite["jours_sans_donnees"]


def test_seule_la_journee_coupee_par_la_fin_de_l_export_est_en_ecart(jeu):
    verite, ventes, resultats = jeu
    ecarts = resultats.pop("totaux des journées")
    assert len(ecarts) == 1
    # L'écart porte sur la journée coupée : ses tickets exportés sont ceux comptés dans l'écart,
    # et la caisse en déclare davantage (ceux d'après minuit, hors de l'export).
    coupee = ventes["journee_commerciale"] == pd.Timestamp(verite["journee_coupee_par_la_fin_de_l_export"])
    ecart = ecarts.iloc[0]
    assert ecart["nombre_tickets_calcule"] == ventes.loc[coupee, "id_ticket"].nunique()
    assert ecart["nombre_tickets"] > ecart["nombre_tickets_calcule"]
    for nom, autres in resultats.items():
        assert autres.empty, nom
