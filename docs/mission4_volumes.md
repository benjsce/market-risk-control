# Mission 4 - Qualité des volumes horaires

`data/volumes_hourly` contient 5,8 millions de lignes de prévisions horaires sur 500 sites. Le desk
s'appuie dessus pour dimensionner ses couvertures. Personne n'a jamais vérifié cette table.

Objectif : une batterie de contrôles de qualité. Chaque contrôle porte **une règle explicite, un
compte de violations, un impact volumétrique et une décision de traitement**.

Familles d'anomalies annoncées par le sujet : **9**.

Notebook associé : `notebooks/mission4_volumes.ipynb`.

## Sources

| Source | Contenu | État |
|---|---|---|
| `data/volumes_hourly` | Parquet partitionné par mois, prévisions horaires | non cadrée |
| `risk.db` → `ref_site` | référentiel des sites, cadré en Mission 0 | acquis |

Schéma de la table des volumes, lu à la source :

| Colonne | Type | Remarque |
|---|---|---|
| `site_id` | chaîne | clé du référentiel |
| `delivery_date` | chaîne | date de livraison, non parsée |
| `hour_index` | entier | rang de l'heure dans la journée |
| `delivery_hour_local` | chaîne | horodatage local, non parsé |
| `volume_mwh` | flottant | aucune colonne d'unité ne l'accompagne |
| `forecast_version` | entier | plusieurs versions coexistent |
| `as_of_date` | chaîne | date de production de la prévision |
| `month` | chaîne | **n'existe dans aucun fichier**, déduite du nom de dossier |

## Méthode

Identique aux missions 0 et 1. Rappel des règles transversales :

- une promesse en français, une prédiction chiffrée, puis la mesure ;
- le commit des prédictions précède le commit des résultats ;
- tout écart chiffré en nombre de lignes **puis** en MWh ;
- toute décision accompagnée de l'alternative écartée ;
- un agrégat qui tombe juste se décompose à la maille inférieure avant d'être accepté.

Spécifique à cette mission : **PySpark d'abord, pandas ensuite pour comparer**. C'est l'outil que le
maître d'alternance a explicitement demandé de travailler, et la dernière question du sujet ne se
répond qu'en ayant écrit les deux.

---

# Acquis des missions précédentes qui servent ici

## Du référentiel, Mission 0

`site_id` est une clé sûre, unique et sans orphelin. `contracted_capacity_kw` est la seule grandeur
numérique exploitable du référentiel et sert de **taille de référence par site** : c'est elle que la
question sur les unités désigne sans la nommer.

`commodity` a pour domaine `{GAS, POWER}` et est fiable. `dso`, `monitored` et `profile_type` sont
affectés au hasard : ne jamais joindre, filtrer ni regrouper dessus.

## Des mécanismes, Mission 1

**Sélection de version.** Sur `trd_deal`, ne pas sélectionner de version surestimait le volume de
15,1 %. Le mécanisme se rejoue ici avec une difficulté supplémentaire : la maille à laquelle
s'applique le maximum.

**Détection d'unité sans colonne d'unité.** 70 lignes du back office étaient en kWh, révélées par le
rapport de deux mesures de la même grandeur. Ici la grandeur de référence ne mesure pas la même
chose que le volume, donc le rapport sera bruité et la séparation devra être argumentée.

**Un extrait trié n'est pas un échantillon.** Deux généralisations fausses à partir de 15 lignes
affichées en Mission 1. Toute affirmation sur une population se mesure sur la population.

**Une clé d'agrégation non injective fusionne en silence.** C'est le miroir de l'explosion de
jointure : là, la décomposition restait juste et le total devenait faux ; ici, le total reste juste
et la décomposition devient fausse.

---

# Environnement

Session Spark en `local[*]` : un seul processus, autant de fils que de cœurs, aucun cluster, aucun
réseau. Démarrage mesuré à environ 4 secondes sur cette machine.

`spark.sql.session.timeZone` fixé à **UTC** délibérément. Les deux colonnes horaires sont des chaînes
de caractères : rien n'est converti à la lecture. Fixer le fuseau de session évite qu'une conversion
implicite réinterprète une date selon le fuseau de la JVM, ce qui rendrait le résultat dépendant de
la machine. Toute conversion vers `Europe/Paris` est donc explicite.

