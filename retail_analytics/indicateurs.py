"""Indicateurs de vente, par mois de journée commerciale (docs/donnees.md, section 10).

Chaque fonction prend des tables nettoyées et rend un tableau d'une ligne par
mois. Les montants restent en centimes : la mise en forme est faite à l'affichage.

Un ticket sans journée connue, déjà signalé par les contrôles, n'est pas écarté
en silence : il est compté dans une ligne au mois vide.
"""

import pandas as pd

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


def canal_des_tickets(tickets, paiements):
    """Ajoute la colonne `canal` : « livraison » si le ticket est payé, même en partie, par la plateforme.

    Tous les autres tickets sont « magasin », y compris ceux payés par un moyen
    inconnu : ce moyen est signalé à part par `moyens_inconnus`.
    """
    livres = paiements.loc[paiements["moyen_paiement"] == "plateforme", "id_ticket"]
    # map remplace chaque valeur par celle que lui associe le dictionnaire.
    return tickets.assign(canal=tickets["id_ticket"].isin(livres).map({True: "livraison", False: "magasin"}))


def panier_moyen(tickets, paiements):
    """Nombre de tickets payants, CA TTC et panier moyen TTC, par mois et par canal.

    Les tickets offerts (à 0 €) n'entrent pas dans le calcul. Un canal sans
    ticket dans un mois n'a pas de ligne : son panier moyen n'existe pas.
    """
    payants = canal_des_tickets(tickets[tickets["montant_ttc"] > 0], paiements)
    payants = payants.assign(mois=mois_commercial(payants["journee_commerciale"]))
    resume = payants.groupby(["mois", "canal"], dropna=False).agg(nombre_tickets=("id_ticket", "count"),
                                                                  ca_ttc=("montant_ttc", "sum"))
    # round arrondit au centime le plus proche ; pile au milieu (100,5), il va au nombre pair (100).
    resume["panier_moyen"] = (resume["ca_ttc"] / resume["nombre_tickets"]).round().astype("int64")
    return resume


def mois_complets(periodes):
    """Pour chaque mois touché par un export : vrai si chacun de ses jours est couvert.

    Un jour de fermeture ou de panne reste couvert : l'export l'inclut, il est
    simplement vide. Seul un jour qu'aucun export ne contient rend le mois incomplet.
    """
    # date_range liste tous les jours entre deux dates, bornes comprises.
    jours = pd.concat([pd.Series(pd.date_range(debut, fin)) for debut, fin in zip(periodes["debut"], periodes["fin"])])
    jours = jours.drop_duplicates()
    couverts = jours.groupby(mois_commercial(jours)).count()
    return couverts == couverts.index.days_in_month


def ventes_par_rayon(ventes):
    """CA HT et quantités vendues par mois et par rayon ; les ventes sans rayon ont leur ligne.

    Les articles offerts n'entrent pas dans les quantités vendues (voir `articles_offerts`).
    """
    ventes = ventes.assign(mois=mois_commercial(ventes["journee_commerciale"]),
                           quantite_vendue=ventes["quantite"].where(~ventes["offert"], 0))
    return ventes.groupby(["mois", "rayon"], dropna=False).agg(ca_ht=("montant_ht", "sum"),
                                                               quantite=("quantite_vendue", "sum"))


def ventes_par_produit(ventes, mois):
    """CA HT, quantités vendues et rayon de chaque produit vendu dans le mois, du plus gros CA au plus petit."""
    du_mois = ventes[mois_commercial(ventes["journee_commerciale"]) == mois]
    du_mois = du_mois.assign(quantite_vendue=du_mois["quantite"].where(~du_mois["offert"], 0))
    resume = du_mois.groupby("libelle").agg(rayon=("rayon", "first"), ca_ht=("montant_ht", "sum"),
                                            quantite=("quantite_vendue", "sum"))
    # À CA égal, l'ordre alphabétique départage, pour un classement identique à chaque lancement.
    return resume.sort_index().sort_values("ca_ht", ascending=False, kind="stable")


