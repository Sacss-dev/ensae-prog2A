"""Étape 5 : nettoyage des annonces BODACC.

À partir des annonces brutes de l'étape 2, on garde les jugements d'ouverture,
on en tire le type de procédure (sauvegarde, redressement, liquidation), la date
du jugement et le SIREN, puis on ne garde que le premier jugement de chaque SIREN.

La période d'étude (config.ANNEE_DEBUT_JUGEMENTS...) n'est PAS appliquée ici :
on garde toutes les années, et le filtre se fera à l'étape 6. Ainsi, changer
la période ne demandera pas de relancer ce nettoyage.

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.nettoyage.nettoyage_bodacc
"""

import json
import re

import pandas as pd

import config
from src.collecte.bodacc import lire_bodacc_brut
from src.collecte.stockage_s3 import lire_parquet_s3, sauvegarder_parquet_s3

# Colonnes du BODACC brut utiles pour la suite (le fichier brut en a 32)
COLONNES_UTILES = ["id", "dateparution", "typeavis", "registre", "numerodepartement", "tribunal", "jugement"]

# Expressions régulières qui reconnaissent le type de procédure dans la nature du jugement.
# \b = frontière de mot : "sauvegarde" doit être un mot entier.
# L'ordre compte : on prend le premier motif trouvé.
MOTIFS_PROCEDURE = [
    ("sauvegarde", r"\bsauvegarde\b"),  # y compris « sauvegarde accélérée »
    ("redressement", r"\bredressement judiciaire\b"),
    ("liquidation", r"\bliquidation judiciaire\b"),  # y compris « liquidation judiciaire simplifiée »
]

# Un SIREN = exactement 9 chiffres collés, entourés de frontières de mot.
# Dans "522 293 257,522293257", seul "522293257" correspond (l'autre a des espaces).
MOTIF_SIREN = r"\b\d{9}\b"
# SIREN bouche-trou saisi par certains greffes quand le vrai numéro manque
SIREN_FICTIF = "000000000"


def lire_jugement_json(texte_jugement):
    """Transforme le texte JSON de la colonne jugement en dictionnaire Python.

    Entrée : un texte comme '{"famille": "Jugement d\'ouverture", "nature": "...", "date": "2022-05-17"}'.
    Sortie : le dictionnaire correspondant, ou un dictionnaire vide si le texte est absent.
    """
    if pd.isna(texte_jugement):
        return {}
    return json.loads(texte_jugement)


def extraire_champs_jugement(df_annonces):
    """Ajoute trois colonnes tirées du JSON jugement : famille, nature et date (encore en texte)."""
    liste_jugements = []
    for texte_jugement in df_annonces["jugement"]:
        liste_jugements.append(lire_jugement_json(texte_jugement))
    # Une ligne par annonce, une colonne par clé du JSON (absente -> NaN)
    df_jugements = pd.DataFrame(liste_jugements, index=df_annonces.index)
    df_annonces["famille_jugement"] = df_jugements["famille"]
    df_annonces["nature_jugement"] = df_jugements["nature"]
    df_annonces["date_jugement_texte"] = df_jugements["date"]
    return df_annonces


def garder_ouvertures(df_annonces):
    """Garde les avis initiaux (pas les rectificatifs ni les annulations) qui sont des ouvertures."""
    est_avis_garde = df_annonces["typeavis"].isin(config.TYPES_AVIS_GARDES)
    est_ouverture = df_annonces["famille_jugement"] == config.FAMILLE_OUVERTURE
    return df_annonces[est_avis_garde & est_ouverture].copy()


def classer_procedure(nature_jugement):
    """Renvoie le type de procédure (sauvegarde, redressement, liquidation) lu dans la nature.

    Renvoie "autre" si aucun motif ne correspond (ex. « Autre jugement d'ouverture »).
    """
    if pd.isna(nature_jugement):
        return "autre"
    for type_procedure, motif in MOTIFS_PROCEDURE:
        # re.IGNORECASE : majuscules et minuscules sont traitées pareil
        if re.search(motif, nature_jugement, flags=re.IGNORECASE):
            return type_procedure
    return "autre"


def ajouter_type_procedure(df_ouvertures):
    """Ajoute la colonne type_procedure et retire les ouvertures de type « autre »."""
    df_ouvertures["type_procedure"] = df_ouvertures["nature_jugement"].apply(classer_procedure)
    return df_ouvertures[df_ouvertures["type_procedure"] != "autre"].copy()


def ajouter_date_jugement(df_ouvertures):
    """Convertit la date du jugement en vraie date et retire les dates absentes ou aberrantes.

    Une date qui n'a pas le format AAAA-MM-JJ devient NaT (errors="coerce"), puis est retirée.
    """
    df_ouvertures["date_jugement"] = pd.to_datetime(
        df_ouvertures["date_jugement_texte"], format="%Y-%m-%d", errors="coerce"
    )
    annee = df_ouvertures["date_jugement"].dt.year
    est_plausible = annee.between(config.ANNEE_MIN_JUGEMENT_PLAUSIBLE, config.ANNEE_MAX_JUGEMENT_PLAUSIBLE)
    df_ouvertures = df_ouvertures[est_plausible].copy()  # une date NaT n'est pas plausible
    df_ouvertures["annee_jugement"] = df_ouvertures["date_jugement"].dt.year
    return df_ouvertures


