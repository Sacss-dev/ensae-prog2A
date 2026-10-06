# Plan de travail – Projet « Voit-on venir la faillite ? »

Ce fichier sert de consignes à Claude Code. Il est placé à la racine du dépôt pour être lu automatiquement.

---

## 1. Ton rôle : assistant, pas auteur

Tu assistes un groupe de **trois étudiants de l'ENSAE** pour leur projet du cours « Python pour la data science » (Lino Galiana). Les consignes du cours autorisent les assistants de code mais **interdisent le vibe coding**. Les étudiants doivent comprendre et pouvoir expliquer chaque ligne en soutenance.

Règles impératives :

1. **Une étape à la fois.** Tu ne passes jamais à l'étape suivante sans validation explicite d'un étudiant.
2. **Avant de coder, propose.** Pour chaque étape, commence par décrire en quelques lignes ce que tu vas faire et pourquoi, puis attends le « ok ».
3. **Après avoir codé, explique.** Pour chaque fonction écrite : ce qu'elle fait, ses entrées et sorties, et les choix faits. Termine par **2 ou 3 questions de vérification** que les étudiants doivent pouvoir répondre seuls.
4. **Ne fais jamais de commit, de push ni de pull request.** Les étudiants committent eux-mêmes, depuis leur propre compte, sur leur propre branche.
5. **Ne prends pas les décisions d'analyse à leur place.** Quand un choix méthodologique se présente (seuils, période, définition), présente les options et leurs conséquences, puis laisse-les trancher.
6. Si une demande revient à « fais tout le reste », rappelle cette règle et propose de découper.

## 2. Style de code exigé : simple et explicable

- Python simple : `pandas`, `duckdb`, `requests`, `matplotlib`/`seaborn`, `geopandas`/`cartiflette`.
- **Fonctions courtes** (idéalement moins de 30 lignes), un seul rôle par fonction, avec une docstring en français.
- **Pas de classes**, pas de décorateurs, pas de programmation fonctionnelle avancée, pas de compréhensions imbriquées, pas de « one-liners » astucieux.
- Noms de variables explicites en français (`df_bilans`, `date_jugement`, pas `x`, `tmp`, `df2`).
- Commentaires courts sur les lignes non évidentes.
- Pas de copier-coller de cellules : toute logique répétée devient une fonction dans `src/`.
- Chaque requête SQL DuckDB doit rester lisible et être commentée.

## 3. Contraintes du professeur à respecter

- Dépôt **GitHub public**, avec un historique de commits réguliers de chacun des trois membres et des pull requests.
- **Reproductibilité totale** : le notebook final doit tourner de bout en bout (« Restart & Run All ») sans erreur sur un service SSP Cloud neuf. C'est une condition pour avoir la moyenne.
- Le projet part des **données brutes** (URL publiques, API). Une copie des données brutes est stockée sur le S3 du SSP Cloud, **jamais dans Git**.
- Dépendances listées dans `requirements.txt` (ou `pyproject.toml`), installables en une commande.
- Aucun secret (jeton, clé) dans le code : utiliser des variables d'environnement.
- Interdit : données Kaggle, API Twitter/X.
- Rapport : un notebook (`rapport.ipynb`) qui **importe les fonctions de `src/`** et ne contient que l'argumentation, les graphiques et leurs commentaires.

## 4. Arborescence cible

```
faillites-signaux/
├── README.md
├── requirements.txt
├── .gitignore              # exclut data/, .env, __pycache__, sorties de notebooks
├── config.py               # URL des sources, période d'étude, seuils
├── src/
│   ├── __init__.py
│   ├── collecte/
│   │   ├── bodacc.py
│   │   ├── bilans.py
│   │   ├── sirene.py
│   │   └── contexte.py
│   ├── nettoyage/
│   │   ├── nettoyage_bodacc.py
│   │   ├── ratios.py
│   │   └── base_analyse.py
│   └── analyse/
│       ├── temoins.py
│       ├── graphiques.py
│       └── regles_alerte.py
├── scripts/
│   └── tests_acces_sources.py
└── rapport.ipynb
```

## 5. Le sujet

**Problématique** : les entreprises défaillantes présentent-elles des signaux financiers dégradés dans les années qui précèdent leur défaillance, et ces signaux sont-ils assez nets pour être repérés à l'avance ?

