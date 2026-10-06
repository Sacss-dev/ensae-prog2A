"""Étape 1 : tests d'accès aux sources de données.

Chaque fonction de test récupère un petit échantillon d'une source
et affiche le nombre de lignes et de colonnes obtenues.

Lancement, depuis la racine du dépôt :
    python -m scripts.tests_acces_sources
"""

import io
import os

import duckdb
import pandas as pd
import requests
import s3fs

import config

TAILLE_ECHANTILLON = 20  # nombre de lignes (ou de SIREN) demandées à chaque source
DELAI_MAX = 60  # secondes avant d'abandonner une requête HTTP
ANNEE_TEST = 2022  # année des annonces BODACC testées (bilans INPI bien couverts avant)


def afficher_resume(nom_source, df):
    """Affiche le nombre de lignes et de colonnes d'un échantillon, et ses premières colonnes."""
    print(f"  {nom_source} : {len(df)} lignes, {len(df.columns)} colonnes")
    print(f"  Premières colonnes : {list(df.columns[:8])}")


def interroger_api_opendatasoft(url, parametres):
    """Interroge une API OpenDataSoft (BODACC, data.economie) et renvoie la réponse JSON.

    Entrées : l'URL du jeu de données et un dictionnaire de paramètres de requête.
    Sortie : un dictionnaire avec notamment "total_count" et "results".
    """
    reponse = requests.get(url, params=parametres, timeout=DELAI_MAX)
    reponse.raise_for_status()  # erreur explicite si le serveur renvoie un code 4xx ou 5xx
    return reponse.json()


def recuperer_echantillon_bodacc(annee):
    """Renvoie un DataFrame de 100 annonces de procédures collectives publiées une année donnée."""
    parametres = {
        # Syntaxe ODSQL de l'API : filtre sur la famille d'annonce et l'année de parution
        "where": f'familleavis="collective" AND year(dateparution)={annee}',
        "limit": 100,  # maximum autorisé par appel
    }
    reponse = interroger_api_opendatasoft(config.URL_BODACC, parametres)
    print(f"  BODACC {annee} : {reponse['total_count']} annonces de procédures collectives au total")
    return pd.DataFrame(reponse["results"])


def tester_bodacc():
    """Teste les deux accès au BODACC : la pagination classique et l'export parquet."""
    df_annonces = recuperer_echantillon_bodacc(ANNEE_TEST)
    afficher_resume("BODACC (records)", df_annonces)

    # L'export renvoie tout le résultat d'un coup : on le teste sur une seule journée
    parametres = {"where": "familleavis=\"collective\" AND dateparution=date'2022-06-15'"}
    reponse = requests.get(config.URL_BODACC_EXPORT_PARQUET, params=parametres, timeout=DELAI_MAX)
    reponse.raise_for_status()
    df_export = pd.read_parquet(io.BytesIO(reponse.content))  # le fichier reste en mémoire
    afficher_resume("BODACC (export parquet, 15 juin 2022)", df_export)


def tester_ratios_entreprises():
    """Teste l'API des ratios financiers BCE/INPI par entreprise."""
    reponse = interroger_api_opendatasoft(config.URL_RATIOS_BCE_INPI, {"limit": TAILLE_ECHANTILLON})
    print(f"  Ratios BCE/INPI : {reponse['total_count']} bilans au total")
    afficher_resume("Ratios BCE/INPI", pd.DataFrame(reponse["results"]))


def tester_ratios_sectoriels():
    """Teste l'API des percentiles sectoriels des ratios (q10 à q90)."""
    reponse = interroger_api_opendatasoft(config.URL_RATIOS_SECTORIELS, {"limit": TAILLE_ECHANTILLON})
    print(f"  Ratios sectoriels : {reponse['total_count']} lignes au total")
    afficher_resume("Ratios sectoriels", pd.DataFrame(reponse["results"]))


def ouvrir_connexion_duckdb():
    """Ouvre une connexion DuckDB capable de lire des fichiers parquet sur Internet."""
    connexion = duckdb.connect()
    # httpfs : extension qui lit un fichier en ligne par morceaux, sans le télécharger en entier
    connexion.sql("INSTALL httpfs")
    connexion.sql("LOAD httpfs")
    return connexion


def lire_echantillon_parquet(url):
    """Renvoie les premières lignes d'un fichier parquet en ligne, sous forme de DataFrame."""
    connexion = ouvrir_connexion_duckdb()
    requete = f"""
        SELECT *
        FROM read_parquet('{url}')
        LIMIT {TAILLE_ECHANTILLON}  -- DuckDB ne lit que le premier morceau du fichier
    """
    return connexion.sql(requete).df()


def tester_bilans_inpi():
    """Teste la lecture partielle du parquet des bilans INPI (2,8 Go)."""
    df_bilans = lire_echantillon_parquet(config.URL_BILANS_INPI)
    afficher_resume("Bilans INPI", df_bilans)
    # La colonne liasse associe chaque code de poste fiscal à sa valeur
    nombre_postes = len(df_bilans.loc[0, "liasse"])
    print(f"  Exemple : le 1er bilan contient {nombre_postes} postes de liasse")


def tester_sirene():
    """Teste la lecture partielle du stock SIRENE et la présence des colonnes utiles."""
    df_sirene = lire_echantillon_parquet(config.URL_SIRENE)
    afficher_resume("SIRENE", df_sirene)
    colonnes_utiles = [
        "siren",
        "activitePrincipaleUniteLegale",  # code NAF
        "dateCreationUniteLegale",
        "trancheEffectifsUniteLegale",
        "categorieEntreprise",
    ]
    for colonne in colonnes_utiles:
        if colonne not in df_sirene.columns:
            raise ValueError(f"colonne absente de SIRENE : {colonne}")
    print(f"  Colonnes utiles toutes présentes : {colonnes_utiles}")


