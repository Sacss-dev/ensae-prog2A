"""Étape 10 (partie 5 du rapport) : le silence comptable avant la défaillance.

Pour chaque entreprise appariée (défaillante ou témoin) et chaque horizon de N-4 à N-1,
on regarde si ses comptes sont publics, confidentiels ou absents. On mesure aussi
le biais de sélection que ce silence crée pour la partie 3 : les défaillantes qui
publient encore à N-1 ressemblent-elles à celles qui se taisent ?
"""

import pandas as pd

import config
from src.analyse.graphiques import tracer_barres_empilees
from src.analyse.trajectoires import calculer_quartiles, presenter_medianes
from src.collecte.stockage_s3 import lire_parquet_s3


def lire_defaillantes():
    """Relit la liste de toutes les défaillantes de la période (étape 6)."""
    colonnes = ["siren", "periode", "a_un_bilan_avant"]
    return lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/defaillantes.parquet", colonnes)


def lire_paires():
    """Relit les paires (défaillante, témoin) de l'étape 6."""
    return lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/paires.parquet", ["siren_defaillante", "siren_temoin"])


def decrire_population_totale(df_defaillantes, df_paires):
    """Tableau descriptif de toutes les défaillantes : avec ou sans bilan, appariées ou non.

    Sortie : nombre et part (en %) de chaque situation, par période.
    """
    est_appariee = df_defaillantes["siren"].isin(df_paires["siren_defaillante"])
    df_defaillantes["situation"] = "aucun bilan de N-4 à N-1"
    df_defaillantes.loc[df_defaillantes["a_un_bilan_avant"], "situation"] = "bilan, mais pas de témoin"
    df_defaillantes.loc[est_appariee, "situation"] = "bilan et témoin (base appariée)"
    df_comptes = df_defaillantes.groupby(["periode", "situation"]).size().unstack("periode")
    df_parts = 100 * df_comptes / df_comptes.sum()  # part dans chaque période
    return pd.concat({"nombre": df_comptes, "part en %": df_parts.round(1)}, axis=1)


def construire_grille(df_paires, df_defaillantes):
    """Construit une ligne par entreprise appariée et par horizon (1 à HORIZON_MAX).

    Défaillantes et témoins sont empilés ; chaque témoin garde le SIREN et la période
    de sa défaillante.
    """
    df_def = pd.DataFrame({"siren": df_paires["siren_defaillante"], "groupe": "défaillante"})
    df_tem = pd.DataFrame({"siren": df_paires["siren_temoin"], "groupe": "témoin"})
    df_def["siren_defaillante"] = df_paires["siren_defaillante"]
    df_tem["siren_defaillante"] = df_paires["siren_defaillante"]
    df_entreprises = pd.concat([df_def, df_tem], ignore_index=True)
    df_horizons = pd.DataFrame({"horizon": range(1, config.HORIZON_MAX + 1)})
    df_grille = df_entreprises.merge(df_horizons, how="cross")  # toutes les combinaisons
    df_periodes = df_defaillantes[["siren", "periode"]].rename(columns={"siren": "siren_defaillante"})
    return df_grille.merge(df_periodes, on="siren_defaillante", how="left")


def ajouter_statut(df_grille, df_base):
    """Ajoute le statut des comptes : public, confidentiel, ou absent s'il n'y a pas de bilan."""
    df_statuts = df_base[["siren", "horizon", "statut_comptes"]]
    df_grille = df_grille.merge(df_statuts, on=["siren", "horizon"], how="left")
    # pas de ligne dans la base appariée = pas de bilan à cet horizon
    df_grille["statut"] = df_grille["statut_comptes"].fillna("absent")
    return df_grille.drop(columns="statut_comptes")


def calculer_taux_silence(df_grille, colonnes_groupes):
    """Part (en %) de chaque statut, par groupes et par horizon.

    Sortie : une ligne par (groupes, horizon), une colonne par statut (public, confidentiel, absent).
    """
    df_parts = df_grille.groupby(colonnes_groupes + ["horizon"])["statut"].value_counts(normalize=True)
    df_parts = df_parts.unstack("statut").fillna(0) * 100  # statut absent du groupe : 0 %
    return df_parts[config.ORDRE_STATUTS].round(1)


def tracer_silence_par_periode(df_grille):
    """Barres empilées des statuts, une figure par période (réutilise tracer_barres_empilees).

    Une barre par (groupe, horizon), de N-4 à N-1. Sortie : un dictionnaire période -> figure.
    """
    df_taux = calculer_taux_silence(df_grille, ["periode", "groupe"])
    figures = {}
    for periode in config.LABELS_PERIODE:
        df_periode = df_taux.loc[periode].sort_index(level=["groupe", "horizon"], ascending=[True, False])
        etiquettes = []
        for groupe, horizon in df_periode.index:
            etiquettes.append(f"{groupe}s, N-{horizon}")  # par exemple « témoins, N-4 »
        df_periode.index = etiquettes
        titre = f"Statut des comptes avant le jugement – jugements {periode}"
        fig, _ = tracer_barres_empilees(df_periode, titre, "Part des entreprises (%)", config.SOURCE_GRAPHIQUES)
        figures[periode] = fig
    return figures


def comparer_publiantes_et_silencieuses(df_base):
    """Mesure du biais de sélection : ratios à N-2 des défaillantes, selon qu'elles publient encore à N-1.

    Sortie : médianes de chaque ratio à N-2, pour les défaillantes qui ont un bilan à N-1
    et pour celles qui n'en ont pas (silencieuses), avec leur nombre.
    """
    est_defaillante = df_base["groupe"] == "défaillante"
    siren_bilan_n1 = df_base[est_defaillante & (df_base["horizon"] == 1)]["siren"]
    df_n2 = df_base[est_defaillante & (df_base["horizon"] == 2)].copy()
    df_n2["comportement_n1"] = "silencieuse à N-1"
    df_n2.loc[df_n2["siren"].isin(siren_bilan_n1), "comportement_n1"] = "publie encore à N-1"
    df_quartiles = calculer_quartiles(df_n2, config.RATIOS_TRAJECTOIRES, ["comportement_n1"])
    df_medianes = presenter_medianes(df_quartiles, ["comportement_n1"]).round(3)
    df_medianes.columns = df_medianes.columns.droplevel("horizon")  # horizon = 2 partout
    print(f"Défaillantes avec un bilan à N-2 : {df_n2['comportement_n1'].value_counts().to_dict()}")
    return df_medianes