def classement_abc(par_produit):
    """Ajoute la part du CA, la part cumulée et la classe A, B ou C de chaque produit.

    `par_produit` est trié du plus gros CA au plus petit. Un produit est en A tant
    que les produits mieux classés font moins de 80 % du CA, en B moins de 95 %,
    en C au-delà (docs/donnees.md, section 10).
    """
    total = par_produit["ca_ht"].sum()
    if total <= 0:
        # Sans chiffre d'affaires, il n'y a rien à classer.
        return par_produit.assign(part=0.0, part_cumulee=0.0, classe="C")
    # cumsum fait la somme cumulée : chaque ligne reçoit le total des lignes jusqu'à elle.
    cumul = par_produit["ca_ht"].cumsum()
    avant = cumul - par_produit["ca_ht"]
    # « avant / total < 80 % » s'écrit en entiers « avant × 100 < 80 × total » :
    # pas d'erreur d'arrondi pour un produit pile à la frontière.
    classe = pd.Series("C", index=par_produit.index)
    classe[avant * 100 < 95 * total] = "B"
    classe[avant * 100 < 80 * total] = "A"
    return par_produit.assign(part=par_produit["ca_ht"] / total, part_cumulee=cumul / total, classe=classe)


def articles_offerts(ventes):
    """Nombre d'articles offerts et leur valeur au prix de vente TTC, par mois."""
    offerts = ventes[ventes["offert"]]
    offerts = offerts.assign(mois=mois_commercial(offerts["journee_commerciale"]),
                             valeur_ttc=offerts["prix_unitaire_ttc"] * offerts["quantite"])
    return offerts.groupby("mois", dropna=False).agg(nombre_articles=("quantite", "sum"),
                                                     valeur_ttc=("valeur_ttc", "sum"))


def comparer_au_mois_precedent(par_mois_et_rayon, mois):
    """CA HT de chaque rayon pour le mois et le mois précédent, et son évolution.

    L'évolution est vide quand le mois précédent n'a pas de vente dans le rayon :
    on ne calcule pas une hausse à partir de rien.
    """
    # unstack fait passer les mois en colonnes ; reindex garde les deux mois voulus, à 0 s'ils manquent.
    ca = par_mois_et_rayon["ca_ht"].unstack("mois", fill_value=0).reindex(columns=[mois - 1, mois], fill_value=0)
    ca.columns = ["precedent", "actuel"]
    ca = ca[(ca["precedent"] != 0) | (ca["actuel"] != 0)]
    evolution = (ca["actuel"] - ca["precedent"]) / ca["precedent"].where(ca["precedent"] != 0)
    return ca.assign(evolution=evolution).sort_values("actuel", ascending=False)


def jours_ouverts(journees, mois):
    """Dates des journées commerciales du mois où la caisse a été ouverte, chacune une fois.

    Une journée ouverte sans aucune vente compte : le magasin était ouvert.
    """
    jours = journees["ouverture"].dt.normalize()
    return jours[mois_commercial(jours) == mois].drop_duplicates()


def heure_de_journee(tickets):
    """Heure de chaque ticket, comptée depuis le minuit qui commence sa journée commerciale.

    Un ticket de 0 h 10 le lendemain donne 24 : il se range après 23 h, pas avant l'ouverture.
    """
    # Diviser un écart de temps par une heure donne un nombre d'heures ; // garde la partie entière.
    return (tickets["date_heure"] - tickets["journee_commerciale"]) // pd.Timedelta(hours=1)


def tickets_du_mois(tickets, paiements, mois):
    """Tickets du mois avec leur canal, leur jour de la semaine (0 = lundi) et leur heure de journée."""
    du_mois = canal_des_tickets(tickets[mois_commercial(tickets["journee_commerciale"]) == mois], paiements)
    # dayofweek donne le jour de la semaine : 0 pour lundi, 6 pour dimanche.
    return du_mois.assign(jour=du_mois["journee_commerciale"].dt.dayofweek, heure=heure_de_journee(du_mois))


