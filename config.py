"""Paramètres du projet : URL des sources, stockage S3, période d'étude, seuils.

Toutes les valeurs du projet qui pourraient changer sont réunies ici,
pour ne jamais les écrire en dur dans le code de src/.
"""

# --- Sources de données (vérifiées à l'étape 1, octobre 2026) ---

# API OpenDataSoft du BODACC, jeu des annonces commerciales.
# "records" renvoie au plus 10 000 résultats (offset + limit) ;
# "exports" renvoie tout le résultat filtré d'un coup, sans cette limite.
URL_BODACC = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/annonces-commerciales/records"
)
URL_BODACC_EXPORT_PARQUET = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/annonces-commerciales/exports/parquet"
)

# Données financières détaillées INPI (Signaux Faibles), parquet de 2,8 Go.
# Lien stable data.gouv.fr : il redirige toujours vers la dernière version.
URL_BILANS_INPI = (
    "https://www.data.gouv.fr/api/1/datasets/r/c4ac8f98-2c97-4417-9070-0cbb9de03875"
)

# Ratios financiers BCE/INPI par entreprise, sur data.economie.gouv.fr
URL_RATIOS_BCE_INPI = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/ratios_inpi_bce/records"
)

# Percentiles sectoriels des ratios (par classe NAF, tranche de CA et exercice)
URL_RATIOS_SECTORIELS = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/ratios_inpi_bce_sectors/records"
)

# Stock SIRENE des unités légales, parquet de 700 Mo.
# Lien stable data.gouv.fr (le fichier daté change chaque mois).
URL_SIRENE = (
    "https://www.data.gouv.fr/api/1/datasets/r/350182c9-148a-46e0-8389-76c2ec1374a3"
)

# Stock SIRENE des établissements, parquet de 2,2 Go (44 millions de lignes).
# Contient la commune (codeCommuneEtablissement) ; etablissementSiege repère le siège.
URL_SIRENE_ETABLISSEMENTS = (
    "https://www.data.gouv.fr/api/1/datasets/r/a29c1297-1f92-4e2a-8f6b-8c902ce96c5f"
)

# API BDM de l'INSEE (accès libre, sans clé), réponse au format XML
URL_INSEE_BDM = "https://api.insee.fr/series/BDM/data/SERIES_BDM/"
# Série trimestrielle : défaillances d'entreprises par date de jugement, France
IDBANK_DEFAILLANCES = "001656164"

# --- Stockage S3 du SSP Cloud (option A : chacun son bucket) ---

# Un bucket porte le nom de l'identifiant SSP Cloud de son propriétaire.
# On ne peut écrire que dans son propre bucket : chacun y range les données
# qu'il collecte. Lignes volontairement séparées : chacun modifie la sienne
# sans créer de conflit Git avec les autres.

BUCKET_LUCAS = "poignantlucas20"  # étape 2 : BODACC

BUCKET_OLIVIER = "a-completer"  # étape 3 : bilans INPI

BUCKET_CLAUDIA = "a-completer"  # étape 4 : SIRENE et contexte

# Le dossier diffusion/ d'un bucket est lisible par les autres utilisateurs
# du SSP Cloud (camarades, correcteur), sans clé, via URL_PUBLIQUE_S3.
DOSSIER_PROJET = "diffusion/faillites-signaux"
URL_PUBLIQUE_S3 = "https://minio.lab.sspcloud.fr"

# Chemins des données brutes sur S3 : "bucket/dossier/fichier"
CHEMIN_S3_BODACC = f"{BUCKET_LUCAS}/{DOSSIER_PROJET}/bodacc"
CHEMIN_S3_BILANS = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/bilans_inpi"
CHEMIN_S3_SIRENE = f"{BUCKET_CLAUDIA}/{DOSSIER_PROJET}/sirene"
CHEMIN_S3_CONTEXTE = f"{BUCKET_CLAUDIA}/{DOSSIER_PROJET}/contexte"

# --- Période d'étude (décision des étudiants, après l'étape 1) ---

ANNEE_DEBUT_JUGEMENTS = None  # À décider avant l'étape 5
ANNEE_FIN_JUGEMENTS = None  # À décider avant l'étape 5

# --- Années de collecte (plus larges que la période d'étude) ---

# BODACC, années de parution des annonces. On collecte large pour ne pas
# trancher trop tôt la période d'étude :
# - avant 2020 : repérer les entreprises déjà en procédure (premier jugement) ;
# - 2025 : les jugements de fin 2024 sont souvent publiés début 2025.
ANNEE_DEBUT_COLLECTE_BODACC = 2017
ANNEE_FIN_COLLECTE_BODACC = 2025

# --- Seuils et paramètres d'analyse ---

# Winsorisation des ratios aux 1er et 99e percentiles
QUANTILE_BAS = 0.01
QUANTILE_HAUT = 0.99

# Graine du tirage aléatoire des témoins (reproductibilité)
GRAINE_ALEATOIRE = 2026
