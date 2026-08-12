# Mission 0 - Cartographie

Profiling systématique et reconstitution du modèle relationnel.
Date de référence du TP : **24 juillet 2026**. Année de livraison sous suivi : **2026**.

---

# Récapitulatif

Synthèse de ce qui est établi, de ce qui ne l'est pas, et de ce qui conditionne la suite.

## Volumétries, clés et mailles

| Table | Lignes | Clé primaire réelle | Maille | Historisation |
|---|---|---|---|---|
| `ref_customer` | 220 | `customer_id` | un client | non, état courant |
| `ref_site` | 1 400 | `site_id` | un point de livraison, rattaché à une seule commodité | non, état courant |
| `ref_contract` | 260 | `contract_id` | un contrat | oui, les contrats successifs coexistent |

`customer_name` est également unique et non nulle sur `ref_customer`, donc clé candidate.
`ref_contract` ne contient aucun contrat futur : tous ont déjà pris effet au 24 juillet 2026.

## Colonnes utilisables et colonnes à écarter

| Colonne | État | Conséquence |
|---|---|---|
| `customer_id`, `site_id`, `contract_id` | **fiables** | clés de jointure sûres, uniques, non nulles, sans orphelin |
| `commodity` | **fiable** des deux côtés | domaine `{GAS, POWER}`, 521 sites gaz sur 1 400, 93 contrats gaz sur 260 |
| `contracted_capacity_kw` | **fiable** | seule grandeur numérique du référentiel, sert de taille de référence par site |
| `sector`, `segment` | fiables, indépendantes entre elles | 7 et 4 modalités, aucune nulle |
| `credit_rating` | fiable, **mais** l'absence de notation est codée `NR` et non `NULL` | 31 clients sur 220 non notés ; exclure `NR` explicitement de toute statistique conditionnée |
| `start_date`, `end_date` | fiables | format `AAAA-MM-JJ`, aucune inversion, durées de 1 à 3 ans |
| `pricing_type` | fiable | 4 modalités : `FIXED` 115, `INDEXED` 59, `CLICK` 54, `SPOT_PASSTHROUGH` 32 |
| `volume_tolerance_pct` | fiable | barème à 4 paliers, 5 / 10 / 15 / 20, convention [0 ; 100] |
| **`dso`, `monitored`, `profile_type`** | **inexploitables** | affectation aléatoire, voir famille n° 1. Ne jamais joindre, filtrer ni regrouper dessus |

## Anomalies retenues : 2 familles sur les 4 annoncées

**Famille 1, `ref_site`.** Les trois attributs descriptifs `dso`, `monitored` et `profile_type` sont
statistiquement indépendants de tout ce qui devrait les déterminer. Volet réfutable ligne à ligne :
267 sites, soit 19,1 % du référentiel et 1 125 523 kW (21,5 % de la puissance), portent une
contradiction physique entre `dso` et `commodity`. Les deux autres colonnes ne se chiffrent pas ligne
à ligne, leur distribution entière étant vide de sens.

**Famille 2, `ref_contract`.** Couverture en double : 35 couples `(client, commodité)` portent deux ou
trois contrats en vigueur simultanément au 24 juillet 2026, soit 41 contrats en excès, 24,0 % des
couples actifs. Non chiffrable en MWh depuis `ref_contract`, qui ne porte aucun volume.

**Candidat non tranché.** 8 couples `(client, commodité)` portent un contrat en vigueur alors que le
client ne possède aucun site dans cette commodité.

## Modèle relationnel

| Paire | Clé de jointure | Cardinalité | Orphelins |
|---|---|---|---|
| `ref_site` → `ref_customer` | `customer_id` | un à plusieurs | 0 des deux côtés |
| `ref_contract` → `ref_customer` | `customer_id` | un à plusieurs | 0 côté contrats, **74 clients** sans contrat |
| `ref_site` ↔ `ref_contract` | `(customer_id, commodity)` + contrat en vigueur | plusieurs à plusieurs | **899 sites** sans contrat, **8 couples** contrat sans site |

Le lien site vers contrat n'existe pas dans le schéma. Il se reconstruit sur le couple
`(customer_id, commodity)` filtré sur `start_date <= '2026-07-24' and end_date >= '2026-07-24'`, seules
colonnes communes aux deux tables. La jointure interne rend 648 lignes, l'externe 1 547, pour 1 400
sites en entrée.

**899 sites sur 1 400** relèvent d'un contrat inexistant ou expiré, soit 64,2 % du référentiel et
3 402 619 kW, 64,91 % de la puissance souscrite. Le verdict entre anomalie et réalité métier n'est pas
rendu.

## Ce qui n'a pas été traité

| Source | État | Renvoyé à |
|---|---|---|
| `trd_deal` | non cadrée | Mission 1 |
| `pos_snapshot` | non ouverte | Mission 2 |
| `mkt_forward_curve` | non ouverte | Mission 3 |
| `mkt_spot_hourly` | non ouverte | Mission 5 |
| `volumes_hourly` | non ouverte | Mission 4 |
| `actuals_daily` | non ouverte | Mission 5 |
| `bo_confirmations_20260724.csv` | non ouvert | Mission 1 |

Deux questions à trancher de la Mission 0 restent ouvertes : la clé primaire réelle de `trd_deal`, et
le verdict sur les 899 sites sans contrat.

---

# Feuille de route pour la Mission 1

## Point d'entrée : la clé primaire de `trd_deal`

C'est la première question à trancher de la Mission 0 et la première dépendance de la Mission 1, dont
l'énoncé prévient qu'« une jointure naïve sur `deal_id` produit plus de lignes qu'il n'y a de deals ».

Éléments connus, issus de l'exploration initiale et **non opposables** au titre du protocole :

- 9 580 lignes pour **9 000 `deal_id` distincts** ;
- 575 `deal_id` apparaissant 2 fois, 5 apparaissant 3 fois ;
- **40 lignes strictement identiques** sur l'ensemble des colonnes ;
- colonne `version` à valeurs `1` et `2` ;
- colonne `status` comportant au moins `CANCELLED` et `PENDING` ;
- 12 contreparties, 5 books dont `B2B_FR_GAS_HEDGE` et `B2B_FR_STRUCT` ;
- `trade_date` du 2025-06-02 au 2026-07-24, mais `trade_ts` allant jusqu'au **2026-07-25 13:16:03**,
  donc au moins un deal dont l'horodatage dépasse sa propre date de transaction et la date de
  référence du TP ;
- livraisons du 2026-01-01 au 2027-12-01 en début, jusqu'au 2028-11-30 en fin.

