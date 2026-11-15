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

BUCKET_OLIVIER = "ocaffier"  # étape 3 : bilans INPI

BUCKET_CLAUDIA = "a-completer"  # étapes 6, 9 et 13

# Le dossier diffusion/ d'un bucket est lisible par les autres utilisateurs
# du SSP Cloud (camarades, correcteur), sans clé, via URL_PUBLIQUE_S3.
DOSSIER_PROJET = "diffusion/faillites-signaux"
URL_PUBLIQUE_S3 = "https://minio.lab.sspcloud.fr"

# Chemins des données brutes sur S3 : "bucket/dossier/fichier"
CHEMIN_S3_BODACC = f"{BUCKET_LUCAS}/{DOSSIER_PROJET}/bodacc"
CHEMIN_S3_BILANS = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/bilans_inpi"
# Étape 4 réattribuée à Olivier : SIRENE et contexte sont dans son bucket
CHEMIN_S3_SIRENE = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/sirene"
CHEMIN_S3_CONTEXTE = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/contexte"

# Données nettoyées (étape 5) : bilans harmonisés avec leurs ratios
CHEMIN_S3_BILANS_RATIOS = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/bilans_ratios"

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

# Bilans INPI, années de clôture des exercices. Pour un jugement début 2020,
# le bilan N-4 peut dater de 2015 ; on filtrera à l'étape 5.
ANNEE_DEBUT_COLLECTE_BILANS = 2015
ANNEE_FIN_COLLECTE_BILANS = 2025

# --- Postes de liasse extraits des bilans INPI (étape 3) ---

# Liste provisoire, à valider avec Lucas avant l'étape 5.
# Les bilans complets (C) et simplifiés (S) n'utilisent pas les mêmes codes :
# l'harmonisation entre les deux se fait à l'étape 5.
CODES_LIASSE_C = [
    "FL",  # chiffre d'affaires net
    "FR",  # total des produits d'exploitation
    "GG",  # résultat d'exploitation
    "HN",  # résultat net (bénéfice ou perte)
    "DL",  # capitaux propres
    "EE",  # total du bilan (passif)
    "EC",  # total des dettes
    "DU",  # emprunts auprès des établissements de crédit
    "CF",  # disponibilités
    "GA",  # dotations aux amortissements
    "FY",  # salaires et traitements
    "FZ",  # charges sociales
]
CODES_LIASSE_S = [
    "210",  # ventes de marchandises
    "214",  # production vendue de biens
    "218",  # production vendue de services
    "232",  # total des produits d'exploitation
    "270",  # résultat d'exploitation
    "310",  # résultat net (bénéfice ou perte)
    "142",  # capitaux propres
    "180",  # total du bilan (passif)
    "176",  # total des dettes
    "156",  # emprunts et dettes assimilées
    # Pas de code pour les disponibilités : les bilans S du fichier ne donnent,
    # à l'actif, que les totaux (110, 112, 110-112).
    "254",  # dotations aux amortissements
    "250",  # rémunérations du personnel
    "252",  # charges sociales
]

# --- Collecte SIRENE (étape 4) ---

# On garde les unités légales actives et celles cessées depuis cette date :
# une entreprise défaillante est souvent cessée aujourd'hui, il ne faut pas l'exclure.
DATE_MIN_CESSATION_SIRENE = "2015-01-01"

# Sections de la NAF rév. 2 (A à U) : chaque section regroupe des divisions,
# c'est-à-dire les 2 premiers chiffres du code NAF (47.11F -> division 47 -> section G).
# Source : nomenclature NAF rév. 2 de l'INSEE.
# Format : (section, première division, dernière division, libellé court)
SECTIONS_NAF = [
    ("A", 1, 3, "Agriculture, sylviculture et pêche"),
    ("B", 5, 9, "Industries extractives"),
    ("C", 10, 33, "Industrie manufacturière"),
    ("D", 35, 35, "Électricité, gaz, vapeur et air conditionné"),
    ("E", 36, 39, "Eau, assainissement, déchets et dépollution"),
    ("F", 41, 43, "Construction"),
    ("G", 45, 47, "Commerce, réparation d'automobiles et de motocycles"),
    ("H", 49, 53, "Transports et entreposage"),
    ("I", 55, 56, "Hébergement et restauration"),
    ("J", 58, 63, "Information et communication"),
    ("K", 64, 66, "Activités financières et d'assurance"),
    ("L", 68, 68, "Activités immobilières"),
    ("M", 69, 75, "Activités spécialisées, scientifiques et techniques"),
    ("N", 77, 82, "Services administratifs et de soutien"),
    ("O", 84, 84, "Administration publique"),
    ("P", 85, 85, "Enseignement"),
    ("Q", 86, 88, "Santé humaine et action sociale"),
    ("R", 90, 93, "Arts, spectacles et activités récréatives"),
    ("S", 94, 96, "Autres activités de services"),
    ("T", 97, 98, "Activités des ménages"),
    ("U", 99, 99, "Activités extra-territoriales"),
]

# --- Nettoyage des bilans (étape 5) ---

# Types de bilan gardés : complet (C) et simplifié (S). Les bilans consolidés (K)
# décrivent un groupe entier : les garder ferait compter deux fois les mêmes entreprises.
TYPES_BILAN_GARDES = ["C", "S"]

# Statut des comptes, regroupé en deux modalités (partie 5 : silence comptable)
STATUTS_COMPTES = {
    "Public": "public",
    "Publication simplifiee": "public",
    "Partiellement confidentiel": "confidentiel",
    "Partiellement confidentiel (RAPCAC)": "confidentiel",
}

# Codes de détail pour lesquels une valeur absente d'un compte public vaut 0
# (pas d'emprunt, pas de salarié...). Les totaux absents restent NULL (inconnus).
CODES_ABSENTS_A_ZERO = [
    "DU", "CF", "GA", "FY", "FZ",  # bilans C
    "210", "214", "218", "156", "254", "250", "252",  # bilans S
]

# Passage des codes de liasse à un poste commun aux bilans C et S.
# Format : nom du poste -> (codes C à additionner, codes S à additionner)
CORRESPONDANCE_POSTES = {
    "chiffre_affaires": (["FL"], ["210", "214", "218"]),
    "produits_exploitation": (["FR"], ["232"]),
    "resultat_exploitation": (["GG"], ["270"]),
    "resultat_net": (["HN"], ["310"]),
    "capitaux_propres": (["DL"], ["142"]),
    "total_bilan": (["EE"], ["180"]),
    "dettes_totales": (["EC"], ["176"]),
    "emprunts": (["DU"], ["156"]),
    "disponibilites": (["CF"], []),  # pas de code en S : reste NULL pour les bilans S
    "dotations_amortissements": (["GA"], ["254"]),
    "charges_personnel": (["FY", "FZ"], ["250", "252"]),
}

# --- Seuils et paramètres d'analyse ---

# Winsorisation des ratios aux 1er et 99e percentiles
QUANTILE_BAS = 0.01
QUANTILE_HAUT = 0.99

# Graine du tirage aléatoire des témoins (reproductibilité)
GRAINE_ALEATOIRE = 2026
