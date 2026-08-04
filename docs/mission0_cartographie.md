# Mission 0 - Cartographie

Profiling systématique et reconstitution du modèle relationnel.
Date de référence du TP : **24 juillet 2026**. Année de livraison sous suivi : **2026**.

## Protocole

Ce découpage en quatre niveaux est une **méthode de travail personnelle**, pas une exigence du sujet.
Le README de la mission demande un profiling systématique et la reconstitution du modèle relationnel,
sans prescrire de démarche. Les niveaux ci-dessous sont l'ordre que j'ai choisi pour y arriver, et les
règles transversales sont la discipline que je m'impose pour que mes résultats soient opposables.

Appliqué à chaque table, dans cet ordre :

- **Niveau 0** - cadrer la table : que représente une ligne, à quelle maille, quelles clés candidates, combien de lignes attendues.
- **Niveau 1** - les colonnes, par ordre d'impact : clés et colonnes de jointure, puis mesures, puis descriptifs.
- **Niveau 2** - les relations entre tables : cardinalités, intégrité référentielle, orphelins.
- **Niveau 3** - la redondance entre sources : invariants, conventions, classification des écarts.

Règles transversales :

- Une promesse formulée en français **avant** toute requête.
- Une prédiction écrite **avant** toute exécution. Le commit de la prédiction précède le commit du résultat.
- Aucun résultat non prédit n'est une information.
- Tout écart chiffré, en nombre de lignes puis en MWh ou en euros. Jamais « faible » ni « négligeable ».
- Toute décision documentée avec l'alternative écartée.

### Réserve méthodologique

Les volumétries des 7 tables de `risk.db` et les cardinalités de `deal_id` sur `trd_deal` ont été
mesurées lors d'une exploration initiale, sans prédiction écrite préalable (commit `6a026d2`).
Ces chiffres sont connus mais ne sont pas opposables au titre du protocole. Le protocole s'applique
strictement à partir du Niveau 1 sur les tables de `risk.db`, et intégralement sur les sources Parquet
et l'extrait back office, qui n'ont pas encore été ouverts.

### Ordre de traitement

L'ordre ci-dessous découle d'un **graphe de références présumé**, et non vérifié. Il est déduit des seuls
noms de colonnes du dictionnaire de données du README : `ref_site` et `ref_contract` portent une colonne
`customer_id` qui n'est pas leur propre identifiant, `ref_customer` ne porte aucune colonne en `_id` autre
que la sienne. C'est une promesse de nom, à tester au Niveau 2, pas un fait acquis.

Deux limites connues de cette déduction :

- une clé étrangère n'est pas tenue de s'appeler `_id` - `dso` dans `ref_site` désigne vraisemblablement
  un gestionnaire de réseau de distribution, donc possiblement une référence vers un référentiel absent
  de la base ;
- une colonne nommée `customer_id` ne garantit pas qu'elle pointe effectivement vers `ref_customer`.
  C'est l'objet du Niveau 2 : intégrité référentielle et comptage des orphelins.

| # | Source | Motif présumé de la position |
|---|--------|------------------------------|
| 1 | `ref_customer` | racine présumée : aucune colonne suggérant une référence sortante |
| 2 | `ref_site` | porte `customer_id` |
| 3 | `ref_contract` | porte `customer_id` ; porte la question du lien site ↔ contrat |
| 4 | `trd_deal` | |
| 5 | `pos_snapshot` | |
| 6 | `mkt_forward_curve`, `mkt_spot_hourly` | |
| 7 | `volumes_hourly`, `actuals_daily` | |
| 8 | `bo_confirmations_20260724.csv` | |

Une clé étrangère ne se teste pas avant la table qu'elle référence : c'est ce qui fixe l'ordre 1-2-3, sous
réserve que le graphe présumé se confirme. S'il est infirmé, l'ordre est révisé - le coût de ce pari est nul.

---

# 1. `ref_customer`

## Niveau 0 - cadrage

**Que représente une ligne** (une phrase, nom au singulier) :

Une ligne représente l'état courant, et pas un historique, d'un client du portefeuille B2B France gaz et électricité. C'est l'entité juridique qui signe le contrat, unique.
Tout *customer_id* référencé dans `ref_site` ou `ref_contract` figure ici.

