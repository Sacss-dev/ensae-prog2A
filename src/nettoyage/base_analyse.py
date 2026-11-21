"""Étape 6 : base d'analyse des entreprises défaillantes.

On part des premiers jugements d'ouverture (étape 5, BODACC), on garde la période
d'étude, on ajoute les caractéristiques SIRENE (étape 4) et les bilans avec leurs
ratios (étape 5). Chaque bilan clos avant le jugement reçoit un horizon glissant :
1 = N-1 (clos dans les 12 mois avant le jugement), 2 = N-2 (12 à 24 mois), etc.
Un tableau en entonnoir compte les entreprises gardées à chaque étape.

Deux tables sont enregistrées sur S3 :
- defaillantes.parquet : une ligne par entreprise jugée pendant la période ;
- bilans_defaillantes.parquet : une ligne par couple (entreprise, horizon).

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.nettoyage.base_analyse
"""

import numpy as np
import pandas as pd

import config
from src.collecte.stockage_s3 import construire_url_publique, ouvrir_connexion_duckdb, sauvegarder_parquet_s3
from src.nettoyage.ratios import COLONNES_RATIOS

# Nombre moyen de jours dans une année (années bissextiles comprises)
JOURS_PAR_AN = 365.25

# Colonnes de bilan qui identifient le bilan, avant les postes et les ratios
COLONNES_IDENTIFIANT_BILAN = [
    "siren", "date_cloture_exercice", "annee_cloture",
    "type_bilan", "statut_comptes", "nombre_postes",
]


def declarer_sources(connexion):
    """Déclare les trois fichiers d'entrée comme des vues DuckDB : jugements, sirene, bilans.

    Une vue est un raccourci : DuckDB relit le fichier à chaque requête qui l'utilise,
    sans jamais le charger en entier en mémoire.
    """
    sources = {
        "jugements": config.CHEMIN_S3_JUGEMENTS + "/premiers_jugements.parquet",
        "sirene": config.CHEMIN_S3_SIRENE + "/sirene.parquet",
        "bilans": config.CHEMIN_S3_BILANS_RATIOS + "/bilans_ratios.parquet",
    }
    for nom_vue, chemin_s3 in sources.items():
        url = construire_url_publique(chemin_s3)
        connexion.sql(f"CREATE VIEW {nom_vue} AS SELECT * FROM read_parquet('{url}')")


def extraire_defaillantes(connexion):
    """Renvoie les entreprises jugées pendant la période d'étude, avec leurs caractéristiques SIRENE.

    LEFT JOIN : une entreprise absente de SIRENE est gardée (colonnes SIRENE à NULL),
    pour pouvoir la compter dans le tableau en entonnoir.
    """
    requete = f"""
        SELECT
            j.siren, j.date_jugement, j.annee_jugement, j.type_procedure,
            s.siren IS NOT NULL AS dans_sirene,           -- vrai si le SIREN existe dans SIRENE
            s.activitePrincipaleUniteLegale AS code_naf,
            s.section_naf, s.libelle_section,
            s.dateCreationUniteLegale AS date_creation,
            s.categorieJuridiqueUniteLegale AS categorie_juridique,
            s.trancheEffectifsUniteLegale AS tranche_effectifs,
            s.departement                                 -- département du siège
        FROM jugements AS j
        LEFT JOIN sirene AS s ON j.siren = s.siren
        WHERE j.annee_jugement BETWEEN {config.ANNEE_DEBUT_JUGEMENTS} AND {config.ANNEE_FIN_JUGEMENTS}
    """
    return connexion.sql(requete).df()


def lister_colonnes_bilans():
    """Liste les colonnes de bilan gardées : identifiants, postes harmonisés (étape 5) et ratios."""
    colonnes = list(COLONNES_IDENTIFIANT_BILAN)
    for nom_poste in config.CORRESPONDANCE_POSTES:
        colonnes.append(nom_poste)
    for nom_ratio in COLONNES_RATIOS:
        colonnes.append(nom_ratio)
    return colonnes


