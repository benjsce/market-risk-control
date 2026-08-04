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

| Colonne | Promesse du nom (une phrase) | Classe de promesse | Prédiction | Résultat | Écart | Verdict |
|---------|------------------------------|--------------------|------------|----------|-------|---------|

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

> à remplir après exécution

## Niveau 1 - colonnes

| Colonne | Promesse du nom (une phrase) | Classe de promesse | Prédiction | Résultat | Écart | Verdict |
|---------|------------------------------|--------------------|------------|----------|-------|---------|

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
