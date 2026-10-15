"""Point d'entrée en ligne de commande : python -m retail_analytics <commande>."""

import argparse
from pathlib import Path

from retail_analytics import generateur


def commande_generer(args):
    verite = generateur.generer(Path(args.sortie), Path(args.exemple))
    print(f"Jeu fictif écrit dans {args.sortie} : {verite['nombre_tickets']} tickets, "
          f"{verite['nombre_lignes']} lignes de vente.")


def main():
    # argparse lit les arguments de la ligne de commande et génère l'aide (--help).
    parseur = argparse.ArgumentParser(prog="retail_analytics")
    commandes = parseur.add_subparsers(dest="commande", required=True)

    generer = commandes.add_parser("generer", help="génère le jeu de données fictif")
    generer.add_argument("--sortie", default="data/fictif")
    generer.add_argument("--exemple", default="data/exemple")
    generer.set_defaults(fonction=commande_generer)

    args = parseur.parse_args()
    args.fonction(args)


if __name__ == "__main__":
    main()
