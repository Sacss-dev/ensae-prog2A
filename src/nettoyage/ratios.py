"""Étape 5 : nettoyage des bilans INPI et calcul des ratios financiers.

Étapes : lecture de l'extrait brut (étape 3), filtres (types de bilan, doublons),
statut des comptes, valeurs absentes, harmonisation des postes C et S,
calcul des ratios, winsorisation, puis enregistrement sur S3.

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.nettoyage.ratios
"""

import pandas as pd

import config
from src.collecte.stockage_s3 import lire_parquet_s3, sauvegarder_parquet_s3

COLONNES_RATIOS = [
    "rentabilite_nette",
    "marge_exploitation",
    "autonomie_financiere",
    "taux_endettement",
    "liquidite",
    "croissance_ca",
]


def lire_bilans_bruts():
    """Relit depuis S3 (sans clé) l'extrait des bilans produit à l'étape 3."""
    return lire_parquet_s3(config.CHEMIN_S3_BILANS + "/bilans.parquet")


def convertir_postes_en_decimaux(df_bilans):
    """Convertit les colonnes poste_<code> en nombres décimaux (float64).

    Selon la version de pandas, les postes sont lus en entiers Int32 avec valeurs
    manquantes : additionner ces colonnes donne des Int64, que pandas refuse ensuite
    de mélanger avec des Int32. En float64, un poste absent vaut simplement NaN.
    """
    for colonne in df_bilans.columns:
        if colonne.startswith("poste_"):
            df_bilans[colonne] = df_bilans[colonne].astype("float64")
    return df_bilans


def filtrer_bilans(df_bilans):
    """Garde les types de bilan retenus et un seul bilan par entreprise et par année.

    En cas de doublon (même SIREN, même année de clôture), on garde le bilan
    le plus complet (nombre_postes), puis le plus récent.
    """
    df_filtre = df_bilans[df_bilans["type_bilan"].isin(config.TYPES_BILAN_GARDES)].copy()
    df_filtre["annee_cloture"] = df_filtre["date_cloture_exercice"].dt.year
    colonnes_tri = ["siren", "annee_cloture", "nombre_postes", "date_cloture_exercice"]
    df_filtre = df_filtre.sort_values(colonnes_tri)
    # keep="last" : après le tri, le dernier est le plus complet puis le plus récent
    df_filtre = df_filtre.drop_duplicates(subset=["siren", "annee_cloture"], keep="last")
    return df_filtre.reset_index(drop=True)


def ajouter_statut_comptes(df_bilans):
    """Ajoute la colonne statut_comptes : "public" ou "confidentiel" (partie 5)."""
    df_bilans["statut_comptes"] = df_bilans["confidentiality"].map(config.STATUTS_COMPTES)
    return df_bilans


def remplacer_absents_par_zero(df_bilans):
    """Remplace par 0 les postes de détail absents, uniquement dans les comptes publics.

    Dans un compte public, un poste de détail absent veut dire « rien » (pas d'emprunt...).
    Dans un compte confidentiel, il veut dire « inconnu » : on laisse NULL.
    """
    est_public = df_bilans["statut_comptes"] == "public"
    for code in config.CODES_ABSENTS_A_ZERO:
        colonne = f"poste_{code}"
        # Un code C ne concerne que les bilans C, un code S que les bilans S
        if code in config.CODES_LIASSE_C:
            type_concerne = "C"
        else:
            type_concerne = "S"
        a_remplacer = est_public & (df_bilans["type_bilan"] == type_concerne) & df_bilans[colonne].isna()
        df_bilans.loc[a_remplacer, colonne] = 0
    return df_bilans


def sommer_postes(df_bilans, liste_codes):
    """Additionne les colonnes poste_<code> d'une liste de codes, ligne par ligne.

    Renvoie NULL si tous les codes sont absents (min_count=1), ou si la liste est vide.
    """
    if len(liste_codes) == 0:
        return pd.Series(float("nan"), index=df_bilans.index)
    colonnes = []
    for code in liste_codes:
        colonnes.append(f"poste_{code}")
    return df_bilans[colonnes].sum(axis=1, min_count=1)


