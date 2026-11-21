"""Étape 6 : appariement des entreprises défaillantes avec des entreprises témoins.

Pour chaque défaillante, on prend son bilan de référence (le plus récent entre N-1
et N-4). On tire au hasard une entreprise témoin dans la même case :
même section NAF, même tranche de taille (total du bilan), même année de clôture.
Les témoins n'ont aucun jugement dans tout le BODACC collecté.
Chaque témoin reçoit la date de jugement de sa défaillante (date fictive), ce qui
permet de calculer ses horizons N-1 à N-4 exactement comme pour les défaillantes.

Lancement, depuis la racine du dépôt (sur le SSP Cloud), après base_analyse :
    python -m src.analyse.temoins
"""

import pandas as pd

import config
from src.collecte.stockage_s3 import lire_parquet_s3, ouvrir_connexion_duckdb, sauvegarder_parquet_s3
from src.nettoyage.base_analyse import (
    ajouter_horizon,
    ajouter_periode,
    ajouter_tranche_taille,
    declarer_sources,
    lister_colonnes_bilans,
)
# Les trois critères d'appariement : une « case » = une combinaison de ces trois valeurs
COLONNES_CELLULE = ["section_naf", "tranche_taille", "annee_cloture"]


def lire_base_defaillantes():
    """Relit depuis S3 (sans clé) les deux tables produites par base_analyse."""
    df_defaillantes = lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/defaillantes.parquet")
    df_bilans = lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/bilans_defaillantes.parquet")
    return df_defaillantes, df_bilans


def choisir_bilans_reference(df_defaillantes, df_bilans):
    """Renvoie une ligne par défaillante : son bilan le plus récent entre N-1 et N-4.

    On ne garde que les défaillantes dont la case est complète (section et tranche connues).
    """
    df_reference = df_bilans.sort_values(["siren", "horizon"])
    # après le tri, le premier est le plus petit horizon, donc le plus récent
    df_reference = df_reference.drop_duplicates(subset="siren", keep="first")
    df_reference = df_reference.merge(df_defaillantes[["siren", "section_naf"]], on="siren")
    colonnes = ["siren", "date_jugement", "total_bilan"] + COLONNES_CELLULE
    df_reference = df_reference[colonnes].dropna(subset=COLONNES_CELLULE)
    # Tri par SIREN
    return df_reference.sort_values("siren").reset_index(drop=True)


def extraire_reservoir(connexion, liste_annees):
    """Renvoie les bilans des entreprises candidates au rôle de témoin.

    Candidates : aucun jugement dans le BODACC (toutes années), section NAF et
    total du bilan connus, bilan clos une des années utiles (liste_annees).
    """
    textes_annees = []
    for annee in liste_annees:
        textes_annees.append(str(annee))
    annees_sql = ", ".join(textes_annees)  # par exemple "2019, 2020, 2021"
    requete = f"""
        SELECT b.siren, b.annee_cloture, b.total_bilan, s.section_naf
        FROM bilans AS b
        JOIN sirene AS s ON b.siren = s.siren
        WHERE b.siren NOT IN (SELECT siren FROM jugements)  -- jamais en procédure collective
          AND b.annee_cloture IN ({annees_sql})
          AND b.total_bilan IS NOT NULL
          AND s.section_naf IS NOT NULL
    """
    return connexion.sql(requete).df()


def melanger_reservoir(df_reservoir):
    """Mélange le réservoir au hasard (graine fixée) et garde un seul bilan par entreprise.

    Le tri préalable rend le tirage reproductible : même entrée, même graine, même résultat.
    Une entreprise ne garde qu'un bilan tiré au hasard : elle ne peut être témoin qu'une fois.
    """
    df_reservoir = df_reservoir.sort_values(["siren", "annee_cloture"]).reset_index(drop=True)
    # sample(frac=1) : tirage de toutes les lignes dans un ordre aléatoire
    df_reservoir = df_reservoir.sample(frac=1, random_state=config.GRAINE_ALEATOIRE)
    df_reservoir = df_reservoir.drop_duplicates(subset="siren", keep="first")
    return df_reservoir.reset_index(drop=True)


def numeroter_dans_cellule(df, colonne_numero):
    """Numérote les lignes 0, 1, 2... à l'intérieur de chaque case, dans l'ordre actuel."""
    # observed=True : ne crée pas de groupe pour les tranches absentes de la table
    df[colonne_numero] = df.groupby(COLONNES_CELLULE, observed=True).cumcount()
    return df


def tirer_temoins(df_reference, df_reservoir):
    """Associe à chaque défaillante NB_TEMOINS_PAR_DEFAILLANTE témoins de la même case.

    Dans chaque case, la défaillante numéro k reçoit les témoins numéros
    k * NB à k * NB + NB - 1 du réservoir mélangé. Une case trop petite laisse
    des défaillantes sans témoin (elles sortent de l'appariement).
    """
    df_reference = numeroter_dans_cellule(df_reference, "numero_paire")
    df_reservoir = numeroter_dans_cellule(df_reservoir, "numero_temoin")
    # Division entière : avec 1 témoin, numero_paire = numero_temoin
    df_reservoir["numero_paire"] = df_reservoir["numero_temoin"] // config.NB_TEMOINS_PAR_DEFAILLANTE
    df_paires = df_reference.merge(
        df_reservoir, on=COLONNES_CELLULE + ["numero_paire"], suffixes=("_defaillante", "_temoin")
    )
    df_paires = df_paires.rename(columns={"date_jugement": "date_jugement_fictive"})
    colonnes = ["siren_defaillante", "siren_temoin", "date_jugement_fictive"] + COLONNES_CELLULE
    return df_paires[colonnes]


