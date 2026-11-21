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

Chaque étape est faite sur sa propre branche et fusionnée par une pull request.

| Étape | Contenu | Responsable |
|---|---|---|
| 0 | Mise en place du dépôt | Lucas |
| 1 | Tests d'accès aux sources | Lucas |
| 2 | Collecte BODACC | Lucas |
| 3 | Collecte des bilans INPI | Olivier |
| 4 | Collecte SIRENE et série INSEE | Olivier (prévue pour Claudia) |
| 5 | Nettoyage : bilans et ratios | Olivier |
| 5 | Nettoyage : jugements BODACC | Lucas |
| 6 | Base d'analyse et groupe témoin | Claudia |
| 7 | Portrait descriptif | Lucas (prévue pour Olivier) |
| 8 | Trajectoires des ratios | Olivier (prévue pour Lucas) |
| 9 | Hétérogénéité | Olivier (prévue pour Claudia) |
| 10 | Silence comptable | Olivier |
| 11 | Règles d'alerte | Lucas |
| 12 | Rédaction du rapport | Tous |
| 13 | Test de reproductibilité | Claudia |
| 14 | Préparation de la soutenance | Tous |

Les étapes 7 et 8 ont été échangées entre Lucas et Olivier : l'étape 8 a besoin du groupe
témoin de l'étape 6, alors que l'étape 7 pouvait commencer tout de suite.

## Usage de l'IA générative

*À compléter.*
