from retail_analytics.catalogue import code_barres_fictif
from retail_analytics.codes_barres import cle_ean, code_barres_valide


def test_cle_d_un_ean_13_connu():
    # Exemple classique d'EAN-13, pris hors du projet pour ne pas se vérifier soi-même.
    assert cle_ean("400638133393") == "1"
    assert code_barres_valide("4006381333931")


def test_cle_d_un_ean_8():
    assert code_barres_valide("96385074")


def test_refuse_une_cle_fausse():
    assert not code_barres_valide("4006381333932")


def test_refuse_deux_chiffres_inverses():
    # L'erreur de saisie la plus courante : la clé la repère.
    assert not code_barres_valide("4006381339331")


def test_refuse_ce_qui_n_est_pas_un_ean():
    for code in ["", "123", "400638133393", "40063813339311", "400638133393A", None, 4006381333931]:
        assert not code_barres_valide(code), code


def test_les_codes_fictifs_sont_valides_et_commencent_par_20():
    for numero in [1, 42, 131]:
        code = code_barres_fictif(numero)
        assert code.startswith("20") and code_barres_valide(code)
