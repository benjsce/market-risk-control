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

### Prédiction

Une journée civile ne dure pas 24 heures les jours de changement d'heure. En Europe, la transition a
lieu le dernier dimanche de mars et le dernier dimanche d'octobre, soit en 2026 le **29 mars** et le
**25 octobre**. Au printemps l'horloge avance de 60 minutes à 2 heures, la journée dure **23 heures** ;
à l'automne elle recule de 60 minutes à 3 heures, la journée dure **25 heures**.

Prédiction faite avant toute mesure. Elle porte sur le calendrier réel, pas sur la table : une base de
données peut parfaitement stocker 24 heures ces deux jours-là et perdre une heure de livraison en
silence. C'est le premier doute à lever.

### Mesure

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

### Mécanisme physique

Le passage à l'heure d'été supprime une heure locale, le passage à l'heure d'hiver en duplique une.
Les deux transitions ne produisent pas le même défaut, et cette asymétrie est tout le sujet.

**Au printemps, un trou.** L'heure locale de 2 heures à 3 heures n'existe pas le 29 mars. Les deux
colonnes s'accordent à 23 : une valeur qui n'existe pas ne s'affiche simplement pas. Un trou est
inoffensif pour une agrégation, il ne fait rien fusionner.

**À l'automne, une collision.** L'heure locale de 2 heures à 3 heures existe deux fois le 25 octobre,
une première fois en heure d'été à UTC+2, une seconde en heure d'hiver à UTC+1. Ce sont deux heures de
livraison distinctes, séparées d'une heure réelle.

### Colonne fiable et colonne ambiguë

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

### Contrôle de la section

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

### Périmètre de mesure

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

### Prédiction

**La somme naïve est juste.** Une somme parcourt les lignes et n'utilise aucune colonne comme clé. Les
25 heures réellement livrées sont présentes en 25 lignes par site, toutes additionnées.

**L'agrégation par `delivery_hour_local` est fausse dans sa décomposition et juste dans son total.**
Elle rend 24 lignes au lieu de 25. Le total est identique, par l'invariance de la somme sous
regroupement. Mais la ligne portant `2026-10-25 02:00` agrège deux heures de livraison distinctes,
celles d'indices 3 et 4, et affiche donc environ le double de ses voisines.

### Mesure

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

### Somme naïve

**Juste.** Le total de 812 269,3 MWh est le vrai volume livré ce jour-là. Le fait que la journée
compte 25 heures et non 24 ne dérange pas une somme : elle additionne ce qui existe, sans hypothèse
sur le nombre de termes.

Un contrôle qui ne regarderait que ce total déclarerait la journée saine.

### Agrégation par `delivery_hour_local`

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

### Ce que la différence enseigne

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

### Décision de traitement

**Ne jamais agréger sur `delivery_hour_local`.** La clé horaire du portefeuille est le couple
`delivery_date` et `hour_index`, injectif par site et par version, vérifié à la question 1.

`delivery_hour_local` reste utilisable pour l'**affichage** à destination d'un humain, où l'ambiguïté
d'une heure par an est sans conséquence, jamais comme clé de calcul.

*Alternative écartée* : désambiguïser la colonne en lui adjoignant le décalage UTC, ce qui la rendrait
injective. Écartée parce que l'information du décalage n'est pas dans la table : elle devrait être
reconstruite depuis `hour_index`, qui est déjà la clé cherchée. Reconstruire une clé fiable à partir
d'une clé fiable pour réparer une clé ambiguë n'a pas d'intérêt.

### Contrôle de la section

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

### Couverture de chaque version

Trois versions coexistent, et elles ne couvrent pas le même portefeuille :

| Version | Sites | Jours | Lignes |
|---|---|---|---|
| 1 | **500** | 365 | 4 374 240 |
| 2 | **110** | 365 | 963 600 |
| 3 | **50** | 365 | 437 280 |

