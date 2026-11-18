from pathlib import Path

import pandas as pd
import pytest

from retail_analytics import indicateurs, nettoyage, rayons, sumup

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


# --- Mois complets -----------------------------------------------------------

def periodes(*bornes):
    return pd.DataFrame({"debut": pd.to_datetime([d for d, _ in bornes]),
                         "fin": pd.to_datetime([f for _, f in bornes])})


def test_un_mois_entierement_exporte_est_complet():
    complets = indicateurs.mois_complets(periodes(("2026-01-01", "2026-01-31"), ("2026-01-31", "2026-02-14")))
    assert complets.to_dict() == {pd.Period("2026-01"): True, pd.Period("2026-02"): False}


def test_un_jour_absent_de_tous_les_exports_rend_le_mois_incomplet():
    complets = indicateurs.mois_complets(periodes(("2026-03-01", "2026-03-15"), ("2026-03-17", "2026-03-31")))
    assert not complets[MARS]


# --- Rayons, produits, articles offerts ---------------------------------------

@pytest.fixture
def ventes(propres):
    correspondances = rayons.lire_correspondances(FIXTURES.parent / "correspondances.csv")
    return rayons.rattacher_rayons(propres["ventes"], correspondances)


def test_ventes_par_rayon(ventes):
    mars = indicateurs.ventes_par_rayon(ventes).loc[MARS]
    assert mars.loc["Alcools"].to_dict() == {"ca_ht": 400, "quantite": 3}
    # Les chips ont été offertes : aucun CA, aucune quantité vendue.
    assert mars.loc["Épicerie salée"].to_dict() == {"ca_ht": 0, "quantite": 0}


def test_les_ventes_sans_rayon_ont_leur_ligne(ventes):
    mars = indicateurs.ventes_par_rayon(ventes).loc[MARS]
    sans_rayon = mars[mars.index.isna()]
    assert sans_rayon["ca_ht"].tolist() == [167]
    assert mars["ca_ht"].sum() == 899


def test_ventes_par_produit_du_plus_gros_ca_au_plus_petit(ventes):
    produits = indicateurs.ventes_par_produit(ventes, MARS)
    assert list(produits.index) == ["Bière blonde 33cl", "Baguette", "Produit mystère", "Cola 33cl",
                                    "Chips nature 150g"]
    assert produits.loc["Baguette"].to_dict() == {"rayon": "Boulangerie", "ca_ht": 209, "quantite": 2}


def test_articles_offerts(ventes):
    offerts = indicateurs.articles_offerts(ventes).loc[MARS]
    assert offerts.to_dict() == {"nombre_articles": 1, "valeur_ttc": 190}


# --- Classement ABC -------------------------------------------------------------

def test_classement_abc():
    par_produit = pd.DataFrame({"ca_ht": [5000, 3000, 1000, 600, 400]}, index=list("PQRST"))
    abc = indicateurs.classement_abc(par_produit)
    # P et Q font 80 % ; R commence pile à 80 %, donc en B ; T commence à 96 %, donc en C.
    assert "".join(abc["classe"]) == "AABBC"
    assert abc["part_cumulee"].iloc[-1] == 1


def test_le_premier_produit_est_toujours_en_a():
    par_produit = pd.DataFrame({"ca_ht": [9500, 500]}, index=["P", "Q"])
    assert list(indicateurs.classement_abc(par_produit)["classe"]) == ["A", "C"]


def test_classement_abc_sans_chiffre_d_affaires():
    par_produit = pd.DataFrame({"ca_ht": [0]}, index=["Chips nature 150g"])
    assert list(indicateurs.classement_abc(par_produit)["classe"]) == ["C"]


# --- Comparaison au mois précédent ----------------------------------------------

def test_comparer_au_mois_precedent():
    par_rayon = pd.DataFrame({
        "mois": [pd.Period("2026-02"), MARS, pd.Period("2026-02"), MARS],
        "rayon": ["Boissons", "Boissons", "Crémerie", "Alcools"],
        "ca_ht": [1000, 1100, 500, 300],
    }).set_index(["mois", "rayon"])
    comparaison = indicateurs.comparer_au_mois_precedent(par_rayon, MARS)
    assert comparaison.loc["Boissons", "evolution"] == pytest.approx(0.10)
    # Crémerie n'a rien vendu en mars : baisse de 100 %. Alcools n'avait rien vendu en février :
    # pas d'évolution calculée à partir de rien.
    assert comparaison.loc["Crémerie", "evolution"] == pytest.approx(-1)
    assert pd.isna(comparaison.loc["Alcools", "evolution"])


def test_comparer_sans_mois_precedent():
    par_rayon = pd.DataFrame({"mois": [MARS], "rayon": ["Boissons"], "ca_ht": [1100]}).set_index(["mois", "rayon"])
    comparaison = indicateurs.comparer_au_mois_precedent(par_rayon, MARS)
    assert comparaison.loc["Boissons", "precedent"] == 0
    assert pd.isna(comparaison.loc["Boissons", "evolution"])


