"""Fonctions de graphiques réutilisables dans tout le rapport.

Chaque fonction renvoie la figure (fig) et ses axes (ax), pour pouvoir l'ajuster
ou l'enregistrer ensuite. Chaque graphique a un titre, des axes nommés et une source.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import PercentFormatter

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


def tracer_panneau_trajectoire(ax, df_ratio, titre, en_pourcentage):
    """Trace, sur un seul panneau, la médiane et l'intervalle interquartile de chaque groupe.

    Entrée : les lignes d'un seul ratio de la sortie de calculer_quartiles
    (colonnes groupe, horizon, q1, mediane, q3). L'axe va de N-4 (à gauche) à N-1.
    """
    liste_groupes = sorted(df_ratio["groupe"].unique())
    for numero, groupe in enumerate(liste_groupes):
        df_groupe = df_ratio[df_ratio["groupe"] == groupe].sort_values("horizon")
        couleur = COULEURS_CATEGORIES[numero]
        ax.plot(df_groupe["horizon"], df_groupe["mediane"], color=couleur, marker="o", label=groupe)
        # bande colorée entre le 1er et le 3e quartile : la moitié centrale des entreprises
        ax.fill_between(df_groupe["horizon"], df_groupe["q1"], df_groupe["q3"], color=couleur, alpha=0.15)
    ax.set_xticks([4, 3, 2, 1], labels=["N-4", "N-3", "N-2", "N-1"])
    ax.invert_xaxis()  # le temps s'écoule vers la droite, jusqu'au jugement
    if en_pourcentage:
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))  # 0,05 s'affiche 5 %
    ax.set_title(titre, loc="left", fontsize=9)
    ax.set_xlabel("Exercice avant le jugement")
    alleger_axes(ax)


def tracer_trajectoires(df_quartiles, libelles, titre, source, en_pourcentage=True):
    """Petits multiples : un panneau par ratio, défaillantes contre témoins, de N-4 à N-1.

    Entrées : la sortie de calculer_quartiles, un dictionnaire ratio -> nom lisible,
    le titre, la source, et en_pourcentage (False pour des rangs de 0 à 100).
    Sortie : (fig, axes).
    """
    liste_ratios = list(df_quartiles["ratio"].unique())
    nombre_lignes = (len(liste_ratios) + 2) // 3  # 3 panneaux par ligne, arrondi au-dessus
    fig, axes = plt.subplots(nombre_lignes, 3, figsize=(14, 4 * nombre_lignes), squeeze=False)
    liste_axes = axes.flatten()
    for numero, ratio in enumerate(liste_ratios):
        df_ratio = df_quartiles[df_quartiles["ratio"] == ratio]
        tracer_panneau_trajectoire(liste_axes[numero], df_ratio, libelles[ratio], en_pourcentage)
    for ax_vide in liste_axes[len(liste_ratios):]:
        ax_vide.set_visible(False)  # panneaux en trop sur la dernière ligne
    liste_axes[0].legend(frameon=False)
    fig.suptitle(titre, x=0.01, ha="left", fontsize=13)
    ajouter_source(fig, source)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    return fig, axes


def tracer_courbe(df, colonne_x, colonne_y, titre, titre_axe, source):
    """Courbe d'une seule série dans le temps. Sortie : (fig, ax)."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(df[colonne_x], df[colonne_y], color=COULEUR_PRINCIPALE, linewidth=1.8)
    ax.set_title(titre, loc="left", fontsize=12)
    ax.set_ylabel(titre_axe)
    ax.set_xlabel("")
    alleger_axes(ax)
    ax.grid(axis="y", color=COULEUR_GRILLE, linewidth=0.8)  # grille horizontale : lecture des niveaux
    ajouter_source(fig, source)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig, ax


def surligner_periode(ax, date_debut, date_fin, libelle):
    """Grise une période sur l'axe horizontal (par exemple la période Covid) et l'annote."""
    ax.axvspan(date_debut, date_fin, color=COULEUR_GRILLE, alpha=0.8, zorder=0)
    # get_xaxis_transform : x en dates, y en part de la hauteur (1.0 = haut du graphique)
    ax.text(date_debut, 1.0, f" {libelle}", transform=ax.get_xaxis_transform(),
            va="top", fontsize=9, color=COULEUR_TEXTE_SECONDAIRE)
