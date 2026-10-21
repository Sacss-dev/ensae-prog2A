"""Étape 2 : collecte des annonces BODACC de procédures collectives.

Les annonces sont téléchargées année par année avec l'export parquet de l'API
(pas de limite de 10 000 résultats), puis enregistrées telles quelles sur S3,
un fichier par année de parution.

Lancement de la collecte complète, depuis la racine du dépôt, sur le SSP Cloud :
    python -m src.collecte.bodacc
"""

import io

import pandas as pd
import requests

import config
from src.collecte.stockage_s3 import lire_parquet_s3, sauvegarder_parquet_s3

DELAI_MAX = 600  # secondes : l'export d'une année entière prend environ 30 secondes


def lister_annees_collecte():
    """Renvoie la liste des années de parution à collecter, bornes incluses."""
    return list(range(config.ANNEE_DEBUT_COLLECTE_BODACC, config.ANNEE_FIN_COLLECTE_BODACC + 1))


def telecharger_bodacc_annee(annee):
    """Télécharge toutes les annonces de procédures collectives publiées une année donnée.

    Entrée : une année (entier). Sortie : un DataFrame, une ligne par annonce.
    """
    parametres = {
        # Filtre ODSQL : famille « procédures collectives » et année de parution
        "where": f'familleavis="collective" AND year(dateparution)={annee}',
    }
    reponse = requests.get(config.URL_BODACC_EXPORT_PARQUET, params=parametres, timeout=DELAI_MAX)
    reponse.raise_for_status()  # erreur explicite si le serveur renvoie un code 4xx ou 5xx
    df_annonces = pd.read_parquet(io.BytesIO(reponse.content))  # le fichier reste en mémoire
    print(f"BODACC {annee} : {len(df_annonces)} annonces téléchargées")
    return df_annonces


def construire_chemin_s3(annee):
    """Renvoie le chemin S3 du fichier brut d'une année, par exemple .../bodacc/annonces_2022.parquet."""
    return f"{config.CHEMIN_S3_BODACC}/annonces_{annee}.parquet"


def collecter_bodacc():
    """Télécharge chaque année de la période de collecte et l'enregistre sur S3.

    Un fichier par année : si une année échoue, on peut la relancer seule.
    """
    for annee in lister_annees_collecte():
        df_annonces = telecharger_bodacc_annee(annee)
        sauvegarder_parquet_s3(df_annonces, construire_chemin_s3(annee))


def lire_bodacc_brut():
    """Relit depuis S3 (sans clé) toutes les années collectées et les assemble en un DataFrame."""
    liste_df_annees = []
    for annee in lister_annees_collecte():
        liste_df_annees.append(lire_parquet_s3(construire_chemin_s3(annee)))
    return pd.concat(liste_df_annees, ignore_index=True)


def compter_annonces_par_annee(df_annonces):
    """Tableau de validation : nombre d'annonces par année de parution.

    Sortie : un DataFrame avec les colonnes annee et nb_annonces.
    """
    annees_parution = pd.to_datetime(df_annonces["dateparution"]).dt.year
    df_comptage = annees_parution.value_counts().sort_index()
    df_comptage = df_comptage.rename_axis("annee").reset_index(name="nb_annonces")
    return df_comptage


if __name__ == "__main__":
    collecter_bodacc()
    print(compter_annonces_par_annee(lire_bodacc_brut()))
