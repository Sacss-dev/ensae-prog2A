"""Étape 11 (partie 6 du rapport) : règles d'alerte simples.

Trois règles, calculées sur un seul bilan (celui de l'horizon étudié) :
- capitaux propres négatifs ;
- trésorerie quasi nulle (disponibilités < 2 % du total du bilan, bilans complets seulement) ;
- règle combinée : au moins 2 signaux parmi capitaux propres négatifs, trésorerie
  quasi nulle et perte nette.

Pour chaque règle et chaque horizon (N-1, N-2) :
- taux de détection = part des défaillantes signalées ;
- taux de fausses alertes = part des témoins signalés.
Les deux taux portent sur les entreprises qui ont un bilan à cet horizon.
Une donnée manquante (compte confidentiel, bilan simplifié) ne déclenche jamais d'alerte.

Lancement d'un contrôle rapide, depuis la racine du dépôt :
    python -m src.analyse.regles_alerte
"""

import pandas as pd

import config
from src.collecte.stockage_s3 import lire_parquet_s3

# Colonnes de la base appariée utiles aux règles
COLONNES_UTILES = [
    "siren_defaillante", "groupe", "horizon", "periode",
    "capitaux_propres", "liquidite", "resultat_net",
]

# Nom de la colonne vrai/faux de chaque règle -> libellé affiché dans les tableaux
REGLES = {
    "alerte_capitaux_propres": "Capitaux propres négatifs",
    "alerte_tresorerie": f"Trésorerie < {100 * config.SEUIL_TRESORERIE_FAIBLE:.0f} % du total du bilan",
    "alerte_combinee": f"Au moins {config.NB_SIGNAUX_MIN} signaux sur 3",
}


def lire_base_appariee():
    """Relit depuis S3 (sans clé) la base appariée de l'étape 6 : défaillantes et témoins.

    Sortie : une ligne par couple (entreprise, horizon), de N-1 à N-4.
    """
    return lire_parquet_s3(config.CHEMIN_S3_BASE_ANALYSE + "/base_appariee.parquet", colonnes=COLONNES_UTILES)


def ajouter_alertes(df_base):
    """Ajoute une colonne vrai/faux par signal et par règle.

    En pandas, une comparaison avec une valeur manquante (NaN < 0) vaut False :
    un poste inconnu ne déclenche donc jamais d'alerte.
    """
    df_base["alerte_capitaux_propres"] = df_base["capitaux_propres"] < 0
    df_base["alerte_tresorerie"] = df_base["liquidite"] < config.SEUIL_TRESORERIE_FAIBLE
    df_base["signal_perte"] = df_base["resultat_net"] < 0
    # True compte pour 1 et False pour 0 : la somme donne le nombre de signaux allumés
    nombre_signaux = (
        df_base["alerte_capitaux_propres"].astype(int)
        + df_base["alerte_tresorerie"].astype(int)
        + df_base["signal_perte"].astype(int)
    )
    df_base["alerte_combinee"] = nombre_signaux >= config.NB_SIGNAUX_MIN
    return df_base


def calculer_performances(df_base, horizon):
    """Taux de détection et de fausses alertes de chaque règle, pour un horizon.

    Entrées : la base avec ses alertes et un horizon (1 pour N-1, 2 pour N-2).
    Sortie : une ligne par règle.
    """
    df_horizon = df_base[df_base["horizon"] == horizon]
    lignes = []
    for colonne_regle, libelle_regle in REGLES.items():
        # moyenne d'une colonne vrai/faux = part de True, calculée dans chaque groupe
        part_signalee = 100 * df_horizon.groupby("groupe")[colonne_regle].mean()
        lignes.append({
            "regle": libelle_regle,
            "horizon": f"N-{horizon}",
            "taux_detection_pct": part_signalee["défaillante"],
            "taux_fausses_alertes_pct": part_signalee["témoin"],
        })
    return pd.DataFrame(lignes)


def estimer_vraies_alertes(df_performances, taux_defaillance):
    """Ajoute la part de vraies alertes attendue dans une population où taux_defaillance échouent.

    Dans l'échantillon, il y a autant de témoins que de défaillantes. En population réelle,
    il y a environ 110 sociétés saines pour une défaillante : les fausses alertes pèsent plus.
    Sur 1 société : vraies alertes = détection x taux ; fausses = fausses alertes x (1 - taux).
    """
    vraies_alertes = df_performances["taux_detection_pct"] * taux_defaillance
    fausses_alertes = df_performances["taux_fausses_alertes_pct"] * (1 - taux_defaillance)
    df_performances["vraies_alertes_population_pct"] = 100 * vraies_alertes / (vraies_alertes + fausses_alertes)
    return df_performances


def tableau_performances(df_base):
    """Tableau final : chaque règle à chaque horizon de config.HORIZONS_ALERTE, arrondi à 0,1."""
    liste_tableaux = []
    for horizon in config.HORIZONS_ALERTE:
        liste_tableaux.append(calculer_performances(df_base, horizon))
    df_performances = pd.concat(liste_tableaux, ignore_index=True)
    df_performances = estimer_vraies_alertes(df_performances, config.TAUX_DEFAILLANCE_POPULATION)
    return df_performances.round(1)


def tableau_performances_par_periode(df_base):
    """Même tableau, calculé séparément pour la période Covid et l'après-Covid."""
    liste_tableaux = []
    for periode in config.LABELS_PERIODE:
        df_periode = tableau_performances(df_base[df_base["periode"] == periode])
        df_periode.insert(0, "periode", periode)  # colonne periode en première position
        liste_tableaux.append(df_periode)
    return pd.concat(liste_tableaux, ignore_index=True)


def calculer_couverture(df_base):
    """Part des défaillantes et des témoins qui ont un bilan à chaque horizon (en %).

    Rappelle sur quelle part de l'échantillon les règles peuvent être évaluées :
    une défaillante sans bilan à N-1 ne peut pas être détectée à N-1.
    """
    nombre_paires = df_base["siren_defaillante"].nunique()  # une paire = une défaillante et son témoin
    df_effectifs = pd.crosstab(df_base["horizon"], df_base["groupe"])
    return (100 * df_effectifs / nombre_paires).round(1)


if __name__ == "__main__":
    df_base_test = ajouter_alertes(lire_base_appariee())
    print(calculer_couverture(df_base_test).to_string())
    print(tableau_performances(df_base_test).to_string(index=False))
    print(tableau_performances_par_periode(df_base_test).to_string(index=False))
