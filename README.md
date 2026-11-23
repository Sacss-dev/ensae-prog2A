# Voit-on venir la faillite ?

Projet du cours « Python pour la data science » (ENSAE, 2A).

## Problématique

Les entreprises défaillantes présentent-elles des signaux financiers dégradés dans les années qui précèdent leur défaillance, et ces signaux sont-ils assez nets pour être repérés à l'avance ?

## Sources de données

Toutes les données partent de sources publiques ; leurs adresses sont dans `config.py`.

| Source | Contenu utilisé | Accès | Années collectées |
|---|---|---|---|
| BODACC, annonces commerciales (DILA) | Jugements de procédures collectives (sauvegarde, redressement, liquidation) | API OpenDataSoft, export parquet | Annonces publiées de 2017 à 2025 |
| Données financières détaillées INPI (Signaux Faibles) | Postes de la liasse fiscale par SIREN et date de clôture | Parquet sur data.gouv.fr, lu avec DuckDB | Clôtures de 2015 à 2025 |
| SIRENE, stock des unités légales (INSEE) | Activité (NAF), date de création, effectifs, catégorie juridique | Parquet sur data.gouv.fr, lu avec DuckDB | Stock actuel |
| SIRENE, stock des établissements (INSEE) | Commune du siège (département) | Parquet sur data.gouv.fr, lu avec DuckDB | Stock actuel |
| INSEE, Banque de données macroéconomiques | Série trimestrielle des défaillances, par date de jugement (idbank 001656164) | API BDM, sans clé | Série entière (depuis 1990) |
| Contours des départements | Carte de la partie 2 | `cartiflette` | 2024 |

Les rangs sectoriels (partie 3) sont calculés à partir des bilans INPI eux-mêmes, et non avec l'API des
ratios sectoriels BCE/INPI testée à l'étape 1 : on garde ainsi les mêmes définitions de ratios partout.

## Reproduire les résultats

Sur un service VSCode ou Jupyter du SSP Cloud :

```bash
git clone <url-du-depot>
cd ensae-prog2A
pip install -r requirements.txt
nb-clean add-filter  # une fois par clone : retire les sorties des notebooks à chaque commit
```

Puis ouvrir `rapport.ipynb` et lancer « Restart & Run All » (environ 3 minutes).

Le rapport relit les résultats intermédiaires enregistrés dans le dossier `diffusion/` des buckets S3 des
membres du groupe, qui est en lecture publique : il tourne sans aucune clé.

### Refaire toute la chaîne depuis les données brutes

Sur un service SSP Cloud avec au moins 16 Go de mémoire, depuis la racine du dépôt, dans cet ordre.
Chaque script enregistre son résultat dans le bucket indiqué dans `config.py` (`BUCKET_LUCAS`,
`BUCKET_OLIVIER`, `BUCKET_CLAUDIA`) : pour refaire la chaîne sur son propre compte, remplacer ces noms
par son identifiant SSP Cloud, puis rendre le dossier `diffusion/` de son bucket lisible publiquement.

| Ordre | Commande | Étape | Durée indicative |
|---|---|---|---|
| 0 | `python -m scripts.tests_acces_sources` | Vérifie l'accès aux sources (facultatif) | 2 min |
| 1 | `python -m src.collecte.bodacc` | Collecte des annonces BODACC | 5 min |
| 2 | `python -m src.collecte.bilans` | Extraction des bilans INPI | 10 à 30 min |
| 3 | `python -m src.collecte.sirene` | Extraction SIRENE (unités légales et sièges) | 5 min |
| 4 | `python -m src.collecte.contexte` | Série INSEE des défaillances | quelques secondes |
| 5 | `python -m src.nettoyage.nettoyage_bodacc` | Premier jugement d'ouverture par SIREN | quelques minutes |
| 6 | `python -m src.nettoyage.ratios` | Nettoyage des bilans et calcul des ratios | quelques minutes |
| 7 | `python -m src.nettoyage.base_analyse` | Base d'analyse (défaillantes et leurs bilans) | quelques minutes |
| 8 | `python -m src.analyse.temoins` | Appariement des témoins | quelques minutes |
| 9 | `python -m src.analyse.trajectoires` | Rangs sectoriels | 2 min |

Les identifiants S3 sont fournis automatiquement par le SSP Cloud sous forme de variables d'environnement : aucun secret n'est écrit dans le code.

## Organisation du dépôt

```
config.py                     # URL des sources, période d'étude, seuils, décisions du groupe
requirements.txt              # dépendances, versions fixées
src/collecte/
    stockage_s3.py            # lecture et écriture sur S3 (fonctions communes)
    bodacc.py                 # annonces BODACC
    bilans.py                 # bilans INPI
    sirene.py                 # SIRENE (unités légales, département du siège, section NAF)
    contexte.py               # série INSEE des défaillances
src/nettoyage/
    nettoyage_bodacc.py       # type et date du premier jugement par SIREN
    ratios.py                 # nettoyage des bilans, ratios, winsorisation
    base_analyse.py           # base d'analyse et horizons N-1 à N-4
src/analyse/
    temoins.py                # appariement des témoins
    graphiques.py             # fonctions de graphiques communes
    portrait.py               # partie 2 : portrait descriptif
    trajectoires.py           # partie 3 : trajectoires, rangs sectoriels, situations extrêmes
    heterogeneite.py          # partie 4 : trajectoires par sous-groupe
    silence_comptable.py      # partie 5 : comptes absents ou confidentiels
    regles_alerte.py          # partie 6 : règles d'alerte
scripts/tests_acces_sources.py  # tests d'accès aux sources (étape 1)
rapport.ipynb                 # rapport final
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

### Olivier CAFFIER
J'ai utilisé Claude Code (Anthropic) tout au long du projet, encadré notamment par le fichier 'Claude.md' placé à la racine du dépôt, qui fixait les règles de travail du groupe.

- **Code.** Le vibe coding n'étant pas autorisé, j'ai surtout utilisé l'I.A pour remettre en question mon utilisation des structures de données (n'étant pas encore très à l'aise je faisais souvent des erreurs ou des opérations trop longues sur des dataframes par exemple). Claude Code a aussi servi à séparer nos espaces en 3 pour qu'on ne s'écrive pas dessus, et a donc réparti les tâches du code, ce qui nous a grandement fait gagner du temps sur la longue. L'I.A nous aidait aussi à bien utiliser github au cas où nous n'arrivions pas à insérer les bonnes commandes dans le terminal etc, et elle écrivait les Pull Request afin que nous y voyions plus clair sur le travail des autres.

- **Écriture du rapport** Au delà de vérifier les chiffres, l'I.A a relu le `rapport.ipynb` en entier pour vérifier les chiffres et remettre en forme le notebook, en synthétisant au maximum nos formulations.
- **Débogage** La véritable force de Claude Code est qu'il peut lire nos outputs et notre code et nous pointer où se trouve l'erreur, ce gain de productivité s'est réellement fait ressentir.

Toutes les décisions de l'I.A ont dû passer par ma validation, surtout quand elle ré-écrivait ma fonction. 

- **Choix méthodologiques** Nous étions à l'initiative des choix méthodologique et des remises en question de certains résultats (
