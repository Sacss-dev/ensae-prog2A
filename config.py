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

BUCKET_CLAUDIA = "claudia"  # étapes 6, 9 et 13

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
# Données nettoyées (étape 5) : premier jugement d'ouverture de chaque SIREN
CHEMIN_S3_JUGEMENTS = f"{BUCKET_LUCAS}/{DOSSIER_PROJET}/jugements"

# --- Période d'étude (décision des étudiants, après l'étape 1) ---

# Années des jugements d'ouverture étudiés (bornes incluses), filtre appliqué à l'étape 6.
# - Début 2020 : le bilan N-4 date alors au plus tôt de 2016 (clôtures 2015 presque
#   absentes du fichier INPI), et on voit 3 ans de BODACC avant (2017-2019) pour
#   écarter les entreprises déjà en procédure.
# - Fin 2024 : les jugements de 2025 ne sont pas tous publiés, et leur bilan N-1
#   (clôture 2024) n'est souvent pas encore déposé.
# La période Covid (jugements 2020-2021) est gardée ; son traitement se décide à l'étape 6.
ANNEE_DEBUT_JUGEMENTS = 2020
ANNEE_FIN_JUGEMENTS = 2024

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

# --- Nettoyage du BODACC (étape 5) ---

# Types d'avis gardés : les avis initiaux. Les rectificatifs et les annulations
# reprennent ou retirent une annonce déjà publiée (risque de double compte).
TYPES_AVIS_GARDES = ["annonce"]

# Famille de jugement gardée : l'ouverture de la procédure. Les autres familles
# (conversion en liquidation, clôture, dépôt de l'état des créances...) arrivent
# après une ouverture : elles ne datent pas le début de la défaillance.
FAMILLE_OUVERTURE = "Jugement d'ouverture"

# Bornes de plausibilité de la date du jugement : en dehors, c'est une coquille
# de saisie (par exemple l'année 5202 au lieu de 2025).
ANNEE_MIN_JUGEMENT_PLAUSIBLE = 2000
ANNEE_MAX_JUGEMENT_PLAUSIBLE = ANNEE_FIN_COLLECTE_BODACC

# --- Portrait descriptif (étape 7) ---

# Champ du portrait : les sociétés commerciales (catégorie juridique 5xxx : SARL, SAS, SA...),
# soit 87 % des défaillances. Les entrepreneurs individuels, les sociétés civiles (SCI...)
# et les associations, très nombreux dans SIRENE mais presque jamais défaillants,
# écraseraient les taux et rendraient les secteurs incomparables.
PREFIXE_CATEGORIE_JURIDIQUE = "5"

# Procédures comptées comme défaillances : définition de l'INSEE et de la Banque de France.
# Les sauvegardes, ouvertes avant la cessation des paiements, n'en font pas partie.
TYPES_DEFAILLANCE = ["redressement", "liquidation"]

# Regroupement des tranches d'effectifs SIRENE (code INSEE -> classe de taille).
# NN = unité non employeuse ou effectif inconnu ; 00 = 0 salarié au 31 décembre.
GROUPES_EFFECTIFS = {
    "NN": "0 salarié ou inconnu",
    "00": "0 salarié ou inconnu",
    "01": "1 à 9 salariés",
    "02": "1 à 9 salariés",
    "03": "1 à 9 salariés",
    "11": "10 à 49 salariés",
    "12": "10 à 49 salariés",
    "21": "50 à 199 salariés",
    "22": "50 à 199 salariés",
    "31": "200 salariés et plus",
    "32": "200 salariés et plus",
    "41": "200 salariés et plus",
    "42": "200 salariés et plus",
    "51": "200 salariés et plus",
    "52": "200 salariés et plus",
    "53": "200 salariés et plus",
}
ORDRE_GROUPES_EFFECTIFS = [
    "0 salarié ou inconnu", "1 à 9 salariés", "10 à 49 salariés",
    "50 à 199 salariés", "200 salariés et plus",
]

# Effectif minimal d'un groupe (en sociétés-années) pour publier son taux :
# en dessous, quelques défaillances suffisent à faire varier fortement le taux.
SEUIL_ENTREPRISES_MIN = 10000

# Millésime du fond de carte des départements (cartiflette)
ANNEE_FOND_CARTE = 2024

# --- Seuils et paramètres d'analyse ---

# Winsorisation des ratios aux 1er et 99e percentiles
QUANTILE_BAS = 0.01
QUANTILE_HAUT = 0.99

# Graine du tirage aléatoire des témoins (reproductibilité)
GRAINE_ALEATOIRE = 2026


