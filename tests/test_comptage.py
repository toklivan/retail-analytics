from retail_analytics import comptage, inventaire

COLA = "2000000000046"


def saisir(chemin, saisies, libelles={COLA: "Cola 33cl"}):
    """Lance la saisie avec des réponses préparées ; rend le nombre de lignes et les messages affichés."""
    reponses = iter(saisies)
    messages = []
    # next(reponses) donne la saisie suivante à chaque question posée, comme si on la tapait.
    enregistrees = comptage.compter(chemin, libelles, lire=lambda question: next(reponses), ecrire=messages.append)
    return enregistrees, messages


def test_lit_la_quantite():
    assert comptage.lire_quantite("") == 1
    assert comptage.lire_quantite(" 12 ") == 12
    assert comptage.lire_quantite("0") == 0
    for texte in ["-2", "1,5", "1O", "1000", COLA]:
        assert comptage.lire_quantite(texte) is None, texte


def test_enregistre_chaque_scan_dans_un_fichier_lisible(tmp_path):
    chemin = tmp_path / "inventaire-2026-11-20.csv"
    enregistrees, messages = saisir(chemin, [COLA, "12", COLA, "", ""])
    assert enregistrees == 2
    assert "  Cola 33cl" in messages
    stock = inventaire.stock_compte(inventaire.lire_inventaire(chemin))
    assert stock["quantite_comptee"].tolist() == [13]


def test_n_enregistre_pas_un_code_mal_lu(tmp_path):
    chemin = tmp_path / "inventaire-2026-11-20.csv"
    enregistrees, messages = saisir(chemin, ["2000000000047", ""])
    assert enregistrees == 0
    assert not chemin.exists()
    assert "scannez à nouveau" in messages[0]


def test_redemande_une_quantite_illisible(tmp_path):
    chemin = tmp_path / "inventaire-2026-11-20.csv"
    # Le code suivant scanné par erreur à la place de la quantité est refusé.
    enregistrees, messages = saisir(chemin, [COLA, "2000000000152", "3", ""])
    assert enregistrees == 1
    assert chemin.read_text(encoding="utf-8") == f"code_barres;quantite\n{COLA};3\n"


def test_enregistre_un_code_inconnu_en_le_signalant(tmp_path):
    chemin = tmp_path / "inventaire-2026-11-20.csv"
    enregistrees, messages = saisir(chemin, ["2000000009995", "2", ""])
    assert enregistrees == 1
    assert "Inconnu du référentiel" in messages[0]


def test_une_seconde_saisie_complete_le_meme_fichier(tmp_path):
    chemin = tmp_path / "inventaire-2026-11-20.csv"
    saisir(chemin, [COLA, "5", ""])
    saisir(chemin, [COLA, "4", ""])
    assert chemin.read_text(encoding="utf-8") == f"code_barres;quantite\n{COLA};5\n{COLA};4\n"
