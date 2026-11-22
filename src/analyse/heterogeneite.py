"""Étape 9 (partie 4 du rapport) : hétérogénéité des trajectoires selon les sous-groupes.

Les calculs et les graphiques réutilisent ceux de l'étape 8 (calculer_quartiles,
tracer_trajectoires), appliqués par sous-groupe : grand secteur, âge au jugement,
taille et type de procédure. Chaque témoin est rangé dans le sous-groupe de sa
défaillante (siren_defaillante), pour garder la comparaison paire par paire.
"""

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

import config
from src.analyse.graphiques import tracer_trajectoires
from src.analyse.trajectoires import calculer_quartiles
from src.collecte.stockage_s3 import lire_parquet_s3


def lire_caracteristiques_defaillantes():
    """Relit, pour chaque défaillante, sa section, sa procédure, ses dates et sa tranche d'appariement.

    Sortie : une ligne par défaillante, identifiée par siren_defaillante.
    """
    colonnes = ["siren", "section_naf", "type_procedure", "date_creation", "date_jugement"]
    df_defaillantes = lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/defaillantes.parquet", colonnes)
    df_defaillantes = df_defaillantes.rename(columns={"siren": "siren_defaillante"})
    # La tranche de taille de la paire est celle de l'appariement (fixe), pas celle de chaque bilan
    df_paires = lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/paires.parquet", ["siren_defaillante", "tranche_taille"])
    df_paires = df_paires.rename(columns={"tranche_taille": "taille_appariement"})
    return df_defaillantes.merge(df_paires, on="siren_defaillante", how="inner")


def calculer_classe_age(df_defaillantes):
    """Ajoute l'âge au jugement (en années) et sa classe, selon les bornes de config.py.

    Une date de création inconnue donne une classe inconnue (NULL).
    """
    date_creation = pd.to_datetime(df_defaillantes["date_creation"])
    date_jugement = pd.to_datetime(df_defaillantes["date_jugement"])
    df_defaillantes["age_jugement"] = (date_jugement - date_creation).dt.days / 365.25
    # right=False : un âge de 3,0 ans tombe dans « 3 à 5 ans », pas dans « moins de 3 ans »
    df_defaillantes["classe_age"] = pd.cut(
        df_defaillantes["age_jugement"], bins=config.BORNES_AGE, labels=config.LABELS_AGE, right=False
    )
    return df_defaillantes


def construire_sous_groupes():
    """Construit la table des sous-groupes : une ligne par défaillante, une colonne par sous-groupe."""
    df_sous_groupes = calculer_classe_age(lire_caracteristiques_defaillantes())
    df_sous_groupes["grand_secteur"] = df_sous_groupes["section_naf"].map(config.GRANDS_SECTEURS)
    colonnes_gardees = ["siren_defaillante"] + list(config.SOUS_GROUPES)
    return df_sous_groupes[colonnes_gardees]


def ajouter_sous_groupes(df_base, df_sous_groupes):
    """Ajoute les sous-groupes à la base appariée : un témoin reçoit ceux de sa défaillante."""
    return df_base.merge(df_sous_groupes, on="siren_defaillante", how="left")


def resumer_par_sous_groupe(df_base, colonne_sous_groupe, ratio):
    """Tableau des médianes d'un ratio : une ligne par sous-groupe, une colonne par (groupe, horizon).

    La dernière colonne donne le nombre de défaillantes qui ont ce ratio à N-1.
    """
    df_quartiles = calculer_quartiles(df_base, [ratio], [colonne_sous_groupe, "groupe"])
    df_resume = df_quartiles.pivot_table(
        index=colonne_sous_groupe, columns=["groupe", "horizon"], values="mediane", observed=True
    )
    est_defaillante_n1 = (df_quartiles["groupe"] == "défaillante") & (df_quartiles["horizon"] == 1)
    effectifs_n1 = df_quartiles[est_defaillante_n1].set_index(colonne_sous_groupe)["nombre"]
    df_resume[("effectif défaillantes", "N-1")] = effectifs_n1
    return df_resume.round(3)


def tracer_par_sous_groupe(df_base, colonne_sous_groupe, ratio):
    """Petits multiples d'un ratio : un panneau par sous-groupe, défaillantes contre témoins.

    Réutilise tracer_trajectoires de l'étape 8 : la colonne « ratio » reçoit
    simplement le nom du sous-groupe, qui devient le titre de chaque panneau.
    """
    df_quartiles = calculer_quartiles(df_base, [ratio], [colonne_sous_groupe, "groupe"])
    df_quartiles["ratio"] = df_quartiles[colonne_sous_groupe].astype(str)
    titres_panneaux = {}
    for valeur in df_quartiles["ratio"].unique():
        titres_panneaux[valeur] = valeur
    titre = f"{config.LIBELLES_RATIOS[ratio]}, selon le {config.SOUS_GROUPES[colonne_sous_groupe]}"
    fig, _ = tracer_trajectoires(df_quartiles, titres_panneaux, titre, config.SOURCE_GRAPHIQUES)
    return fig


def tracer_tous_les_sous_groupes(df_base):
    """Trace un graphique par (sous-groupe, ratio) choisis dans config.py.

    Sortie : un dictionnaire (sous-groupe, ratio) -> figure.
    """
    figures = {}
    for colonne_sous_groupe in config.SOUS_GROUPES:
        for ratio in config.RATIOS_HETEROGENEITE:
            figures[(colonne_sous_groupe, ratio)] = tracer_par_sous_groupe(df_base, colonne_sous_groupe, ratio)
    return figures


def afficher_sous_groupe(df_base, colonne_sous_groupe):
    """Pour le rapport : affiche, pour chaque ratio étudié, le graphique puis le tableau d'un sous-groupe.

    Évite de recopier la même boucle dans chaque cellule du notebook (une cellule par sous-groupe).
    """
    for ratio in config.RATIOS_HETEROGENEITE:
        tracer_par_sous_groupe(df_base, colonne_sous_groupe, ratio)
        plt.show()  # affiche le graphique tout de suite, avant son tableau
        display(resumer_par_sous_groupe(df_base, colonne_sous_groupe, ratio))