**Maille** :

Une ligne par client. Pas de *client × date*, pas de *client × site* ni de *client × contrat*.

**Clés candidates** (colonnes seules ou combinées qui devraient identifier une ligne) :

Clés candidates : 
- *customer_id*. 
- *customer_name* est une clé candidate **plausible mais non garantie** : un groupe est un ensemble de sociétés, chacun étant une entité 
juridique distincte.

**Nombre de lignes prédit**, et le raisonnement qui y mène :

Prédiction : 0 doublon sur customer_name. Si j'en trouve, deux lectures possibles - deux filiales légitimes d'un même groupe, ou une double saisie du même client. Je trancherai en regardant si les lignes concernées partagent leurs autres attributs.

On s'attend à 220 lignes exactement. Le §1 annonce 220 clients sans approximation, contrairement aux 1 400 sites. Tolérance 0.

**Résultat et écart** :

Tests exécutés dans `notebooks/mission0_cartographie.ipynb`, section `ref_customer`.

| Promesse | Prédiction | Résultat | Écart |
|---|---|---|---|
| Nombre de lignes | 220, tolérance 0 | 220 | **0** |
| `customer_id` unique | unique | 220 lignes / 220 distincts | **0** |
| `customer_name` sans doublon | 0 | 0, à 5 niveaux de normalisation | **0** |
| Exhaustivité : tout `customer_id` de `ref_site` existe ici | 0 orphelin | 0 | **0** |
| Exhaustivité : tout `customer_id` de `ref_contract` existe ici | 0 orphelin | 0 | **0** |
| Périmètre : tout client a au moins un site | 0 | 0 client sans site | **0** |
| Périmètre : tout client a signé un contrat | 0 | **74 clients sans aucun contrat** | **74 lignes, 33,6 %** |

Six promesses sur sept sont confirmées. La septième est falsifiée sur un tiers de la table :
la phrase de Niveau 0 affirme *« c'est l'entité juridique qui signe le contrat »*, or 74 clients
sur 220 n'ont aucune ligne dans `ref_contract`. Aucun verdict à ce stade - anomalie, bruit ou
réalité métier mal comprise reste à trancher, et le sujet exige d'argumenter les deux positions
avant de conclure.

Dissymétrie à retenir : **tout client a au moins un site, mais un tiers n'a aucun contrat.**
Des sites rattachés à aucun engagement contractuel tracé, c'est la matière de la troisième
question de la Mission 0.

Point reporté au **Niveau 2**, avec sa liste de tests discriminants. Il ne peut pas être tranché ici :
la question du sujet porte sur les *sites* sans contrat valide, or le lien site ↔ contrat n'existe pas
dans le schéma et reste à reconstruire. Et mesurer `ref_contract` maintenant reviendrait à la profiler
avant de l'avoir cadrée.

**Sur `customer_name` comme clé candidate** : unique, non nulle, robuste aux 5 normalisations testées.
L'égalité `count(*) = count(DISTINCT customer_name) = 220` établit à la fois l'unicité et l'absence
de nul - 219 lignes ne peuvent pas produire 220 valeurs distinctes. Réserve : l'échelle de
normalisation n'a fusionné aucune ligne à aucun échelon. Elle n'est donc pas *validée*, elle n'a
simplement rien eu à normaliser. Ce qui est établi : « aucun doublon de nom n'est détectable par
les normalisations testées ». Ce qui ne l'est pas : « la fonction de normalisation est correcte ».

**Contrôle vert sur données fausses - à conserver pour la question 5 des restitutions.**
Le cinquième échelon de normalisation a d'abord été écrit
`regexp_replace(strip_accents(upper(trim(customer_name))), '[^A-Z0-9]', 'g')` - trois arguments
au lieu de quatre. Le `'g'` était lu comme le *texte de remplacement*, pas comme l'option globale :
la requête remplaçait le premier caractère non alphanumérique par la lettre `g`
(`CARREFOUR S.A.S.` → `CARREFOURgS.A.S.`). Aucune erreur levée, résultat `220` parfaitement
plausible et cohérent avec les quatre autres colonnes. Détecté en relisant le code, pas le résultat.

