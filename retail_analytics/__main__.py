"""Point d'entrée en ligne de commande : python -m retail_analytics <commande>."""

import argparse
from pathlib import Path

from retail_analytics import controles, generateur, nettoyage, rayons, sumup
from retail_analytics.affichage import date_fr, euros, nombre, pourcentage


def commande_generer(args):
    verite = generateur.generer(Path(args.sortie), Path(args.exemple))
    print(f"Jeu fictif écrit dans {args.sortie} : {verite['nombre_tickets']} tickets, "
          f"{verite['nombre_lignes']} lignes de vente.")


def preparer(dossier_export, chemin_correspondances):
    """Ventes propres et catégorisées, et résultats des contrôles, depuis les fichiers."""
    propres = nettoyage.nettoyer(sumup.lire_export(dossier_export))
    correspondances = rayons.lire_correspondances(chemin_correspondances)
    ventes = rayons.rattacher_rayons(propres["ventes"], correspondances)
    return ventes, controles.controler(propres)


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
    ventes, resultats = preparer(export, correspondances)
    ventes.to_csv(sortie, sep=";", index=False, encoding="utf-8")
    afficher_resume(ventes, resultats)
    print(f"Ventes propres écrites dans {sortie}")


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

    args = parseur.parse_args()
    args.fonction(args)


if __name__ == "__main__":
    main()