Ces chiffres sont à reprendre sous protocole : promesse écrite, prédiction, puis mesure.

## Ce que la Mission 0 apporte à la Mission 1

**Le book `B2B_FR_STRUCT` a un sens.** 54 contrats sont en `pricing_type = CLICK`, produit structuré
où le client fige son prix par tranches successives. La couverture correspondante se construit
progressivement et non à la signature.

**Le taux de couverture attendu dépend de `pricing_type`.** 32 contrats en `SPOT_PASSTHROUGH`
n'appellent quasiment aucune couverture, 115 en `FIXED` en appellent une intégrale dès la signature.
Toute comparaison entre position couverte et volume client doit segmenter sur cette colonne.

**Les contreparties du fichier back office ne suivront pas les codes du front.** Le rapprochement se
fera par une fonction de normalisation. L'échelle construite sur `customer_name` en Mission 0 n'a
fusionné aucune ligne, faute de matière : casse, espaces, points, accents. Elle n'est donc pas validée,
seulement écrite. Elle sera réellement éprouvée sur l'extrait back office.

**`merge(..., indicator=True)` est l'outil de la réconciliation.** Il produit une partition exclusive
et exhaustive en `both`, `left_only`, `right_only` sans reposer sur aucune hypothèse de nullité,
contrairement à l'anti-jointure par test de nul. C'est exactement ce que l'énoncé de la Mission 1
demande : « classer chaque transaction dans une catégorie d'écart exclusive et exhaustive ».

**Le format de date `AAAA-MM-JJ` du référentiel se trie correctement en ordre lexicographique.** Ce ne
sera pas le cas de l'extrait back office, dont l'énoncé annonce que quatre caractéristiques de format
s'opposent à une lecture par défaut.

## Méthode reconduite

- Une promesse en français, une prédiction chiffrée, puis la mesure. Un commit pour les prédictions,
  un commit pour les résultats.
- Tout écart chiffré en nombre de lignes **puis** dans une unité métier, MWh ou euros.
- Toute décision accompagnée de l'alternative écartée.
- Un agrégat qui tombe juste se décompose à la maille inférieure avant d'être accepté.

---

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
| `contracted_capacity_kw` | Donne la puissance souscrite au raccordement, en kilowatts. | ordre de grandeur, convention d'unité, complétude | voir ci-dessous | voir ci-dessous | | |
| `commodity` | Indique l'énergie livrée sur ce point de livraison. | domaine de valeurs, complétude | à remplir | | | |
| `monitored` | Indique si le site est suivi en granularité horaire. | domaine de valeurs, complétude | environ 500 à 1 (traité au Niveau 0) | domaine `{0, 1}`, 0 nul, 500 à 1 et 900 à 0 | 0 | conforme |
| `profile_type` | Donne le profil de consommation type servant à estimer la courbe de charge d'un site non télérelevé. | domaine de valeurs, complétude | à remplir | | | |
| `region` | Localise le point de livraison à la maille région administrative. | domaine de valeurs, complétude | à remplir | | | |
| `dso` | Nomme le gestionnaire de réseau de distribution qui achemine l'énergie jusqu'au compteur. | domaine de valeurs, dépendance fonctionnelle, cohérence physique | voir ci-dessous | voir ci-dessous | | |

### `contracted_capacity_kw` : seule mesure du référentiel

Seule grandeur numérique de `ref_site`, et seule colonne du référentiel sur laquelle un ordre de
grandeur et une convention d'unité peuvent être testés plutôt qu'une simple liste de modalités. Elle
servira de grandeur de référence en Mission 4 pour détecter des volumes horaires exprimés dans une
autre unité.

**Prédictions, écrites avant exécution :**

| # | Promesse | Classe | Prédiction | Justification |
|---|---|---|---|---|
| 1 | La colonne est toujours renseignée | complétude | **0 nul** | la puissance souscrite est une donnée contractuelle : sans elle, ni raccordement ni tarif d'acheminement, donc pas de facturation possible |
| 2 | Les valeurs sont strictement positives | domaine | **aucune valeur ≤ 0** | on ne délivre pas de puissance négative ; 0 est exclu parce que la table est un état courant et qu'un site résilié n'y figure plus |
| 3 | Les valeurs sont plausibles pour un site B2B raccordé au réseau de distribution | ordre de grandeur | **minimum 36 kW, maximum 50 000 kW** | 36 kW est l'ordre de grandeur qui sépare un particulier ou un très petit professionnel d'un site de taille supérieure ; au-delà d'environ 40 à 50 MW un site n'est plus raccordé au réseau de distribution mais au réseau de transport, or `dso` désigne des distributeurs |
| 4 | Les sites télérelevés sont les gros raccordements | cohérence inter-colonnes | les 500 sites `monitored = 1` détiennent **90 %** de la puissance souscrite totale | promesse formulée lors du cadrage de `monitored` : un site est télérelevé parce qu'il est gros. Point neutre : 35,7 %, la part que ces sites représentent en nombre de lignes. Toute valeur proche de 35,7 % réfuterait la promesse |

**Réserve d'unité.** La colonne est nommée en kilowatts. En France, la puissance souscrite est
contractualisée tantôt en kVA (puissance apparente) tantôt en kW (puissance active), les deux étant
liées par le facteur de puissance, en général compris entre 0,9 et 1. Les prédictions ci-dessus sont
formulées en kW, conformément au nom de la colonne. Un écart systématique d'environ 10 % sur une
sous-population pourrait signaler une saisie en kVA.

**Grandeurs déjà connues, donc non prédictibles.** Le total de la colonne vaut 5 242 077 kW et la
moyenne 3 744 kW par site. Ces deux valeurs ont été calculées lors du chiffrage de l'anomalie `dso`,
sans prédiction préalable, et ne sont pas opposables. La médiane, le minimum et le maximum n'ont pas
été mesurés et restent prédictibles. L'écart entre médiane et moyenne renseignera sur l'asymétrie de
la distribution.

**Résultats :**

`describe()` : count 1 400, moyenne 3 744,34, écart-type 5 057,85, min 61, Q1 1 157,50,
médiane 2 258, Q3 4 538,75, max 89 750.

| # | Prédiction | Résultat | Écart | Verdict |
|---|---|---|---|---|
| 1 | 0 nul | 0 | **0** | confirmée |
| 2 | aucune valeur ≤ 0 | 0, minimum à 61 kW | **0** | confirmée |
| 3 | entre 36 kW et 50 000 kW | min 61 kW, **max 89 750 kW** | borne basse tenue ; borne haute dépassée de **79,5 %** | **falsifiée** |
| 4 | `monitored = 1` détient 90 % de la puissance | **36,6 %** | **-53,4 points**, à 0,9 point du point neutre de 35,7 % | **falsifiée** |