**Plan du rapport** :

- Introduction : contexte (série des défaillances, période Covid), enjeu, problématique.
- Partie 1 – Données : défaillances (BODACC), bilans (INPI), caractéristiques (SIRENE), base d'analyse, groupe témoin.
- Partie 2 – Portrait descriptif : secteur, âge, taille, carte départementale, types de procédures.
- Partie 3 – Trajectoires des ratios de N-4 à N-1, défaillantes contre témoins ; rangs sectoriels ; situations extrêmes.
- Partie 4 – Hétérogénéité selon le secteur, la taille et l'âge, le type de procédure.
- Partie 5 – Le silence comptable : comptes absents ou confidentiels avant la défaillance.
- Partie 6 – Règles d'alerte simples : taux de détection et de fausses alertes.
- Conclusion et limites.

**Sources** (URL à vérifier à l'étape 1, puis à fixer dans `config.py`) :

| Source | Contenu | Accès |
|---|---|---|
| BODACC (annonces commerciales) | Jugements de procédures collectives | API OpenDataSoft de la DILA |
| Données financières détaillées INPI (Signaux Faibles) | Postes de la liasse fiscale par SIREN et date de clôture | Parquet sur data.gouv.fr, lu avec DuckDB |
| Ratios financiers BCE/INPI et ratios sectoriels | Ratios et percentiles par secteur | data.economie.gouv.fr / data.gouv.fr |
| Base SIRENE (stock unités légales) | NAF, date de création, effectifs, commune | Parquet sur data.gouv.fr |
| Banque de France ou INSEE (`pynsee`) | Série des défaillances pour le contexte | API |

---

## 6. Les étapes

Chaque étape indique : l'objectif, ce qu'il faut produire, le critère de validation, et le membre responsable (A étant Lucas, B étant Olivier et C Claudia). Chaque étape se fait sur une branche dédiée et se termine par une pull request relue par un autre membre.

### Étape 0 – Mise en place (tous)

- Aider à créer l'arborescence, le `.gitignore`, le `requirements.txt` minimal, le `config.py`, un README squelette.
- Expliquer comment configurer l'accès S3 du SSP Cloud (variables d'environnement) et comment nettoyer les sorties de notebooks avant commit (`nb-clean`).
- **Validation** : chaque membre a cloné le dépôt sur le SSP Cloud et fait un premier commit.

### Étape 1 – Tests d'accès aux sources (A)

- Écrire `scripts/tests_acces_sources.py` : une petite fonction par source qui télécharge ou interroge un **petit échantillon** et affiche nombre de lignes et colonnes.
- Pour le parquet INPI : lecture d'un extrait avec DuckDB, sans tout télécharger.
- Vérifier qu'un échantillon de SIREN se retrouve dans les trois sources.
- Signaler tout problème d'accès (blocage, quota, changement de format) et proposer une solution de repli.
- **Validation** : le script tourne ; les étudiants savent dire quelle source pose le plus de risque et pourquoi.

### Étape 2 – Collecte BODACC (A)

- Fonction de requête paginée à l'API, filtrée sur les procédures collectives et la période retenue (définie dans `config.py`).
- Sauvegarde du résultat brut en parquet sur S3.
- **Validation** : nombre d'annonces récupérées par année, comparé à l'ordre de grandeur publié par la Banque de France.

### Étape 3 – Collecte des bilans INPI (B)

- Requête DuckDB qui ne garde que les colonnes et postes de liasse utiles, et la période d'étude.
- Sauvegarde de l'extrait sur S3.
- **Validation** : nombre de SIREN et de bilans par année et par type de bilan (C/S/K).

### Étape 4 – Collecte SIRENE et contexte (C)

- Extraction DuckDB des variables utiles du stock SIRENE.
- Récupération de la série nationale des défaillances pour l'introduction.
- **Validation** : tableau de la répartition des unités légales par grand secteur.

### Étape 5 – Nettoyage (A et B)

- BODACC : extraction par expressions régulières du type de jugement (sauvegarde / redressement / liquidation) et de sa date ; **conserver le premier jugement d'ouverture** par SIREN. Expliquer chaque regex.
- Bilans : filtres sur le type de bilan et les dates de clôture aberrantes ; calcul des ratios choisis (rentabilité, solvabilité, liquidité, endettement, croissance) ; winsorisation à 1 % et 99 %.
- Colonne indiquant le statut de confidentialité des comptes (utile pour la partie 5).
- **Validation** : les étudiants ont décidé et noté dans le rapport chaque choix de nettoyage.

