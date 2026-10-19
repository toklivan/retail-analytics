"""Point d'entrée en ligne de commande : python -m retail_analytics <commande>."""

import argparse
from pathlib import Path

import pandas as pd

from retail_analytics import controles, generateur, indicateurs, nettoyage, rayons, sumup
from retail_analytics.affichage import NOMS_MOYENS, date_fr, euros, evolution_fr, mois_fr, nombre, pourcentage


def commande_generer(args):
    verite = generateur.generer(Path(args.sortie), Path(args.exemple))
    print(f"Jeu fictif écrit dans {args.sortie} : {verite['nombre_tickets']} tickets, "
          f"{verite['nombre_lignes']} lignes de vente.")


def preparer(dossier_export, chemin_correspondances):
    """Tables nettoyées, ventes catégorisées, et résultats des contrôles, depuis les fichiers."""
    propres = nettoyage.nettoyer(sumup.lire_export(dossier_export))
    correspondances = rayons.lire_correspondances(chemin_correspondances)
    resultats = controles.controler(propres)
    propres["ventes"] = rayons.rattacher_rayons(propres["ventes"], correspondances)
    return propres, resultats


def afficher_resume(ventes, resultats):
    debut, fin = ventes["journee_commerciale"].min(), ventes["journee_commerciale"].max()
    print(f"Du {date_fr(debut)} au {date_fr(fin)} : {nombre(ventes['id_ticket'].nunique())} tickets, "
          f"{nombre(len(ventes))} lignes, CA {euros(ventes['montant_ht'].sum())} HT.")

    inconnus = rayons.libelles_inconnus(ventes)
    print(f"Part du CA non rattachée à un rayon : {pourcentage(rayons.part_ca_non_rattachee(ventes))}")
    for libelle, ligne in inconnus.iterrows():
        print(f"  libellé inconnu : {libelle} ({euros(ligne['ca_ht'])} HT)")

    print("Contrôles (écarts en centimes) :")
    for nom, ecarts in resultats.items():
        print(f"  {nom} : {'OK' if ecarts.empty else f'{len(ecarts)} écart(s)'}")
        if not ecarts.empty:
            print(ecarts.head().to_string())


def commande_nettoyer(args):
    export = Path(args.export)
    # Par défaut, les sorties vont à côté des exports : celles des données réelles
    # restent ainsi dans data/raw/, ignoré par Git.
    correspondances = Path(args.correspondances or export.parent / "correspondances.csv")
    sortie = Path(args.sortie or export.parent / "ventes_propres.csv")
    propres, resultats = preparer(export, correspondances)
    ventes = propres["ventes"]
    ventes.to_csv(sortie, sep=";", index=False, encoding="utf-8")
    afficher_resume(ventes, resultats)
    print(f"Ventes propres écrites dans {sortie}")


def afficher_chiffre_affaires(tickets, complets):
    print("Chiffre d'affaires par mois de journée commerciale :")
    print(f"  {'Mois':<13}{'CA TTC':>15}{'CA HT':>15}{'Tickets':>9}{'Offerts':>9}")
    for mois, ligne in indicateurs.chiffre_affaires(tickets).iterrows():
        mention = "" if complets.get(mois, False) else "  mois incomplet"
        print(f"  {mois_fr(mois):<13}{euros(ligne['ca_ttc']):>15}{euros(ligne['ca_ht']):>15}"
              f"{nombre(ligne['tickets_payants']):>9}{nombre(ligne['tickets_offerts']):>9}{mention}")


def afficher_moyens(paiements, tickets):
    moyens = indicateurs.ventes_par_moyen(paiements, tickets)
    print("Encaissements TTC par moyen de paiement :")
    entete = "".join(f"{NOMS_MOYENS.get(moyen, moyen):>23}" for moyen in moyens.columns)
    print(f"  {'Mois':<13}{entete}")
    for mois, ligne in moyens.iterrows():
        total = ligne.sum()
        cellules = "".join(f"{euros(montant) + ' (' + pourcentage(montant / total if total else 0) + ')':>23}"
                           for montant in ligne)
        print(f"  {mois_fr(mois):<13}{cellules}")
    for moyen, ligne in indicateurs.moyens_inconnus(paiements).iterrows():
        print(f"  moyen de paiement inconnu : {moyen} ({nombre(ligne['nombre_paiements'])} paiement(s), "
              f"{euros(ligne['montant_ttc'])})")


def afficher_paniers(tickets, paiements):
    paniers = indicateurs.panier_moyen(tickets, paiements)
    print("Panier moyen TTC par canal (nombre de tickets payants entre parenthèses) :")
    print(f"  {'Mois':<13}{'Magasin':>23}{'Livraison':>23}")
    # unstack fait passer les canaux en colonnes ; un canal absent du mois devient une valeur vide.
    for mois, ligne in paniers.unstack("canal").iterrows():
        cellules = ""
        for canal in ["magasin", "livraison"]:
            panier, nombre_tickets = ligne.get(("panier_moyen", canal)), ligne.get(("nombre_tickets", canal))
            texte = "-" if pd.isna(panier) else f"{euros(int(panier))} ({nombre(int(nombre_tickets))})"
            cellules += f"{texte:>23}"
        print(f"  {mois_fr(mois):<13}{cellules}")


