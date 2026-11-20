"""Saisie d'un inventaire à la scanette, dans le terminal.

Une scanette USB ou Bluetooth se comporte comme un clavier : elle tape le code-barres
puis Entrée. Chaque ligne est écrite dans le fichier dès sa saisie : un comptage
interrompu n'est pas perdu, et relancer la saisie le même jour le complète.
"""

from retail_analytics.codes_barres import code_barres_valide

# Au-delà, c'est presque toujours un code-barres scanné à la place de la quantité.
QUANTITE_MAXIMUM = 999


def lire_quantite(texte):
    """Quantité saisie : vide -> 1, '12' -> 12 ; None si ce n'est pas un entier de 0 à 999."""
    texte = texte.strip()
    if texte == "":
        return 1
    if not texte.isdigit() or int(texte) > QUANTITE_MAXIMUM:
        return None
    return int(texte)


def ajouter_ligne(chemin, code, quantite):
    """Ajoute une ligne au fichier d'inventaire, en écrivant l'en-tête s'il est nouveau."""
    nouveau = not chemin.exists()
    # Le mode "a" (append) écrit à la fin du fichier sans effacer ce qu'il contient.
    with chemin.open("a", encoding="utf-8") as fichier:
        if nouveau:
            fichier.write("code_barres;quantite\n")
        fichier.write(f"{code};{quantite}\n")


def compter(chemin, libelles, lire=input, ecrire=print):
    """Boucle de saisie : un code-barres, puis sa quantité ; une ligne vide termine.

    `libelles` relie chaque code-barres connu à son libellé. `lire` et `ecrire` sont
    input et print, remplacés dans les tests par une liste de saisies préparées.
    Rend le nombre de lignes enregistrées.
    """
    enregistrees = 0
    while True:
        code = lire("Code-barres (Entrée seule pour finir) : ").strip()
        if code == "":
            return enregistrees
        if not code_barres_valide(code):
            ecrire("  Code-barres illisible, scannez à nouveau.")
            continue
        ecrire(f"  {libelles.get(code, 'Inconnu du référentiel : à y ajouter après le comptage')}")
        quantite = lire_quantite(lire("  Quantité (Entrée seule pour 1) : "))
        while quantite is None:
            ecrire(f"  Quantité illisible : un nombre entier de 0 à {QUANTITE_MAXIMUM}.")
            quantite = lire_quantite(lire("  Quantité (Entrée seule pour 1) : "))
        ajouter_ligne(chemin, code, quantite)
        enregistrees += 1
