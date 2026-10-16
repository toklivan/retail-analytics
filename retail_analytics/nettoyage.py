"""Nettoyage des tables lues par un adaptateur.

Trois opérations, chacune dans sa fonction :
- retirer les doublons laissés par des exports qui se chevauchent ;
- rattacher chaque ticket à sa journée de caisse (la journée dépasse minuit) ;
- repérer les articles offerts.

Rien n'est deviné : un ticket clos hors de toute journée connue garde une
journée vide, et il est signalé.
"""

import pandas as pd

COLONNES_VENTES = ["id_ticket", "numero_ticket", "date_heure", "journee_commerciale", "libelle",
                   "quantite", "prix_unitaire_ttc", "montant_ttc", "montant_ht", "offert"]


def dedoublonner(table, cle):
    """Garde, pour chaque valeur de `cle`, les lignes du premier export où elle apparaît.

    On ne supprime pas simplement les lignes identiques : deux paiements de
    2,00 € par carte sur un même ticket sont deux vrais paiements.
    """
    # transform("min") calcule le plus petit export de chaque groupe et le recopie
    # sur toutes les lignes du groupe, ce qui permet de comparer ligne à ligne.
    premier_export = table.groupby(cle)["export"].transform("min")
    return table[table["export"] == premier_export].drop(columns="export").reset_index(drop=True)


def rattacher_journees(tickets, journees):
    """Ajoute à chaque ticket `id_journee` et `journee_commerciale` (date d'ouverture de la caisse)."""
    caisses = journees[["id_journee", "ouverture", "fermeture"]].sort_values("ouverture")
    # merge_asof associe à chaque ticket la dernière caisse ouverte avant sa clôture.
    # Les deux tables doivent être triées sur la colonne de rapprochement.
    rattaches = pd.merge_asof(tickets.sort_values("date_heure"), caisses,
                              left_on="date_heure", right_on="ouverture")
    # Si cette caisse était déjà fermée, ou s'il n'y en a pas, le ticket reste sans journée.
    hors_journee = ~(rattaches["date_heure"] <= rattaches["fermeture"])
    rattaches["id_journee"] = rattaches["id_journee"].mask(hors_journee)
    # normalize() ramène une date et heure à minuit : il ne reste que le jour.
    rattaches["journee_commerciale"] = rattaches["ouverture"].dt.normalize().mask(hors_journee)
    return rattaches.drop(columns=["ouverture", "fermeture"])


def tickets_sans_journee(tickets):
    """Les tickets qu'aucune journée de caisse connue ne couvre."""
    return tickets[tickets["id_journee"].isna()]


def marquer_offerts(ventes):
    """Un article offert a un prix catalogue mais un montant encaissé nul."""
    ventes = ventes.copy()
    ventes["offert"] = (ventes["montant_ttc"] == 0) & (ventes["prix_unitaire_ttc"] > 0)
    return ventes


def nettoyer(export):
    """Applique tout le nettoyage aux tables d'un adaptateur ; les périodes passent telles quelles."""
    journees = dedoublonner(export["journees"], "id_journee")
    tickets = rattacher_journees(dedoublonner(export["tickets"], "id_ticket"), journees)
    paiements = dedoublonner(export["paiements"], "id_ticket")
    ventes = marquer_offerts(dedoublonner(export["ventes"], "id_ticket"))
    infos_ticket = tickets[["id_ticket", "numero_ticket", "journee_commerciale"]]
    ventes = ventes.merge(infos_ticket, on="id_ticket", how="left")[COLONNES_VENTES]
    return {"ventes": ventes, "tickets": tickets, "paiements": paiements, "journees": journees,
            "periodes": export["periodes"]}
