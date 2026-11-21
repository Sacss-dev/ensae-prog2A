"""Étape 7 (partie 2 du rapport) : portrait descriptif des défaillances.

Taux de défaillance selon le secteur, l'âge, la taille et le département, puis
répartition des types de procédure.

Définition du taux : pour chaque année de la période d'étude, on prend les sociétés
commerciales qui existent au 1er janvier (créées avant, pas encore cessées) et on compte
celles qui ont un jugement de redressement ou de liquidation dans l'année. Le taux
annuel moyen, pour 1 000 sociétés, vaut :
    1 000 x (défaillances de toutes les années) / (sociétés présentes, toutes années comprises)

Lancement d'un contrôle rapide, depuis la racine du dépôt :
    python -m src.analyse.portrait
"""

import pandas as pd
from cartiflette import carti_download

import config
from src.collecte.stockage_s3 import lire_parquet_s3, ouvrir_connexion_duckdb

URL_SIRENE_NETTOYE = f"{config.URL_PUBLIQUE_S3}/{config.CHEMIN_S3_SIRENE}/sirene.parquet"
URL_JUGEMENTS = f"{config.URL_PUBLIQUE_S3}/{config.CHEMIN_S3_JUGEMENTS}/premiers_jugements.parquet"

ORDRE_TRANCHES_AGE = ["0 à 2 ans", "3 à 5 ans", "6 à 10 ans", "11 à 20 ans", "21 ans et plus"]


def construire_requete_presences():
    """Écrit la partie SQL qui donne une ligne par société et par année où elle existe au 1er janvier.

    Sortie : le texte SQL d'un SELECT (colonnes de SIRENE, plus annee et age).
    """
    return f"""
        WITH annees AS (
            -- une ligne par année de la période d'étude (range exclut la borne de fin)
            SELECT range AS annee
            FROM range({config.ANNEE_DEBUT_JUGEMENTS}, {config.ANNEE_FIN_JUGEMENTS + 1})
        ),
        societes AS (
            SELECT siren, dateCreationUniteLegale AS date_creation,
                   etatAdministratifUniteLegale AS etat, date_debut_etat,
                   trancheEffectifsUniteLegale AS tranche_effectifs,
                   section_naf, libelle_section, departement
            FROM read_parquet('{URL_SIRENE_NETTOYE}')
            -- sociétés commerciales seulement (catégorie juridique 5xxx)
            WHERE left(CAST(categorieJuridiqueUniteLegale AS VARCHAR), 1) = '{config.PREFIXE_CATEGORIE_JURIDIQUE}'
        )
        SELECT societes.*, annees.annee, annees.annee - year(date_creation) AS age
        FROM societes
        CROSS JOIN annees  -- chaque société est recopiée une fois par année
        -- on garde l'année si la société existe au 1er janvier : créée avant, et active
        -- aujourd'hui ou cessée après cette date (date_debut_etat = date de cessation)
        WHERE date_creation < make_date(annees.annee, 1, 1)
          AND (etat = 'A' OR date_debut_etat >= make_date(annees.annee, 1, 1))
    """


def construire_requete_comptages():
    """Écrit la requête qui compte sociétés présentes et défaillances par année et par groupe.

    Sortie : le texte SQL. Une ligne par combinaison (année, secteur, département,
    tranche d'effectifs, tranche d'âge), avec nb_entreprises et nb_defaillances.
    """
    types_defaillance = "', '".join(config.TYPES_DEFAILLANCE)  # -> redressement', 'liquidation
    return f"""
        WITH presences AS ({construire_requete_presences()}),
        defaillances AS (
            SELECT siren, annee_jugement
            FROM read_parquet('{URL_JUGEMENTS}')
            WHERE type_procedure IN ('{types_defaillance}')
        )
        SELECT annee, section_naf, libelle_section, departement, tranche_effectifs,
            CASE
                WHEN age < 3 THEN '0 à 2 ans'
                WHEN age < 6 THEN '3 à 5 ans'
                WHEN age < 11 THEN '6 à 10 ans'
                WHEN age < 21 THEN '11 à 20 ans'
                ELSE '21 ans et plus'
            END AS tranche_age,
            count(*) AS nb_entreprises,
            -- count(colonne) ignore les NULL : seules les sociétés jointes à un jugement comptent
            count(defaillances.siren) AS nb_defaillances
        FROM presences
        -- jointure sur le SIREN ET l'année : la défaillance compte l'année du jugement
        LEFT JOIN defaillances
            ON presences.siren = defaillances.siren
           AND presences.annee = defaillances.annee_jugement
        GROUP BY ALL  -- regroupe sur toutes les colonnes qui ne sont pas des count
    """


