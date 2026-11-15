"""Étape 3 : collecte des bilans INPI (données financières détaillées, Signaux Faibles).

Le parquet source contient une ligne par bilan et une colonne liasse qui associe
chaque code de poste fiscal à sa valeur. On en extrait une colonne par code utile,
pour les clôtures de la période de collecte, puis on enregistre l'extrait sur S3.

Lancement, depuis la racine du dépôt (sur le SSP Cloud) :
    python -m src.collecte.bilans
"""

import config
from src.collecte.stockage_s3 import ouvrir_connexion_duckdb, sauvegarder_parquet_s3


def construire_colonnes_postes(liste_codes):
    """Transforme une liste de codes de poste en morceaux de SQL, un par code.

    Entrée : une liste de codes, par exemple ["FL", "210"].
    Sortie : une liste de textes, par exemple ["liasse['FL'] AS poste_FL", ...].
    Un code absent de la liasse d'un bilan donne NULL (et non 0).
    """
    colonnes_sql = []
    for code in liste_codes:
        colonnes_sql.append(f"liasse['{code}'] AS poste_{code}")
    return colonnes_sql


def construire_requete_bilans(annee_debut, annee_fin, limite=None):
    """Écrit la requête SQL qui extrait les bilans et les postes utiles.

    Entrées : les années de clôture de début et de fin (incluses), et un nombre
    maximal de lignes (limite) pour tester la requête sur un petit échantillon.
    Sortie : le texte de la requête.
    """
    codes = config.CODES_LIASSE_C + config.CODES_LIASSE_S
    colonnes_postes = ",\n            ".join(construire_colonnes_postes(codes))
    requete = f"""
        SELECT
            siren,
            date_cloture_exercice,
            type_bilan,                            -- C, S ou K
            confidentiality,                       -- statut de confidentialité
            cardinality(liasse) AS nombre_postes,  -- nombre de postes renseignés (partie 5)
            {colonnes_postes}
        FROM read_parquet('{config.URL_BILANS_INPI}')
        -- on garde tous les types de bilan et tous les statuts de confidentialité
        WHERE year(date_cloture_exercice) BETWEEN {annee_debut} AND {annee_fin}
    """
    if limite is not None:
        requete = requete + f"LIMIT {limite}"
    return requete


def extraire_bilans(limite=None):
    """Exécute la requête d'extraction et renvoie les bilans dans un DataFrame.

    Attention : sans limite, DuckDB lit toute la colonne liasse (environ 2,8 Go).
    À lancer sur le SSP Cloud, une seule fois.
    """
    connexion = ouvrir_connexion_duckdb()
    requete = construire_requete_bilans(
        config.ANNEE_DEBUT_COLLECTE_BILANS, config.ANNEE_FIN_COLLECTE_BILANS, limite
    )
    df_bilans = connexion.sql(requete).df()
    connexion.close()
    return df_bilans


def resumer_extrait(df_bilans):
    """Compte les bilans et les SIREN distincts par année de clôture et par type de bilan.

    Entrée : le DataFrame renvoyé par extraire_bilans.
    Sortie : un DataFrame avec une ligne par couple (année, type de bilan).
    """
    df_resume = df_bilans.assign(annee_cloture=df_bilans["date_cloture_exercice"].dt.year)
    df_resume = df_resume.groupby(["annee_cloture", "type_bilan"]).agg(
        nombre_bilans=("siren", "size"),  # nombre de lignes
        nombre_siren=("siren", "nunique"),  # nombre d'entreprises distinctes
    )
    return df_resume.reset_index()


def collecter_bilans():
    """Extrait les bilans, les enregistre sur S3 et affiche le tableau de validation."""
    df_bilans = extraire_bilans()
    sauvegarder_parquet_s3(df_bilans, config.CHEMIN_S3_BILANS + "/bilans.parquet")
    print(resumer_extrait(df_bilans).to_string(index=False))
    return df_bilans


if __name__ == "__main__":
    collecter_bilans()