def tester_contexte_insee():
    """Teste l'API BDM de l'INSEE sur la série trimestrielle des défaillances."""
    url = config.URL_INSEE_BDM + config.IDBANK_DEFAILLANCES
    reponse = requests.get(url, params={"lastNObservations": 8}, timeout=DELAI_MAX)
    reponse.raise_for_status()
    # Réponse en XML : chaque balise <Obs> est une observation (un trimestre)
    df_serie = pd.read_xml(io.StringIO(reponse.text), xpath=".//Obs", parser="etree")
    afficher_resume("INSEE, défaillances trimestrielles", df_serie)
    print(df_serie[["TIME_PERIOD", "OBS_VALUE"]].to_string(index=False))


def tester_acces_s3():
    """Écrit, relit puis supprime un petit fichier sur le S3 du SSP Cloud."""
    if config.BUCKET_S3 == "a-completer":
        raise ValueError("BUCKET_S3 n'est pas encore renseigné dans config.py")
    if "AWS_S3_ENDPOINT" not in os.environ:
        raise ValueError("variables S3 absentes : ce test ne tourne que sur le SSP Cloud")
    # s3fs lit seul les clés AWS_ACCESS_KEY_ID, etc. dans les variables d'environnement
    stockage = s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": "https://" + os.environ["AWS_S3_ENDPOINT"]}
    )
    chemin = f"{config.BUCKET_S3}/{config.DOSSIER_S3}/test_acces.txt"
    with stockage.open(chemin, "w") as fichier:
        fichier.write("test")
    with stockage.open(chemin, "r") as fichier:
        contenu = fichier.read()
    stockage.rm(chemin)  # on ne laisse pas traîner le fichier de test
    print(f"  S3 : écriture et relecture réussies ({contenu!r}) dans {chemin}")


def extraire_siren_bodacc(df_annonces, nombre):
    """Tire au hasard `nombre` SIREN distincts parmi des annonces BODACC.

    La colonne registre contient le SIREN sous deux formes, dans un ordre variable :
    ['887736767', '887 736 767'] ou ['887 736 767', '887736767'].
    On prend donc le premier élément et on retire les espaces.
    """
    df_avec_siren = df_annonces.dropna(subset=["registre"])
    serie_siren = df_avec_siren["registre"].str[0].str.replace(" ", "")
    serie_siren = serie_siren.drop_duplicates()
    echantillon = serie_siren.sample(n=nombre, random_state=config.GRAINE_ALEATOIRE)
    return list(echantillon)


def compter_siren_presents(url, liste_siren):
    """Compte combien des SIREN donnés apparaissent au moins une fois dans un parquet en ligne."""
    connexion = ouvrir_connexion_duckdb()
    # Transforme ['111', '222'] en texte SQL : '111', '222'
    liste_sql = ", ".join(f"'{siren}'" for siren in liste_siren)
    requete = f"""
        SELECT count(DISTINCT siren)       -- chaque entreprise n'est comptée qu'une fois
        FROM read_parquet('{url}')
        WHERE siren IN ({liste_sql})
    """
    return connexion.sql(requete).fetchone()[0]


def verifier_siren_communs():
    """Vérifie qu'un échantillon de SIREN du BODACC se retrouve dans INPI et dans SIRENE."""
    df_annonces = recuperer_echantillon_bodacc(ANNEE_TEST)
    liste_siren = extraire_siren_bodacc(df_annonces, TAILLE_ECHANTILLON)
    nb_inpi = compter_siren_presents(config.URL_BILANS_INPI, liste_siren)
    nb_sirene = compter_siren_presents(config.URL_SIRENE, liste_siren)
    print(f"  Sur {len(liste_siren)} SIREN tirés dans le BODACC {ANNEE_TEST} :")
    print(f"  {nb_inpi} ont au moins un bilan INPI, {nb_sirene} sont dans SIRENE")


def lancer_test(nom_test, fonction_test):
    """Exécute un test sans arrêter le script en cas d'erreur, et renvoie son statut."""
    print(f"\n=== {nom_test} ===")
    try:
        fonction_test()
        return "OK"
    except Exception as erreur:  # une source en panne ne doit pas bloquer les autres tests
        print(f"  ÉCHEC : {erreur}")
        return f"ÉCHEC : {str(erreur)[:80]}"


def main():
    """Lance tous les tests puis affiche un tableau récapitulatif."""
    tests = [
        ("BODACC", tester_bodacc),
        ("Bilans INPI", tester_bilans_inpi),
        ("Ratios BCE/INPI", tester_ratios_entreprises),
        ("Ratios sectoriels", tester_ratios_sectoriels),
        ("SIRENE", tester_sirene),
        ("Contexte INSEE", tester_contexte_insee),
        ("Stockage S3", tester_acces_s3),
        ("SIREN communs", verifier_siren_communs),
    ]
    lignes_recapitulatif = []
    for nom_test, fonction_test in tests:
        statut = lancer_test(nom_test, fonction_test)
        lignes_recapitulatif.append({"test": nom_test, "statut": statut})
    print("\n=== Récapitulatif ===")
    print(pd.DataFrame(lignes_recapitulatif).to_string(index=False))


if __name__ == "__main__":
    main()
