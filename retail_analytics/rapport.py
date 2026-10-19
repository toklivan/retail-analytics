"""Rapport mensuel des ventes, en une page HTML autonome.

Le rapport ne calcule rien de nouveau : il met en forme les indicateurs, les
graphiques et les contrôles. `construire_rapport` rend le texte de la page ;
c'est la commande `rapport` qui l'écrit dans un fichier.

Tout texte venu des données (libellé, rayon) passe par `html.escape`, qui
remplace « < », « > » et « & » par leur écriture HTML : un libellé qui en
contient casserait sinon la page.
"""

import base64
import html
import io
from string import Template

from retail_analytics import graphiques, indicateurs, rayons
from retail_analytics.affichage import (NOMS_MOYENS, date_fr, euros, evolution_fr, mois_fr, mois_long, nombre,
                                        pourcentage)
from retail_analytics.graphiques import nom_de_rayon

# Squelette de la page. string.Template remplace chaque $nom par la valeur donnée à substitute.
PAGE = Template("""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$titre</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 860px; margin: 0 auto; padding: 24px 16px;
       color: #1a1a1a; background: #fff; line-height: 1.5; }
h1 { margin-bottom: 0; }
h2 { border-bottom: 2px solid #1f4e79; padding-bottom: 4px; margin-top: 40px; }
.sous-titre, .note { color: #555; }
.alerte { background: #fff4e5; border-left: 4px solid #e08a00; padding: 8px 12px; }
.chiffres { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.chiffre { border: 1px solid #ddd; border-radius: 6px; padding: 12px; }
.chiffre span { display: block; }
.valeur { font-size: 1.5em; font-weight: bold; }
.nom, .evolution { color: #555; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.95em; }
th, td { padding: 4px 8px; border-bottom: 1px solid #ddd; text-align: left; }
th { background: #f0f4f8; }
.nombre { text-align: right; white-space: nowrap; }
img { max-width: 100%; height: auto; }
@page { size: A4; margin: 15mm; }
@media print {
  body { max-width: none; padding: 0; }
  h2 { break-after: avoid; }
  img, tr, .chiffres { break-inside: avoid; }
}
</style>
</head>
<body>
<h1>$titre</h1>
<p class="sous-titre">$periode. Rapport établi le $etabli_le.</p>
$contenu
</body>
</html>
""")


def evolution(actuel, precedent):
    """Évolution relative ; vide quand il n'y a rien à comparer (précédent nul)."""
    return (actuel - precedent) / precedent if precedent else float("nan")


def tableau(entetes, lignes, nombres=()):
    """Tableau HTML ; les colonnes dont le rang est dans `nombres` sont alignées à droite."""
    def cellule(balise, rang, texte):
        classe = ' class="nombre"' if rang in nombres else ""
        return f"<{balise}{classe}>{html.escape(str(texte))}</{balise}>"

    # enumerate donne le rang de chaque élément en même temps que l'élément : 0, 1, 2...
    tete = "".join(cellule("th", rang, texte) for rang, texte in enumerate(entetes))
    corps = "".join("<tr>" + "".join(cellule("td", rang, texte) for rang, texte in enumerate(ligne)) + "</tr>"
                    for ligne in lignes)
    return f"<table><thead><tr>{tete}</tr></thead><tbody>{corps}</tbody></table>"


def paragraphe(texte, classe=None):
    attribut = f' class="{classe}"' if classe else ""
    return f"<p{attribut}>{html.escape(texte)}</p>"


def image(figure, description):
    """La figure en PNG, intégrée dans la page : le fichier HTML se suffit à lui-même."""
    # BytesIO est un fichier en mémoire : savefig y écrit l'image sans toucher au disque.
    tampon = io.BytesIO()
    figure.savefig(tampon, format="png", dpi=150)
    # base64 écrit les octets de l'image en lettres et en chiffres, qu'une page HTML peut contenir.
    code = base64.b64encode(tampon.getvalue()).decode("ascii")
    return f'<img src="data:image/png;base64,{code}" alt="{html.escape(description)}">'