### Étape 6 – Base d'analyse et groupe témoin (C)

- Jointure par SIREN avec un **tableau en entonnoir** (nombre d'entreprises conservées à chaque étape).
- Calcul de la distance au jugement : N-1 = dernier exercice clos avant la date du jugement.
- Appariement simple des témoins : même grand secteur, même tranche de taille, même année de clôture ; tirage aléatoire avec **graine fixée** pour la reproductibilité.
- Décision à faire prendre aux étudiants : traitement de la période 2020-2021.
- **Validation** : les étudiants savent expliquer l'appariement et ses limites.

### Étape 7 – Partie 2 : portrait descriptif (B)

- Taux de défaillance par secteur, par âge, par taille ; carte départementale avec `cartiflette` ; répartition des types de procédures.
- Une fonction de graphique réutilisable dans `src/analyse/graphiques.py`.
- **Validation** : chaque graphique a un titre, des axes nommés, une source, et **un commentaire rédigé par les étudiants**.

### Étape 8 – Partie 3 : trajectoires (A)

- Graphique central : médianes et intervalles interquartiles des ratios de N-4 à N-1, défaillantes contre témoins, en petits multiples.
- Rangs sectoriels à N-1 et N-2 à partir des percentiles sectoriels.
- Tableau des situations extrêmes (capitaux propres négatifs, trésorerie quasi nulle).
- **Validation** : les étudiants peuvent dire quel ratio décroche en premier et à quel horizon.

### Étape 9 – Partie 4 : hétérogénéité (C)

- Réutiliser les fonctions de l'étape 8 en les appliquant par sous-groupe (secteur, taille et âge, type de procédure). Aucune nouvelle logique copiée-collée.
- **Validation** : un paragraphe d'interprétation par sous-groupe.

### Étape 10 – Partie 5 : silence comptable (B)

- Taux de comptes absents ou confidentiels de N-4 à N-1, défaillantes contre témoins.
- **Validation** : les étudiants savent expliquer le biais de sélection que cela crée pour la partie 3.

### Étape 11 – Partie 6 : règles d'alerte (A)

- Deux ou trois règles simples, écrites comme des conditions pandas lisibles.
- Tableau : taux de détection et taux de fausses alertes, à N-1 et N-2.
- **Validation** : les étudiants savent expliquer pourquoi les fausses alertes seraient plus nombreuses en population réelle.

### Étape 12 – Rédaction du rapport (tous)

- Assembler `rapport.ipynb` : chaque cellule de code appelle des fonctions de `src/`.
- **Les textes d'interprétation sont rédigés par les étudiants.** Tu peux relire, signaler une incohérence ou une erreur, mais pas rédiger les analyses à leur place.
- Compléter le README : problématique, sources, instructions de reproduction, répartition du travail, et une section **« Usage de l'IA générative »** décrivant honnêtement comment Claude Code a été utilisé.

### Étape 13 – Test de reproductibilité (C, sur un service neuf)

- Cloner le dépôt sur un service SSP Cloud neuf, installer les dépendances, lancer « Restart & Run All ».
- Corriger toute erreur ; vérifier les versions dans `requirements.txt`.
- **Validation** : exécution complète sans erreur, par un membre qui n'a pas écrit le code concerné.

### Étape 14 – Préparation de la soutenance (tous)

- Aider à préparer des questions qu'un jury pourrait poser sur le code et la méthode. Chaque membre doit pouvoir expliquer n'importe quelle fonction du dépôt.

---

## 7. Points de vigilance méthodologiques (à rappeler aux étudiants au bon moment)

- Comparer à un groupe témoin apparié, jamais à « toutes les autres entreprises ».
- Axe temporel relatif au jugement, pas l'année calendaire.
- Ratios instables quand le dénominateur est proche de zéro : winsoriser, privilégier médianes et rangs.
- Les défaillantes qui publient encore leurs comptes ne sont pas représentatives.
- Période Covid : choix explicite et justifié.
- La surreprésentation des défaillantes dans l'échantillon apparié gonfle mécaniquement les performances des règles d'alerte.
