"""Le jeu fictif cache des défauts connus ; l'outil doit tous les retrouver."""

import pandas as pd
import pytest

from retail_analytics import generateur, indicateurs, rayons
from retail_analytics.__main__ import preparer


@pytest.fixture(scope="module")
def jeu(tmp_path_factory):
    # scope="module" : le jeu est généré une seule fois pour tous les tests de ce fichier.
    dossier = tmp_path_factory.mktemp("fictif")
    verite = generateur.generer(dossier, tmp_path_factory.mktemp("exemple"))
    propres, resultats = preparer(dossier / "sumup", dossier / "correspondances.csv")
    return verite, propres, resultats


def test_retrouve_les_tickets_les_lignes_et_le_ca(jeu):
    verite, propres, _ = jeu
    ventes = propres["ventes"]
    assert ventes["id_ticket"].nunique() == verite["nombre_tickets"]
    assert len(ventes) == verite["nombre_lignes"]
    assert ventes["montant_ttc"].sum() == verite["ca_ttc_centimes"]
    assert ventes["montant_ht"].sum() == verite["ca_ht_centimes"]


def test_retrouve_les_tickets_offerts(jeu):
    verite, propres, _ = jeu
    ventes = propres["ventes"]
    assert ventes.loc[ventes["offert"], "id_ticket"].nunique() == verite["nombre_tickets_offerts"]


def test_retrouve_les_libelles_inconnus(jeu):
    verite, propres, _ = jeu
    ventes = propres["ventes"]
    assert sorted(rayons.libelles_inconnus(ventes).index) == verite["libelles_inconnus"]


def test_retrouve_les_jours_sans_donnees(jeu):
    verite, propres, _ = jeu
    ventes = propres["ventes"]
    periode = pd.date_range(*verite["periode"])
    jours_vus = set(ventes["journee_commerciale"])
    manquants = [jour.date().isoformat() for jour in periode if jour not in jours_vus]
    assert manquants == verite["jours_sans_donnees"]


def test_seule_la_journee_coupee_par_la_fin_de_l_export_est_en_ecart(jeu):
    verite, propres, resultats = jeu
    ventes = propres["ventes"]
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


def test_retrouve_les_tickets_payes_par_la_plateforme(jeu):
    verite, propres, _ = jeu
    paiements = propres["paiements"]
    payes_plateforme = paiements.loc[paiements["moyen_paiement"] == "plateforme", "id_ticket"]
    assert payes_plateforme.nunique() == verite["nombre_tickets_plateforme"]
    paniers = indicateurs.panier_moyen(propres["tickets"], paiements)
    assert paniers.xs("livraison", level="canal")["nombre_tickets"].sum() == verite["nombre_tickets_plateforme"]
    assert indicateurs.moyens_inconnus(paiements).empty