def compter_entreprises_et_defaillances():
    """Exécute la requête de comptage et ajoute la classe de taille.

    Sortie : un DataFrame d'environ 100 000 lignes, base de tous les taux de l'étape 7.
    Attention : lit SIRENE en ligne (environ 400 Mo), compter 2 à 5 minutes.
    """
    connexion = ouvrir_connexion_duckdb()
    df_comptages = connexion.sql(construire_requete_comptages()).df()
    connexion.close()
    df_comptages["groupe_effectifs"] = df_comptages["tranche_effectifs"].map(config.GROUPES_EFFECTIFS)
    # Catégories ordonnées : les tableaux et graphiques suivent l'ordre naturel des classes
    df_comptages["groupe_effectifs"] = pd.Categorical(
        df_comptages["groupe_effectifs"], categories=config.ORDRE_GROUPES_EFFECTIFS, ordered=True
    )
    df_comptages["tranche_age"] = pd.Categorical(
        df_comptages["tranche_age"], categories=ORDRE_TRANCHES_AGE, ordered=True
    )
    return df_comptages


def calculer_taux(df_comptages, variable):
    """Calcule le taux annuel moyen de défaillance pour 1 000 sociétés, selon une variable.

    Entrées : le DataFrame de compter_entreprises_et_defaillances et le nom d'une colonne
    de regroupement (ex. "libelle_section", "tranche_age", "departement").
    Sortie : une ligne par modalité, avec nb_entreprises, nb_defaillances et taux_pour_mille.
    Les modalités inconnues (NaN) sont écartées par groupby, et les trop petites
    (moins de config.SEUIL_ENTREPRISES_MIN sociétés-années) par le filtre final.
    """
    colonnes_comptage = ["nb_entreprises", "nb_defaillances"]
    # observed=True : ne garde que les modalités présentes dans les données
    df_taux = df_comptages.groupby(variable, observed=True)[colonnes_comptage].sum()
    df_taux["taux_pour_mille"] = (1000 * df_taux["nb_defaillances"] / df_taux["nb_entreprises"]).round(1)
    df_taux = df_taux[df_taux["nb_entreprises"] >= config.SEUIL_ENTREPRISES_MIN]
    return df_taux.reset_index()


def lire_jugements_periode():
    """Relit les premiers jugements (étape 5) et garde ceux de la période d'étude."""
    df_jugements = lire_parquet_s3(config.CHEMIN_S3_JUGEMENTS + "/premiers_jugements.parquet")
    dans_periode = df_jugements["annee_jugement"].between(config.ANNEE_DEBUT_JUGEMENTS, config.ANNEE_FIN_JUGEMENTS)
    return df_jugements[dans_periode].copy()


def repartir_procedures(df_jugements):
    """Part de chaque type de procédure (en %) parmi les jugements de chaque année.

    Sortie : une ligne par année, une colonne par type (liquidation, redressement, sauvegarde).
    """
    # normalize="index" : chaque ligne (année) est divisée par son total
    df_parts = pd.crosstab(df_jugements["annee_jugement"], df_jugements["type_procedure"], normalize="index")
    return (100 * df_parts).round(1)


def preparer_carte(df_taux_departements):
    """Associe les taux départementaux aux contours des départements (cartiflette).

    Entrée : la sortie de calculer_taux(df_comptages, "departement").
    Sortie : un GeoDataFrame des 101 départements (DROM rapprochés de la métropole),
    avec la colonne taux_pour_mille.
    """
    gdf_departements = carti_download(
        values="France",
        borders="DEPARTEMENT",
        filter_by="FRANCE_ENTIERE_DROM_RAPPROCHES",  # DROM affichés près de la métropole
        year=config.ANNEE_FOND_CARTE,
    )
    # how="left" : un département sans données reste sur la carte (en gris)
    return gdf_departements.merge(
        df_taux_departements, left_on="INSEE_DEP", right_on="departement", how="left"
    )


if __name__ == "__main__":
    df_comptages_test = compter_entreprises_et_defaillances()
    for variable_test in ["libelle_section", "tranche_age", "groupe_effectifs"]:
        print(calculer_taux(df_comptages_test, variable_test).to_string(index=False))
    print(repartir_procedures(lire_jugements_periode()).to_string())