**Distribution.** Moyenne 3 744 kW contre médiane 2 258 kW : la moyenne dépasse le troisième
quartile de peu et se situe bien au-dessus de la médiane, donc plus de la moitié des sites sont sous
la moyenne. Distribution fortement asymétrique vers le haut, tirée par une minorité de gros sites.
L'écart-type, 5 058 kW, dépasse la moyenne, ce qui confirme la dispersion.

**Écart 3, chiffré.** Deux sites dépassent 50 000 kW : 89 750 et 55 238. Soit **2 lignes sur 1 400**,
0,14 % du référentiel, et **2,77 %** de la puissance souscrite totale. Le classement des vingt plus
grandes valeurs ne montre **aucun palier** : après 55 238 la série retombe à 38 433 puis décroît
régulièrement. Ce ne sont donc pas les membres d'une famille mais deux valeurs isolées. Erreur de
saisie ou sites réellement très gros mal rattachés au réseau de distribution : indécidable sur deux
points. **Non retenu comme famille d'anomalies.**

Leçon de méthode à conserver : les prédictions 3 et 4 sont toutes deux falsifiées, et elles ne pèsent
pas du tout la même chose. La troisième vaut 2 lignes et 2,77 % de la puissance, la quatrième invalide
une colonne entière. Sans chiffrage, elles auraient eu le même poids dans un rapport. **Une prédiction
falsifiée n'est pas automatiquement une trouvaille.**

### `monitored` et `profile_type` : deux colonnes sans déterminant

L'écart 4 ci-dessus ouvrait deux lectures : soit `monitored` est aléatoire, soit il encode une réalité
autre que la taille du raccordement. Deux croisements supplémentaires tranchent.

`pd.crosstab(df_ref_site.monitored, df_ref_site.commodity)` et
`pd.crosstab(df_ref_site.monitored, df_ref_site.profile_type)`

| Croisement | `monitored = 0` | `monitored = 1` | Ensemble |
|---|---|---|---|
| Part de gaz | 37,4 % | 36,8 % | 37,2 % |
| PROFILE_BASE | 24,4 % | 25,2 % | 24,7 % |
| PROFILE_FLAT | 26,0 % | 26,0 % | 26,0 % |
| PROFILE_PEAK | 25,7 % | 24,4 % | 25,2 % |
| PROFILE_SEASONAL | 23,9 % | 24,4 % | 24,1 % |
| Médiane de puissance | 2 190,5 kW | 2 338,5 kW | 2 258 kW |

`monitored` est indépendant de `commodity`, de `profile_type` et de `contracted_capacity_kw`. Le
rapport des médianes vaut 1,07, celui des moyennes 1,04 : les sites télérelevés sont indistinguables
des autres. La lecture de repli tombe : une colonne qui encoderait une réalité autre serait corrélée
à quelque chose.

**Promesse sur `profile_type`.** Les profils de consommation gaz et électricité sont des objets
distincts. `profile_type` devrait donc dépendre de `commodity`, avec au moins une modalité concentrée
à plus de 90 % sur une seule énergie. Point neutre : 37,2 % de gaz partout.

`pd.crosstab(df_ref_site.profile_type, df_ref_site.commodity, normalize="index")`

| Profil | Part de gaz |
|---|---|
| PROFILE_BASE | 37,3 % |
| PROFILE_FLAT | 38,2 % |
| PROFILE_PEAK | 37,1 % |
| PROFILE_SEASONAL | 36,2 % |
| **portefeuille** | **37,2 %** |

Prédiction falsifiée. Les quatre profils collent au taux global à un point près. `profile_type` est
indépendant de `commodity`.

Observation complémentaire : un profil type sert à **estimer** la consommation d'un site qu'on ne
mesure pas. Les 500 sites télérelevés en portent pourtant un, dans les mêmes proportions que les
autres. Cohérent avec une affectation aléatoire, incohérent avec un usage métier.

### Famille d'anomalies n° 1 : les attributs descriptifs de `ref_site` sont affectés au hasard

Trois colonnes, un seul mécanisme.

| Colonne | Ce qui devrait la déterminer | Résultat |
|---|---|---|
| `dso` | `region` et `commodity` | indépendante des deux |
| `monitored` | `contracted_capacity_kw` | indépendante, plus indépendante de `commodity` et `profile_type` |
| `profile_type` | `commodity` | indépendante |

**Comptée comme une seule famille** parmi les quatre annoncées par le sujet. Une famille d'anomalies
se définit par sa cause et par son remède, non par le nombre de colonnes qu'elle touche : la cause est
unique, une affectation aléatoire à la génération du référentiel, et le remède est unique, reconstruire
la source. Trois familles restent donc à chercher ailleurs.

*Alternative écartée* : compter trois familles, une par colonne, au motif que les conséquences métier
diffèrent, `dso` cassant la logique d'acheminement, `monitored` le périmètre de suivi horaire et
`profile_type` l'estimation de courbe de charge. Écartée parce qu'elle conduirait à annoncer trois
familles sur quatre trouvées, ce que la démonstration ne soutient pas.

**Chiffrage de la famille.** Seul `dso` est réfutable ligne à ligne, par contradiction physique :
267 lignes, 19,1 % du référentiel, 1 125 523 kW soit 21,5 % de la puissance. `monitored` et
`profile_type` ne se chiffrent pas de la même manière : aucune de leurs valeurs n'est individuellement
impossible, c'est leur distribution qui est vide de sens. Pour ces deux colonnes, l'impact n'est pas un
nombre de lignes mais l'inexploitabilité complète, soit 1 400 lignes sur 1 400.

**Portée pour la suite.** Aucun contrôle, aucune jointure et aucun regroupement ne doit s'appuyer sur
`dso`, `monitored` ou `profile_type`. Conséquence directe sur la Mission 4 : `monitored` ne permet pas
d'identifier les sites suivis en horaire, il faudra dériver ce périmètre de `volumes_hourly` elle-même.
`contracted_capacity_kw` reste exploitable et conserve son rôle de grandeur de référence par site.

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

**Classement** : anomalie de référentiel. `dso` n'est pas une famille à lui seul : il est le volet
réfutable ligne à ligne d'une famille plus large, décrite plus bas sous « Famille d'anomalies n° 1 »,
qui couvre également `monitored` et `profile_type`. Alternative écartée : bruit statistique. Elle ne
tient pas, une affectation bruitée resterait corrélée à la géographie et à l'énergie, ce qui n'est le
cas d'aucun des deux tests.

