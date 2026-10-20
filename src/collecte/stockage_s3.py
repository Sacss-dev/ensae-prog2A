"""Lecture et écriture des données brutes sur le S3 du SSP Cloud.

Fonctions communes aux trois collectes (BODACC, bilans INPI, SIRENE).
Les chemins S3 sont définis dans config.py.
"""

import os

import pandas as pd
import s3fs

import config


def ouvrir_connexion_s3():
    """Ouvre une connexion au stockage S3 du SSP Cloud.

    Les clés d'accès sont lues dans les variables d'environnement
    que le SSP Cloud crée à chaque lancement de service : aucun secret dans le code.
    Sortie : un objet s3fs qui s'utilise comme un disque (open, ls, rm).
    """
    if "AWS_S3_ENDPOINT" not in os.environ:
        raise ValueError("variables S3 absentes : lancer ce code sur un service SSP Cloud")
    # s3fs lit seul AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY et AWS_SESSION_TOKEN
    return s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": "https://" + os.environ["AWS_S3_ENDPOINT"]}
    )


def sauvegarder_parquet_s3(df, chemin_s3):
    """Enregistre un DataFrame en parquet sur S3, dans son propre bucket.

    Entrées : le DataFrame et un chemin "bucket/dossier/fichier.parquet".
    """
    stockage = ouvrir_connexion_s3()
    with stockage.open(chemin_s3, "wb") as fichier:  # "wb" : écriture binaire
        df.to_parquet(fichier, index=False)
    print(f"Enregistré sur S3 : {chemin_s3} ({len(df)} lignes)")


def lire_parquet_s3(chemin_s3):
    """Lit un fichier parquet du dossier diffusion/ d'un bucket, sans clé.

    Fonctionne pour le bucket de n'importe quel membre du groupe,
    et pour le correcteur, puisque le dossier diffusion/ est en lecture publique.
    """
    url = f"{config.URL_PUBLIQUE_S3}/{chemin_s3}"
    return pd.read_parquet(url)