def points_a_retenir(comparaison, par_produit, mois, comparable):
    """Phrases sur le rayon qui progresse le plus, celui qui recule le plus, et le produit n°1.

    Les rayons sont classés sur l'écart en euros, pas en pourcentage : un petit
    rayon qui passe de 50 € à 100 € fait +100 % sans peser sur le magasin.
    Les ventes sans rayon n'entrent pas dans ce classement. Quand l'un des deux
    mois est incomplet, la comparaison n'a pas de sens : on le dit à la place.
    """
    points = []
    if not comparable:
        points.append(f"Pas de comparaison par rayon avec {mois_fr(mois - 1)} : "
                      "l'un des deux mois est incomplet ou sans vente.")
    else:
        avec_rayon = comparaison[comparaison.index.notna()]
        ecarts = avec_rayon["actuel"] - avec_rayon["precedent"]
        # idxmax et idxmin donnent l'étiquette de la ligne qui porte la plus grande et la plus petite valeur.
        if not ecarts.empty and ecarts.max() > 0:
            rayon = ecarts.idxmax()
            points.append(f"Le rayon {rayon} progresse le plus : +{euros(ecarts[rayon])} HT "
                          f"par rapport à {mois_fr(mois - 1)}{entre_parentheses(avec_rayon.loc[rayon, 'evolution'])}.")
        if not ecarts.empty and ecarts.min() < 0:
            rayon = ecarts.idxmin()
            points.append(f"Le rayon {rayon} recule le plus : {euros(ecarts[rayon])} HT "
                          f"par rapport à {mois_fr(mois - 1)}{entre_parentheses(avec_rayon.loc[rayon, 'evolution'])}.")
    total = par_produit["ca_ht"].sum()
    if total > 0:
        premier = par_produit.index[0]
        points.append(f"Produit n°1 : {premier}, avec {euros(par_produit['ca_ht'].iloc[0])} HT, "
                      f"soit {pourcentage(par_produit['ca_ht'].iloc[0] / total)} du CA HT du mois.")
    return points


def entre_parentheses(part):
    """' (+31,4 %)', ou rien quand l'évolution est vide (rayon absent le mois précédent)."""
    texte = evolution_fr(part)
    return "" if texte == "-" else f" ({texte})"


def section_alertes(mois, complets, resultats):
    """Bandeaux en tête de page : mois incomplet, contrôles en écart."""
    messages = []
    if not complets.get(mois, False):
        messages.append(f"{mois_long(mois).capitalize()} est incomplet : les exports ne couvrent pas tous ses jours. "
                        "Les chiffres ne portent que sur les jours couverts.")
    en_ecart = [nom for nom, ecarts in resultats.items() if not ecarts.empty]
    if en_ecart:
        messages.append(f"Contrôles en écart sur l'ensemble des exports : {', '.join(en_ecart)}. "
                        "Détail dans « Fiabilité des données ».")
    return "".join(paragraphe(message, "alerte") for message in messages)


def panier(ligne):
    """Panier moyen TTC de tous les tickets payants, au centime ; None sans ticket payant."""
    if not ligne["tickets_payants"]:
        return None
    return int(round(ligne["ca_ttc"] / ligne["tickets_payants"]))


def chiffres_du_mois(ligne):
    """Les quatre chiffres d'une ligne de `indicateurs.chiffre_affaires`, par nom affiché."""
    return {"CA TTC": ligne["ca_ttc"], "CA HT": ligne["ca_ht"],
            "Tickets payants": ligne["tickets_payants"], "Panier moyen TTC": panier(ligne)}


def section_essentiel(ca, complets, mois, comparable, points):
    """Les quatre chiffres du mois, leur évolution, les points à retenir et l'évolution du CA."""
    actuels = chiffres_du_mois(ca.loc[mois])
    precedents = chiffres_du_mois(ca.loc[mois - 1]) if comparable else {}
    cases = ""
    for nom, valeur in actuels.items():
        mise_en_forme = nombre if nom == "Tickets payants" else euros
        precedent = precedents.get(nom)
        if valeur is not None and precedent is not None:
            texte_evolution = f"{evolution_fr(evolution(valeur, precedent))} par rapport à {mois_fr(mois - 1)}"
        else:
            texte_evolution = f"pas de comparaison avec {mois_fr(mois - 1)}"
        texte_valeur = "-" if valeur is None else mise_en_forme(valeur)
        cases += (f'<div class="chiffre"><span class="valeur">{html.escape(texte_valeur)}</span>'
                  f'<span class="nom">{nom}</span><span class="evolution">{html.escape(texte_evolution)}</span></div>')
    liste = "".join(f"<li>{html.escape(point)}</li>" for point in points)
    return ("<section><h2>L'essentiel</h2>"
            f'<div class="chiffres">{cases}</div>'
            f"<h3>À retenir</h3><ul>{liste}</ul>"
            + image(graphiques.evolution_ca(ca, complets, mois), "Chiffre d'affaires HT par mois")
            + paragraphe("Le mois du rapport est en foncé. Un mois hachuré est incomplet : "
                         "sa barre ne couvre pas tout le mois.", "note")
            + "</section>")