Le compte de versions par site donne **356 sites** à une seule version, **128** à deux et **16** aux
trois. Mais ce compte ne dit pas lesquelles. La combinaison réellement détenue est plus instructive :

| Versions détenues | Sites |
|---|---|
| {1} | 356 |
| {1, 2} | 94 |
| {1, 3} | 34 |
| {1, 2, 3} | 16 |

**La version 1 est toujours présente.** C'est le socle du portefeuille : toute règle de sélection peut
s'y replier, et aucun site n'existe sans elle. Les versions 2 et 3 sont des révisions partielles,
portant sur des sous-ensembles disjoints à 16 sites près.

### Complétude, par version

L'année 2026 compte **8 760 heures** : 365 jours de 24 heures, les 23 heures du 29 mars et les 25 du
25 octobre se compensant exactement.

Neuf couples site et version sont en deçà, tous à **8 040 heures**, soit un déficit de 720 heures ou
30 jours pleins :

| Version | Couples incomplets |
|---|---|
| 1 | 8 |
| 2 | 0 |
| 3 | 1 |

Huit sites sont concernés, pour **6 480 heures absentes** de la table. Sept d'entre eux ne détiennent
que la version 1. Le huitième, **S500318**, détient les versions 1 et 3, et les deux sont incomplètes.

### Le piège du `MAX(version)` par site

Le sujet annonce un piège de granularité. Il est réel, et il faut distinguer deux formes.

**La première forme est le maximum pris trop haut.** Le maximum global de `forecast_version` vaut 3,
et seuls 50 sites détiennent cette version. Filtrer dessus jette 450 sites sur 500. C'est la règle A,
et elle est catastrophique.

**La seconde forme est le maximum pris par site alors qu'une version tardive ne couvre qu'une partie
du calendrier.** Un site dont la version 3 ne porterait que 335 jours perdrait 30 jours de prévision
que sa version 1 fournissait, sans qu'aucun contrôle de cohérence ne le signale : la table filtrée
serait propre, simplement amputée.

Un seul site pouvait déclencher ce défaut, S500318, dont la version 3 est incomplète. Mesure de ses
deux calendriers :

| Version | Dates couvertes | Dates communes aux deux |
|---|---|---|
| 1 | **335** | **335** |
| 3 | **335** | |

Deux ensembles de même cardinal dont l'intersection a ce cardinal sont égaux : **les deux versions ont
exactement le même trou**, les mêmes 30 jours. Retenir la version 3 pour ce site ne perd donc rien, et
le trou relève de la question 6 et non de la sélection de version.

**Le piège ne se matérialise pas sur cet extrait.** C'est un résultat, pas une absence de résultat :
la règle par site est sûre ici, et on sait pourquoi. Elle ne le serait pas sur un extrait où une
révision partielle porterait sur un sous-ensemble de dates.

### Comparaison des trois règles

Base du taux : la règle C, posée à la maille la plus fine, donc tenue pour correcte.

| Lecture | Lignes | Sites | Total MWh | Écart à C |
|---|---|---|---|---|
| sans filtre | 5 775 120 | 500 | **347 013 213,3** | **+19,7 %** |
| **A**, max global = 3 | 437 280 | **50** | 9 929 072,5 | **-96,6 %** |
| **B**, max par site | 4 374 240 | 500 | **289 888 282,2** | 0 |
| **C**, max par site et heure | 4 374 240 | 500 | **289 888 282,2** | 0 |

**Sens et ampleur de l'erreur.** La somme sans filtre **surestime de 19,7 %**, soit **57 124 931 MWh**
comptés en double, parce que les heures des 144 sites multi-versions sont superposées deux ou trois
fois. Le sens est toujours la surestimation : une superposition ajoute des lignes, elle n'en retire
jamais.

**B et C sont strictement identiques**, vérifié par soustraction dans les deux sens, zéro ligne de
différence. C'est la conséquence directe du résultat précédent : chaque version tardive couvre
l'intégralité du calendrier de son site, et la seule exception a un trou identique dans sa version 1.
Descendre à la maille de l'heure n'apporte rien **ici**.