Volumétrie mesurée à la lecture : **5 775 120 lignes**, **500 sites**, 12 partitions mensuelles pour
18 Mo compressés.

---

# Questions à trancher

## 1. Combien d'heures compte une journée

> Vérifie-le sur les 365 jours de 2026 avant de répondre. Deux jours n'ont pas 24 heures. Explique le
> mécanisme physique, puis dis-moi laquelle des deux colonnes horaires est fiable et laquelle est
> ambiguë.

## Prédiction

Une journée civile ne dure pas 24 heures les jours de changement d'heure. En Europe, la transition a
lieu le dernier dimanche de mars et le dernier dimanche d'octobre, soit en 2026 le **29 mars** et le
**25 octobre**. Au printemps l'horloge avance de 60 minutes à 2 heures, la journée dure **23 heures** ;
à l'automne elle recule de 60 minutes à 3 heures, la journée dure **25 heures**.

Prédiction faite avant toute mesure. Elle porte sur le calendrier réel, pas sur la table : une base de
données peut parfaitement stocker 24 heures ces deux jours-là et perdre une heure de livraison en
silence. C'est le premier doute à lever.

## Mesure

Comptage, pour chaque jour de livraison, des valeurs distinctes des **deux** colonnes horaires. Les
compter séparément est ce qui répond aux deux moitiés de la question d'un seul coup.

Distribution sur les 365 jours :

| `heures_index` | `heures_locales` | Jours |
|---|---|---|
| 24 | 24 | **363** |
| 23 | 23 | **1** |
| 25 | 24 | **1** |

Détail des jours anormaux :

| Date | `hour_index` | `delivery_hour_local` |
|---|---|---|
| 2026-03-29 | **23** | **23** |
| 2026-10-25 | **25** | **24** |

La table respecte donc la réalité physique : elle stocke bien 23 heures le 29 mars et 25 heures le
25 octobre.

## Mécanisme physique

Le passage à l'heure d'été supprime une heure locale, le passage à l'heure d'hiver en duplique une.
Les deux transitions ne produisent pas le même défaut, et cette asymétrie est tout le sujet.

**Au printemps, un trou.** L'heure locale de 2 heures à 3 heures n'existe pas le 29 mars. Les deux
colonnes s'accordent à 23 : une valeur qui n'existe pas ne s'affiche simplement pas. Un trou est
inoffensif pour une agrégation, il ne fait rien fusionner.

**À l'automne, une collision.** L'heure locale de 2 heures à 3 heures existe deux fois le 25 octobre,
une première fois en heure d'été à UTC+2, une seconde en heure d'hiver à UTC+1. Ce sont deux heures de
livraison distinctes, séparées d'une heure réelle.

## Colonne fiable et colonne ambiguë

`hour_index` est **fiable**. C'est un rang positionnel dans la journée de livraison, qui suit le nombre
réel d'heures livrées : 23, 24 ou 25 selon le jour. Vérifié contigu à partir de 1 sur les 365 jours, et
unique à la maille site, date, version.

`delivery_hour_local` est **ambiguë**. Elle n'en compte que 24 le 25 octobre : la chaîne
`2026-10-25 02:00` porte deux lignes distinctes et ne permet pas de les séparer.

La raison tient en une phrase, et elle dépasse cette table : **un horodatage local sans son décalage
UTC n'est pas un identifiant.** Le même libellé d'horloge désigne deux instants réels une fois par an.
Ajouter le décalage, ou stocker l'instant en UTC, lèverait l'ambiguïté.

Volume de l'ambiguïté : **une heure sur 8 760**, soit un jour de l'année et une heure de ce jour. Elle
est minuscule et ce n'est pas ce qui compte, car elle ne se manifeste pas comme une erreur mais comme
une fusion silencieuse. C'est l'objet de la question 2.

## Contrôle de la section

Trois invariants et deux valeurs de référence, tous vérifiés :