def afficher_offerts(ventes):
    print("Articles offerts, valeur au prix de vente TTC :")
    for mois, ligne in indicateurs.articles_offerts(ventes).iterrows():
        print(f"  {mois_fr(mois):<13}{nombre(ligne['nombre_articles']):>6} article(s){euros(ligne['valeur_ttc']):>15}")


def afficher_comparaison(ventes, mois, complets):
    comparaison = indicateurs.comparer_au_mois_precedent(indicateurs.ventes_par_rayon(ventes), mois)
    print(f"CA HT par rayon, comparé à {mois_fr(mois - 1)} :")
    incomplets = [mois_fr(m) for m in [mois - 1, mois] if not complets.get(m, False)]
    if incomplets:
        print(f"  Attention, mois incomplet : {', '.join(incomplets)}. La comparaison n'est pas significative.")
    print(f"  {'Rayon':<22}{mois_fr(mois):>15}{mois_fr(mois - 1):>15}{'Évolution':>11}")
    # iterrows convertirait toute la ligne en décimaux (à cause de l'évolution) ;
    # itertuples garde le type de chaque colonne, ici des centimes entiers.
    for ligne in comparaison.itertuples():
        nom = "non rattaché" if pd.isna(ligne.Index) else ligne.Index
        print(f"  {nom:<22}{euros(ligne.actuel):>15}{euros(ligne.precedent):>15}{evolution_fr(ligne.evolution):>11}")
    total = comparaison[["actuel", "precedent"]].sum()
    evolution = (total["actuel"] - total["precedent"]) / total["precedent"] if total["precedent"] else float("nan")
    print(f"  {'Total':<22}{euros(total['actuel']):>15}{euros(total['precedent']):>15}{evolution_fr(evolution):>11}")


def afficher_abc(ventes, mois, nombre_affiches=10):
    abc = indicateurs.classement_abc(indicateurs.ventes_par_produit(ventes, mois))
    print(f"Classement ABC des produits, {mois_fr(mois)} :")
    for classe, groupe in abc.groupby("classe"):
        print(f"  {classe} : {nombre(len(groupe)):>4} produit(s), {pourcentage(groupe['part'].sum())} du CA HT")
    print(f"  Les {nombre_affiches} premiers :")
    for libelle, ligne in abc.head(nombre_affiches).iterrows():
        print(f"    {ligne['classe']}  {libelle:<32}{euros(ligne['ca_ht']):>13}{nombre(ligne['quantite']):>7} vendus")


def mois_a_detailler(choisi, complets, tickets):
    """Le mois demandé, sinon le dernier mois complet, sinon le dernier mois des ventes."""
    if choisi:
        return pd.Period(choisi, freq="M")
    if complets.any():
        return complets[complets].index.max()
    return indicateurs.mois_commercial(tickets["journee_commerciale"]).max()


def commande_indicateurs(args):
    export = Path(args.export)
    correspondances = Path(args.correspondances or export.parent / "correspondances.csv")
    propres, resultats = preparer(export, correspondances)
    en_ecart = [nom for nom, ecarts in resultats.items() if not ecarts.empty]
    if en_ecart:
        # Des écarts aux contrôles rendent les indicateurs douteux : on le dit avant de les afficher.
        print(f"Attention, contrôles en écart : {', '.join(en_ecart)}. Détail avec la commande nettoyer.")
    complets = indicateurs.mois_complets(propres["periodes"])
    afficher_chiffre_affaires(propres["tickets"], complets)
    afficher_moyens(propres["paiements"], propres["tickets"])
    afficher_paniers(propres["tickets"], propres["paiements"])
    afficher_offerts(propres["ventes"])
    mois = mois_a_detailler(args.mois, complets, propres["tickets"])
    print()
    afficher_comparaison(propres["ventes"], mois, complets)
    afficher_abc(propres["ventes"], mois)


def main():
    # argparse lit les arguments de la ligne de commande et génère l'aide (--help).
    parseur = argparse.ArgumentParser(prog="retail_analytics")
    commandes = parseur.add_subparsers(dest="commande", required=True)

    generer = commandes.add_parser("generer", help="génère le jeu de données fictif")
    generer.add_argument("--sortie", default="data/fictif")
    generer.add_argument("--exemple", default="data/exemple")
    generer.set_defaults(fonction=commande_generer)

    nettoyer = commandes.add_parser("nettoyer", help="produit le fichier des ventes propres et catégorisées")
    nettoyer.add_argument("--export", default="data/fictif/sumup", help="dossier des exports SumUp")
    nettoyer.add_argument("--correspondances", help="table libellé;rayon (par défaut, à côté des exports)")
    nettoyer.add_argument("--sortie", help="fichier produit (par défaut, à côté des exports)")
    nettoyer.set_defaults(fonction=commande_nettoyer)

    calculer = commandes.add_parser("indicateurs", help="affiche les indicateurs de vente par mois")
    calculer.add_argument("--export", default="data/fictif/sumup", help="dossier des exports SumUp")
    calculer.add_argument("--correspondances", help="table libellé;rayon (par défaut, à côté des exports)")
    calculer.add_argument("--mois", help="mois détaillé, au format AAAA-MM (par défaut, le dernier mois complet)")
    calculer.set_defaults(fonction=commande_indicateurs)

    args = parseur.parse_args()
    args.fonction(args)


if __name__ == "__main__":
    main()