def section_rayons(par_rayon, comparaison, mois, comparable):
    """Graphique et tableau du CA HT par rayon, comparé au mois précédent."""
    # xs prend les lignes d'un mois dans un index à deux niveaux (mois, rayon) ; reindex les aligne
    # sur les rayons de la comparaison, à 0 pour un rayon vendu le mois précédent seulement.
    quantites = par_rayon["quantite"].xs(mois, level="mois").reindex(comparaison.index, fill_value=0)
    tableau_rayons = comparaison.assign(quantite=quantites)
    total = comparaison["actuel"].sum()
    # itertuples parcourt les lignes ; ligne.Index est l'étiquette de la ligne, ici le rayon.
    lignes = [[nom_de_rayon(ligne.Index), euros(ligne.actuel), pourcentage(ligne.actuel / total if total else 0),
               nombre(ligne.quantite), euros(ligne.precedent), evolution_fr(ligne.evolution)]
              for ligne in tableau_rayons.itertuples()]
    total_precedent = comparaison["precedent"].sum()
    lignes.append(["Total", euros(total), pourcentage(1 if total else 0), nombre(quantites.sum()),
                   euros(total_precedent), evolution_fr(evolution(total, total_precedent))])
    entetes = ["Rayon", f"CA HT {mois_fr(mois)}", "Part du CA", "Quantités vendues",
               f"CA HT {mois_fr(mois - 1)}", "Évolution"]
    note = "" if comparable else paragraphe(
        "L'un des deux mois est incomplet ou sans vente : l'évolution n'est pas significative.", "alerte")
    return ("<section><h2>Les rayons</h2>"
            + image(graphiques.rayons(comparaison, mois), "Chiffre d'affaires HT par rayon")
            + note + tableau(entetes, lignes, nombres=(1, 2, 3, 4, 5)) + "</section>")


def section_produits(par_produit, mois, nombre_affiches=20):
    """Les dix premiers produits, le résumé du classement ABC et les premiers produits de la classe A.

    Au-delà de `nombre_affiches`, les autres produits de la classe A sont résumés en une ligne.
    """
    if par_produit.empty:
        return "<section><h2>Les produits</h2>" + paragraphe("Aucun produit vendu ce mois-ci.") + "</section>"
    resume = [[classe, nombre(len(groupe)), pourcentage(groupe["part"].sum())]
              for classe, groupe in par_produit.groupby("classe")]
    classe_a = par_produit[par_produit["classe"] == "A"]
    affiches, autres = classe_a.head(nombre_affiches), classe_a.iloc[nombre_affiches:]
    lignes_a = [[nombre(rang), ligne.Index, nom_de_rayon(ligne.rayon), euros(ligne.ca_ht), nombre(ligne.quantite),
                 pourcentage(ligne.part), pourcentage(ligne.part_cumulee)]
                for rang, ligne in enumerate(affiches.itertuples(), start=1)]
    reste = "" if autres.empty else paragraphe(
        f"Et {nombre(len(autres))} autre(s) produit(s) en classe A, qui font {pourcentage(autres['part'].sum())} "
        "du CA HT.", "note")
    return ("<section><h2>Les produits</h2>"
            + image(graphiques.premiers_produits(par_produit), "Les dix premiers produits, CA HT")
            + "<h3>Classement ABC</h3>"
            + paragraphe("Classe A : les produits qui font ensemble 80 % du CA HT. "
                         "Classe B : les 15 % suivants. Classe C : les 5 % restants.", "note")
            + tableau(["Classe", "Produits", "Part du CA HT"], resume, nombres=(1, 2))
            + f"<h3>Les premiers produits de la classe A, {html.escape(mois_long(mois))}</h3>"
            + tableau(["Rang", "Produit", "Rayon", "CA HT", "Vendus", "Part du CA", "Part cumulée"], lignes_a,
                      nombres=(0, 3, 4, 5, 6))
            + reste
            + "</section>")


