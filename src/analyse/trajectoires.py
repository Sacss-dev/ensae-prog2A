"""Étape 8 (partie 3 du rapport) : trajectoires des ratios de N-4 à N-1.

- Quartiles (1er quartile, médiane, 3e quartile) de chaque ratio, par groupe
  (défaillantes, témoins) et par horizon, éventuellement par sous-groupe (étape 9).
- Rangs sectoriels : position (0 à 100) de chaque bilan parmi tous les bilans INPI
  de la même section NAF et de la même année de clôture.
- Situations extrêmes : capitaux propres négatifs, trésorerie quasi nulle.

Calcul des rangs sectoriels (une seule fois, sur le SSP Cloud), depuis la racine du dépôt :
    python -m src.analyse.trajectoires
"""

import pandas as pd

import config
from src.analyse.graphiques import tracer_trajectoires
from src.collecte.stockage_s3 import (
    construire_url_publique,
    lire_parquet_s3,
    ouvrir_connexion_duckdb,
    sauvegarder_parquet_s3,
)


def lire_base_appariee(colonnes=None):
    """Relit depuis S3 (sans clé) la base appariée de l'étape 6 : défaillantes et témoins.

    colonnes : liste des colonnes à garder (None = toutes), pour économiser la mémoire.
    Sortie : une ligne par couple (entreprise, horizon), de N-1 à N-4.
    """
    return lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/base_appariee.parquet", colonnes)


def garder_entreprises_completes(df_base):
    """Garde les entreprises qui ont un bilan à chacun des horizons N-1 à N-4.

    Sert de vérification : on suit alors exactement les mêmes entreprises d'un
    horizon à l'autre, au lieu d'une population qui change.
    """
    nombre_horizons = df_base.groupby("siren")["horizon"].nunique()
    siren_complets = nombre_horizons[nombre_horizons == config.HORIZON_MAX].index
    return df_base[df_base["siren"].isin(siren_complets)]


def calculer_quartiles(df_base, liste_colonnes, colonnes_groupes):
    """Calcule 1er quartile, médiane, 3e quartile et nombre de valeurs connues.

    Entrées : la base, les colonnes à résumer (ratios ou rangs) et les colonnes
    qui définissent les groupes, par exemple ["groupe"] ou ["periode", "groupe"].
    Sortie : une ligne par (groupes, horizon, ratio).
    """
    liste_resultats = []
    for colonne in liste_colonnes:
        valeurs_groupees = df_base.groupby(colonnes_groupes + ["horizon"])[colonne]
        df_stats = valeurs_groupees.quantile([0.25, 0.5, 0.75]).unstack()  # une colonne par quantile
        df_stats.columns = ["q1", "mediane", "q3"]
        df_stats["nombre"] = valeurs_groupees.count()  # valeurs connues (hors NULL)
        df_stats["ratio"] = colonne
        liste_resultats.append(df_stats.reset_index())
    return pd.concat(liste_resultats, ignore_index=True)


def presenter_medianes(df_quartiles, colonnes_groupes):
    """Tableau lisible des médianes : une ligne par ratio, une colonne par (groupes, horizon)."""
    return df_quartiles.pivot_table(
        index="ratio", columns=colonnes_groupes + ["horizon"], values="mediane", sort=False
    )


def tracer_trajectoires_par_periode(df_base, liste_colonnes, titre, en_pourcentage=True):
    """Trace un graphique de trajectoires par période (Covid, après Covid).

    Sortie : un dictionnaire période -> figure.
    """
    df_quartiles = calculer_quartiles(df_base, liste_colonnes, ["periode", "groupe"])
    figures = {}
    for periode in config.LABELS_PERIODE:
        df_periode = df_quartiles[df_quartiles["periode"] == periode]
        titre_complet = f"{titre} – jugements {periode}"
        fig, _ = tracer_trajectoires(
            df_periode, config.LIBELLES_RATIOS, titre_complet, config.SOURCE_GRAPHIQUES, en_pourcentage
        )
        figures[periode] = fig
    return figures


def marquer_situations_extremes(df_base):
    """Ajoute deux indicateurs (1 = oui, 0 = non, NULL = inconnu).

    - capitaux_propres_negatifs : capitaux propres < 0 ;
    - tresorerie_quasi_nulle : liquidité sous le seuil de l'étape 11 (bilans C seulement).
    """
    capitaux_negatifs = (df_base["capitaux_propres"] < 0).astype(float)
    df_base["capitaux_propres_negatifs"] = capitaux_negatifs.where(df_base["capitaux_propres"].notna())
    tresorerie_faible = (df_base["liquidite"] < config.SEUIL_TRESORERIE_FAIBLE).astype(float)
    df_base["tresorerie_quasi_nulle"] = tresorerie_faible.where(df_base["liquidite"].notna())
    return df_base


