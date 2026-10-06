"""Paramètres du projet : URL des sources, stockage S3, période d'étude, seuils.

Toutes les valeurs du projet qui pourraient changer sont réunies ici,
pour ne jamais les écrire en dur dans le code de src/.
"""

# --- Sources de données (à vérifier à l'étape 1) ---

# API OpenDataSoft du BODACC, jeu des annonces commerciales
URL_BODACC = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/annonces-commerciales/records"
)

# Données financières détaillées INPI (Signaux Faibles), parquet sur data.gouv.fr
URL_BILANS_INPI = None  # À trouver à l'étape 1

# Ratios financiers BCE/INPI sur data.economie.gouv.fr
URL_RATIOS_BCE_INPI = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/ratios_inpi_bce/records"
)

# Stock SIRENE des unités légales, parquet sur data.gouv.fr
URL_SIRENE = (
    "https://object.files.data.gouv.fr/data-pipeline-open"
    "/siren/stock/StockUniteLegale_utf8.parquet"
)

# --- Stockage S3 du SSP Cloud ---

# Nom du bucket (identifiant SSP Cloud du membre qui héberge les données)
BUCKET_S3 = "a-completer"
DOSSIER_S3 = "faillites-signaux"

# --- Période d'étude (décision des étudiants, après l'étape 1) ---

ANNEE_DEBUT_JUGEMENTS = None  # À décider après l'étape 1
ANNEE_FIN_JUGEMENTS = None  # À décider après l'étape 1

# --- Seuils et paramètres d'analyse ---

# Winsorisation des ratios aux 1er et 99e percentiles
QUANTILE_BAS = 0.01
QUANTILE_HAUT = 0.99

# Graine du tirage aléatoire des témoins (reproductibilité)
GRAINE_ALEATOIRE = 2026
