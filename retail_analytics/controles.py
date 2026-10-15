"""Contrôles de cohérence entre les tables nettoyées (docs/donnees.md, section 4).

Chaque contrôle rend un tableau des écarts : vide si tout concorde au centime,
sinon une ligne par ticket ou par journée en défaut, avec le montant de
l'export et le montant recalculé côte à côte. Un contrôle ne corrige rien :
il signale, pour qu'on ne produise pas des chiffres faux sans le savoir.
"""

import pandas as pd


def comparer(attendu, calcule):
    """Lignes où le total de l'export (`attendu`) diffère du total recalculé (`calcule`).

    Les deux tables ont le même index (l'identifiant du ticket ou de la journée)
    et les mêmes colonnes. Une clé absente d'un côté compte pour zéro.
    """
    # align met les deux tables sur les mêmes lignes ; fill_value=0 remplit les trous.
    attendu, calcule = attendu.align(calcule, join="outer", fill_value=0)
    differe = (attendu != calcule).any(axis=1)
    return attendu[differe].join(calcule[differe], rsuffix="_calcule")


def ecarts_lignes_tickets(ventes, tickets):
    """La somme des lignes d'un ticket est égale au total du ticket, en TTC et en HT."""
    colonnes = ["montant_ttc", "montant_ht"]
    sommes = ventes.groupby("id_ticket")[colonnes].sum()
    return comparer(tickets.set_index("id_ticket")[colonnes], sommes)


def ecarts_paiements_tickets(paiements, tickets):
    """La somme des paiements d'un ticket est égale à son total TTC (zéro pour un ticket offert)."""
    sommes = paiements.groupby("id_ticket")[["montant_ttc"]].sum()
    return comparer(tickets.set_index("id_ticket")[["montant_ttc"]], sommes)


def ecarts_journees(tickets, journees):
    """Nombre de tickets, CA TTC et CA HT d'une journée sont égaux à ceux de ses tickets."""
    # agg calcule plusieurs résumés à la fois : nom de la colonne résultat = (colonne source, opération).
    sommes = tickets.groupby("id_journee").agg(nombre_tickets=("id_ticket", "count"),
                                               ca_ttc=("montant_ttc", "sum"),
                                               ca_ht=("montant_ht", "sum"))
    attendu = journees.set_index("id_journee")[["nombre_tickets", "ca_ttc", "ca_ht"]]
    return comparer(attendu, sommes)


def ecarts_remises(ventes, tickets, journees):
    """La valeur catalogue des articles offerts d'une journée est égale à ses remises."""
    offerts = ventes[ventes["offert"]].merge(tickets[["id_ticket", "id_journee"]], on="id_ticket")
    valeur = (offerts["prix_unitaire_ttc"] * offerts["quantite"]).groupby(offerts["id_journee"]).sum()
    calcule = pd.DataFrame({"remises_ttc": valeur})
    return comparer(journees.set_index("id_journee")[["remises_ttc"]], calcule)


def controler(propres):
    """Tous les contrôles sur les tables nettoyées : {nom du contrôle: tableau des écarts}."""
    ventes, tickets = propres["ventes"], propres["tickets"]
    return {
        "lignes des tickets": ecarts_lignes_tickets(ventes, tickets),
        "paiements des tickets": ecarts_paiements_tickets(propres["paiements"], tickets),
        "totaux des journées": ecarts_journees(tickets, propres["journees"]),
        "remises des journées": ecarts_remises(ventes, tickets, propres["journees"]),
        "tickets sans journée": tickets[tickets["id_journee"].isna()].set_index("id_ticket"),
    }