**Portée pour la suite** : toute jointure, tout regroupement ou tout filtre s'appuyant sur `dso` produira
un résultat sans signification. `region` n'est pas disqualifiée pour autant, sa cohérence propre reste
à tester séparément.

*Note de provenance : la connaissance métier mobilisée ici, parts de marché d'Enedis et de GRDF,
périmètre départemental de GEREDIS et de SRD, séparation physique des réseaux gaz et électricité,
n'est pas déduite des données. Elle vient de l'extérieur du jeu de données et c'est elle qui rend la
prédiction falsifiable.*

---

# 3. `ref_contract`

Colonnes : `contract_id`, `customer_id`, `commodity`, `start_date`, `end_date`, `pricing_type`,
`volume_tolerance_pct`.

Première table du référentiel à porter des dates. Première à contenir une mesure exprimée en
pourcentage. Elle porte deux des trois questions à trancher de la Mission 0 : la reconstruction du
lien site vers contrat, et le décompte des sites relevant d'un contrat inexistant ou expiré.

## Niveau 0 - cadrage

**Que représente une ligne** (une phrase, nom au singulier) :

Une ligne représente un contrat, expiré, en cours, ou futur, d'un client de la plateforme B2B France gaz et électricité portant sur une commodité. Les contrats successifs d'un client coexistent dans la table au lieu de s'écraser. Un client peut avoir plusieurs contrats, mais un contrat ne peut pas concerner plusieurs clients.

**Maille** :

Une ligne par *contract_id*. 
- Pas de *contract_id x customer_id* car un contrat n'appartient qu'à un seul client : *customer_id* est déterminé par *contract_id* et n'ajoute aucun pouvoir discriminant. 
- pas de *contract_id x date*, 
- pas de *contract_id x site*
- pas de *contract_id x commodity*

**Clés candidates** (colonnes seules ou combinées qui devraient identifier une ligne) :

*contract_id*.

*(customer_id, commodity)* ne peut pas représenter une clé candidate : un client qui renouvelle son contrat reste dans la table par historique. Donc non unique.

**Nombre de lignes prédit**, et le raisonnement qui y mène :

**Plancher, à partir de faits établis.**

| Fait | Source |
|---|---|
| 146 clients sur 220 ont au moins un contrat | anti-jointure, Niveau 0 de `ref_customer` |
| 37 clients porteurs de contrats ont des contrats dans les deux commodités | mesuré sur `ref_contract`, voir réserve ci-dessous |

```
 37 clients bi-commodité   x 2 contrats minimum  =  74
109 clients mono-commodité x 1 contrat minimum   = 109
                                        plancher = 183 lignes au total
```

Ce plancher porte sur le **nombre total de lignes**, toutes dates confondues, puisque le comptage des
37 clients bi-commodité n'applique aucun filtre temporel. Il ne dit rien du nombre de contrats en
vigueur.

La prédiction totale vaut 183 multiplié par le **facteur de renouvellement**, c'est-à-dire le nombre
moyen de générations de contrats que la table conserve par client.

**Facteur de renouvellement retenu : 2.** La table conserverait la génération en cours et une
génération précédente. Sur des contrats pluriannuels de l'ordre de trois ans, cela correspond à un
historique d'environ cinq à six ans, ce qui est cohérent avec une base d'extraction alimentant un
suivi de position sur l'année de livraison 2026 et les deux suivantes.

**Prédiction de volumétrie : environ 370 lignes, intervalle [275 ; 460].** L'intervalle est large et
assumé : il traduit l'incertitude sur le facteur de renouvellement, qui est le seul inconnu réel.
Une tolérance étroite serait ici une tolérance inventée.

**Prédictions annexes, sur des grandeurs jamais affichées.**

Les trois parts ci-dessous portent sur la même table et doivent sommer à 100 % : un contrat est soit
expiré, soit en vigueur, soit à venir au 24 juillet 2026.

| # | Promesse | Prédiction | Raisonnement |
|---|---|---|---|
| A | Nombre de contrats par client | minimum 1, maximum de l'ordre de 4 à 6, en tout état de cause inférieur à 10 | un client détient au plus un contrat par commodité et par génération ; deux commodités et deux générations bornent le maximum |
| B | Part des contrats expirés (`end_date` antérieure au 24 juillet 2026) | **environ 50 %**, intervalle [35 % ; 65 %] | découle directement du facteur de renouvellement de 2 : la génération précédente représente la moitié des lignes. Une part supérieure à 65 % impliquerait un facteur supérieur à 3, donc un historique d'une quinzaine d'années, incompatible avec une base d'extraction. Une part inférieure à 35 % contredirait l'affirmation de Niveau 0 selon laquelle les contrats successifs coexistent |
| C | Part des contrats à venir (`start_date` postérieure au 24 juillet 2026) | **entre 0 et 10 %** | un renouvellement se signe plusieurs mois avant sa date de prise d'effet, il est donc normal qu'une petite part des lignes ne soit pas encore entrée en vigueur. Une part nulle signalerait que la table ne conserve que les contrats déjà démarrés, ce qui contredirait la phrase de Niveau 0 qui annonce des contrats futurs |
| D | Part des contrats en vigueur, par complément | environ 45 %, soit de l'ordre de 165 lignes | complément de B et C. À rapprocher des 146 clients porteurs de contrats : cela donnerait environ 1,1 contrat en vigueur par client, cohérent avec le fait que 37 clients seulement sont bi-commodité |


**Prédiction brûlée, à ne pas compter comme opposable.**

La part de clients bi-commodité côté contrats devait faire l'objet d'une prédiction. Elle a été
mesurée avant que la prédiction soit écrite : **37 clients sur 146**, soit 25,3 %.

Ce chiffre est à rapprocher de la mesure correspondante sur `ref_site` : **188 clients sur 220**, soit
85,5 %, disposent de sites dans les deux commodités. L'écart est considérable. La majorité des clients
est fournie en gaz et en électricité alors qu'un quart seulement est contractualisé dans les deux
énergies. Beaucoup de clients détiennent donc des sites dans une commodité pour laquelle aucun contrat
n'existe.

Point reporté au **Niveau 2**. Il alimente la troisième question à trancher de la Mission 0, celle des
sites relevant d'un contrat inexistant, et il est plus discriminant que le décompte des 74 clients sans
aucun contrat. Ne pas conclure avant que le lien site vers contrat soit reconstruit.

**Résultat et écart** :

Tests exécutés dans `notebooks/mission0_cartographie.ipynb`, section `ref_contract`.

