# Voit-on venir la faillite ?

Projet du cours « Python pour la data science » (ENSAE, 2A).

## Problématique

Les entreprises défaillantes présentent-elles des signaux financiers dégradés dans les années qui précèdent leur défaillance, et ces signaux sont-ils assez nets pour être repérés à l'avance ?

## Sources de données

*À compléter après l'étape 1.*

| Source | Contenu | Accès |
|---|---|---|
| BODACC | Jugements de procédures collectives | API OpenDataSoft (DILA) |
| INPI (Signaux Faibles) | Postes de la liasse fiscale | Parquet, data.gouv.fr |
| Ratios BCE/INPI | Ratios et percentiles sectoriels | data.economie.gouv.fr |
| SIRENE | Secteur, âge, taille, localisation | Parquet, data.gouv.fr |
| Banque de France / INSEE | Série nationale des défaillances | API |

## Reproduire les résultats

Sur un service VSCode ou Jupyter du SSP Cloud :

```bash
git clone <url-du-depot>
cd ensae-prog2A
pip install -r requirements.txt
nb-clean add-filter  # une fois par clone : retire les sorties des notebooks à chaque commit
```

Puis ouvrir `rapport.ipynb` et lancer « Restart & Run All ».

Les identifiants S3 sont fournis automatiquement par le SSP Cloud sous forme de variables d'environnement : aucun secret n'est écrit dans le code.

## Organisation du dépôt

```
config.py        # URL des sources, période d'étude, seuils
src/collecte/    # téléchargement des données brutes
src/nettoyage/   # nettoyage, calcul des ratios, base d'analyse
src/analyse/     # groupe témoin, graphiques, règles d'alerte
scripts/         # scripts ponctuels (tests d'accès aux sources)
rapport.ipynb    # rapport final
```

## Répartition du travail

*À compléter.*

## Usage de l'IA générative

*À compléter.*
