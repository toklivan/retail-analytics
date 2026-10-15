"""Catalogue du magasin fictif : produits, rayons, prix et taux de TVA.

Tous les produits sont inventés et génériques (aucune marque).
Chaque rayon a un taux de TVA par défaut et une saisonnalité ; un produit
peut porter son propre taux quand il diffère de celui du rayon.
"""

TVA_REDUITE = 0.055   # alimentation, boissons sans alcool
TVA_INTERMEDIAIRE = 0.10   # plats et sandwichs à emporter
TVA_NORMALE = 0.20   # alcools, confiserie, hygiène

# Coefficient de vente par mois (janvier = indice 0) : 1,0 = mois moyen.
SAISONS = {
    "stable": [1.0] * 12,
    "ete": [0.7, 0.7, 0.8, 0.9, 1.1, 1.3, 1.6, 1.5, 1.1, 0.9, 0.8, 0.8],
    "hiver": [1.3, 1.3, 1.1, 1.0, 0.9, 0.7, 0.6, 0.6, 0.8, 1.0, 1.2, 1.3],
}

# Un prix à None signale une touche libre : le vendeur tape le prix à chaque vente.
# Chaque produit : (libellé, prix TTC en euros, popularité de 1 à 10[, taux de TVA]).
RAYONS = {
    "Boissons": (TVA_REDUITE, "ete", [
        ("Eau minérale 1,5L", 0.95, 10), ("Eau gazeuse 1L", 1.10, 5),
        ("Pack eau 6x1,5L", 4.20, 4), ("Cola 33cl", 1.30, 10),
        ("Cola 1,5L", 2.60, 6), ("Cola zéro 33cl", 1.30, 7),
        ("Limonade 1,5L", 1.90, 3), ("Thé glacé pêche 50cl", 1.80, 6),
        ("Jus d'orange 1L", 2.40, 5), ("Jus de pomme 1L", 2.10, 3),
        ("Boisson énergisante 25cl", 1.70, 8), ("Sirop de menthe 75cl", 3.20, 2),
        ("Soda orange 33cl", 1.30, 5), ("Eau aromatisée citron 50cl", 1.20, 4),
    ]),
    "Alcools": (TVA_NORMALE, "ete", [
        ("Bière blonde 33cl", 1.60, 9), ("Bière blonde 50cl", 2.30, 8),
        ("Pack bière 6x25cl", 5.90, 5), ("Bière ambrée 33cl", 2.10, 4),
        ("Bière blanche 33cl", 2.20, 4), ("Cidre brut 75cl", 3.90, 2),
        ("Vin rouge 75cl", 5.50, 5), ("Vin rosé 75cl", 5.20, 5),
        ("Vin blanc 75cl", 5.40, 3), ("Pastis 70cl", 19.90, 2),
        ("Rhum blanc 70cl", 17.50, 1), ("Vodka 70cl", 16.90, 2),
        ("Whisky 70cl", 21.90, 2), ("Champagne brut 75cl", 29.90, 1),
    ]),
    "Épicerie salée": (TVA_REDUITE, "stable", [
        ("Pâtes coquillettes 500g", 1.20, 6), ("Pâtes spaghetti 500g", 1.30, 6),
        ("Riz long 1kg", 2.10, 4), ("Sauce tomate 400g", 1.60, 5),
        ("Thon au naturel 140g", 2.40, 5), ("Sardines à l'huile 135g", 2.10, 3),
        ("Huile de tournesol 1L", 2.90, 3), ("Huile d'olive 50cl", 6.50, 2),
        ("Sel fin 1kg", 0.90, 1), ("Moutarde 370g", 1.90, 3),
        ("Mayonnaise 235g", 2.20, 4), ("Ketchup 500g", 2.60, 4),
        ("Chips nature 150g", 1.90, 9), ("Chips paprika 150g", 1.90, 6),
        ("Cacahuètes grillées 200g", 2.30, 4), ("Soupe de légumes 1L", 2.80, 3),
        ("Lentilles 500g", 1.80, 2), ("Couscous moyen 500g", 1.70, 3),
        ("Conserve petits pois 400g", 1.40, 2), ("Bouillon cube x10", 1.60, 2),
    ]),
    "Épicerie sucrée": (TVA_REDUITE, "stable", [
        ("Biscuits petit beurre 200g", 1.60, 6), ("Biscuits chocolat 300g", 2.40, 7),
        ("Céréales chocolat 375g", 3.60, 4), ("Pâte à tartiner 400g", 3.90, 5),
        ("Confiture fraise 370g", 2.70, 3), ("Sucre en morceaux 1kg", 1.90, 2),
        ("Café moulu 250g", 3.80, 4), ("Thé noir x25", 2.50, 2),
        ("Chocolat noir 100g", 1.90, 4), ("Madeleines x12", 2.30, 4),
        ("Compote pomme x4", 2.20, 3), ("Miel 250g", 4.50, 1),
        ("Chocolat au lait 100g", 1.80, 5, TVA_NORMALE),
        ("Bonbons gélifiés 200g", 2.10, 6, TVA_NORMALE),
        ("Barre chocolatée 50g", 1.10, 9, TVA_NORMALE),
        ("Chewing-gum menthe", 1.40, 7, TVA_NORMALE),
    ]),
    "Crèmerie": (TVA_REDUITE, "stable", [
        ("Lait demi-écrémé 1L", 1.25, 10), ("Lait entier 1L", 1.45, 4),
        ("Beurre doux 250g", 3.20, 5), ("Œufs x6", 2.60, 7),
        ("Œufs x12", 4.90, 3), ("Yaourt nature x4", 1.90, 5),
        ("Yaourt fruits x4", 2.40, 4), ("Crème fraîche 20cl", 1.80, 4),
        ("Emmental râpé 200g", 2.60, 5), ("Camembert 250g", 2.90, 3),
        ("Comté 200g", 4.60, 2), ("Mozzarella 125g", 1.70, 4),
        ("Jambon blanc x4", 3.40, 7), ("Lardons fumés 200g", 2.70, 4),
        ("Saucisson sec 250g", 4.90, 3), ("Dessert chocolat x4", 2.30, 3),
    ]),
    "Surgelés et glaces": (TVA_REDUITE, "ete", [
        ("Pizza surgelée 4 fromages", 3.90, 5), ("Frites surgelées 1kg", 2.90, 3),
        ("Légumes poêlée 750g", 3.40, 2), ("Glace vanille 1L", 4.50, 3),
        ("Cône glacé chocolat", 2.20, 6), ("Bâtonnet glacé x4", 4.20, 3),
        ("Esquimau vanille", 1.80, 5), ("Glaçons 2kg", 2.50, 3),
    ]),
    "Fruits et légumes": (TVA_REDUITE, "stable", [
        ("Fruits et légumes vrac", None, 9),
        ("Bananes", 0.40, 7), ("Avocat", 1.20, 4), ("Citron", 0.50, 5),
        ("Barquette tomates cerises 250g", 2.50, 4), ("Salade sachet 150g", 1.90, 4),
        ("Pommes de terre 2,5kg", 3.50, 3), ("Oignons filet 1kg", 2.20, 3),
        ("Ail tête", 0.80, 2),
    ]),
    "Boulangerie": (TVA_REDUITE, "stable", [
        ("Baguette", 1.10, 10), ("Baguette tradition", 1.40, 6),
        ("Pain de mie 500g", 2.20, 5), ("Croissant", 1.20, 6),
        ("Pain au chocolat", 1.30, 6), ("Brioche tranchée 500g", 2.90, 3),
        ("Pain burger x4", 2.40, 2),
    ]),
    "Snacking": (TVA_INTERMEDIAIRE, "stable", [
        ("Sandwich jambon beurre", 3.90, 8), ("Sandwich poulet crudités", 4.50, 6),
        ("Sandwich thon", 4.20, 4), ("Salade composée", 5.50, 4),
        ("Wrap poulet", 4.90, 4), ("Plat cuisiné lasagnes", 5.90, 3),
        ("Café à emporter", 1.50, 7), ("Croque-monsieur", 3.50, 3),
    ]),
    "Hygiène et entretien": (TVA_NORMALE, "hiver", [
        ("Papier toilette x6", 3.90, 5), ("Essuie-tout x2", 2.90, 3),
        ("Mouchoirs boîte", 1.90, 4), ("Dentifrice 75ml", 2.60, 3),
        ("Brosse à dents", 2.20, 2), ("Gel douche 250ml", 2.90, 3),
        ("Shampoing 250ml", 3.40, 2), ("Déodorant 150ml", 3.60, 3),
        ("Liquide vaisselle 500ml", 2.10, 3), ("Lessive liquide 1,5L", 7.90, 2),
        ("Sacs poubelle 30L x20", 2.40, 3), ("Éponges x3", 1.70, 2),
        ("Briquet", 1.50, 6), ("Piles AA x4", 5.90, 2),
        ("Couches taille 4 x20", 9.90, 1), ("Serviettes hygiéniques x14", 3.20, 2),
        ("Rasoirs jetables x5", 4.50, 1), ("Allumettes", 0.60, 1),
    ]),
    "Divers": (TVA_NORMALE, "stable", [
        ("Divers 20 %", None, 3),
    ]),
}


def lister_produits():
    """Rend la liste des produits, un dictionnaire par produit."""
    produits = []
    for rayon, (taux_rayon, saison, articles) in RAYONS.items():
        for article in articles:
            libelle, prix, popularite = article[:3]
            # Un quatrième élément, s'il existe, remplace le taux du rayon.
            taux = article[3] if len(article) > 3 else taux_rayon
            produits.append({
                "libelle": libelle,
                "rayon": rayon,
                "prix_ttc": prix,
                "taux_tva": taux,
                "popularite": popularite,
                "saison": saison,
            })
    return produits