| Promesse | Prédiction | Résultat | Écart |
|---|---|---|---|
| Volumétrie | ~370, intervalle [275 ; 460] | **260** | **falsifiée**, 15 lignes sous la borne basse |
| `contract_id` unique | unique | 260 / 260 | **0** |
| Clients porteurs de contrats | 146 | 146 | **0** |
| A, contrats par client | min 1, max 4 à 6, en tout état de cause < 10 | min 1, **max 7** | **partiellement falsifiée** : au-dessus de la fourchette, sous la borne de sécurité |
| B, part des expirés | 50 %, intervalle [35 % ; 65 %] | **28,1 %** (73 lignes) | **falsifiée**, sous la borne basse |
| C, part des contrats à venir | 0 à 10 % | **0 %** (0 ligne) | confirmée à la borne |
| D, part en vigueur | ~45 %, ~165 lignes | **71,9 %** (187 lignes) | **falsifiée** |

Contrôle de somme : 73 + 0 + 187 = 260. Aucune ligne n'échappe aux trois filtres, donc aucune date
nulle et la convention de bornes retenue est la bonne.

**Distribution des contrats par client**

| Contrats | Clients |
|---|---|
| 1 | 76 |
| 2 | 39 |
| 3 | 22 |
| 4 | 7 |
| 5 | 1 |
| 7 | 1 |

Somme de contrôle : 146 clients, 260 contrats. Le client à 7 contrats implique, avec deux commodités
seulement, au moins un couple client-commodité portant 4 contrats successifs.

### Une seule hypothèse fausse explique trois écarts

Le facteur retenu était de 2 contrats par couple client-commodité. La réalité donne :

```
260 lignes / 183 couples = 1,42
```

La volumétrie, la part d'expirés et la part en vigueur ne sont pas trois erreurs indépendantes : ce
sont trois conséquences d'un seul paramètre mal calibré. La couche historique est plus mince que
prévu, donc moins d'expirés et davantage de contrats en vigueur. Le modèle de Niveau 0 est juste,
seule sa profondeur temporelle était surestimée.

Correction de vocabulaire par rapport à la prédiction : 183 n'est pas un nombre de renouvellements
mais le nombre de couples client-commodité, donc de premiers contrats. Les renouvellements sont les
77 lignes excédentaires, et ils sont bornés par le nombre de contrats expirés puisqu'on ne renouvelle
pas un contrat en cours.

### La validation apparente du modèle était fausse

Premier constat, séduisant et trompeur :

```
plancher structurel   183 couples
contrats en vigueur   187
écart                   4
```

Quatre lignes d'écart ressemble à une confirmation du modèle « un contrat en cours par client et par
commodité ». C'est faux. Le détail par couple donne :

| Mesure | Valeur |
|---|---|
| Couples client-commodité au total | 183 |
| dont ayant au moins un contrat en vigueur | 146 |
| dont **aucun** contrat en vigueur | **37** |
| Couples portant **plusieurs** contrats en vigueur | **35** |
| Contrats en excès sur ces couples | **41** |

```
41 contrats en trop  -  37 couples découverts  =  4
```

Les quatre lignes d'écart ne sont pas un petit résidu : c'est la **différence entre deux défauts
opposés de grande taille qui se compensent presque**. Un agrégat qui tombe juste peut masquer deux
erreurs importantes de sens contraire.

**Troisième contrôle vert sur données fausses du projet**, et le plus instructif des trois. Le premier
venait d'une requête fautive, le deuxième d'une convention d'encodage, celui-ci d'une **compensation
entre deux anomalies**. Aucune relecture de code ne l'aurait détecté : il fallait descendre d'une
maille, du total vers le couple.

Contrôle à ajouter au harnais : **un total qui correspond ne prouve rien tant qu'il n'a pas été
décomposé à la maille inférieure.**

### Défaut A : couverture en double

35 couples client-commodité portent deux ou trois contrats en vigueur simultanément au 24 juillet
2026, dont 6 en portent trois. Soit **41 contrats en excès**.

| Rapporté à | Part |
|---|---|
| Couples ayant un contrat actif (146) | **24,0 %** |
| Contrats en vigueur (187) | **21,9 %** |
| Lignes de la table (260) | 15,8 % |

Un même client, sur la même énergie, sous deux ou trois contrats actifs à la même date. C'est
impossible métier : le client serait fourni et facturé plusieurs fois pour la même consommation, et le
desk couvrirait plusieurs fois le même volume.

**Retenu comme deuxième famille d'anomalies** parmi les quatre annoncées. Le défaut est structuré et
non diffus : 35 couples nettement identifiés, avec une concentration apparente sur `POWER`.

*Alternative écartée* : des contrats successifs dont les bornes se recouvrent d'un jour ou deux lors
d'un renouvellement, ce qui serait un artefact de saisie sans portée. Écartée en l'état parce que le
recouvrement porterait alors sur une fenêtre étroite, alors qu'ici il est constaté à une date de
référence unique et arbitraire, le 24 juillet. À confirmer en mesurant la durée réelle des
recouvrements.

**Limite de chiffrage.** L'impact ne peut pas être exprimé en MWh ni en euros à ce stade :
`ref_contract` ne porte aucun volume, `volume_tolerance_pct` étant une marge et non une quantité. Le
chiffrage volumétrique passera par les sites, donc par le Niveau 2.

### Défaut B : couverture absente

37 couples client-commodité ont eu un contrat par le passé mais n'en ont aucun en vigueur au
24 juillet 2026.

*Attention à une coïncidence piégeuse* : ce 37 n'a aucun rapport avec les 37 clients bi-commodité
mesurés plus haut. Même nombre, mailles différentes.

Le constat s'élargit quand on le rapporte à la couverture réelle en énergie :

| Périmètre, à la maille client-commodité | Couples |
|---|---|
| Ayant au moins un **site** | 188 × 2 + 32 × 1 = **408** |
| Ayant eu un **contrat**, à n'importe quelle date | 183 |
| Ayant un contrat **en vigueur** | 146 |

Sur 408 couples effectivement fournis en énergie, 146 seulement sont couverts par un contrat en
vigueur. Aux 37 couples qui n'ont plus de contrat s'ajoutent 225 couples qui n'en ont jamais eu.

**Non tranché, reporté au Niveau 2.** Ces nombres sont à la maille client-commodité, alors que la
troisième question du sujet porte sur les **sites**. Le passage de l'une à l'autre suppose le lien
site vers contrat, qui n'est pas matérialisé et reste à reconstruire.

### Révision de la phrase de Niveau 0

La phrase annonce des contrats « expiré, en cours, ou **futur** ». La table n'en contient **aucun de
futur** : 0 ligne sur 260 a une `start_date` postérieure au 24 juillet 2026. La phrase est donc fausse
sur ce point et se corrige en « expiré ou en cours ».

