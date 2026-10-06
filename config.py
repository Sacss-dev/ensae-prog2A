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

# API BDM de l'INSEE (accès libre, sans clé), réponse au format XML
URL_INSEE_BDM = "https://api.insee.fr/series/BDM/data/SERIES_BDM/"
# Série trimestrielle : défaillances d'entreprises par date de jugement, France
IDBANK_DEFAILLANCES = "001656164"

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
