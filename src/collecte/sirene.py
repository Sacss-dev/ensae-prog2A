"""Étape 4 : collecte des caractéristiques des entreprises dans la base SIRENE.

On extrait du stock des unités légales les variables utiles (activité, date de
création, effectifs, catégorie juridique...), on y ajoute le département du siège
(pris dans le stock des établissements) et la section NAF (A à U), puis on
enregistre le résultat sur S3.

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.collecte.sirene
"""

import pandas as pd

import config
from src.collecte.stockage_s3 import ouvrir_connexion_duckdb, sauvegarder_parquet_s3


def construire_table_divisions():
    """Construit la table de passage de la division NAF (2 chiffres) à la section (A à U).

    Sortie : un DataFrame avec une ligne par division, par exemple ("47", "G", "Commerce...").
    """
    lignes = []
    for section, premiere_division, derniere_division, libelle in config.SECTIONS_NAF:
        for numero in range(premiere_division, derniere_division + 1):
            division = str(numero).zfill(2)  # 1 -> "01", pour coller au format du code NAF
            lignes.append({"division": division, "section_naf": section, "libelle_section": libelle})
    return pd.DataFrame(lignes)


def construire_requete_unites_legales(limite=None):
    """Écrit la partie de la requête qui lit le stock des unités légales.

    Entrée : un nombre maximal d'unités légales (limite), pour tester sur un échantillon.
    Sortie : le texte SQL d'un SELECT.
    """
    requete = f"""
        SELECT siren, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale,
               activitePrincipaleNAF25UniteLegale, dateCreationUniteLegale,
               trancheEffectifsUniteLegale, categorieEntreprise,
               categorieJuridiqueUniteLegale, etatAdministratifUniteLegale,
               dateDebut AS date_debut_etat  -- date du dernier changement d'état (ex. cessation)
        FROM read_parquet('{config.URL_SIRENE}')
        -- unités actives, ou cessées depuis la date choisie (date inconnue : on garde)
        WHERE etatAdministratifUniteLegale = 'A'
           OR dateDebut >= DATE '{config.DATE_MIN_CESSATION_SIRENE}'
           OR dateDebut IS NULL
    """
    if limite is not None:
        requete = requete + f"LIMIT {limite}"
    return requete


def construire_requete_sieges():
    """Écrit la partie de la requête qui lit la commune du siège dans le stock des établissements."""
    return f"""
        SELECT siren, codeCommuneEtablissement AS code_commune_siege
        FROM read_parquet('{config.URL_SIRENE_ETABLISSEMENTS}')
        WHERE etablissementSiege  -- un seul siège par SIREN
    """


def construire_requete_sirene(limite=None):
    """Assemble la requête complète : unités légales, département du siège et section NAF.

    Sortie : le texte de la requête. La table table_divisions doit avoir été
    déclarée dans la connexion DuckDB (voir extraire_sirene).
    """
    return f"""
        WITH unites AS ({construire_requete_unites_legales(limite)}),
             sieges AS ({construire_requete_sieges()})
        SELECT
            unites.*,
            sieges.code_commune_siege,
            CASE
                WHEN left(code_commune_siege, 2) IN ('97', '98')
                    THEN left(code_commune_siege, 3)  -- outre-mer : 3 caractères (971...)
                ELSE left(code_commune_siege, 2)      -- métropole, Corse comprise (2A, 2B)
            END AS departement,                       -- NULL si siège à l'étranger
            divisions.section_naf,
            divisions.libelle_section
        FROM unites
        LEFT JOIN sieges ON unites.siren = sieges.siren
        -- la section n'est définie que pour les codes en NAF rév. 2
        LEFT JOIN table_divisions AS divisions
            ON unites.nomenclatureActivitePrincipaleUniteLegale = 'NAFRev2'
           AND left(unites.activitePrincipaleUniteLegale, 2) = divisions.division
    """


def extraire_sirene(limite=None):
    """Exécute la requête d'extraction et renvoie les unités légales dans un DataFrame.

    Les colonnes gardent le format Arrow (types_mapper) : avec environ 24 millions
    de lignes, c'est plusieurs fois moins de mémoire que le format pandas habituel.
    """
    connexion = ouvrir_connexion_duckdb()
    # Rend le DataFrame des divisions utilisable comme une table dans la requête SQL
    connexion.register("table_divisions", construire_table_divisions())
    table_arrow = connexion.sql(construire_requete_sirene(limite)).to_arrow_table()
    connexion.close()
    return table_arrow.to_pandas(types_mapper=pd.ArrowDtype)


def resumer_par_section(df_sirene):
    """Tableau de validation : nombre et part des unités légales par section NAF.

    Les unités sans section (anciennes nomenclatures) sont comptées à part.
    """
    df_resume = df_sirene.groupby(["section_naf", "libelle_section"], dropna=False).size()
    df_resume = df_resume.reset_index(name="nombre_unites")
    df_resume["part_en_pct"] = (100 * df_resume["nombre_unites"] / len(df_sirene)).round(1)
    return df_resume


def collecter_sirene():
    """Extrait SIRENE, l'enregistre sur S3 et affiche le tableau de validation."""
    df_sirene = extraire_sirene()
    sauvegarder_parquet_s3(df_sirene, config.CHEMIN_S3_SIRENE + "/sirene.parquet")
    print(resumer_par_section(df_sirene).to_string(index=False))
    return df_sirene


if __name__ == "__main__":
    collecter_sirene()