def compter_situations_extremes(df_base, colonnes_groupes):
    """Part (en %) des entreprises en situation extrême, par groupes et par horizon.

    La part est calculée parmi les entreprises dont l'indicateur est connu.
    """
    df_marque = marquer_situations_extremes(df_base.copy())
    indicateurs = ["capitaux_propres_negatifs", "tresorerie_quasi_nulle"]
    df_parts = df_marque.groupby(colonnes_groupes + ["horizon"])[indicateurs].mean() * 100
    return df_parts.round(1).unstack(colonnes_groupes)  # une colonne par groupe


def creer_table_population(connexion):
    """Charge dans DuckDB tous les bilans nettoyés (étape 5), avec leur section NAF (SIRENE).

    La table est créée une seule fois puis réutilisée pour chaque ratio :
    on ne lit qu'une fois les fichiers en ligne.
    """
    url_bilans = construire_url_publique(config.CHEMIN_S3_BILANS_RATIOS + "/bilans_ratios.parquet")
    url_sirene = construire_url_publique(config.CHEMIN_S3_SIRENE + "/sirene.parquet")
    colonnes_ratios = ", ".join(config.RATIOS_TRAJECTOIRES)
    connexion.sql(f"""
        CREATE TABLE population AS
        SELECT bilans.siren, bilans.annee_cloture, sirene.section_naf, {colonnes_ratios}
        FROM read_parquet('{url_bilans}') AS bilans
        JOIN read_parquet('{url_sirene}') AS sirene ON bilans.siren = sirene.siren
        WHERE sirene.section_naf IS NOT NULL  -- secteur inconnu : pas de rang possible
    """)


def construire_requete_rang(ratio):
    """Écrit la requête qui calcule le rang sectoriel (0 à 100) d'un ratio.

    percent_rank : part des bilans du même secteur et de la même année qui ont une
    valeur plus faible (0 = le plus faible, 100 = le plus élevé). On ne garde
    ensuite que les bilans de la base appariée (table cles_base).
    """
    return f"""
        WITH rangs AS (
            SELECT siren, annee_cloture,
                   100 * percent_rank() OVER (
                       PARTITION BY section_naf, annee_cloture  -- même secteur, même année
                       ORDER BY {ratio}
                   ) AS rang_{ratio}
            FROM population
            WHERE {ratio} IS NOT NULL  -- un ratio inconnu n'a pas de rang
        )
        SELECT rangs.*
        FROM rangs
        JOIN cles_base USING (siren, annee_cloture)
    """


def calculer_rangs_sectoriels(df_base):
    """Calcule les rangs sectoriels de chaque ratio pour les bilans de la base appariée.

    Sortie : une ligne par (siren, annee_cloture), une colonne rang_<ratio> par ratio.
    """
    connexion = ouvrir_connexion_duckdb()
    df_rangs = df_base[["siren", "annee_cloture"]].drop_duplicates()
    connexion.register("cles_base", df_rangs)  # utilisable comme une table dans le SQL
    creer_table_population(connexion)
    for ratio in config.RATIOS_TRAJECTOIRES:
        df_rang_ratio = connexion.sql(construire_requete_rang(ratio)).df()
        df_rangs = df_rangs.merge(df_rang_ratio, on=["siren", "annee_cloture"], how="left")
    connexion.close()
    return df_rangs


def lire_rangs_sectoriels():
    """Relit depuis S3 (sans clé) les rangs sectoriels calculés par calculer_rangs_sectoriels."""
    return lire_parquet_s3(config.CHEMIN_S3_RANGS_SECTORIELS + "/rangs_sectoriels.parquet")


def ajouter_rangs(df_base, df_rangs):
    """Ajoute à la base appariée les colonnes rang_<ratio> (jointure sur siren et année)."""
    return df_base.merge(df_rangs, on=["siren", "annee_cloture"], how="left")


def lister_colonnes_rangs():
    """Renvoie les noms des colonnes de rangs, par exemple rang_liquidite."""
    liste_colonnes = []
    for ratio in config.RATIOS_TRAJECTOIRES:
        liste_colonnes.append(f"rang_{ratio}")
    return liste_colonnes


def resumer_rangs(df_base_avec_rangs):
    """Médianes des rangs sectoriels à N-1 et N-2, défaillantes contre témoins."""
    df_horizons = df_base_avec_rangs[df_base_avec_rangs["horizon"].isin(config.HORIZONS_RANGS)]
    df_quartiles = calculer_quartiles(df_horizons, lister_colonnes_rangs(), ["groupe"])
    return presenter_medianes(df_quartiles, ["groupe"]).round(1)


def calculer_et_sauvegarder_rangs():
    """Calcule les rangs sectoriels (lourd : lit tous les bilans) et les enregistre sur S3."""
    df_base = lire_base_appariee()
    df_rangs = calculer_rangs_sectoriels(df_base)
    sauvegarder_parquet_s3(df_rangs, config.CHEMIN_S3_RANGS_SECTORIELS + "/rangs_sectoriels.parquet")
    print(resumer_rangs(ajouter_rangs(df_base, df_rangs)).to_string())


if __name__ == "__main__":
    calculer_et_sauvegarder_rangs()