Deux lectures de cette absence, à départager plus tard : soit la table ne conserve que les contrats
déjà entrés en vigueur, soit les renouvellements sont enregistrés à leur date d'effet et non à leur
date de signature. La seconde impliquerait qu'un contrat signé aujourd'hui pour janvier prochain est
invisible dans le référentiel, ce qui serait une limite sérieuse pour le dimensionnement des
couvertures.

*Note d'honnêteté* : la prédiction initiale sur ce point était de 0 %, et elle a été élargie à
[0 % ; 10 %] au motif qu'un 0 contredirait la phrase de Niveau 0. C'est la prédiction initiale qui
était la bonne, et la révision qui a affaibli le test. La contradiction relevée était réelle, mais
elle portait sur la phrase de Niveau 0, pas sur la prédiction.

## Niveau 1 - colonnes

Ordre retenu : clés et colonnes de jointure, puis les dates qui commandent la validité du contrat,
puis la mesure, puis les descriptifs. Les dates passent avant `volume_tolerance_pct` bien qu'elles ne
soient pas des clés : ce sont elles qui déterminent si une ligne est en vigueur, et tout le Niveau 0
repose déjà dessus.

| Colonne | Promesse du nom | Classe | Prédiction | Résultat | Écart | Verdict |
|---|---|---|---|---|---|---|
| `contract_id` | Identifie un contrat de façon unique et stable. | unicité, complétude | unique et non nul (traité au Niveau 0) | 260 lignes / 260 distincts | 0 | conforme |
| `customer_id` | Rattache le contrat au client signataire, et sert de clé de jointure vers `ref_customer`. | complétude, intégrité référentielle | 146 valeurs distinctes, 0 orphelin (traité au Niveau 0) | 146 distincts, 0 orphelin | 0 | conforme |
| `start_date` et `end_date` | Donnent la date de prise d'effet et la date d'échéance du contrat. | cohérence de couple | **0 ligne** avec `start_date` postérieure à `end_date` : une base de gestion contractuelle contrôle en principe cette cohérence à la saisie | | | |
| `start_date` et `end_date` | La durée séparant les deux bornes. | ordre de grandeur | durée comprise **entre 1 et 3 ans**, le sujet qualifiant les contrats de pluriannuels | | | |
| `volume_tolerance_pct` | Donne la marge autour du volume prévisionnel à l'intérieur de laquelle le client ne subit ni pénalité ni règlement au prix du marché. | complétude, domaine, ordre de grandeur, convention d'unité | **0 nul**, tout contrat porte une tolérance ; **aucune valeur négative ni nulle** ; valeurs **entre 10 et 20** ; convention **[0 ; 100]** et non [0 ; 1] | | | |
| `commodity` | Indique l'énergie sur laquelle porte le contrat. | domaine de valeurs, complétude | domaine exactement **{GAS, POWER}**, le dictionnaire du README ne mentionnant que ces deux énergies | | | |
| `pricing_type` | Indique le mode de fixation du prix de l'énergie sur la durée du contrat. | domaine de valeurs, complétude | **2 modalités**, un prix fixé à la signature et un prix indexé sur un indice de marché | | | |

Ce qui est déjà acquis par le Niveau 0 et n'a pas à être retesté : `contract_id` est unique et non nul,
`customer_id` compte 146 valeurs distinctes sans orphelin, et aucune des deux dates n'est nulle,
puisque les trois filtres temporels totalisent exactement 260 lignes.

### Résultat et écart

| Promesse | Prédiction | Résultat | Écart |
|---|---|---|---|
| Dates inversées | 0 | **0** | **0** |
| Durée des contrats | entre 1 et 3 ans | min 1, médiane 2, max 3 | **0** |
| `volume_tolerance_pct` nulle | 0 | 0 sur 260 | **0** |
| `volume_tolerance_pct` négative ou nulle | 0 | 0 | **0** |
| `volume_tolerance_pct`, plage de valeurs | entre 10 et 20 | **min 5**, max 20 | **partiellement falsifiée**, borne basse dépassée |
| `volume_tolerance_pct`, convention | [0 ; 100] | valeurs 5, 10, 15, 20 | **0** |
| `commodity`, domaine | {GAS, POWER} | 2 modalités | **0** |
| `pricing_type`, nombre de modalités | 2 | **4** | **falsifiée**, +2 |

**Distribution de `volume_tolerance_pct`**

| Valeur | Contrats | Part |
|---|---|---|
| 5 | 53 | 20,4 % |
| 10 | 78 | 30,0 % |
| 15 | 65 | 25,0 % |
| 20 | 64 | 24,6 % |

Les quatre valeurs forment une grille régulière de 5 en 5. Ce n'est pas une distribution continue mais
un **barème**, ce qui explique que la borne basse ait été dépassée : la fourchette usuelle de 10 à 20 %
décrit une pratique de marché, pas une échelle de valeurs contractuelles. Une bande de 5 % est serrée
mais légitime, typiquement sur un site à consommation très prévisible.

**Distribution de `pricing_type` croisée avec `commodity`**

| `pricing_type` | POWER | GAS | Total | Part |
|---|---|---|---|---|
| FIXED | 75 | 40 | **115** | 44,2 % |
| INDEXED | 36 | 23 | **59** | 22,7 % |
| CLICK | 34 | 20 | **54** | 20,8 % |
| SPOT_PASSTHROUGH | 22 | 10 | **32** | 12,3 % |
| **Total** | 167 | 93 | 260 | |

Les parts par commodité s'écartent de moins de trois points des parts globales : `pricing_type` et
`commodity` sont indépendants. Ce constat n'appelle aucune remarque, rien dans le métier n'imposant
qu'un mode de fixation du prix dépende de l'énergie livrée. Au passage, 93 contrats gaz sur 260 font
35,8 %, proche des 37,2 % de sites gaz mesurés sur `ref_site`.

### `pricing_type` détermine ce que le desk doit couvrir

La prédiction de deux modalités reposait sur une vision incomplète du produit. Les quatre modalités
observées ne sont pas des étiquettes équivalentes : elles déterminent **qui porte le risque de prix**,
donc le volume que le desk doit couvrir sur le marché de gros.

| Modalité | Qui porte le risque de prix | Couverture attendue |
|---|---|---|
| `FIXED` | le fournisseur, intégralement | 100 % du volume, dès la signature |
| `INDEXED` | partagé, le prix suit un indice | partielle |
| `CLICK` | le client, qui fixe son prix par tranches successives | progressive, construite au fil des clics |
| `SPOT_PASSTHROUGH` | le client, le prix spot lui est répercuté | quasi nulle |