Contrôle à ajouter au harnais : **un agrégat cache sa matière première**. Toute colonne calculée
s'inspecte en clair (`SELECT col, col_transformee LIMIT 10`) avant d'être agrégée.

## Niveau 1 - colonnes

Ordre de traitement : clés et colonnes de jointure, puis mesures, puis descriptifs.

| Colonne | Promesse du nom | Classe | Prédiction | Résultat | Écart | Verdict |
|---|---|---|---|---|---|---|
| `customer_id` | Identifie un client de façon unique et stable, et sert de clé de jointure vers `ref_site` et `ref_contract`. | unicité, complétude | unique et non nul (traité au Niveau 0) | 220 lignes / 220 distincts, 0 nul | 0 | conforme |
| `customer_name` | Porte la dénomination sociale de l'entité juridique signataire. | unicité, convention de saisie | 0 doublon, y compris après normalisation | 220 distincts aux 5 échelons | 0 | conforme, sous réserve que l'échelle de normalisation n'a rien eu à normaliser |
| `sector` | Indique le secteur d'activité économique du client. | domaine de valeurs, complétude | *non écrite avant exécution* | 7 modalités, 0 nul. Sante 39, Tertiaire 35, Distribution 33, Industrie 33, Collectivite 27, Transport 27, Agroalimentaire 26. Modalité la plus fréquente : 17,7 %. | non mesurable | distribution plate, aucun secteur dominant |
| `segment` | Indique le segment commercial auquel le client est rattaché, indépendamment de son secteur. | domaine de valeurs, complétude | *non écrite avant exécution* | 4 modalités, 0 nul. PME 74, ETI 66, PUBLIC 43, GRAND_COMPTE 37. | non mesurable | voir observation 2 |
| `credit_rating` | Porte la notation de crédit de la contrepartie, sur une échelle ordinale et non numérique. | domaine de valeurs, convention d'échelle, complétude | *non écrite avant exécution* | 6 modalités, 0 nul au sens SQL. BBB 64, BB 54, A 33, **NR 31**, B 27, AA 11. | non mesurable | voir observation 1 |

Ordre retenu : `customer_id` et `customer_name` d'abord, ce sont la clé de jointure et la clé
naturelle. `ref_customer` ne contient aucune mesure, le reste est descriptif.

**Réserve** : les trois lignes descriptives ont été mesurées sans prédiction écrite préalable. Les
résultats sont exacts, l'écart n'est pas mesurable, et rien n'y est opposable au titre du protocole.
Deuxième occurrence après l'exploration initiale du 3 août.

### Observation 1 - l'absence de notation est encodée comme une valeur

`credit_rating` ne contient **aucun nul au sens SQL**, mais 31 clients sur 220, soit **14,1 %**, portent
la modalité `NR`, c'est-à-dire *not rated*. Un contrôle de complétude écrit `isna().sum()` ou
`count(*) - count(credit_rating)` renverrait donc 0 et passerait au vert, alors qu'un client sur sept
n'a pas de notation.

Conséquence directe : toute statistique conditionnée à la notation doit exclure `NR` explicitement,
et le taux de couverture de la notation doit être publié à côté de la statistique elle-même.

Deuxième contrôle vert sur données fausses du projet, à conserver pour la question 5 des restitutions.
Mécanisme différent du premier : ici ce n'est pas la requête qui est fautive, c'est la convention
d'encodage de la source qui rend le contrôle inopérant.

### Observation 2 - l'échelle de notation et le profil de risque

L'échelle observée est `AA`, `A`, `BBB`, `BB`, `B`, plus `NR`. Elle est **contiguë, sans trou**, ce qui
est cohérent avec une échelle ordinale de type agence de notation. Absentes : `AAA` vers le haut,
`CCC` et en dessous vers le bas.

Répartition par catégorie de risque, hors `NR` :

| Catégorie | Notations | Clients | Part du portefeuille |
|---|---|---|---|
| Investment grade | `AA`, `A`, `BBB` | 108 | 49,1 % |
| Speculative grade | `BB`, `B` | 81 | **36,8 %** |
| Non noté | `NR` | 31 | 14,1 % |