Un faux ami à signaler : la règle B retient 4 374 240 lignes, ce qui est aussi le compte de la
version 1 seule. Les populations sont différentes ; le nombre coïncide parce que dans les deux cas
exactement huit calendriers de site sont amputés de 720 heures.

### Règle retenue

**Règle C**, maximum de version à la maille site, date, indice horaire.

*Alternative écartée* : la règle B, par site. Elle donne exactement le même résultat sur cet extrait
et coûte moins cher, mais sa justesse **dépend d'une propriété des données** et non de sa
construction. Elle tomberait dès qu'une révision porterait sur un sous-ensemble de dates, ce qui est
un cas de production banal. La règle C est correcte par construction, quelle que soit la couverture
des versions.

*Alternative écartée* : la règle A, maximum global. Elle confond « la dernière version qui existe »
avec « la dernière version de ce site », et détruit 90 % du portefeuille.

### Un artefact de flottants, à ne pas prendre pour un écart

Les règles B et C retiennent les mêmes lignes, mais leurs totaux diffèrent de **7,15 × 10⁻⁷ MWh**,
soit un écart relatif de **2,4 × 10⁻¹⁵**. Le signe lui-même varie d'une exécution à l'autre.

Cause : **l'addition des flottants n'est pas associative**. Spark somme partition par partition, et le
découpage diffère entre un regroupement par site et un regroupement par triplet, donc l'ordre des
additions change et le dernier bit avec lui.

C'est la raison concrète pour laquelle tout contrôle de total se pose comme une comparaison à une
tolérance explicite, jamais comme une égalité. Voir `formalisation_controles.md`, section 15.

### Points laissés ouverts

**Le contenu des versions, point fermé.** Sur les 1 260 720 heures portant plus d'une version,
**1 259 414 changent de valeur d'une version à l'autre, soit 99,90 %** :

| Valeurs distinctes de volume sur le triplet | Triplets |
|---|---|
| 1 | 1 306 |
| 2 | 1 119 645 |
| 3 | 139 769 |
| **total** | **1 260 720** |

Le total retombe sur le nombre de triplets multi-versions, ce qui contrôle la mesure. Les révisions
sont donc authentiques : la sélection de version ne se contente pas de dédoublonner, elle **décide
quelle prévision fait foi**. Les 1 306 triplets à valeur unique, 0,10 %, sont des heures où la révision
est tombée sur la même valeur, sans qu'on puisse distinguer la coïncidence numérique de la recopie.

Le nombre de valeurs distinctes est borné par le nombre de versions présentes, d'où le domaine
{1, 2, 3}. Les triplets à trois valeurs appartiennent aux 16 sites détenant les trois versions.

**`as_of_date` est constante, donc muette.** Une seule date de production, 2026-07-24, identique pour
les trois versions sur les 5 775 120 lignes. Elle ne date pas la production de chaque prévision mais
l'extraction du fichier.

Conséquence à retenir : **rien dans la table ne permet de vérifier qu'une version est postérieure à une
autre.** On l'admet parce que le numéro est plus grand. Une table versionnée qui n'horodate pas ses
versions ne permet à personne de contrôler l'ordre des révisions ; c'est une remarque de qualité de
donnée à remonter au producteur.

Cela laisse l'hypothèse des trois campagnes de production non tranchée. Elle reste cohérente avec les
effectifs, les combinaisons {1}, {1,2}, {1,3} et {1,2,3} redonnant exactement 500, 110 et 50 sites par
campagne. La règle C est insensible à cette question, puisqu'elle ne compare jamais que des versions
d'une même cellule.

**Le contrôle de section n'a pas été écrit**, faute de temps. Il devrait vérifier que la table filtrée
par la règle retenue est injective sur le triplet site, date, indice horaire, et que les 500 sites
sont conservés. À reprendre avant la clôture de la mission.

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