`CLICK` est la modalité la plus spécifique au B2B. Le client fige une fraction de son volume au prix
forward du jour, à des moments qu'il choisit pendant la vie du contrat. Entre deux clics, la position
reste ouverte. C'est un produit structuré, ce qui donne son sens au book `B2B_FR_STRUCT` observé dans
`trd_deal`.

**Conséquence pour la Mission 2.** Le taux de couverture attendu diffère selon `pricing_type`.
Comparer la position couverte au volume client sans distinguer ces quatre modalités produirait un
déséquilibre apparent qui n'en serait pas un : 12,3 % des contrats n'appellent quasiment aucune
couverture, et 20,8 % en appellent une construite progressivement. Segmentation à reprendre au moment
de croiser position et volumes clients.

### Verdict du Niveau 1 de `ref_contract`

**Aucune anomalie.** Les deux prédictions falsifiées le sont par défaut de connaissance métier de ma
part, non par défaut de la donnée : la grille de tolérance est régulière, les dates sont cohérentes,
les durées sont conformes à des contrats pluriannuels, et les quatre modalités de tarification sont
toutes légitimes.

Les deux défauts de cette table sont ceux identifiés au Niveau 0, la couverture en double et la
couverture absente, et ils portent sur la structure des lignes, pas sur le contenu des colonnes.


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

| # | Paire | Colonne de jointure | Cardinalité | Statut |
|---|-------|---------------------|-------------|--------|
| 1 | `ref_site` → `ref_customer` | `customer_id` | un à plusieurs | **traitée**, voir ci-dessous |
| 2 | `ref_contract` → `ref_customer` | `customer_id` | un à plusieurs | **traitée**, voir ci-dessous |
| 3 | `ref_site` ↔ `ref_contract` | `(customer_id, commodity)` + filtre temporel | plusieurs à plusieurs | **prédite**, mesure à venir |
| 4 | `volumes_hourly` → `ref_site` | `site_id` | | Mission 4 |
| 5 | `actuals_daily` → `ref_site` | `site_id` | | Mission 5 |
| 6 | `pos_snapshot` ↔ `trd_deal` | `book`, `commodity`, mois de livraison | | Mission 2 |
| 7 | `mkt_forward_curve` ↔ `trd_deal` | `commodity`, mois de livraison | | Mission 3 |
| 8 | `bo_confirmations` ↔ `trd_deal` | `deal_ref` / `deal_id` | | clé non propre, Mission 1 |

Les paires 4 à 8 ne sont pas traitées en Mission 0 : elles engagent des tables dont le cadrage est
renvoyé à la mission qui les exploite.

## Paire 1 : `ref_site` → `ref_customer`

**Colonne de jointure** : `customer_id`. Seule colonne commune aux deux tables, et clé candidate de
`ref_customer`, établie unique et non nulle au Niveau 0. Une jointure sur une clé candidate du côté
référencé est la seule qui garantisse qu'une ligne de gauche ne rencontre au plus qu'une ligne de
droite.

**Cardinalité : un à plusieurs.** Un client possède plusieurs sites, un site appartient à un seul
client. Côté `ref_site`, la cardinalité vaut 1 par construction, la maille étant le site et chaque
ligne ne portant qu'un `customer_id`. Côté `ref_customer`, 1 400 sites pour 220 clients établissent
que « plusieurs » est bien atteint.

**Orphelins, comptés séparément :**

| Sens | Résultat |
|---|---|
| de `ref_site` vers `ref_customer` | **0** : tout `customer_id` de `ref_site` existe dans `ref_customer` |
| de `ref_customer` vers `ref_site` | **0** : tout client possède au moins un site |

**Nombre de lignes de la jointure : exactement 1 400.** La clé du côté référencé étant unique, aucune
ligne n'est dupliquée ; aucun orphelin d'aucun côté, donc aucune ligne perdue. Jointure interne et
jointure externe donnent ici le même résultat.

C'est le cas de référence auquel comparer les deux paires suivantes.

## Paire 2 : `ref_contract` → `ref_customer`

**Colonne de jointure** : `customer_id`, même justification qu'à la paire 1.

**Cardinalité : un à plusieurs.** 260 contrats pour 146 clients porteurs, la distribution mesurée au
Niveau 1 allant jusqu'à 7 contrats pour un même client.

**Orphelins, comptés séparément :**

| Sens | Résultat |
|---|---|
| de `ref_contract` vers `ref_customer` | **0** : aucun contrat ne pointe vers un client inexistant |
| de `ref_customer` vers `ref_contract` | **74 clients** sans aucun contrat |

Ces deux échecs n'auraient pas la même signification. Le premier serait une rupture d'intégrité
référentielle, défaut de données franc sans lecture métier possible. Le second signifie seulement
qu'un client n'a pas de contrat, ce qui peut relever d'une réalité métier. D'où l'exigence de les
compter séparément.

**Nombre de lignes de la jointure :**

| Type | Lignes |
|---|---|
| Interne | **260**, aucune duplication et aucune perte côté contrats |
| Externe depuis `ref_customer` | **334**, soit 260 plus les 74 clients sans contrat |

**Différence décisive avec la paire 1.** La paire 1 n'ayant d'orphelin d'aucun côté, les deux types de
jointure coïncident. La paire 2 en a 74 d'un seul côté : interne et externe divergent d'autant. Un
reporting construit sur une jointure interne perdrait silencieusement 74 clients, sans qu'aucun total
ne le signale.

## Paire 3 : `ref_site` ↔ `ref_contract`

C'est la deuxième question à trancher de la Mission 0.

**Colonne de jointure.** Aucune clé étrangère ne matérialise ce lien. Les deux tables n'ont que deux
colonnes en commun, `customer_id` et `commodity`. Le lien se reconstruit donc sur le couple
`(customer_id, commodity)`, complété du filtre `start_date <= '2026-07-24' and end_date >= '2026-07-24'`,
un site devant être rattaché à un contrat en vigueur et non à un contrat expiré.

*Alternative écartée* : joindre sur `customer_id` seul. Elle rattacherait un site gaz à un contrat
électricité du même client, ce qui n'a pas de sens métier, et gonflerait artificiellement le nombre
d'appariements.

**Cardinalité prédite : plusieurs à plusieurs.** Contrairement aux paires 1 et 2, la clé de jointure
n'est unique d'aucun des deux côtés. Un couple porte plusieurs sites et jusqu'à trois contrats en
vigueur.

**Base de calcul.** Les couples `(client, commodité)` se dénombrent des deux côtés :