def extraire_bilans_temoins(connexion, df_paires):
    """Renvoie les bilans des témoins clos avant leur date de jugement fictive, avec leur horizon."""
    # Rend le DataFrame utilisable comme une table dans la requête SQL
    connexion.register("table_paires", df_paires[["siren_temoin", "date_jugement_fictive"]])
    colonnes_sql = []
    for colonne in lister_colonnes_bilans():
        colonnes_sql.append(f"b.{colonne}")
    requete = f"""
        SELECT {", ".join(colonnes_sql)}, p.date_jugement_fictive
        FROM bilans AS b
        JOIN table_paires AS p ON b.siren = p.siren_temoin
        WHERE b.date_cloture_exercice < p.date_jugement_fictive  -- même règle que les défaillantes
    """
    df_bilans_temoins = connexion.sql(requete).df()
    df_bilans_temoins = ajouter_horizon(df_bilans_temoins, "date_jugement_fictive")
    return ajouter_tranche_taille(df_bilans_temoins)


def assembler_base_appariee(df_bilans, df_bilans_temoins, df_paires):
    """Empile les bilans des défaillantes appariées et ceux de leurs témoins.

    Colonnes ajoutées : groupe ("défaillante" ou "témoin") et siren_defaillante,
    qui identifie la paire (pour une défaillante, c'est son propre SIREN).
    """
    df_def = df_bilans[df_bilans["siren"].isin(df_paires["siren_defaillante"])].copy()
    df_def["groupe"] = "défaillante"
    df_def["siren_defaillante"] = df_def["siren"]
    df_def = df_def.rename(columns={"date_jugement": "date_reference"})
    df_tem = df_bilans_temoins.merge(
        df_paires[["siren_temoin", "siren_defaillante"]], left_on="siren", right_on="siren_temoin"
    )
    df_tem = df_tem.drop(columns="siren_temoin")
    df_tem["groupe"] = "témoin"
    df_tem = df_tem.rename(columns={"date_jugement_fictive": "date_reference"})
    df_base = pd.concat([df_def, df_tem], ignore_index=True)
    # Recalculée pour tous : un témoin prend la période de sa défaillante (date fictive)
    return ajouter_periode(df_base, "date_reference")


def construire_entonnoir_appariement(df_defaillantes, df_reference, df_paires):
    """Tableau en entonnoir de l'appariement : défaillantes gardées à chaque étape."""
    etapes = [
        (f"avec un bilan entre N-1 et N-{config.HORIZON_MAX}", df_defaillantes["horizon_dernier_bilan"].notna().sum()),
        ("case complète (section et taille connues)", len(df_reference)),
        ("appariées à au moins un témoin", df_paires["siren_defaillante"].nunique()),
    ]
    return pd.DataFrame(etapes, columns=["etape", "nombre_defaillantes"])


def comparer_groupes(df_base):
    """Tableau de validation : nombre de bilans par période et par horizon, défaillantes contre témoins."""
    return pd.crosstab(
        [df_base["periode"], df_base["horizon"]], df_base["groupe"], margins=True, margins_name="total"
    )

def apparier_temoins():
    """Enchaîne toutes les étapes de l'appariement, affiche les contrôles et enregistre sur S3."""
    df_defaillantes, df_bilans = lire_base_defaillantes()
    df_reference = choisir_bilans_reference(df_defaillantes, df_bilans)
    connexion = ouvrir_connexion_duckdb()
    declarer_sources(connexion)
    liste_annees = sorted(df_reference["annee_cloture"].unique())
    df_reservoir = ajouter_tranche_taille(extraire_reservoir(connexion, liste_annees))
    print(f"Réservoir : {len(df_reservoir)} bilans d'entreprises jamais jugées")
    df_reservoir = melanger_reservoir(df_reservoir)
    df_paires = tirer_temoins(df_reference, df_reservoir)
    df_bilans_temoins = extraire_bilans_temoins(connexion, df_paires)
    connexion.close()
    df_base = assembler_base_appariee(df_bilans, df_bilans_temoins, df_paires)
    print(construire_entonnoir_appariement(df_defaillantes, df_reference, df_paires).to_string(index=False))
    print(comparer_groupes(df_base).to_string())
    sauvegarder_parquet_s3(df_paires, config.CHEMIN_S3_BASE_ANALYSE + "/paires.parquet")
    sauvegarder_parquet_s3(df_base, config.CHEMIN_S3_BASE_ANALYSE + "/base_appariee.parquet")
    return df_paires, df_base


if __name__ == "__main__":
    apparier_temoins()