### Périmètre

Toutes les mesures portent sur `volumes_retenus`, la table issue de la règle C de la question 3 :
**4 374 240 lignes**, **500 sites**, **289 888 282,2 MWh**. Sur la table brute, les 144 sites
multi-versions verraient leurs lignes négatives comptées deux ou trois fois.

### Les trois cas légitimes, posés avant de mesurer

Un volume négatif n'est **pas nécessairement une erreur**. Trois situations le rendent physiquement
légitime dans un portefeuille de clients professionnels.

**L'injection de production sur place.** Un site équipé de photovoltaïque ou de cogénération peut
produire plus qu'il ne consomme et renvoyer le surplus sur le réseau. Le comptage le voit comme un
soutirage négatif.

**Le déstockage.** Un site doté de stockage, batterie ou froid, restitue au réseau à certaines heures.

**Une convention de comptage nette.** Certaines chaînes de mesure enregistrent soutirage et injection
sur une même colonne signée plutôt que sur deux colonnes séparées.

Chacune de ces trois situations laisse une **signature mesurable**, et c'est ce qui permet de les
tester au lieu d'en débattre.

### Recensement

| Grandeur | Valeur |
|---|---|
| lignes de volume strictement négatif | **2 287** |
| part des lignes de la table de travail | **0,052 %**, une ligne sur 1 913 |
| sites concernés | **495 sur 500** |
| volume négatif cumulé | **-149 265,1 MWh** |
| part du volume du portefeuille | 0,051 % |

Base des taux : la table de travail, 4 374 240 lignes et 289 888 282,2 MWh.

Le premier chiffre remarquable est le nombre de sites : **99 % du portefeuille** porte au moins une
heure négative, pour moins de cinq heures par site en moyenne. Ce n'est déjà pas le profil d'un
injecteur, qui injecte régulièrement et sur des plages cohérentes.

### Les deux populations, puis leur disparition

La distribution des valeurs absolues fait d'abord croire à deux populations : médiane à 1,27 MWh,
troisième quartile à 2,69, mais maximum à 11 644,3, soit 9 200 fois la médiane. La moyenne, 65,27, est
tirée par cette queue et l'écart type vaut neuf fois la moyenne.

La comparaison avec les lignes positives dissout cette lecture :

| Statistique | Positifs, 4 371 953 lignes | Négatifs en valeur absolue, 2 287 lignes |
|---|---|---|
| minimum | 0,0365 | 0,0504 |
| premier quartile | 0,6045 | 0,574 |
| **médiane** | **1,2654** | **1,2653** |
| troisième quartile | 2,531 | 2,6869 |
| maximum | 14 524,3 | 11 644,3 |
| moyenne | 66,34 | 65,27 |
| écart type | 581,31 | 584,68 |

**Les deux distributions sont la même.** Les médianes coïncident à la quatrième décimale. Il n'y a pas
deux populations de négatifs, il y a un échantillon du portefeuille dont le signe a été retourné.

Le classement des sites par médiane le confirme à la maille du site : les sites en tête des négatifs
sont **les mêmes** que ceux en tête des positifs, dans presque le même ordre, S501142, S500688,
S500766, S501186. Un négatif y vaut ce qu'un positif y vaut.

*Erreur de lecture commise en chemin*, à noter parce qu'elle est instructive : la moyenne des négatifs,
65,27 MWh, avait d'abord été rapprochée de la moyenne du portefeuille, 66,34 MWh, pour conclure à une
inversion de signe. La conclusion était juste mais l'argument était faux, la moyenne étant ici dominée
par la queue. Sur une distribution à écart type neuf fois supérieur à la moyenne, **c'est la médiane et
les quartiles qui parlent**, pas la moyenne.

### Le test d'indépendance

Chacune des trois situations légitimes se réfute par un découpage, en comparant le taux de lignes
négatives du groupe au point neutre de **0,0523 %**.

