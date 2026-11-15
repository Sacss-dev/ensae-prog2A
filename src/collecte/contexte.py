"""Étape 4 : collecte de la série nationale des défaillances d'entreprises (INSEE).

Série trimestrielle, en données brutes, par date de jugement, utilisée pour
l'introduction du rapport (évolution des défaillances, période Covid).

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.collecte.contexte
"""

import io

import pandas as pd
import requests

import config
from src.collecte.stockage_s3 import sauvegarder_parquet_s3

DELAI_MAX = 60  # secondes avant d'abandonner la requête


def telecharger_serie_insee(idbank, nombre_observations=None):
    """Télécharge une série de l'API BDM de l'INSEE.

    Entrées : l'identifiant de la série (idbank) et, si on ne veut que les
    dernières valeurs, leur nombre. Par défaut, toute la série.
    Sortie : un DataFrame avec les colonnes periode (ex. "2024-Q3") et valeur.
    """
    parametres = {}
    if nombre_observations is not None:
        parametres["lastNObservations"] = nombre_observations
    reponse = requests.get(config.URL_INSEE_BDM + idbank, params=parametres, timeout=DELAI_MAX)
    reponse.raise_for_status()  # erreur explicite si le serveur renvoie un code 4xx ou 5xx
    # Réponse en XML : chaque balise <Obs> est une observation (un trimestre)
    df_serie = pd.read_xml(io.StringIO(reponse.text), xpath=".//Obs", parser="etree")
    df_serie = df_serie.rename(columns={"TIME_PERIOD": "periode", "OBS_VALUE": "valeur"})
    df_serie = df_serie[["periode", "valeur"]].sort_values("periode")  # du plus ancien au plus récent
    return df_serie.reset_index(drop=True)


def collecter_contexte():
    """Télécharge toute la série des défaillances et l'enregistre sur S3."""
    df_defaillances = telecharger_serie_insee(config.IDBANK_DEFAILLANCES)
    df_defaillances = df_defaillances.rename(columns={"valeur": "nombre_defaillances"})
    sauvegarder_parquet_s3(df_defaillances, config.CHEMIN_S3_CONTEXTE + "/defaillances_insee.parquet")
    premiere, derniere = df_defaillances["periode"].iloc[0], df_defaillances["periode"].iloc[-1]
    print(f"Série INSEE : {len(df_defaillances)} trimestres, de {premiere} à {derniere}")
    return df_defaillances


if __name__ == "__main__":
    collecter_contexte()