def extraire_bilans_avant_jugement(connexion, df_defaillantes):
    """Renvoie les bilans des défaillantes clos avant leur jugement, avec la date du jugement.

    Seuls les bilans clos AVANT le jugement peuvent servir de signal d'alerte.
    """
    # Rend le DataFrame utilisable comme une table dans la requête SQL
    connexion.register("table_defaillantes", df_defaillantes[["siren", "date_jugement"]])
    colonnes_sql = []
    for colonne in lister_colonnes_bilans():
        colonnes_sql.append(f"b.{colonne}")
    requete = f"""
        SELECT {", ".join(colonnes_sql)}, d.date_jugement
        FROM bilans AS b
        JOIN table_defaillantes AS d ON b.siren = d.siren
        WHERE b.date_cloture_exercice < d.date_jugement  -- strictement avant le jugement
    """
    return connexion.sql(requete).df()


def calculer_horizon(date_cloture, date_reference):
    """Calcule l'horizon glissant d'un bilan par rapport à une date de référence.

    Entrées : deux colonnes de dates. Sortie : une colonne d'entiers.
    1 à 365 jours d'écart -> 1 (N-1), 366 à 730 jours -> 2 (N-2), etc.
    Réutilisée pour les témoins, avec la date de jugement de leur défaillante.
    """
    nombre_jours = (date_reference - date_cloture).dt.days
    # np.ceil arrondit à l'entier supérieur : 0,3 an -> 1 ; 1,2 an -> 2
    return np.ceil(nombre_jours / JOURS_PAR_AN).astype(int)


def ajouter_horizon(df_bilans, colonne_date_reference):
    """Ajoute la colonne horizon et ne garde que les bilans de N-1 à N-HORIZON_MAX.

    Si deux bilans tombent dans le même horizon (exercice raccourci après un changement
    de date de clôture), on garde le plus récent.
    """
    df_bilans["horizon"] = calculer_horizon(
        df_bilans["date_cloture_exercice"], df_bilans[colonne_date_reference]
    )
    df_bilans = df_bilans[df_bilans["horizon"] <= config.HORIZON_MAX].copy()
    df_bilans = df_bilans.sort_values(["siren", "horizon", "date_cloture_exercice"])
    # keep="last" : après le tri, le dernier est le plus récent
    df_bilans = df_bilans.drop_duplicates(subset=["siren", "horizon"], keep="last")
    return df_bilans.reset_index(drop=True)


def ajouter_tranche_taille(df_bilans):
    """Ajoute la tranche de taille, d'après le total du bilan et les seuils de config.py.

    pd.cut range chaque valeur dans un intervalle [borne basse, borne haute[ ;
    un total du bilan absent donne une tranche absente (NaN).
    """
    bornes = [-np.inf] + config.SEUILS_TAILLE_BILAN + [np.inf]
    df_bilans["tranche_taille"] = pd.cut(
        df_bilans["total_bilan"], bins=bornes, labels=config.LABELS_TAILLE_BILAN, right=False
    )
    return df_bilans


def ajouter_periode(df, colonne_date):
    """Ajoute la colonne periode : Covid (jugement jusqu'en ANNEE_FIN_PERIODE_COVID) ou après Covid.

    Pour un témoin, colonne_date est sa date fictive : il prend la période de sa défaillante.
    """
    est_covid = df[colonne_date].dt.year <= config.ANNEE_FIN_PERIODE_COVID
    # np.where : premier label si la condition est vraie, second sinon
    df["periode"] = np.where(est_covid, config.LABELS_PERIODE[0], config.LABELS_PERIODE[1])
    return df