Plus d'un tiers du portefeuille est en catégorie spéculative. Sur des contrats pluriannuels couverts
par des achats de gros, un défaut client laisse la couverture ouverte et transforme un risque de crédit
en risque de marché. Ce chiffre est à rapprocher plus tard des volumes concernés, pas seulement du
nombre de clients : 36,8 % des clients ne signifie pas 36,8 % du volume.

### Observation 3 - `segment` et `sector` sont indépendants, mais `PUBLIC` interroge

Le tableau croisé totalise 220, aucune ligne n'est écartée. La répartition est proche de
l'indépendance, ce qui confirme l'hypothèse de Niveau 0 : les deux colonnes décrivent bien des
dimensions différentes.

Une incohérence sémantique reste à trancher. Sur les 43 clients de segment `PUBLIC`, seuls **6** sont
du secteur `Collectivite`, contre 11 en `Sante`, 9 en `Industrie`, 9 en `Tertiaire` et 4 en
`Agroalimentaire`. Symétriquement, sur les 27 clients de secteur `Collectivite`, **21 sont classés
`PME`, `ETI` ou `GRAND_COMPTE`**, segments qui désignent des tailles d'entreprise privée.

Deux lectures, à départager plus tard : soit `PUBLIC` désigne un mode de contractualisation, un marché
public par exemple, et peut alors coexister avec n'importe quel secteur ; soit l'affectation des
modalités est incohérente et relève d'une anomalie de référentiel. Ne pas trancher sans avoir vu le
comportement de `ref_contract`, où `pricing_type` pourrait porter la même information.

Classes de promesse : unicité, domaine de valeurs, complétude, ordre de grandeur, convention.
Verdicts possibles : anomalie, bruit, réalité métier mal comprise. Un verdict s'accompagne de
l'hypothèse retenue et de l'alternative écartée.

---

# 2. `ref_site`

Colonnes : `site_id`, `customer_id`, `commodity`, `region`, `dso`, `contracted_capacity_kw`,
`profile_type`, `monitored`.

## Niveau 0 - cadrage

**Que représente une ligne** (une phrase, nom au singulier) :

Une ligne représente l'état courant de la desserte d'un lieu physique en une commodité, pour un client du portefeuille B2B France gaz et électricité. Un lieu desservi en gaz et en électricité occupe deux lignes portant le même site_id, chacune avec sa commodité et son gestionnaire de réseau. Le DSO est déterminé par la géographie du lieu et par la commodité. Un site appartient à un seul client, l'entité juridique signataire. En l'absence de toute colonne de date, la table est un état courant : un changement de puissance souscrite ou une résiliation écrase la valeur précédente, aucun historique n'est conservé.

**Maille** :

Une ligne par *site x commodité*. Pas de *site x client* : "un site appartient à un seul client". Pas de *site x date* 

**Clés candidates** (colonnes seules ou combinées qui devraient identifier une ligne) :

*site_id x commodity*. *site_id* est écarté en raison qu'un même site peut recevoir plusieurs commodités.

**Nombre de lignes prédit**, et le raisonnement qui y mène :

Prédiction : 1 400 lignes, intervalle [1 350 ; 1 450], soit ±3,6 %. Lecture retenue : les « environ 1 400 sites » du README comptent des lignes de *ref_site*.

Prédiction dérivée, celle qui teste la définition retenue : `count(distinct site_id)` **strictement
inférieur** au nombre de lignes, de l'ordre de 1 250 à 1 350 si 5 à 10 % des lieux sont desservis en
gaz et en électricité. Si `count(distinct site_id)` égale `count(*)`, la définition de Niveau 0 est
fausse et doit être remplacée par « le site est le point de livraison ».

Pour *monitored* : Prédiction : environ 500 lignes à monitored = 1. La Mission 4 annonce 5,8 millions de lignes de prévisions horaires sur 500 sites. Contrôle de cohérence : 500 × 8 760 = 4 380 000, soit 1,32 fois moins que 5,8 millions ; l'écart s'explique par la coexistence de plusieurs versions de prévision, qui multiplie les lignes sans multiplier les sites.

**Résultat et écart** :

Tests exécutés dans `notebooks/mission0_cartographie.ipynb`, section `ref_site`.