def extraire_sirens(registre):
    """Renvoie la liste des SIREN distincts cités dans le champ registre.

    Entrée : un texte comme "522 293 257,522293257". Sortie : ["522293257"].
    Une annonce peut viser plusieurs entreprises (procédure commune) : plusieurs SIREN.
    """
    if pd.isna(registre):
        return []
    liste_sirens = []
    for siren in re.findall(MOTIF_SIREN, registre):
        # sans doublon, dans l'ordre d'apparition, et sans le SIREN fictif
        if siren not in liste_sirens and siren != SIREN_FICTIF:
            liste_sirens.append(siren)
    return liste_sirens


def ajouter_siren(df_ouvertures):
    """Ajoute la colonne siren : une ligne par entreprise visée ; retire les annonces sans SIREN."""
    df_ouvertures["siren"] = df_ouvertures["registre"].apply(extraire_sirens)
    # explode : une annonce qui cite 2 SIREN devient 2 lignes ; une liste vide devient NaN
    df_ouvertures = df_ouvertures.explode("siren")
    return df_ouvertures[df_ouvertures["siren"].notna()].reset_index(drop=True)


def garder_premier_jugement(df_ouvertures):
    """Garde, pour chaque SIREN, le jugement d'ouverture le plus ancien.

    À date égale (même jugement publié deux fois), on garde la première parution.
    """
    colonnes_tri = ["siren", "date_jugement", "dateparution"]
    df_ouvertures = df_ouvertures.sort_values(colonnes_tri)
    df_premiers = df_ouvertures.drop_duplicates(subset="siren", keep="first")
    return df_premiers.reset_index(drop=True)


def mettre_en_forme(df_premiers):
    """Garde et renomme les colonnes utiles pour la suite du projet."""
    df_premiers = df_premiers.rename(columns={
        "id": "id_annonce",
        "dateparution": "date_parution",
        "numerodepartement": "departement_tribunal",
    })
    df_premiers["date_parution"] = pd.to_datetime(df_premiers["date_parution"])  # même type que date_jugement
    colonnes_finales = [
        "siren", "date_jugement", "annee_jugement", "type_procedure", "nature_jugement",
        "date_parution", "departement_tribunal", "tribunal", "id_annonce",
    ]
    return df_premiers[colonnes_finales]


def compter_par_annee_et_type(df_premiers):
    """Tableau de validation : nombre de premiers jugements par année et par type de procédure."""
    return pd.crosstab(df_premiers["annee_jugement"], df_premiers["type_procedure"], margins=True, margins_name="total")


def comparer_avec_insee(df_premiers):
    """Compare, par année, nos redressements et liquidations à la série INSEE des défaillances.

    L'INSEE compte les ouvertures de redressement et de liquidation (pas les sauvegardes),
    par date de jugement. Sortie : une ligne par année, avec le rapport bodacc / insee.
    """
    df_insee = lire_parquet_s3(config.CHEMIN_S3_CONTEXTE + "/defaillances_insee.parquet")
    df_insee["annee_jugement"] = df_insee["periode"].str[:4].astype(int)  # "2024-Q3" -> 2024
    df_insee = df_insee.groupby("annee_jugement")["nombre_defaillances"].sum()
    est_defaillance = df_premiers["type_procedure"].isin(["redressement", "liquidation"])
    df_bodacc = df_premiers[est_defaillance].groupby("annee_jugement").size()
    df_comparaison = pd.DataFrame({"bodacc": df_bodacc, "insee": df_insee}).dropna()
    # Avant la première année collectée, le BODACC ne contient que des jugements publiés en retard
    df_comparaison = df_comparaison[df_comparaison.index >= config.ANNEE_DEBUT_COLLECTE_BODACC].copy()
    df_comparaison["rapport_bodacc_insee"] = (df_comparaison["bodacc"] / df_comparaison["insee"]).round(2)
    return df_comparaison.astype({"bodacc": int, "insee": int})


def nettoyer_bodacc(sauvegarder=True):
    """Enchaîne toutes les étapes du nettoyage et affiche le tableau en entonnoir.

    sauvegarder=False : n'écrit rien sur S3 (utile pour tester sans clé S3).
    """
    df_annonces = lire_bodacc_brut(COLONNES_UTILES)
    entonnoir = [("annonces brutes (procédures collectives)", len(df_annonces))]
    df_annonces = extraire_champs_jugement(df_annonces)
    df_ouvertures = garder_ouvertures(df_annonces)
    entonnoir.append(("avis initiaux de jugement d'ouverture", len(df_ouvertures)))
    df_ouvertures = ajouter_type_procedure(df_ouvertures)
    entonnoir.append(("type de procédure reconnu", len(df_ouvertures)))
    df_ouvertures = ajouter_date_jugement(df_ouvertures)
    entonnoir.append(("date de jugement plausible", len(df_ouvertures)))
    df_ouvertures = ajouter_siren(df_ouvertures)
    entonnoir.append(("couples (annonce, SIREN)", len(df_ouvertures)))
    df_premiers = mettre_en_forme(garder_premier_jugement(df_ouvertures))
    entonnoir.append(("SIREN distincts (premier jugement)", len(df_premiers)))
    print(pd.DataFrame(entonnoir, columns=["étape", "nombre de lignes"]).to_string(index=False))
    if sauvegarder:
        sauvegarder_parquet_s3(df_premiers, config.CHEMIN_S3_JUGEMENTS + "/premiers_jugements.parquet")
    return df_premiers


if __name__ == "__main__":
    df_premiers_jugements = nettoyer_bodacc()
    print(compter_par_annee_et_type(df_premiers_jugements).to_string())
    print(comparer_avec_insee(df_premiers_jugements).to_string())