def resumer_rythme(du_mois, par):
    """CA HT, tickets payants, et de quoi calculer le panier moyen du magasin, par jour ou par heure."""
    payants = du_mois[du_mois["montant_ttc"] > 0]
    magasin = payants[payants["canal"] == "magasin"]
    # Les quatre séries sont alignées sur leur index ; un jour absent de l'une reçoit 0.
    resume = pd.DataFrame({"ca_ht": du_mois.groupby(par)["montant_ht"].sum(),
                           "tickets_payants": payants.groupby(par)["id_ticket"].count(),
                           "ca_ttc_magasin": magasin.groupby(par)["montant_ttc"].sum(),
                           "tickets_magasin": magasin.groupby(par)["id_ticket"].count()})
    return resume.fillna(0).astype("int64")


def ajouter_moyennes(resume, nombre_jours):
    """Ajoute le CA HT et les tickets moyens par jour ouvert, et le panier moyen TTC du magasin.

    Sans jour ouvert ou sans ticket, la moyenne reste vide : on ne divise pas par zéro.
    "Int64" (avec une majuscule) est un entier qui accepte une valeur vide.
    """
    ca_par_jour = (resume["ca_ht"] / nombre_jours).round().astype("Int64")
    panier = (resume["ca_ttc_magasin"] / resume["tickets_magasin"]).round().astype("Int64")
    return resume.assign(jours_ouverts=nombre_jours, ca_ht_par_jour=ca_par_jour,
                         tickets_par_jour=resume["tickets_payants"] / nombre_jours,
                         panier_moyen_magasin=panier)


def ouvertures_par_jour(journees, mois):
    """Nombre de journées ouvertes dans le mois pour chaque jour de la semaine, de lundi (0) à dimanche (6)."""
    # value_counts compte les occurrences de chaque valeur : ici, le nombre de lundis ouverts, etc.
    return jours_ouverts(journees, mois).dt.dayofweek.value_counts().reindex(range(7), fill_value=0)


def rythme_par_jour(tickets, paiements, journees, mois):
    """Ventes d'un mois par jour de la semaine, de lundi (0) à dimanche (6), ramenées à un jour ouvert.

    Un mois peut compter cinq samedis et quatre lundis : les totaux ne se comparent
    pas, les moyennes par jour ouvert si. Un jour de la semaine jamais ouvert garde
    sa ligne, avec des moyennes vides.
    """
    resume = resumer_rythme(tickets_du_mois(tickets, paiements, mois), "jour").reindex(range(7), fill_value=0)
    return ajouter_moyennes(resume, ouvertures_par_jour(journees, mois))


def rythme_par_heure(tickets, paiements, journees, mois):
    """Ventes d'un mois par heure de journée, ramenées à un jour ouvert.

    Les heures après minuit valent 24, 25… (voir `heure_de_journee`). Les heures
    sans vente entre la première et la dernière ont leur ligne, à 0.
    """
    resume = resumer_rythme(tickets_du_mois(tickets, paiements, mois), "heure")
    if resume.empty:
        return ajouter_moyennes(resume, 0)
    resume = resume.reindex(range(resume.index.min(), resume.index.max() + 1), fill_value=0)
    return ajouter_moyennes(resume, len(jours_ouverts(journees, mois)))


def ca_jour_heure(tickets, paiements, journees, mois):
    """CA HT moyen par jour ouvert, en centimes : une ligne par jour de la semaine, une colonne par heure.

    Chaque ligne est divisée par le nombre de journées ouvertes de ce jour-là :
    la case « lundi 18 h » est ce que rapporte en moyenne un lundi entre 18 h et 19 h.
    Un jour jamais ouvert a une ligne vide, différente d'une ligne à 0 €.
    """
    du_mois = tickets_du_mois(tickets, paiements, mois)
    if du_mois.empty:
        return pd.DataFrame()
    # unstack fait passer les heures en colonnes ; une case sans vente reçoit 0.
    ca = du_mois.groupby(["jour", "heure"])["montant_ht"].sum().unstack(fill_value=0)
    heures = range(ca.columns.min(), ca.columns.max() + 1)
    ca = ca.reindex(index=range(7), columns=heures, fill_value=0)
    # div(..., axis=0) divise chaque ligne par la valeur qui lui correspond : le nombre de lundis, etc.
    # Pour un jour jamais ouvert, 0 / 0 donne une case vide.
    return ca.div(ouvertures_par_jour(journees, mois), axis=0).round()