| Contrôle | Nature | Résultat |
|---|---|---|
| jours de livraison distincts | invariant | 365 |
| jours où `hour_index` n'est pas un intervalle partant de 1 | invariant | 0 |
| groupes site/date/version où `hour_index` n'est pas unique | invariant | 0 |
| jours anormaux et leurs comptes d'heures | référence | 29 mars à 23, 25 octobre à 25 |
| jours où les deux colonnes divergent, et écart | référence | 1 jour, 1 heure |

Les deux derniers sont des valeurs de référence et non des invariants : ils sont liés à l'année 2026 et
tomberaient sur un autre extrait.

Deux pièges rencontrés en écrivant ce contrôle, formalisés dans `formalisation_controles.md` :

**L'étendue seule ne teste pas un rang.** L'identité entre le maximum moins le minimum plus un et le
compte distinct est invariante par translation : elle est vérifiée par un rang partant de 0 comme par
un rang partant de 1. La forme correcte est minimum égal à 1 **et** maximum égal au compte distinct,
qui a en outre l'avantage de s'adapter d'elle-même aux journées de 23 et 25 heures, là où un maximum
figé à 24 échouerait précisément sur les jours à contrôler.

**Un contrôle posé à la maille du jour ne prouve rien sur les sites.** La projection distincte commute
avec la réunion : un site auquel il manque une heure est invisible dès qu'un autre site la fournit.
D'où le second contrôle, posé à la maille site, date, version.

## 2. L'horodatage local dupliqué

> Une somme naïve sur cette journée est-elle fausse ? Et un `GROUP BY delivery_hour_local` ? Les deux
> réponses ne sont pas les mêmes, et c'est tout le sujet.

Prédiction :

> à remplir

Somme naïve :

> à remplir

Agrégation par `delivery_hour_local` :

> à remplir

Ce que la différence enseigne :

> à remplir

## 3. Les versions de prévision

> Une somme sans filtre donne un total faux. De combien, et dans quel sens ? Quelle règle de
> sélection retiens-tu, et pourquoi le `MAX(version)` par site est un piège si tu ne réfléchis pas à
> la granularité à laquelle tu l'appliques.

Couverture de chaque version :

> à remplir

Comparaison des trois règles :

| Règle | Maille du `MAX` | Total MWh | Écart au total brut |
|---|---|---|---|
| A | global | à remplir | à remplir |
| B | par site | à remplir | à remplir |
| C | par site et maille temporelle | à remplir | à remplir |

Règle retenue et alternative écartée :

> à remplir

## 4. Détection d'unité sans la colonne d'unité

> Comment le montres-tu proprement, sachant qu'aucune colonne ne l'indique ? Indice de méthode : tu
> disposes d'une grandeur de référence par site dans le référentiel.

Rapport de référence attendu, posé avant de mesurer :

> à remplir

Séparation des populations :

> à remplir

Sites suspects, volume déclaré et volume corrigé :

> à remplir

Sensibilité au seuil :

> à remplir

## 5. Les volumes négatifs

> Un volume négatif est-il nécessairement une erreur dans un portefeuille B2B ? Réponds en
> distinguant les cas, ne tranche pas d'un bloc.

Recensement :

> à remplir

Cas retenus et critère de séparation :

> à remplir

Décision de traitement par cas :

> à remplir

## 6. Les trous

> Détecte-les sans supposer a priori ce que devrait être la complétude : construis un calendrier de
> référence et fais une anti-jointure contre lui. Combien de sites, combien d'heures, quelle période ?

Construction du calendrier de référence :

> à remplir

Résultat de l'anti-jointure :

> à remplir

Caractérisation des manquants :

> à remplir

## 7. PySpark contre pandas

> Mesure le temps d'exécution des deux. Puis explique pourquoi le résultat te surprend, et ce que ça
> t'apprend sur le vrai critère de choix entre les deux.

Protocole de mesure :

> à remplir

Temps mesurés :

> à remplir

Explication et vrai critère de choix :

> à remplir

---

# Classification des anomalies

> à remplir : une ligne par famille, avec règle, compte de violations, impact MWh et décision

Familles annoncées : 9.

---

# Livrables

> à remplir
