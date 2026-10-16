"""Mise en forme des nombres pour un lecteur humain, aux conventions françaises."""

import pandas as pd


def nombre(entier):
    """28578 -> '28 578'."""
    # Le format ',' sépare les milliers par une virgule ; on la remplace par une espace.
    return f"{entier:,}".replace(",", " ")


def euros(centimes):
    """1234560 -> '12 345,60 €'."""
    signe = "-" if centimes < 0 else ""
    return f"{signe}{nombre(abs(centimes) // 100)},{abs(centimes) % 100:02d} €"


def pourcentage(part):
    """0.0328 -> '3,3 %'."""
    return f"{part * 100:.1f} %".replace(".", ",")


def date_fr(moment):
    """Date au format JJ/MM/AAAA."""
    return moment.strftime("%d/%m/%Y")


def mois_fr(mois):
    """Mois au format MM/AAAA ; un mois vide (ticket sans journée connue) est nommé comme tel."""
    # pd.isna reconnaît toutes les formes de valeur manquante, dont celle d'un mois vide.
    if pd.isna(mois):
        return "sans journée"
    return mois.strftime("%m/%Y")