| Mesure | Prédiction | Résultat | Écart |
|---|---|---|---|
| `count(*)` | 1 400, intervalle [1 350 ; 1 450] | 1 400 | **0** |
| `count(distinct site_id)` | 1 250 à 1 350, **strictement inférieur** au nombre de lignes | **1 400** | +50 à +150 selon la borne, et surtout l'inégalité stricte est fausse |
| `count(distinct (site_id, commodity))` | égal au nombre de lignes | 1 400 | 0 |
| `count(distinct (site_id, commodity, dso))` | égal au précédent | 1 400 | 0 |
| `count(distinct customer_id)` | 220 | 220 | **0** |
| lignes à `monitored = 1` | environ 500 | 500 | **0** |

`monitored` a pour domaine `{0, 1}`, sans nul : 500 lignes à 1 et 900 à 0.

### Verdict : la définition de Niveau 0 est falsifiée

`count(distinct site_id) = count(*) = 1 400`. **`site_id` est unique.** La définition retenue supposait
qu'un lieu bi-énergie occupe deux lignes de même `site_id` ; elle est contredite par les données.
La lecture concurrente, écartée au moment de la prédiction, est la bonne : le site est le point de
livraison, pas le lieu physique.

Conséquences : la maille annoncée `site × commodity` est fausse, et `(site_id, commodity)` n'est pas
une clé candidate mais une **surclé**, puisqu'elle n'est pas minimale.

### Deux tests ne pouvaient pas échouer

`count(distinct (site_id, commodity))` et `count(distinct (site_id, commodity, dso))` valent 1 400 par
construction : dès lors que `site_id` est unique, aucune combinaison le contenant ne peut donner une
autre valeur. Ces deux contrôles sont passés au vert sans avoir la possibilité de rougir.

Il reste donc non établi que `dso` soit fonctionnellement déterminé par la géographie et la commodité.
Le tester exige une clé qui ne contienne pas `site_id`, par exemple `(region, commodity)`. Reporté au
Niveau 1.

Troisième occurrence d'un contrôle structurellement incapable d'échouer, après l'échelle de
normalisation de `ref_customer` et le comptage de `credit_rating`. Le point commun : dans les trois
cas le résultat était correct et l'information nulle.

### La tolérance n'a jamais servi

Le résultat est 1 400 pile, alors que l'énoncé annonçait « environ ». L'intervalle [1 350 ; 1 450],
construit sur l'arrondi à la centaine, n'a été mis à l'épreuve à aucun moment. La méthode de
construction de la tolérance reste défendable, mais elle n'est pas validée par ce test.

## Niveau 0 bis - cadrage révisé

**Ceci n'est pas une prédiction.** C'est une reformulation établie après mesure, et elle tombe juste
par construction sur le point qui l'a produite. Elle n'a pas la même valeur probante que le bloc
précédent.

**Que représente une ligne** :

Une ligne représente l'état courant d'un point de livraison d'énergie du portefeuille B2B France gaz et
électricité, rattaché à une seule commodité. Un point de livraison appartient à un seul client,
l'entité juridique signataire. Le DSO est déterminé par la géographie et par la commodité. En l'absence
de toute colonne de date, la table est un état courant : un changement de puissance souscrite ou une
résiliation écrase la valeur précédente, aucun historique n'est conservé.

**Maille** : une ligne par `site_id`. Pas de `site × commodity`, pas de `site × client`, pas de
`site × date`.

**Clés candidates** : `site_id` seul, minimale. `(site_id, commodity)` est unique mais non minimale,
donc surclé et non clé candidate.

### Ce que la version révisée affirme sans pouvoir le prouver

La formulation « un lieu desservi en gaz et en électricité compte deux points de livraison distincts »
est **invérifiable avec cette table**. Aucune colonne n'identifie le lieu physique : `site_id` identifie
le point de livraison, pas l'adresse. Rien ne permet donc de dire si deux points de livraison sont au
même endroit.

C'est une limite structurelle du référentiel, du même ordre que l'absence d'historique. Un raisonnement
par site géographique, par exemple pour mesurer une exposition par implantation industrielle, n'est pas
possible à partir de `ref_site` seule. Un rapprochement approximatif serait envisageable via
`customer_id`, `region` et `dso`, jamais une preuve.

## Niveau 1 - colonnes

