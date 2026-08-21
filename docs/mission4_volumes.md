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

## Périmètre de mesure

Le 25 octobre, **version 1 uniquement**. La table porte trois versions de prévision, dont une seule
couvre l'ensemble du portefeuille :

| Version | Sites | Jours | Lignes |
|---|---|---|---|
| 1 | **500** | 365 | 4 374 240 |
| 2 | 110 | 365 | 963 600 |
| 3 | 50 | 365 | 437 280 |

Les laisser toutes trois mêlerait deux effets, la collision et la superposition de versions, et aucune
mesure ne dirait lequel produit quoi. La superposition est le sujet de la question 3 ; ici elle est
neutralisée en fixant la version 1, la seule complète.

Le périmètre compte donc **12 500 lignes**, soit 500 sites multipliés par les 25 heures du jour. Le
compte confirme à la maille de la ligne ce que la question 1 avait établi à la maille des valeurs
distinctes.

## Prédiction

**La somme naïve est juste.** Une somme parcourt les lignes et n'utilise aucune colonne comme clé. Les
25 heures réellement livrées sont présentes en 25 lignes par site, toutes additionnées.

**L'agrégation par `delivery_hour_local` est fausse dans sa décomposition et juste dans son total.**
Elle rend 24 lignes au lieu de 25. Le total est identique, par l'invariance de la somme sous
regroupement. Mais la ligne portant `2026-10-25 02:00` agrège deux heures de livraison distinctes,
celles d'indices 3 et 4, et affiche donc environ le double de ses voisines.

## Mesure

| Lecture | Lignes en sortie | Total MWh |
|---|---|---|
| sans regroupement | **12 500** | **812 269,3** |
| groupé par `hour_index` | **25** | **812 269,3** |
| groupé par `delivery_hour_local` | **24** | **812 269,3** |

Écart de total entre les trois lectures : **zéro** à la précision machine. Écart de lignes entre les
deux clés : **une heure perdue**.

Le profil horaire autour de la collision montre le mécanisme à nu :

| `hour_index` | `delivery_hour_local` | Volume MWh |
|---|---|---|
| 1 | 2026-10-25 00:00 | 23 896,5 |
| 2 | 2026-10-25 01:00 | 26 395,2 |
| **3** | **2026-10-25 02:00** | **25 720,2** |
| **4** | **2026-10-25 02:00** | **25 517,9** |
| 5 | 2026-10-25 03:00 | 26 439,2 |
| 6 | 2026-10-25 04:00 | 28 022,0 |

La ligne collisionnée agrège **1 000 lignes d'origine**, soit les 500 sites multipliés par les deux
heures réelles, pour un volume de **51 238,1 MWh**. Cette valeur est exactement la somme des indices 3
et 4, et vaut **1,94 fois** la moyenne des heures voisines, les indices 2 et 5.

## Somme naïve

**Juste.** Le total de 812 269,3 MWh est le vrai volume livré ce jour-là. Le fait que la journée
compte 25 heures et non 24 ne dérange pas une somme : elle additionne ce qui existe, sans hypothèse
sur le nombre de termes.

Un contrôle qui ne regarderait que ce total déclarerait la journée saine.

## Agrégation par `delivery_hour_local`

**Total juste, décomposition fausse.** C'est le point de la question, et il est général : pour une
grandeur extensive, la somme est **invariante** par tout regroupement, injectif ou non, puisque les
groupes partitionnent les lignes.

$$\sum_{g} \ \sum_{t \in T_g} v(t) \ = \ \sum_{t \in T} v(t)$$

Ce qui se perd n'est pas le total mais le **cardinal** : le regroupement rend
$\lvert \pi_c(T) \rvert$ lignes, et cette quantité est strictement inférieure au nombre d'heures
réelles dès que la clé n'est pas injective.

Concrètement, le profil horaire produit porte une pointe fictive de près du double à 2 heures, et une
heure a disparu. C'est ce profil, et non le total, que le desk utilise pour dimensionner sa
couverture.

## Ce que la différence enseigne

Les deux défauts possibles d'une agrégation sont **symétriques**, et aucun contrôle unique ne les
attrape tous les deux.

| Défaut | Total | Décomposition | Contrôle qui l'attrape |
|---|---|---|---|
| explosion de jointure | **faux** | juste | contrôle de total |
| fusion par clé non injective | juste | **fausse** | contrôle de cardinal |

La Mission 1 avait rencontré le premier : la jointure naïve produisait 9 495 lignes pour 8 850 deals,
chaque ligne restant individuellement correcte tandis que le total enflait. La Mission 4 rencontre le
second, exactement à l'envers.

**Il faut donc les deux contrôles.** Un harnais qui ne vérifie que les totaux valide une décomposition
fausse ; un harnais qui ne vérifie que les cardinaux valide un total faux.

La règle générale, formalisée dans `formalisation_controles.md`, sections 7 et 11 : avant d'agréger
par une colonne, vérifier qu'elle est injective à la maille visée ; avant de joindre, vérifier
l'unicité de la clé des deux côtés.

## Décision de traitement

**Ne jamais agréger sur `delivery_hour_local`.** La clé horaire du portefeuille est le couple
`delivery_date` et `hour_index`, injectif par site et par version, vérifié à la question 1.

`delivery_hour_local` reste utilisable pour l'**affichage** à destination d'un humain, où l'ambiguïté
d'une heure par an est sans conséquence, jamais comme clé de calcul.

*Alternative écartée* : désambiguïser la colonne en lui adjoignant le décalage UTC, ce qui la rendrait
injective. Écartée parce que l'information du décalage n'est pas dans la table : elle devrait être
reconstruite depuis `hour_index`, qui est déjà la clé cherchée. Reconstruire une clé fiable à partir
d'une clé fiable pour réparer une clé ambiguë n'a pas d'intérêt.

## Contrôle de la section

| Contrôle | Nature | Résultat |
|---|---|---|
| lignes du périmètre | référence | 12 500 |
| heures réelles et étiquettes locales | référence | 25 et 24 |
| total conservé sous les trois lectures | invariant | écart nul à 10⁻⁶ MWh près |
| étiquettes locales collisionnées | référence | 1 |
| heures réelles fusionnées sous cette étiquette | référence | 2 |
| lignes d'origine fusionnées | référence | 1 000 |
| volume fusionné égal à la somme des deux heures | **invariant** | vérifié |

Le dernier est le contrôle central : il prouve que la fusion est bien le mécanisme à l'oeuvre, et non
une coïncidence de volumétrie. Les autres constatent, celui-ci démontre.

Deux points de méthode retenus en l'écrivant :

**Comparer une pointe à la bonne référence.** Rapportée à la moyenne des 23 autres heures de la
journée, la ligne fusionnée ne vaut que 1,55 fois la référence, parce que les heures de jour sont
bien plus grosses que celles du milieu de nuit. Rapportée aux heures **voisines**, elle vaut 1,94
fois. La première mesure sous-estime l'anomalie d'un tiers en changeant de population de référence.

**Ne jamais comparer deux flottants par égalité.** Les deux totaux coïncident, mais à une erreur de
représentation près. Le contrôle compare leur écart absolu à une tolérance explicite.

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