| Découpage | Étendue du taux, pour 10 000 lignes | Ce que ça élimine |
|---|---|---|
| par `hour_index`, 25 groupes | 4,33 à 5,87 | l'injection photovoltaïque, qui culmine entre 8 et 18 heures et disparaît la nuit |
| par `month`, 12 groupes | 4,70 à 5,54 | toute production sur place, qui a une saisonnalité |
| par `commodity`, 2 groupes | GAS 5,16, POWER 5,27 | l'injection tout court : **le gaz ne peut pas être injecté** depuis un site de consommation raccordé à la distribution |

Les trois taux collent au point neutre. Le signe négatif est **indépendant de l'heure, de la saison et
de l'énergie**.

Le croisement avec `commodity` est le plus fort des trois, parce qu'il est une **contradiction
physique** et non une invraisemblance statistique : un point de livraison de gaz ne renvoie pas de
méthane dans le réseau de distribution. Même raisonnement que celui appliqué à `dso` en Mission 0.

### Verdict

Une **inversion de signe tirée au hasard**, affectant une ligne sur 1 913, sans lien avec le site,
l'heure, le mois ni l'énergie.

Aucun phénomène physique ne produit un défaut réparti uniformément sur tout ce qui devrait le
déterminer. C'est la signature d'un artefact de production de la donnée, exactement comme les attributs
descriptifs de `ref_site` en Mission 0.

### Impact

Une inversion de signe déplace la valeur de **deux fois** le montant, la valeur vraie étant l'opposée
de celle enregistrée.

| Grandeur | Valeur |
|---|---|
| lignes touchées | 2 287 |
| volume négatif enregistré | -149 265,1 MWh |
| **sous-estimation du portefeuille** | **298 530,1 MWh** |
| part du volume déclaré | **0,103 %** |

L'impact en lignes, 0,052 %, et l'impact en volume, 0,103 %, diffèrent d'un facteur exactement 2. Ce
n'est pas un hasard : les lignes fautives ayant la même distribution que les autres, leur poids en
volume est proportionnel à leur poids en lignes, et le facteur 2 est celui du retournement de signe.

### Décision de traitement

**Marquer, ne pas corriger en silence.** Les 2 287 lignes sont signalées dans la liste d'anomalies avec
leur impact, et le défaut est remonté à la source. Un moteur qui corrigerait sans le dire priverait le
producteur de l'information qui lui permettrait de ne pas reproduire le défaut.

**Publier les deux totaux**, déclaré et corrigé, plutôt qu'un seul. L'écart de 298 530,1 MWh est la
mesure de l'anomalie ; le masquer par une correction silencieuse le fait disparaître du rapport.

*Alternative écartée* : supprimer les lignes négatives. Elle sous-estimerait le portefeuille de
149 265,1 MWh au lieu de le sous-estimer de 298 530,1, donc améliorerait le chiffre tout en détruisant
de l'information. Une correction qui rapproche du bon résultat pour une mauvaise raison est pire qu'une
anomalie signalée.

*Alternative écartée* : corriger par valeur absolue dans la table de travail. Défendable pour un calcul
de couverture, mais alors la table corrigée doit être **distincte** de la table brute et le marquage
conservé, sinon la trace du défaut est perdue.

### La réserve

On a démontré que la **population** n'a aucune signature physique, pas que **chaque ligne** est fausse.
Un injecteur réel noyé dans les 2 287 resterait indétectable par ces trois tests, qui portent tous sur
des agrégats.

C'est le raisonnement du plancher de la Mission 0 appliqué en sens inverse : là, les lignes non
réfutées n'étaient pas validées ; ici, les lignes réfutées collectivement ne le sont pas
individuellement.

### Contrôle non fait

Après la jointure avec `ref_site`, le compte de lignes n'a pas été vérifié. Les taux obtenus le
suggèrent inchangé à 4 374 240, mais une jointure interne sur une clé non unique multiplierait les
lignes sans rien signaler. À ajouter.

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