| Colonne | Promesse du nom | Classe | Prédiction | Résultat | Écart | Verdict |
|---|---|---|---|---|---|---|
| `site_id` | Identifie un point de livraison de façon unique et stable. | unicité, complétude | unique et non nul (traité au Niveau 0) | 1 400 lignes / 1 400 distincts | 0 | conforme |
| `customer_id` | Rattache le point de livraison au client titulaire, et sert de clé de jointure vers `ref_customer`. | complétude, intégrité référentielle | à remplir | 220 valeurs distinctes, 0 orphelin (traité au Niveau 0 de `ref_customer`) | | |
| `contracted_capacity_kw` | Donne la puissance souscrite au raccordement, en kilowatts. | ordre de grandeur, convention d'unité, complétude | à remplir | | | |
| `commodity` | Indique l'énergie livrée sur ce point de livraison. | domaine de valeurs, complétude | à remplir | | | |
| `monitored` | Indique si le site est suivi en granularité horaire. | domaine de valeurs, complétude | environ 500 à 1 (traité au Niveau 0) | domaine `{0, 1}`, 0 nul, 500 à 1 et 900 à 0 | 0 | conforme |
| `profile_type` | Donne le profil de consommation type servant à estimer la courbe de charge d'un site non télérelevé. | domaine de valeurs, complétude | à remplir | | | |
| `region` | Localise le point de livraison à la maille région administrative. | domaine de valeurs, complétude | à remplir | | | |
| `dso` | Nomme le gestionnaire de réseau de distribution qui achemine l'énergie jusqu'au compteur. | domaine de valeurs, dépendance fonctionnelle, cohérence physique | voir ci-dessous | voir ci-dessous | | |

### `dso` : dépendance fonctionnelle et cohérence physique

**Promesse.** Un point de livraison est raccordé au réseau qui dessert son adresse. Le gestionnaire de
réseau n'est pas choisi par le client ni par le fournisseur : il est imposé par la géographie et par
l'énergie. `dso` devrait donc être **fonctionnellement déterminé par `(region, commodity)`**, et non
constituer une dimension libre.

#### Test 1, réalisé : `dso` croisé avec `region`

`pd.crosstab(df_ref_site.dso, df_ref_site.region)`

Les cinq DSO apparaissent dans les **dix** régions, avec des effectifs comparables partout, compris
entre 15 et 38.

| DSO | Sites | Part |
|---|---|---|
| GEREDIS | 297 | 21,2 % |
| SRD | 289 | 20,6 % |
| GRDF | 287 | 20,5 % |
| ENEDIS | 268 | 19,1 % |
| RESEAU_LOCAL | 259 | 18,5 % |

**Verdict : la promesse est contredite.** `dso` n'est pas déterminé par la région ; les cinq valeurs
se répartissent uniformément sur tout le territoire.

Deux invraisemblances métier s'ajoutent au constat statistique :

- Enedis exploite environ 95 % du réseau de distribution d'électricité français et GRDF environ 95 %
  de celui du gaz. Une répartition à environ 20 % chacun sur cinq opérateurs est incompatible avec la
  structure réelle du marché français.
- GEREDIS et SRD sont des entreprises locales de distribution dont le territoire est **départemental**,
  respectivement les Deux-Sèvres et la Vienne, toutes deux en Nouvelle-Aquitaine. Les voir desservir
  37 sites en Bretagne ou 36 dans le Grand Est est physiquement impossible.

La répartition quasi uniforme sur cinq opérateurs et dix régions est la signature d'une affectation
aléatoire.

#### Test 2, à exécuter : `dso` croisé avec `commodity`

Le test 1 établit une invraisemblance. Le test 2 vise une **contradiction dure**, qui ne dépend
d'aucune connaissance de parts de marché.

Enedis exploite un réseau électrique, GRDF un réseau gaz. Ce sont deux infrastructures physiques
distinctes, des câbles d'un côté et des canalisations de l'autre. Un point de livraison de gaz
raccordé à Enedis n'est pas improbable : il est impossible.

**Prédiction, écrite avant exécution** : `pd.crosstab(df_ref_site.dso, df_ref_site.commodity)` doit
donner ENEDIS à 100 % sur `POWER` et GRDF à 100 % sur `GAS`. Nombre de lignes en contradiction
attendu : **0**. Les trois autres valeurs, GEREDIS, SRD et RESEAU_LOCAL, ne sont pas contraintes par
ce raisonnement : GEREDIS et SRD distribuent de l'électricité dans la réalité, mais leur affectation
étant déjà démontrée aléatoire au test 1, aucune prédiction n'est formulée à leur sujet.

