"""Codes-barres EAN : clé de contrôle et validation.

Un EAN-13 (ou EAN-8 sur les petits articles) se termine par une clé calculée
à partir des autres chiffres. Une erreur de lecture ou de saisie change
presque toujours la clé : c'est ce qui permet de la repérer.
"""

import re


def cle_ean(chiffres):
    """Clé de contrôle des chiffres d'un EAN, sans la clé : '200000000001' -> '5'.

    En partant de la droite, les chiffres sont pondérés 3, 1, 3, 1…
    La clé est ce qu'il faut ajouter à la somme pour atteindre la dizaine suivante.
    """
    # reversed parcourt la chaîne de droite à gauche ; enumerate numérote chaque chiffre.
    somme = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(chiffres)))
    return str((10 - somme % 10) % 10)


def code_barres_valide(code):
    """Vrai pour un EAN-13 ou un EAN-8 dont la clé de contrôle est juste."""
    # fullmatch exige que toute la chaîne corresponde : 8 ou 13 chiffres, rien d'autre.
    if not isinstance(code, str) or not re.fullmatch(r"\d{8}|\d{13}", code):
        return False
    return cle_ean(code[:-1]) == code[-1]
