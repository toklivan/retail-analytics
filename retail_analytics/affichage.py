"""Mise en forme des nombres pour un lecteur humain, aux conventions françaises."""


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