Si des lignes contredisent la prédiction, chiffrer l'écart en nombre de lignes puis en puissance
souscrite cumulée (`contracted_capacity_kw`), et rapprocher cette famille des quatre familles
d'anomalies de référentiel annoncées par le sujet.

#### Test 2, résultat : prédiction falsifiée

`pd.crosstab(df_ref_site.dso, df_ref_site.commodity)`

| DSO | GAS | POWER | Part gaz |
|---|---|---|---|
| ENEDIS | **102** | 166 | 38,1 % |
| GEREDIS | 109 | 188 | 36,7 % |
| GRDF | 122 | **165** | 42,5 % |
| RESEAU_LOCAL | 93 | 166 | 35,9 % |
| SRD | 95 | 194 | 32,9 % |
| **ensemble** | **521** | **879** | **37,2 %** |

| | Prédiction | Résultat | Écart |
|---|---|---|---|
| Lignes en contradiction physique | 0 | **267** | **+267** |

**Chiffrage.** 267 lignes sur 1 400, soit **19,1 %** du référentiel, représentant **1 125 523 kW** de
puissance souscrite sur 5 242 077 kW au total, soit **21,5 %** du portefeuille en puissance. Détail :
102 sites gaz raccordés à Enedis, 165 sites électriques raccordés à GRDF.

Les deux parts sont proches, 19,1 % en lignes contre 21,5 % en puissance. L'anomalie ne se concentre
donc **ni sur les gros sites ni sur les petits**, elle frappe uniformément. Une erreur de saisie
humaine se concentrerait quelque part ; une affectation aléatoire non.

#### Verdict : `dso` est aléatoire, pas erroné à 19 %

Chacun des cinq opérateurs présente la même proportion de gaz que le portefeuille global, entre 32,9 %
et 42,5 % contre 37,2 % d'ensemble. `dso` est donc **indépendant de `commodity`**, comme le test 1
l'avait déjà montré indépendant de `region`.

Une colonne indépendante de tout ce qui devrait la déterminer ne porte aucune information. La lecture
correcte n'est pas « 19,1 % des valeurs sont fausses » mais **« la colonne est inexploitable »**.

GRDF, gestionnaire du réseau **gaz**, est d'ailleurs majoritairement affecté à des sites **électriques**,
165 contre 122.

**Le 267 est un plancher, pas une mesure.** C'est le nombre de lignes réfutables avec une connaissance
externe portant sur deux opérateurs seulement. Les 1 133 autres ne sont pas validées : elles sont
seulement non réfutables par ce test. GEREDIS desservant la Bretagne est tout aussi impossible, mais
la contradiction gaz/électricité ne permet pas de le démontrer.

Cette distinction commande la recommandation :

| Lecture | Recommandation induite |
|---|---|
| « 19,1 % de la colonne est erronée » | corriger 267 lignes |
| « la colonne est aléatoire » | n'utiliser `dso` dans aucun contrôle tant que la source n'est pas reconstruite |

La seconde est celle que les données soutiennent.

**Classement** : anomalie de référentiel, retenue comme l'une des quatre familles annoncées par le
sujet. Alternative écartée : bruit statistique. Elle ne tient pas, une affectation bruitée resterait
corrélée à la géographie et à l'énergie, ce qui n'est le cas d'aucun des deux tests.

**Portée pour la suite** : toute jointure, tout regroupement ou tout filtre s'appuyant sur `dso` produira
un résultat sans signification. `region` n'est pas disqualifiée pour autant, sa cohérence propre reste
à tester séparément.

*Note de provenance : la connaissance métier mobilisée ici, parts de marché d'Enedis et de GRDF,
périmètre départemental de GEREDIS et de SRD, séparation physique des réseaux gaz et électricité,
n'est pas déduite des données. Elle vient de l'extérieur du jeu de données et c'est elle qui rend la
prédiction falsifiable.*

---

# 3. `ref_contract`

*à ouvrir une fois `ref_site` clos*

---
---