def tickets_sur_deux_lundis():
    # Mars 2026 : les lundis 2 et 9, et le samedi 7. Le lundi 9, un ticket offert et un ticket livré.
    tickets = pd.DataFrame({"id_ticket": ["L1", "L2", "L3", "L4", "S1"],
                            "date_heure": pd.to_datetime(["2026-03-02 10:15", "2026-03-09 10:40",
                                                          "2026-03-09 11:05", "2026-03-09 18:00",
                                                          "2026-03-08 00:30"]),
                            "journee_commerciale": pd.to_datetime(["2026-03-02", "2026-03-09", "2026-03-09",
                                                                   "2026-03-09", "2026-03-07"]),
                            "montant_ttc": [300, 500, 0, 1000, 800],
                            "montant_ht": [250, 450, 0, 900, 700]})
    paiements = pd.DataFrame({"id_ticket": ["L1", "L2", "L4", "S1"],
                              "moyen_paiement": ["carte", "especes", "plateforme", "carte"],
                              "montant_ttc": [300, 500, 1000, 800]})
    journees = pd.DataFrame({"ouverture": pd.to_datetime(["2026-03-02 08:00", "2026-03-07 08:00",
                                                          "2026-03-09 08:00", "2026-03-10 08:00"])})
    return tickets, paiements, journees


def test_un_ticket_apres_minuit_se_range_apres_23_h(propres):
    # T4, clos le 3 mars à 0 h 10 dans la journée du 2 mars.
    heures = indicateurs.heure_de_journee(propres["tickets"])
    assert list(heures) == [10, 18, 21, 24]


def test_jours_ouverts_compte_une_journee_sans_vente():
    _, _, journees = tickets_sur_deux_lundis()
    # Le mardi 10 n'a aucun ticket, mais la caisse a été ouverte.
    assert len(indicateurs.jours_ouverts(journees, MARS)) == 4


def test_rythme_par_jour_ramene_a_un_jour_ouvert():
    rythme = indicateurs.rythme_par_jour(*tickets_sur_deux_lundis(), MARS)
    assert list(rythme.index) == list(range(7))
    lundi = rythme.loc[0]
    assert lundi["jours_ouverts"] == 2
    assert lundi["ca_ht"] == 1600
    assert lundi["ca_ht_par_jour"] == 800
    # Le ticket offert ne compte pas : trois tickets payants sur deux lundis.
    assert lundi["tickets_par_jour"] == 1.5
    # Le ticket livré ne compte pas dans le panier du magasin : (300 + 500) / 2.
    assert lundi["panier_moyen_magasin"] == 400


def test_la_vente_de_0_h_30_compte_pour_le_samedi():
    rythme = indicateurs.rythme_par_jour(*tickets_sur_deux_lundis(), MARS)
    assert rythme.loc[5, "ca_ht"] == 700
    assert rythme.loc[6, "ca_ht"] == 0


def test_un_jour_jamais_ouvert_a_des_moyennes_vides():
    rythme = indicateurs.rythme_par_jour(*tickets_sur_deux_lundis(), MARS)
    dimanche = rythme.loc[6]
    assert dimanche["jours_ouverts"] == 0
    assert pd.isna(dimanche["ca_ht_par_jour"])
    assert pd.isna(dimanche["panier_moyen_magasin"])


def test_rythme_par_heure():
    rythme = indicateurs.rythme_par_heure(*tickets_sur_deux_lundis(), MARS)
    # De 10 h à 24 h (0 h 30 du dimanche), sans trou.
    assert list(rythme.index) == list(range(10, 25))
    # 10 h : deux tickets, 700 € HT au total, sur quatre jours ouverts.
    assert rythme.loc[10, "ca_ht"] == 700
    assert rythme.loc[10, "ca_ht_par_jour"] == 175
    assert rythme.loc[12, "ca_ht"] == 0
    assert rythme.loc[24, "ca_ht"] == 700


def test_les_rythmes_retrouvent_le_chiffre_d_affaires_du_mois():
    tickets, paiements, journees = tickets_sur_deux_lundis()
    ca = indicateurs.chiffre_affaires(tickets).loc[MARS, "ca_ht"]
    assert indicateurs.rythme_par_jour(tickets, paiements, journees, MARS)["ca_ht"].sum() == ca
    assert indicateurs.rythme_par_heure(tickets, paiements, journees, MARS)["ca_ht"].sum() == ca


def test_rythme_d_un_mois_sans_vente():
    tickets, paiements, journees = tickets_sur_deux_lundis()
    avril = pd.Period("2026-04")
    assert indicateurs.rythme_par_jour(tickets, paiements, journees, avril)["ca_ht"].sum() == 0
    assert indicateurs.rythme_par_heure(tickets, paiements, journees, avril).empty