| Côté | Construction | Couples |
|---|---|---|
| `ref_site` | 188 clients bi-commodité × 2 + 32 mono-commodité × 1 | **408** |
| `ref_contract`, toutes dates | 37 clients bi-commodité × 2 + 109 mono-commodité × 1 | **183** |
| `ref_contract`, en vigueur au 24/07/2026 | mesuré au Niveau 0 | **146** |

Encadrement de vraisemblance : avec 220 clients et 2 commodités, le nombre de couples côté sites est
nécessairement compris entre 220 et 440. Côté contrats, entre 146 et 292. Les deux valeurs s'y
inscrivent.

**Prédictions**, sous hypothèse d'une répartition uniforme des sites entre les 408 couples, soit
1 400 / 408 = **3,43 sites par couple**. C'est le pari neutre, faute d'élément indiquant que les
couples couverts seraient plus gros.

| # | Grandeur | Prédiction | Dérivation |
|---|---|---|---|
| A | Lignes de la jointure interne | **environ 640** | 187 contrats en vigueur × 3,43 sites par couple |
| B | Sites orphelins, sans contrat en vigueur | **au moins 900**, intervalle [750 ; 1 000] | au moins 262 couples découverts sur 408, soit 64,2 % de 1 400 |
| C | Puissance des sites orphelins | **environ 3,37 M kW**, soit 64,2 % | prédiction neutre : les sites orphelins sont de taille moyenne |
| D | Contrats orphelins, sans site correspondant | **faible, quelques dizaines** | un contrat sur une commodité où le client ne possède aucun site |

**Pourquoi B est un plancher et non une valeur.** Le calcul 408 - 146 = 262 suppose que les 146 couples
sous contrat sont tous inclus dans les 408 couples ayant des sites. Rien ne le garantit : un client
peut détenir un contrat gaz en vigueur sans posséder le moindre site gaz, ce qui est précisément
l'objet de la prédiction D. Si de tels cas existent, moins de 146 couples-sites sont couverts et le
nombre de sites orphelins dépasse 900. Une soustraction entre deux ensembles n'a de sens que si
l'un est inclus dans l'autre, et l'inclusion n'est pas établie.

**Piège à signaler.** La jointure interne rendrait environ **640 lignes pour 1 400 sites**, donc moins
que le nombre de sites, alors qu'elle en duplique une partie : les sites appartenant aux 35 couples
multi-contrats apparaîtront deux ou trois fois. Perte massive et duplication partielle sont deux effets
opposés dont un simple `count(*)` ne montrerait que la résultante.

Troisième occurrence de ce mécanisme, après la fausse validation du plancher de 183 et le contrôle de
somme à 260. Même conclusion : un agrégat ne se lit pas sans être décomposé à la maille inférieure.

### Résultat et écart

Mesures réalisées avec `pandas.merge(..., indicator=True)`, qui produit une partition exclusive et
exhaustive en trois catégories sans reposer sur aucune hypothèse de nullité, contrairement à
l'anti-jointure `left join ... is null` qui suppose que la colonne testée ne peut pas être nulle par
elle-même.

**Couples client-commodité, fusion externe des deux côtés :**

```
left_only   270    couples ayant des sites, sans contrat en vigueur
both        138    couples couverts
right_only    8    couples ayant un contrat en vigueur, sans aucun site
```

Contrôles : `270 + 138 = 408` côté sites, `138 + 8 = 146` côté contrats. Les deux dénombrements
déduits au moment de la prédiction sont confirmés.

| # | Grandeur | Prédiction | Résultat | Écart |
|---|---|---|---|---|
| | Couples côté sites | 408, déduit | **408** | **0** |
| | Couples sous contrat en vigueur | 146 | **146** | **0** |
| A | Lignes de la jointure interne | ~640 | **648** | +8, soit +1,3 % |
| | Lignes de la jointure externe | ~1 540 | **1 547** | +7 |
| B | Sites orphelins | au moins 900, [750 ; 1 000] | **899** | dans l'intervalle, mais le plancher « au moins 900 » est faux d'une unité |
| C | Puissance des sites orphelins | 3,37 M kW, soit 64,2 % | **3 402 619 kW**, soit **64,91 %** | +0,7 point |
| D | Couples contrats sans site | quelques dizaines | **8** | ordre de grandeur surestimé |

### La réserve sur le plancher était fondée

La prédiction B signalait que `408 - 146 = 262` était un plancher et non une valeur, la soustraction
supposant une inclusion non démontrée. Elle ne l'est effectivement pas : **8 couples ont un contrat en
vigueur sans aucun site**. Seuls 138 couples-sites sont donc couverts, et les orphelins sont **270**,
non 262.

### Le 899 tombe juste pour de mauvaises raisons

La dérivation prédite était `262 couples × 3,43 sites = 899,4`. Le réel est `270 couples × 3,33
sites = 899`.

Les deux composantes sont fausses et dans des sens opposés : le nombre de couples découverts était
sous-estimé, le nombre de sites par couple surestimé. Les erreurs se compensent presque exactement.

**Quatrième occurrence du mécanisme de compensation dans cette mission**, après la fausse validation du
plancher de 183, le contrôle de somme à 260 et la jointure qui perd et duplique simultanément. C'est
l'enseignement le plus solide de la Mission 0 : **un résultat juste ne valide pas le raisonnement qui y
mène**, et seule la décomposition permet de le savoir.

Note complémentaire sur C : les sites orphelins pèsent 64,91 % de la puissance pour 64,21 % des lignes.
L'écart de 0,7 point est faible, l'absence de contrat ne se concentre donc ni sur les gros sites ni sur
les petits.

### Candidat d'anomalie : 8 couples sous contrat sans point de livraison

8 couples `(client, commodité)` portent un contrat **en vigueur** au 24 juillet 2026 alors que le
client ne possède **aucun site** dans cette commodité. Le desk serait engagé à fournir une énergie
qu'il ne livre nulle part, et couvrirait un volume sans point de livraison associé.

L'explication la plus naturelle, un contrat signé par anticipation avant raccordement du site, ne tient
pas : le Niveau 1 a établi qu'il n'existe **aucun contrat futur** dans la table, tous les contrats ont
déjà pris effet.

Deux lectures restent ouvertes : soit les sites correspondants ont été supprimés du référentiel alors
que leurs contrats subsistent, soit la commodité est mal renseignée sur l'une des deux tables. La
seconde est plausible compte tenu de la famille d'anomalies n° 1, où trois colonnes descriptives de
`ref_site` se sont révélées aléatoires, mais `commodity` n'en fait pas partie et son domaine est propre
des deux côtés.

Population faible, incohérence franche. À rapprocher des quatre familles annoncées, sans conclure.

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
