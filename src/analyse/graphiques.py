"""Fonctions de graphiques réutilisables dans tout le rapport.

Chaque fonction renvoie la figure (fig) et ses axes (ax), pour pouvoir l'ajuster
ou l'enregistrer ensuite. Chaque graphique a un titre, des axes nommés et une source.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# Palette commune à tous les graphiques (couleurs lisibles par les daltoniens)
COULEUR_PRINCIPALE = "#2a78d6"  # bleu : graphiques à une seule série
COULEURS_CATEGORIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # bleu, orange, vert d'eau : 3 séries au plus
COULEUR_TEXTE_SECONDAIRE = "#52514e"  # gris foncé : sources, graduations
COULEUR_GRILLE = "#e4e3df"  # gris clair : lignes de repère discrètes
COULEUR_SANS_DONNEES = "#d9d8d4"  # gris : départements sans données sur la carte
# Dégradé du bleu clair (faible) au bleu foncé (élevé), pour la carte
DEGRADE_BLEU = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def ajouter_source(fig, source):
    """Écrit la source en bas à gauche de la figure, en petit et en gris."""
    fig.text(0.01, 0.01, f"Source : {source}", fontsize=8, color=COULEUR_TEXTE_SECONDAIRE, ha="left")


def alleger_axes(ax):
    """Retire les bordures inutiles et garde une grille verticale discrète."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color=COULEUR_GRILLE, linewidth=0.8)
    ax.set_axisbelow(True)  # la grille passe derrière les barres
    ax.tick_params(colors=COULEUR_TEXTE_SECONDAIRE)


def tracer_barres_horizontales(df, colonne_libelle, colonne_valeur, titre, titre_axe, source):
    """Diagramme en barres horizontales, une barre par ligne du DataFrame.

    Les barres suivent l'ordre des lignes (la première en haut) : trier df avant l'appel
    si l'on veut un classement. Sortie : (fig, ax).
    """
    hauteur_figure = 1.5 + 0.4 * len(df)  # la figure grandit avec le nombre de barres
    fig, ax = plt.subplots(figsize=(9, hauteur_figure))
    ax.barh(df[colonne_libelle].astype(str), df[colonne_valeur], color=COULEUR_PRINCIPALE, height=0.65)
    ax.invert_yaxis()  # par défaut matplotlib place la première ligne en bas
    ax.set_xlabel(titre_axe)
    ax.set_title(titre, loc="left", fontsize=12)
    alleger_axes(ax)
    ajouter_source(fig, source)
    fig.tight_layout(rect=(0, 0.03, 1, 1))  # garde de la place en bas pour la source
    return fig, ax


def tracer_barres_empilees(df_parts, titre, titre_axe, source):
    """Barres horizontales empilées : une barre par ligne, un segment par colonne.

    Entrée : un DataFrame comme celui de repartir_procedures (lignes = années,
    colonnes = catégories, valeurs en %). Trois catégories au plus. Sortie : (fig, ax).
    """
    fig, ax = plt.subplots(figsize=(9, 1.5 + 0.5 * len(df_parts)))
    df_parts.plot(
        kind="barh", stacked=True, ax=ax, width=0.65,
        color=COULEURS_CATEGORIES[:len(df_parts.columns)],
        edgecolor="white", linewidth=1,  # fin liseré blanc entre les segments
    )
    ax.invert_yaxis()  # première année en haut
    ax.set_xlabel(titre_axe)
    ax.set_ylabel("")
    ax.set_title(titre, loc="left", fontsize=12, pad=30)  # pad : place pour la légende sous le titre
    # Légende au-dessus du graphique, sur une ligne
    ax.legend(ncols=len(df_parts.columns), loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False)
    alleger_axes(ax)
    ajouter_source(fig, source)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig, ax


def tracer_carte(gdf, colonne_valeur, titre, titre_legende, source):
    """Carte des départements colorés selon une valeur (du bleu clair au bleu foncé).

    Entrée : un GeoDataFrame, par exemple la sortie de preparer_carte. Sortie : (fig, ax).
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    degrade = LinearSegmentedColormap.from_list("degrade_bleu", DEGRADE_BLEU)
    gdf.plot(
        column=colonne_valeur, cmap=degrade, ax=ax,
        edgecolor="white", linewidth=0.4,  # frontières fines entre départements
        legend=True, legend_kwds={"label": titre_legende, "shrink": 0.6},
        missing_kwds={"color": COULEUR_SANS_DONNEES},  # départements sans données
    )
    ax.set_axis_off()  # pas d'axes de longitude et latitude
    ax.set_title(titre, loc="left", fontsize=12)
    ajouter_source(fig, source)
    return fig, ax