# --- Trajectoires des ratios (étape 8) ---
# Ratios suivis de N-4 à N-1, dans l'ordre des panneaux du graphique central
RATIOS_TRAJECTOIRES = [
    "rentabilite_nette",
    "marge_exploitation",
    "autonomie_financiere",
    "taux_endettement",
    "liquidite",
    "croissance_ca",
]
# Noms lisibles des ratios, pour les titres des graphiques et des tableaux
LIBELLES_RATIOS = {
    "rentabilite_nette": "Rentabilité nette (résultat net / CA)",
    "marge_exploitation": "Marge d'exploitation (résultat d'exploitation / CA)",
    "autonomie_financiere": "Autonomie financière (capitaux propres / total du bilan)",
    "taux_endettement": "Taux d'endettement (dettes / total du bilan)",
    "liquidite": "Liquidité (disponibilités / total du bilan, bilans complets)",
    "croissance_ca": "Croissance du chiffre d'affaires sur un an",
}
# Rangs sectoriels : position (0 à 100) de chaque bilan parmi tous les bilans
# de la même section NAF et de la même année de clôture (calculés à partir des bilans INPI)
CHEMIN_S3_RANGS_SECTORIELS = f"{BUCKET_OLIVIER}/{DOSSIER_PROJET}/rangs_sectoriels"
HORIZONS_RANGS = [1, 2]  # rangs étudiés à N-1 et N-2
# Seuil de trésorerie quasi nulle : SEUIL_TRESORERIE_FAIBLE (défini à l'étape 11), le même
# que pour les règles d'alerte, pour que les parties 3 et 6 restent cohérentes.
SOURCE_GRAPHIQUES = "BODACC, INPI (bilans), INSEE (SIRENE) ; calculs des auteurs"


# --- Hétérogénéité (étape 9) ---
# Ratios étudiés par sous-groupe : un par grande famille (rentabilité, solvabilité,
# liquidité). Liste provisoire, à ajuster selon les ratios qui décrochent le plus (étape 8).
RATIOS_HETEROGENEITE = ["rentabilite_nette", "autonomie_financiere", "liquidite"]

# Grands secteurs : regroupement des sections NAF selon la nomenclature agrégée
# de l'INSEE en 10 postes (A10). Les témoins ont la même section que leur défaillante.
GRANDS_SECTEURS = {
    "A": "Agriculture",
    "B": "Industrie", "C": "Industrie", "D": "Industrie", "E": "Industrie",
    "F": "Construction",
    "G": "Commerce, transports, hébergement-restauration",
    "H": "Commerce, transports, hébergement-restauration",
    "I": "Commerce, transports, hébergement-restauration",
    "J": "Information et communication",
    "K": "Finance et assurance",
    "L": "Immobilier",
    "M": "Services aux entreprises", "N": "Services aux entreprises",
    "O": "Administration, enseignement, santé",
    "P": "Administration, enseignement, santé",
    "Q": "Administration, enseignement, santé",
    "R": "Autres services", "S": "Autres services", "T": "Autres services", "U": "Autres services",
}

# Classes d'âge de la défaillante à la date du jugement (en années révolues)
BORNES_AGE = [0, 3, 5, 10, float("inf")]
LABELS_AGE = ["moins de 3 ans", "3 à 5 ans", "5 à 10 ans", "10 ans et plus"]

# Sous-groupes étudiés : nom de colonne -> nom lisible.
# Chaque témoin est rangé dans le sous-groupe de sa défaillante (comparaison par paire).
SOUS_GROUPES = {
    "grand_secteur": "grand secteur",
    "classe_age": "âge au jugement",
    "taille_appariement": "taille (total du bilan à l'appariement)",
    "type_procedure": "type de procédure",
}


# --- Base d'analyse et témoins (étape 6) ---
# Résultats de l'étape 6 : base des défaillantes et témoins, dans le bucket de Claudia
CHEMIN_S3_BASE_ANALYSE = f"{BUCKET_CLAUDIA}/{DOSSIER_PROJET}/base_analyse"

# Horizons étudiés : de N-1 (bilan clos dans les 12 mois avant le jugement) à N-4
HORIZON_MAX = 4
 
# Tranches de taille d'après le total du bilan (en euros), choisies avec les
# quantiles des défaillantes à N-1 (médiane d'environ 525 k€). Le total du bilan
# est connu même quand le compte de résultat (donc le CA) est confidentiel.
SEUILS_TAILLE_BILAN = [100_000, 500_000, 2_000_000]
LABELS_TAILLE_BILAN = ["moins de 100 k€", "100 k€ à 500 k€", "500 k€ à 2 M€", "plus de 2 M€"]
# Nombre de témoins tirés pour chaque entreprise défaillante
NB_TEMOINS_PAR_DEFAILLANTE = 1
# Période Covid (décision du groupe) : on garde les jugements 2020-2021, repérés par
# une colonne periode, car les aides (PGE, chômage partiel, reports de charges)
# ont rendu ces défaillances atypiques. Les graphiques seront refaits par période.
ANNEE_FIN_PERIODE_COVID = 2021
LABELS_PERIODE = ["Covid (2020-2021)", "après Covid (2022-2024)"]

# --- Règles d'alerte (étape 11) ---
# Horizons sur lesquels on évalue les règles : N-1 et N-2
HORIZONS_ALERTE = [1, 2]
# Trésorerie « quasi nulle » : disponibilités inférieures à 2 % du total du bilan.
# Le ratio liquidite n'existe que pour les bilans complets (C) : un bilan simplifié
# n'est jamais signalé par cette règle.
SEUIL_TRESORERIE_FAIBLE = 0.02
# Règle combinée : alerte si au moins ce nombre de signaux sur les trois
# (capitaux propres négatifs, trésorerie quasi nulle, perte nette)
NB_SIGNAUX_MIN = 2
# Taux annuel de défaillance des sociétés commerciales, 2020-2024 (étape 7) :
# 170 264 défaillances pour 18,7 millions de sociétés-années, soit 9,1 pour 1 000.
# Sert à estimer ce que donneraient les règles sur la population réelle.
TAUX_DEFAILLANCE_POPULATION = 0.0091