def section_encaissements(paiements, tickets, mois):
    """Encaissements TTC par moyen de paiement, et panier moyen du magasin et de la livraison."""
    moyens = indicateurs.ventes_par_moyen(paiements, tickets).loc[mois]
    total = moyens.sum()
    lignes_moyens = [[NOMS_MOYENS.get(moyen, moyen), euros(montant), pourcentage(montant / total if total else 0)]
                     for moyen, montant in moyens.items()]
    paniers = indicateurs.panier_moyen(tickets, paiements).loc[mois]
    lignes_paniers = [[canal.capitalize(), nombre(paniers.loc[canal, "nombre_tickets"]),
                       euros(paniers.loc[canal, "ca_ttc"]), euros(paniers.loc[canal, "panier_moyen"])]
                      for canal in ["magasin", "livraison"] if canal in paniers.index]
    return ("<section><h2>Encaissements et livraison</h2>"
            + tableau(["Moyen de paiement", "Encaissé TTC", "Part"], lignes_moyens, nombres=(1, 2))
            + tableau(["Canal", "Tickets payants", "CA TTC", "Panier moyen TTC"], lignes_paniers, nombres=(1, 2, 3))
            + paragraphe("Un ticket payé, même en partie, par la plateforme de livraison compte dans la livraison.",
                         "note")
            + "</section>")


def section_offerts(ventes, mois):
    """Nombre d'articles offerts dans le mois et leur valeur au prix de vente."""
    offerts = indicateurs.articles_offerts(ventes)
    if mois in offerts.index:
        ligne = offerts.loc[mois]
        texte = (f"{nombre(ligne['nombre_articles'])} article(s) offert(s) ce mois-ci, "
                 f"pour une valeur de {euros(ligne['valeur_ttc'])} TTC au prix de vente.")
    else:
        texte = "Aucun article offert ce mois-ci."
    return "<section><h2>Articles offerts</h2>" + paragraphe(texte) + "</section>"


def section_fiabilite(ventes_du_mois, resultats):
    """Ce que valent les chiffres : ventes sans rayon et résultat des contrôles."""
    inconnus = rayons.libelles_inconnus(ventes_du_mois)
    texte = (f"Part du CA HT du mois non rattachée à un rayon : "
             f"{pourcentage(rayons.part_ca_non_rattachee(ventes_du_mois))}.")
    contenu = paragraphe(texte)
    if not inconnus.empty:
        lignes = [[libelle, nombre(ligne["nombre_lignes"]), euros(ligne["ca_ht"])]
                  for libelle, ligne in inconnus.iterrows()]
        contenu += (paragraphe("Libellés absents de la table de correspondance, à y ajouter :")
                    + tableau(["Libellé", "Lignes de vente", "CA HT"], lignes, nombres=(1, 2)))
    lignes_controles = [[nom, "OK" if ecarts.empty else f"{nombre(len(ecarts))} écart(s)"]
                        for nom, ecarts in resultats.items()]
    contenu += (paragraphe("Contrôles de cohérence entre les rapports de la caisse, sur l'ensemble des exports :")
                + tableau(["Contrôle", "Résultat"], lignes_controles))
    return "<section><h2>Fiabilité des données</h2>" + contenu + "</section>"


def construire_rapport(propres, resultats, mois, complets, etabli_le):
    """Le texte HTML du rapport d'un mois, à partir des tables nettoyées et des résultats des contrôles.

    `complets` vient de `indicateurs.mois_complets` ; `etabli_le` est la date
    imprimée sur le rapport, passée en paramètre pour que les tests la fixent.
    """
    tickets, ventes = propres["tickets"], propres["ventes"]
    ca = indicateurs.chiffre_affaires(tickets)
    if mois not in ca.index:
        raise ValueError(f"Aucune vente en {mois_fr(mois)}.")
    # La comparaison n'a de sens qu'entre deux mois complets, tous deux avec des ventes.
    comparable = bool(complets.get(mois, False) and complets.get(mois - 1, False)) and (mois - 1) in ca.index
    par_rayon = indicateurs.ventes_par_rayon(ventes)
    comparaison = indicateurs.comparer_au_mois_precedent(par_rayon, mois)
    par_produit = indicateurs.classement_abc(indicateurs.ventes_par_produit(ventes, mois))
    ventes_du_mois = ventes[indicateurs.mois_commercial(ventes["journee_commerciale"]) == mois]
    contenu = (section_alertes(mois, complets, resultats)
               + section_essentiel(ca, complets, mois, comparable,
                                   points_a_retenir(comparaison, par_produit, mois, comparable))
               + section_rayons(par_rayon, comparaison, mois, comparable)
               + section_produits(par_produit, mois)
               + section_encaissements(propres["paiements"], tickets, mois)
               + section_offerts(ventes, mois)
               + section_fiabilite(ventes_du_mois, resultats))
    periode = f"Journées de caisse du {date_fr(mois.start_time)} au {date_fr(mois.end_time)}"
    return PAGE.substitute(titre=html.escape(f"Rapport de ventes, {mois_long(mois)}"),
                           periode=periode, etabli_le=date_fr(etabli_le), contenu=contenu)