def ajouter_indicateurs_bilans(df_defaillantes, df_bilans_avant, df_bilans):
    """Ajoute aux défaillantes deux colonnes, utiles pour l'entonnoir et la partie 5.

    a_un_bilan_avant : au moins un bilan clos avant le jugement, quel que soit l'écart.
    horizon_dernier_bilan : horizon du bilan le plus récent (1 à HORIZON_MAX), NaN sinon.
    """
    df_defaillantes["a_un_bilan_avant"] = df_defaillantes["siren"].isin(df_bilans_avant["siren"])
    # Pour chaque SIREN, le plus petit horizon = le bilan le plus proche du jugement
    horizon_plus_recent = df_bilans.groupby("siren")["horizon"].min()
    df_defaillantes["horizon_dernier_bilan"] = df_defaillantes["siren"].map(horizon_plus_recent)
    return df_defaillantes


def construire_entonnoir(nombre_jugements_total, df_defaillantes):
    """Tableau en entonnoir : nombre d'entreprises gardées à chaque étape.

    Chaque condition s'ajoute aux précédentes (&) : le nombre ne peut que baisser.
    """
    garde = df_defaillantes["dans_sirene"]
    etapes = [
        ("premiers jugements d'ouverture (toutes années)", nombre_jugements_total),
        (f"jugées de {config.ANNEE_DEBUT_JUGEMENTS} à {config.ANNEE_FIN_JUGEMENTS}", len(df_defaillantes)),
        ("présentes dans SIRENE", garde.sum()),
    ]
    garde = garde & df_defaillantes["section_naf"].notna()
    etapes.append(("avec une section NAF", garde.sum()))
    garde = garde & df_defaillantes["a_un_bilan_avant"]
    etapes.append(("avec au moins un bilan clos avant le jugement", garde.sum()))
    garde = garde & df_defaillantes["horizon_dernier_bilan"].notna()
    etapes.append((f"avec un bilan entre N-1 et N-{config.HORIZON_MAX}", garde.sum()))
    df_entonnoir = pd.DataFrame(etapes, columns=["etape", "nombre_entreprises"])
    # Part calculée par rapport aux entreprises jugées pendant la période
    df_entonnoir["part_periode_pct"] = (100 * df_entonnoir["nombre_entreprises"] / len(df_defaillantes)).round(1)
    return df_entonnoir


def compter_par_horizon(df_bilans):
    """Tableau de validation : nombre de bilans par horizon et par tranche de taille."""
    return pd.crosstab(
        df_bilans["horizon"], df_bilans["tranche_taille"], margins=True, margins_name="total"
    )


def construire_base_analyse():
    """Enchaîne toutes les étapes, affiche les tableaux de validation et enregistre sur S3."""
    connexion = ouvrir_connexion_duckdb()
    declarer_sources(connexion)
    # fetchall() renvoie [(nombre,)] : [0][0] prend le nombre seul
    nombre_jugements_total = connexion.sql("SELECT count(*) FROM jugements").fetchall()[0][0]
    df_defaillantes = extraire_defaillantes(connexion)
    df_bilans_avant = extraire_bilans_avant_jugement(connexion, df_defaillantes)
    connexion.close()
    df_bilans = ajouter_horizon(df_bilans_avant, "date_jugement")
    df_bilans = ajouter_tranche_taille(df_bilans)
    df_bilans = ajouter_periode(df_bilans, "date_jugement")
    df_defaillantes = ajouter_indicateurs_bilans(df_defaillantes, df_bilans_avant, df_bilans)
    df_defaillantes = ajouter_periode(df_defaillantes, "date_jugement")
    print(construire_entonnoir(nombre_jugements_total, df_defaillantes).to_string(index=False))
    print(compter_par_horizon(df_bilans).to_string())
    sauvegarder_parquet_s3(df_defaillantes, config.CHEMIN_S3_BASE_ANALYSE + "/defaillantes.parquet")
    sauvegarder_parquet_s3(df_bilans, config.CHEMIN_S3_BASE_ANALYSE + "/bilans_defaillantes.parquet")
    return df_defaillantes, df_bilans


if __name__ == "__main__":
    construire_base_analyse()