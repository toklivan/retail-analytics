"""Indicateurs de vente, par mois de journée commerciale (docs/donnees.md, section 10).

Chaque fonction prend des tables nettoyées et rend un tableau d'une ligne par
mois. Les montants restent en centimes : la mise en forme est faite à l'affichage.

Un ticket sans journée connue, déjà signalé par les contrôles, n'est pas écarté
en silence : il est compté dans une ligne au mois vide.
"""

# Moyens de paiement du format interne, dans l'ordre d'affichage.
MOYENS_CONNUS = ["especes", "carte", "plateforme"]


def mois_commercial(journees_commerciales):
    """Mois de chaque journée commerciale : 2026-03-31 -> 2026-03. Une journée vide reste vide."""
    # to_period("M") ramène une date à son mois.
    return journees_commerciales.dt.to_period("M")


def chiffre_affaires(tickets):
    """CA TTC, CA HT, nombre de tickets payants et de tickets offerts (à 0 €), par mois."""
    tickets = tickets.assign(mois=mois_commercial(tickets["journee_commerciale"]),
                             payant=tickets["montant_ttc"] > 0,
                             offert=tickets["montant_ttc"] == 0)
    # dropna=False garde la ligne des tickets sans mois au lieu de la supprimer.
    # La somme d'une colonne de vrai/faux compte les « vrai ».
    return tickets.groupby("mois", dropna=False).agg(ca_ttc=("montant_ttc", "sum"),
                                                     ca_ht=("montant_ht", "sum"),
                                                     tickets_payants=("payant", "sum"),
                                                     tickets_offerts=("offert", "sum"))


def ventes_par_moyen(paiements, tickets):
    """Montant TTC encaissé par moyen de paiement : une ligne par mois, une colonne par moyen.

    Un ticket payé en partie en carte, en partie en espèces compte dans les deux
    colonnes, pour le montant payé de chaque façon. Les moyens connus viennent en
    premier, même s'ils n'ont pas servi ; un moyen inconnu a sa propre colonne.
    """
    rattaches = paiements.merge(tickets[["id_ticket", "journee_commerciale"]], on="id_ticket", how="left")
    rattaches["mois"] = mois_commercial(rattaches["journee_commerciale"])
    sommes = rattaches.groupby(["mois", "moyen_paiement"], dropna=False)["montant_ttc"].sum()
    # unstack fait passer les moyens de paiement des lignes aux colonnes.
    tableau = sommes.unstack(fill_value=0)
    inconnus = [moyen for moyen in tableau.columns if moyen not in MOYENS_CONNUS]
    # reindex impose la liste et l'ordre des colonnes ; une colonne absente est créée à 0.
    return tableau.reindex(columns=MOYENS_CONNUS + inconnus, fill_value=0)


def moyens_inconnus(paiements):
    """Moyens de paiement que l'adaptateur n'a pas su traduire, avec leur nombre et leur montant."""
    # isin teste l'appartenance à une liste ; ~ inverse le test.
    inconnus = paiements[~paiements["moyen_paiement"].isin(MOYENS_CONNUS)]
    return inconnus.groupby("moyen_paiement").agg(nombre_paiements=("id_ticket", "count"),
                                                  montant_ttc=("montant_ttc", "sum"))
