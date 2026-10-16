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