def harmoniser_postes(df_bilans):
    """Crée une colonne par poste commun (chiffre_affaires...), que le bilan soit C ou S."""
    est_bilan_c = df_bilans["type_bilan"] == "C"
    for nom_poste, (codes_c, codes_s) in config.CORRESPONDANCE_POSTES.items():
        valeur_c = sommer_postes(df_bilans, codes_c)
        valeur_s = sommer_postes(df_bilans, codes_s)
        # where : garde la valeur C sur les bilans C, et prend la valeur S ailleurs
        df_bilans[nom_poste] = valeur_c.where(est_bilan_c, valeur_s)
    return df_bilans


def diviser(numerateur, denominateur):
    """Divise deux colonnes ; NULL si le dénominateur est nul ou négatif (ratio sans sens)."""
    return numerateur / denominateur.where(denominateur > 0)


def calculer_ratios(df_bilans):
    """Calcule les ratios de rentabilité, de solvabilité, d'endettement et de liquidité."""
    df_bilans["rentabilite_nette"] = diviser(df_bilans["resultat_net"], df_bilans["chiffre_affaires"])
    df_bilans["marge_exploitation"] = diviser(df_bilans["resultat_exploitation"], df_bilans["chiffre_affaires"])
    df_bilans["autonomie_financiere"] = diviser(df_bilans["capitaux_propres"], df_bilans["total_bilan"])
    df_bilans["taux_endettement"] = diviser(df_bilans["dettes_totales"], df_bilans["total_bilan"])
    df_bilans["liquidite"] = diviser(df_bilans["disponibilites"], df_bilans["total_bilan"])  # bilans C seulement
    return df_bilans


def calculer_croissance_ca(df_bilans):
    """Calcule la croissance du chiffre d'affaires par rapport au bilan de l'année précédente.

    NULL si l'entreprise n'a pas de bilan l'année juste avant (trou d'un an ou plus).
    """
    df_bilans = df_bilans.sort_values(["siren", "annee_cloture"]).reset_index(drop=True)
    # shift(1) par entreprise : valeur du bilan précédent du même SIREN
    ca_precedent = df_bilans.groupby("siren")["chiffre_affaires"].shift(1)
    annee_precedente = df_bilans.groupby("siren")["annee_cloture"].shift(1)
    croissance = diviser(df_bilans["chiffre_affaires"], ca_precedent) - 1
    annees_consecutives = df_bilans["annee_cloture"] - annee_precedente == 1
    df_bilans["croissance_ca"] = croissance.where(annees_consecutives)
    return df_bilans


def winsoriser(df_bilans, liste_colonnes):
    """Ramène les valeurs extrêmes de chaque colonne aux quantiles choisis dans config.py.

    Les quantiles sont calculés sur toutes les années ensemble.
    """
    for colonne in liste_colonnes:
        borne_basse = df_bilans[colonne].quantile(config.QUANTILE_BAS)
        borne_haute = df_bilans[colonne].quantile(config.QUANTILE_HAUT)
        df_bilans[colonne] = df_bilans[colonne].clip(lower=borne_basse, upper=borne_haute)
    return df_bilans


def resumer_ratios(df_bilans):
    """Tableau de contrôle : nombre de valeurs connues et médiane de chaque ratio, par type de bilan."""
    df_resume = df_bilans.groupby("type_bilan")[COLONNES_RATIOS].agg(["count", "median"])
    return df_resume.round(3).T  # une ligne par (ratio, indicateur), une colonne par type


def nettoyer_bilans():
    """Enchaîne toutes les étapes du nettoyage, enregistre le résultat sur S3 et l'affiche."""
    df_bilans = lire_bilans_bruts()
    print(f"Bilans bruts : {len(df_bilans)}")
    df_bilans = convertir_postes_en_decimaux(df_bilans)
    df_bilans = filtrer_bilans(df_bilans)
    print(f"Après filtres (types {config.TYPES_BILAN_GARDES}, un bilan par an) : {len(df_bilans)}")
    df_bilans = ajouter_statut_comptes(df_bilans)
    df_bilans = remplacer_absents_par_zero(df_bilans)
    df_bilans = harmoniser_postes(df_bilans)
    df_bilans = calculer_ratios(df_bilans)
    df_bilans = calculer_croissance_ca(df_bilans)
    df_bilans = winsoriser(df_bilans, COLONNES_RATIOS)
    sauvegarder_parquet_s3(df_bilans, config.CHEMIN_S3_BILANS_RATIOS + "/bilans_ratios.parquet")
    print(resumer_ratios(df_bilans).to_string())
    return df_bilans


if __name__ == "__main__":
    nettoyer_bilans()