# Niveau 2 - relations entre tables

Ne porte pas sur une table mais sur une **paire** de tables. Ne peut être traité qu'une fois les
mailles des deux tables établies aux Niveaux 0 et 1. C'est ici que se reconstitue le modèle
relationnel demandé par la Mission 0.

Pour chaque paire, dans cet ordre :

1. sur quelle colonne la jointure se fait, et pourquoi celle-là ;
2. cardinalité **prédite** : un à un, un à plusieurs, plusieurs à plusieurs ;
3. cardinalité réelle **des deux côtés** ;
4. intégrité référentielle : chaque valeur référencée existe-t-elle en face ;
5. orphelins comptés **de chaque côté séparément** ;
6. nombre de lignes que produirait la jointure, prédit puis comparé au réel.

## Paires identifiées

| # | Paire | Colonne de jointure présumée | Cardinalité prédite | Statut |
|---|-------|------------------------------|---------------------|--------|
| 1 | `ref_site` → `ref_customer` | `customer_id` | | partiellement traité au Niveau 0 de `ref_customer` (0 orphelin dans les deux sens sur l'existence) |
| 2 | `ref_contract` → `ref_customer` | `customer_id` | | idem, plus 74 clients sans contrat |
| 3 | `ref_site` ↔ `ref_contract` | **aucune clé étrangère** | | question centrale de la Mission 0 : sur quoi reconstruire le lien, et combien de lignes le choix laisse de côté |
| 4 | `volumes_hourly` → `ref_site` | `site_id` | | |
| 5 | `actuals_daily` → `ref_site` | `site_id` | | |
| 6 | `pos_snapshot` ↔ `trd_deal` | `book`, `commodity`, mois de livraison | | |
| 7 | `mkt_forward_curve` ↔ `trd_deal` | `commodity`, mois de livraison | | |
| 8 | `bo_confirmations` ↔ `trd_deal` | `deal_ref` / `deal_id` | | clé non propre, voir Mission 1 |

## Point ouvert reporté du Niveau 0 de `ref_customer`

74 clients sur 220 n'ont aucune ligne dans `ref_contract`, alors que tous ont au moins un site.
Verdict non tranché. Tests discriminants à mener ici, une fois `ref_site` et `ref_contract` cadrées :

- répartition `commodity` des sites des 74 contre les 146 autres, et répartition `commodity` de `ref_contract` ;
- mêmes comparaisons sur `segment`, `sector`, `region` : un écart concentré sur une modalité est structurel, un écart uniforme évoque une perte de données ;
- population voisine non testée : clients dont **tous** les contrats sont expirés au 24/07/2026 (`ref_contract.end_date`) ;
- quantification en MWh via `ref_site.contracted_capacity_kw` cumulée sur les sites de ces 74 clients.

---

# Niveau 3 - redondance entre sources

Deux sources décrivent la même réalité et devraient s'accorder. En Mission 0, l'objet est de
**repérer** ces redondances et de **formuler** l'invariant. La vérification appartient aux
Missions 1, 2 et 5.

Avant toute comparaison, vérifier que les conventions sont comparables : unité, signe, fuseau
horaire, granularité, format de clé. Comparer les totaux avant de comparer ligne à ligne.

| # | Sources | Ce qui devrait être égal | À quelle maille | Conventions à vérifier d'abord | Mission |
|---|---------|--------------------------|-----------------|-------------------------------|---------|
| 1 | `bo_confirmations` vs `trd_deal` | chaque transaction confirmée correspond à un deal front | deal | format de clé, unité de quantité, signe, format de date, code contrepartie | 1 |
| 2 | `pos_snapshot` source A vs source B | les deux photos de position | commodité × mois de livraison × book | signe, convention de ventilation | 2 |
| 3 | `pos_snapshot` vs position reconstruite depuis `trd_deal` | la position nette | idem | ventilation multi-mois, sélection de version, statut des deals | 2 |
| 4 | `volumes_hourly` vs `actuals_daily` | prévision contre relevé | site × jour | granularité horaire vs jour, fuseau, jour de 23 et 25 heures | 5 |
| 5 | `mkt_spot_hourly` vs `volumes_hourly` | valorisation de la consommation | heure | **UTC contre heure locale** | 5 |
