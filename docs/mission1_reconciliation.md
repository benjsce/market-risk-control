# Mission 1 - Réconciliation front / back office

Le back office a envoyé son extrait du 24 juillet 2026. Il doit correspondre au contenu de `trd_deal`.
Il ne correspond pas.

Objectif : un moteur de réconciliation qui classe chaque transaction dans une catégorie d'écart
**exclusive et exhaustive**, avec un montant d'impact.

Date de référence : **24 juillet 2026**. Familles d'écarts annoncées par le sujet : **13**.

## Sources

| Source | Contenu | État |
|---|---|---|
| `risk.db` → `trd_deal` | deals de couverture saisis au front, en temps réel | non cadrée |
| `data/raw/bo_confirmations_20260724.csv` | extrait plat du back office, confirmations avec les contreparties | non ouvert |

Le back office « envoie un extrait plat chaque soir. Schéma différent, conventions différentes,
personne ne sait exactement pourquoi. » Il n'existe aucune spécification écrite du mapping entre les
deux systèmes.

## Méthode

Identique à la Mission 0, voir `docs/mission0_cartographie.md`. Rappel des règles transversales :

- une promesse en français, une prédiction chiffrée, puis la mesure ;
- le commit des prédictions précède le commit des résultats ;
- tout écart chiffré en nombre de lignes **puis** en MWh et en euros ;
- toute décision accompagnée de l'alternative écartée ;
- un agrégat qui tombe juste se décompose à la maille inférieure avant d'être accepté.

---

# Acquis de la Mission 0

Le détail est dans `docs/mission0_cartographie.md`. Ne sont repris ici que les éléments qui servent
directement à cette mission.

## Ce qui est fiable dans le référentiel

`customer_id`, `site_id`, `contract_id` sont des clés sûres, uniques et sans orphelin. `commodity` a
pour domaine `{GAS, POWER}` des deux côtés. `contracted_capacity_kw` est la seule grandeur numérique
exploitable et sert de taille de référence par site.

## Ce qui est inexploitable

`dso`, `monitored` et `profile_type` sont affectés au hasard dans `ref_site`. Ne jamais joindre,
filtrer ni regrouper dessus. `credit_rating` code l'absence de notation par la valeur `NR` et non par
un nul, ce qui rend tout contrôle de complétude inopérant sur cette colonne.

## Ce qui éclaire la couverture

`pricing_type` compte quatre modalités qui déterminent **qui porte le risque de prix**, donc ce que le
desk doit couvrir :

| Modalité | Contrats | Couverture attendue |
|---|---|---|
| `FIXED` | 115 | intégrale, dès la signature |
| `INDEXED` | 59 | partielle |
| `CLICK` | 54 | progressive, construite au fil des clics du client |
| `SPOT_PASSTHROUGH` | 32 | quasi nulle, le client porte le risque |

Les 54 contrats en `CLICK` donnent son sens au book `B2B_FR_STRUCT` observé dans `trd_deal`.

## Outils déjà éprouvés

`pandas.merge(..., indicator=True)` produit une partition exclusive et exhaustive en `both`,
`left_only`, `right_only`, sans reposer sur aucune hypothèse de nullité. C'est l'outil de la
réconciliation demandée ici.

L'échelle de normalisation construite sur `customer_name` en Mission 0 n'a fusionné aucune ligne,
faute de matière. Elle n'est donc pas validée, seulement écrite. Elle sera réellement éprouvée sur les
codes contrepartie de l'extrait back office.

---

# Point ouvert repris de la Mission 0 : la clé primaire réelle de `trd_deal`

Première question à trancher de la Mission 0, laissée ouverte, et première dépendance de la Mission 1 :
tant qu'on ne sait pas ce qu'est **un deal**, on ne sait pas ce qu'on réconcilie.

Le sujet formule la question ainsi : *« Quelle est la clé primaire réelle de `trd_deal` ? Ce n'est pas
`deal_id`. Pourquoi, et qu'est-ce que ça implique pour toute jointure future ? »*

## Éléments bruts déjà observés

Issus de l'exploration initiale du 3 août, **non opposables** au titre du protocole : ils ont été vus
avant toute prédiction écrite. À reprendre sous protocole.

| Observation | Valeur |
|---|---|
| Lignes | 9 580 |
| `deal_id` distincts | 9 000 |
| `deal_id` apparaissant plus d'une fois | 575 |
| dont apparaissant 3 fois | 5 |
| dont apparaissant 2 fois, par différence | 570 |
| Lignes strictement identiques sur toutes les colonnes | 40 |
| Valeurs de `version` | 1 et 2 |
| Valeurs de `status` | au moins `CANCELLED` et `PENDING` |
| Contreparties distinctes | 12 |
| Books distincts | 5, dont `B2B_FR_GAS_HEDGE` et `B2B_FR_STRUCT` |
| `trade_date` | du 2025-06-02 au 2026-07-24 |
| `trade_ts` | jusqu'au **2026-07-25 13:16:03** |
| `delivery_start` | du 2026-01-01 au 2027-12-01 |
| `delivery_end` | du 2026-01-31 au 2028-11-30 |

Colonnes : `deal_id`, `trade_date`, `trade_ts`, `commodity`, `direction`, `delivery_start`,
`delivery_end`, `volume_mwh`, `price_eur_mwh`, `counterparty`, `book`, `status`, `version`.

**Incohérence relevée et jamais reprise** : `trade_ts` va jusqu'au 25 juillet 2026 alors que
`trade_date` s'arrête au 24. Au moins un deal porte donc un horodatage postérieur à sa propre date de
transaction, et postérieur à la date de référence du TP.

## Niveau 0 - cadrage de `trd_deal`

**Que représente une ligne** (une phrase, nom au singulier) :

Une ligne représente un état successif d'une transaction de couverture conclue par le desk sur le
marché de gros. La table est un journal alimenté au fil de l'eau : toute intervention sur un deal,
amendement, annulation ou reconfirmation, ajoute une ligne sans supprimer les précédentes. Elle ne
possède ni clé primaire déclarée ni clé reconstituable à partir de ses colonnes.

**Maille** :

Une ligne par état enregistré. Cet état n'a pas d'identifiant : la table n'a pas de maille au sens
strict, puisque aucune combinaison de colonnes ne distingue toutes ses lignes.

Ce n'est donc pas une clé qu'il faut chercher, mais une **règle de sélection** permettant de passer du
journal à l'ensemble des deals réellement en vigueur. Règle retenue : conserver, pour chaque `deal_id`,
la version la plus élevée, puis écarter les statuts annulés.

**Clés candidates** :

Aucune. Les trois candidates envisageables sont écartées, et la troisième l'est par une démonstration
qui vaut pour toutes les autres.

| Candidate | Verdict | Motif |
|---|---|---|
| `deal_id` seul | écartée | 9 000 valeurs distinctes pour 9 580 lignes |
| `(deal_id, version)` | écartée | `version` ne prend que les valeurs 1 et 2, or 5 `deal_id` occupent 3 lignes : au moins deux de ces trois lignes partagent le même numéro de version |
| **l'ensemble des colonnes** | écartée | 40 lignes sont strictement identiques sur toutes les colonnes |

La troisième est décisive. **Si l'ensemble des colonnes ne distingue pas toutes les lignes, aucun
sous-ensemble ne le peut**, une clé plus courte ne pouvant pas séparer davantage qu'une clé plus
longue. L'absence de clé primaire est donc démontrée, et pas seulement constatée sur les candidates
testées.

**Nombre de lignes prédit** :

*Réserve d'opposabilité* : la volumétrie de `trd_deal` et les cardinalités de `deal_id` ont été vues
lors de l'exploration initiale du 3 août, avant toute prédiction écrite. Elles ne sont pas opposables.

Les prédictions ci-dessous portent sur des grandeurs jamais mesurées.

### A. Domaine et répartition de `status`

**3 modalités** : `CONFIRMED`, `PENDING`, `CANCELLED`. Un système de trading distingue une transaction
saisie mais non encore confirmée par la contrepartie, une transaction confirmée, et une transaction
défaite.

Deux répartitions distinctes sont prédites, sur deux populations différentes :

| Population | `CONFIRMED` | `PENDING` | `CANCELLED` |
|---|---|---|---|
| Les 9 580 lignes | 90 % | 7 % | 3 % |
| Les dernières versions seulement, 9 000 deals | **93 %** | **3.8 %** | **3.2 %** |

Les deux répartitions diffèrent par une contrainte arithmétique, non par une estimation :

- `PENDING` est un état **transitoire**. Un deal saisi passe en attente puis est confirmé, sa ligne
  `PENDING` étant remplacée par une ligne `CONFIRMED`. Les `PENDING` survivants sont uniquement les
  deals encore en attente au 24 juillet 2026, d'où une part plus faible parmi les dernières versions.
- `CANCELLED` est un état **terminal**, jamais remplacé. Chaque deal annulé apporte exactement une
  ligne annulée quel que soit son nombre de lignes, donc sa part vaut `X / 9 580` sur les lignes et
  `X / 9 000` sur les deals. Elle est mécaniquement supérieure dans le rapport 9 580 / 9 000 = 1,064,
  soit 3,2 % contre 3 %.

Règle générale : tout état terminal est sur-représenté parmi les dernières versions, tout état
transitoire y est sous-représenté.

### B. Nombre de deals en vigueur

**8 370 deals**, soit 93 % de 9 000.

Un deal est en vigueur si son **état le plus récent** est confirmé. Deux populations le composent :
les `deal_id` sans amendement dont l'unique version est confirmée, et les `deal_id` amendés dont la
dernière version est confirmée, quel qu'ait été le statut de la précédente.

9 000 est la **borne haute** et non la réponse : il n'existe que 9 000 `deal_id` distincts, et
certains derniers états sont annulés ou en attente.

Contrôle de bouclage : 8 370 confirmés + 342 en attente + 288 annulés = 9 000.

**Cohérence entre les deux répartitions prédites.** Les deux tables de A ne sont pas indépendantes :
l'écart entre lignes et deals doit correspondre au nombre de lignes remplacées, soit
9 580 - 9 000 = 580.

| Statut | Lignes prédites | Deals prédits | Lignes remplacées |
|---|---|---|---|
| `CONFIRMED` | 8 622 | 8 370 | 252 |
| `PENDING` | 670 | 342 | 328 |
| `CANCELLED` | 287 | 288 | 0 |
| **Total** | 9 579 | 9 000 | **580** |

Les deux jeux de prédictions se referment l'un sur l'autre à l'arrondi près. Et la ligne `CANCELLED`
vérifie l'argument de l'état terminal : un deal annulé apportant exactement une ligne annulée, les deux
comptages doivent coïncider, ce qu'ils font à une unité près.

**Ordre des opérations.** La règle enchaîne deux étapes qui ne commutent pas :

```
1. pour chaque deal_id, ne conserver que la version la plus élevée
2. sur ce résultat seulement, filtrer sur le statut
```

Un filtre sur le statut appliqué seul produirait deux erreurs simultanées : un deal amendé dont les
deux versions sont confirmées serait compté deux fois, et un deal confirmé puis annulé serait retenu à
tort. C'est la mécanique que le sujet annonce lorsqu'il prévient qu'« une jointure naïve sur `deal_id`
produit plus de lignes qu'il n'y a de deals ».

*Alternative écartée* : retenir tout deal ayant été confirmé au moins une fois, sans considérer son
état final. Elle serait juste pour une piste d'audit, où l'on cherche ce qui a été conclu à un moment
donné. Elle est fausse pour une position, où l'on cherche ce qui existe aujourd'hui. Retenir un deal
annulé reviendrait à compter une couverture qui n'existe plus, donc à croire le portefeuille couvert
alors qu'il ne l'est pas. C'est la direction d'erreur la plus dangereuse pour un contrôle des risques :
elle rassure à tort.

### C. Amendements contre doublons de saisie

Parmi les 575 `deal_id` occupant plus d'une ligne :

| Mécanisme | Prédiction | Part des cas multi-lignes |
|---|---|---|
| Amendement réel | **au moins 535** | 93 % |
| Doublon de saisie strict | **au plus 40** | 7 % |

Dérivation : un groupe de lignes strictement identiques partage nécessairement son `deal_id`, donc les
40 groupes de doublons stricts sont inclus dans les 575. Par différence, au moins 535 `deal_id`
multi-lignes relèvent d'un amendement, soit 5,9 % des 9 000 deals.

Ces deux mécanismes constituent **deux familles d'écarts distinctes** parmi les treize annoncées, et ne
doivent pas être traités ensemble : un amendement est légitime et se résout par la sélection de
version, un doublon de saisie est une anomalie à remonter au back office.

**Résultat et écart** :

Mesures dans `notebooks/mission1_reconciliation.ipynb`.

### A. Domaine et répartition de `status`

**Domaine confirmé** : trois modalités, `CONFIRMED`, `PENDING`, `CANCELLED`. Aucune autre.

La structure des `deal_id` est également confirmée : 8 425 occupent une ligne, 570 en occupent deux,
5 en occupent trois, soit 9 000 `deal_id` pour 9 580 lignes.

| | Prédit lignes | **Réel lignes** | Prédit dernières versions | **Réel dernières versions** |
|---|---|---|---|---|
| `CONFIRMED` | 90 % | **92,67 %** | 93 % | **92,63 %** |
| `PENDING` | 7 % | **4,29 %** | 3,8 % | **4,28 %** |
| `CANCELLED` | 3 % | **3,04 %** | 3,2 % | **3,09 %** |

Écarts relatifs de chaque prédiction à la population qui la concerne : 2,97 %, 38,7 % et 1,25 % pour la
première ; 0,39 %, 12,6 % et 3,47 % pour la seconde.

### `status` est indépendant de `version` : il n'existe pas de machine à états

Les deux répartitions **observées** sont identiques : 92,67 / 4,29 / 3,04 contre 92,63 / 4,28 / 3,09.

La prédiction sur les dernières versions reposait sur l'idée que `PENDING` est un état transitoire,
donc appelé à disparaître des dernières versions, et `CANCELLED` un état terminal, donc sur-représenté.
**Ce raisonnement est réfuté.** Un deal ne passe pas de `PENDING` à `CONFIRMED` : le statut est
attribué ligne par ligne, sans lien avec la position dans la séquence des versions.

Même signature que les colonnes aléatoires de `ref_site` en Mission 0 : une colonne indépendante de ce
qui devrait la déterminer.

La seconde prédiction est plus proche du réel que la première, mais pour une raison qui ne tient pas :
la première surestimait `PENDING` à 7 % alors qu'il vaut 4,3 % dans les deux populations, et
l'ajustement a corrigé ce chiffre à la baisse par un mécanisme inexistant.

### Décomposition des 580 lignes remplacées

| Statut | Lignes | Dernières versions | Remplacées |
|---|---|---|---|
| `CONFIRMED` | 8 878 | 8 337 | **541** |
| `PENDING` | 411 | 385 | **26** |
| `CANCELLED` | 291 | 278 | **13** |
| **Total** | 9 580 | 9 000 | **580** |

Les lignes remplacées se répartissent à 93,3 / 4,5 / 2,2, soit sensiblement la répartition globale.
Une ligne remplacée a donc le même statut qu'une ligne quelconque, ce qui confirme l'indépendance
entre `status` et `version`.

**Effectifs dérivés.** Seuls les 9 580, 9 000 et 8 337 sont mesurés. Les neuf autres nombres de ce
tableau sont reconstitués à partir de proportions arrondies à six décimales, et les colonnes
« Remplacées » en sont des différences. Le 13, qui fonde un candidat d'anomalie, est donc une
différence entre deux valeurs approchées et doit être compté directement avant toute remontée.

### Candidat d'écart : 13 deals amendés après annulation

La dernière ligne du tableau contient une impossibilité métier. **13 lignes `CANCELLED` ne sont pas la
dernière version de leur deal** : une version leur succède.

Une annulation défait la transaction. Rien ne vient après. Ces 13 cas sont un écart franc, chiffrable,
et relèvent d'une remontée au back office.

À rapprocher des treize familles d'écarts annoncées, sans conclure avant d'avoir vérifié le statut de
la version qui succède à l'annulation : une réactivation explicite ne serait pas la même chose qu'un
amendement aveugle.

### Seuil absolu et seuil relatif ne classent pas les mêmes lignes

La quatrième question à trancher du sujet demande de montrer que ces deux seuils ne sélectionnent pas
les mêmes lignes. La mesure ci-dessus en fournit une démonstration issue des données elles-mêmes.

Écarts de la seconde prédiction à la réalité :

| Statut | Écart absolu | Écart relatif |
|---|---|---|
| `CONFIRMED` | 0,37 point | **0,39 %** |
| `PENDING` | 0,48 point | 12,6 % |
| `CANCELLED` | **0,11 point** | 3,47 % |

Classement en absolu : `CANCELLED`, `CONFIRMED`, `PENDING`.
Classement en relatif : `CONFIRMED`, `CANCELLED`, `PENDING`.

Les deux premiers rangs s'inversent. La cause est mécanique : un écart relatif rapporté à une base
faible, ici 3,2 %, est amplifié. Un seuil absolu protège les petites bases, un seuil relatif les
pénalise. La même fonction et le même raisonnement seront repris sur les écarts de prix.

### B. Deals en vigueur

| Mesure | Prédiction | Résultat | Écart |
|---|---|---|---|
| Lignes après sélection de la version maximale | 9 000 | **9 000**, pour 9 000 `deal_id` distincts | **0** |
| Deals en vigueur, dernière version confirmée | 8 370 | **8 337** | **-33**, soit -0,39 % |

La règle de sélection rend exactement un état par `deal_id`. L'écart sur le nombre de deals en vigueur
provient entièrement de la part de `CONFIRMED` prédite à 93 % contre 92,63 % réels ; le mécanisme de
sélection était juste.

**Réserve sur le déterminisme.** La sélection s'appuie sur `sort_values` puis `drop_duplicates`, ce qui
départage arbitrairement les ex aequo. Elle rend le bon nombre de lignes, mais le choix reste
indéterminé lorsque deux lignes partagent la version maximale. Les cas concernés sont identifiés
ci-dessous et sont sans conséquence ici, les lignes en concurrence étant identiques.

### C. Amendements contre doublons de saisie

| Mesure | Prédiction | Résultat | Écart |
|---|---|---|---|
| Lignes strictement dupliquées | au plus 40 | **40** | conforme |
| `deal_id` portant un doublon strict | au plus 40 | **40** | conforme |
| `deal_id` relevant d'un amendement | au moins 535 | **540** | conforme |

Les 40 lignes en excès appartiennent à 40 `deal_id` distincts, soit un excès chacun.

**Les deux familles ne sont pas exclusives à la maille `deal_id`.** Les 5 `deal_id` à trois lignes
portent simultanément un amendement et une copie. Décomposition complète des 575 `deal_id`
multi-lignes :

| Composition | `deal_id` | Mécanisme | Statut du chiffre |
|---|---|---|---|
| 2 lignes différentes | 535 | amendement pur | **dérivé** |
| 2 lignes identiques | 35 | doublon strict pur | **dérivé** |
| 3 lignes : original, amendement, copie | **5** | les deux à la fois | mesuré |
| | **575** | | mesuré |

**Les 535 et 35 sont dérivés, non mesurés.** Ils reposent sur l'hypothèse que les 5 `deal_id` à trois
lignes portent chacun exactement un doublon, ce qui ramènerait les doublons purs à 40 - 5 = 35 et les
amendements purs à 570 - 35 = 535. Cette hypothèse vient de l'observation que, dans chaque triplet,
deux lignes partagent le même `trade_ts` ; l'égalité des horodatages n'implique pas l'identité stricte
des lignes, qui n'a pas été vérifiée.

Mesure permettant de trancher : `df[df.duplicated(keep='first')]["version"].value_counts()`.

Ce recouvrement devra être tranché avant de construire la classification des écarts, que le sujet
exige exclusive : soit une troisième catégorie pour les cas mixtes, soit une classification à la maille
ligne plutôt qu'à la maille `deal_id`. Classer par ligne et classer par deal ne donnent ni les mêmes
catégories ni les mêmes totaux.

**Ce que modifie un amendement.** Sur `D2600313`, le volume passe de 177,2 à 185,7 MWh et le prix de
70,160 à 68,693 EUR/MWh. Un amendement change le volume **et** le prix. Une agrégation sans sélection
de version compterait donc deux volumes différents pour une même transaction.

### `trade_ts` est fabriqué sur les lignes amendées

Observation initiale sur les 5 triplets : l'horodatage de l'amendement vaut celui de l'original **plus
exactement un jour**, à la seconde près, l'heure de la journée étant préservée.

| `deal_id` | Original | Amendement |
|---|---|---|
| D2600313 | 2025-06-05 08:43:30 | 2025-06-06 08:43:30 |
| D2601497 | 2025-09-24 11:53:37 | 2025-09-25 11:53:37 |
| D2601680 | 2025-09-22 14:33:01 | 2025-09-23 14:33:01 |
| D2601976 | 2025-07-08 17:34:22 | 2025-07-09 17:34:22 |
| D2608057 | 2025-08-13 14:31:18 | 2025-08-14 14:31:18 |

Généralisation sur les 575 `deal_id` multi-lignes, écart en jours entre premier et dernier horodatage :

| Écart | `deal_id` | Prédit |
|---|---|---|
| 1,0 jour | **540** | 540 |
| 0,0 jour | **35** | 35 |

Aucune autre valeur. Prédiction confirmée à l'unité près.

**Le décalage est mécanique, pas naturel.** Dans un système de trading réel, un amendement survient
quelques minutes après une erreur de saisie, quelques heures après une renégociation, quelques jours
après une réconciliation : la distribution des écarts serait étalée. Ici 540 sur 540 valent exactement
1,0 jour et conservent l'heure de l'original à la seconde.

L'hypothèse concurrente, un traitement de nuit horodatant tous les amendements au passage du batch, est
réfutée par les données : l'heure serait alors identique pour tous les deals, or elle varie et suit
celle de l'original.

Conclusion : sur une ligne amendée, `trade_ts` n'est pas l'horodatage de l'amendement, c'est celui de
l'original augmenté de 24 heures.

**Conséquence opératoire.** `trade_ts` ne peut servir ni à dater un amendement, ni à ordonner les
versions. C'est important : `MAX(trade_ts)` est la deuxième façon évidente de sélectionner l'état
courant après `MAX(version)`. Elle donnerait ici le bon résultat, mais sur une valeur inventée, et elle
ne départagerait pas les deux lignes identiques d'un cas mixte.

### Vérification : `trade_ts` incohérent avec `trade_date`

Prédiction dérivée du mécanisme : 535 amendements purs apportant chacun une ligne décalée, plus les
cas mixtes selon l'emplacement de leur copie, trois sur l'amendement et deux sur l'original, soit
`535 + 3 × 2 + 2 × 1 = 543` lignes.

**Résultat : 543 lignes.** Prédiction confirmée exactement.

Toutes portent `version = 2`. La correspondance est donc parfaite dans les deux sens : une ligne est de
version 2 si et seulement si son `trade_ts` est décalé d'un jour par rapport à sa `trade_date`.

### Modèle structurel complet de `trd_deal`

L'ensemble des mesures se referme sans résidu :

| Population | `deal_id` | Lignes |
|---|---|---|
| Deals à ligne unique | 8 425 | 8 425 |
| Deals amendés, deux lignes différentes | 535 | 1 070 |
| Deals avec doublon strict, deux lignes identiques | 35 | 70 |
| Deals mixtes, trois lignes | 5 | 15 |
| **Total** | **9 000** | **9 580** |

**Répartition par version : dérivée, non mesurée.** 9 037 lignes de version 1 et 543 de version 2,
l'excédent de 37 sur les 9 000 deals correspondant aux 35 doublons purs et aux 2 cas mixtes dont la
copie porterait sur l'original, et les 3 lignes de version 2 en excès aux 3 cas mixtes dont la copie
porterait sur l'amendement. Les 40 doublons se répartiraient ainsi en 37 sur version 1 et 3 sur
version 2.

Aucun de ces cinq nombres n'a été compté. Le 543 lui-même est déduit de l'affichage des lignes à date
décalée, où toutes portaient `version = 2`, sans que le comptage ait été fait dans les deux sens.

Trois mesures les fixeraient : `df["version"].value_counts()`,
`df[df.duplicated(keep='first')]["version"].value_counts()`, et les effectifs de `status` comptés
directement plutôt que reconstitués à partir de proportions arrondies, ce dernier point valant aussi
pour les 541, 26 et 13 lignes remplacées.

Ce marquage est délibéré : un nombre qui boucle arithmétiquement n'est pas un nombre mesuré, et le
projet en a déjà rencontré plusieurs cas où deux erreurs de sens opposé se compensaient dans un total
juste.

### Candidats d'écarts issus de `trd_deal`

Trois, à confronter aux treize familles annoncées, sans conclure avant la réconciliation :

| # | Candidat | Volume | Statut du chiffre | Nature |
|---|---|---|---|---|
| 1 | Doublons de saisie stricts | 40 lignes, 40 `deal_id` | **mesuré** | anomalie à remonter au back office |
| 2 | `trade_ts` fabriqué sur les lignes amendées | 543 lignes | **mesuré** | colonne inexploitable pour dater ou ordonner |
| 3 | Deals amendés après annulation | 13 lignes `CANCELLED` non terminales | **dérivé** | impossibilité métier |

Le troisième reste à qualifier : il faut vérifier le statut de la version qui succède à l'annulation.
Une réactivation explicite ne serait pas la même chose qu'un amendement aveugle.

## Implications pour toute jointure future

> à remplir : ce que la clé réelle change pour la réconciliation, et ce qu'une jointure sur `deal_id`
> seul produirait

---

# Questions à trancher

Les huit questions posées par le sujet, dans l'ordre où elles se traitent.

## 1. Lecture du fichier back office

*« Le fichier ne se lit pas correctement avec les paramètres par défaut de `read_csv`. Quatre
caractéristiques du format s'y opposent. Lesquelles, et laquelle des quatre corrompt les données
silencieusement plutôt que de lever une erreur ? »*

`setup_check.py` affiche l'en-tête du fichier sans le parser. Le lire est légitime, c'est du matériel
fourni. Écrire les quatre prédictions **avant** d'ouvrir le fichier lui-même.

### Volumétrie

`data/raw/bo_confirmations_20260724.csv` : 9 011 lignes de texte, soit un en-tête et **9 010
confirmations**, 13 champs séparés par `;`, aucun champ vide, aucun guillemet, aucun `\r`. À comparer
aux 9 580 lignes et 9 000 `deal_id` distincts de `trd_deal`.

### Pistes écartées par mesure, avant d'accuser le format

Deux hypothèses ont été testées et réfutées, chacune en une mesure. Elles sont consignées parce
qu'écarter une piste est un résultat, pas une perte de temps.

**L'encodage.** Un fichier français mal encodé est le suspect réflexe. Lecture du fichier en binaire et
inventaire des octets hors ASCII :

```python
with open("data/raw/bo_confirmations_20260724.csv", "rb") as f:
    octets = f.read()

sorted({b for b in octets if b > 127})
```

Résultat : liste vide. Aucun octet au-dessus de 127, le fichier est en **ASCII pur**. Or ASCII est le
sous-ensemble commun de UTF-8, latin-1 et cp1252 : ces trois encodages produisent ici exactement les
mêmes caractères. L'encodage ne peut pas être en cause, quel que soit le défaut de `read_csv`.

**Les jetons de valeur manquante.** Par défaut pandas convertit en `NaN` une quinzaine de chaînes
(`NA`, `N/A`, `NULL`, `nan`, `None`, `-`, ...). Un code métier légitime valant l'une d'elles
disparaîtrait sans bruit.

Prédiction : 0 `NaN` partout, aucune colonne concernée.

`bo.isna().sum()` renvoie 0 sur les 13 colonnes. Prédiction confirmée, piste close.

### Les quatre caractéristiques

Elles ne sont pas des propriétés exotiques du fichier : ce sont exactement les quatre arguments qu'il
faut passer pour que la lecture soit juste.

```python
bo = pd.read_csv(chemin, sep=";", decimal=",",
                 parse_dates=["trade_dt", "del_from", "del_to"], dayfirst=True)
```

| # | Caractéristique du format | Défaut de `read_csv` | Comment le défaut se manifeste |
|---|---|---|---|
| 1 | séparateur `;` | `sep=","` | une colonne unique contenant la ligne entière |
| 2 | décimale `,` | `decimal="."` | `quantity` et `unit_price` restent en `object` |
| 3 | les dates sont des chaînes, pandas 2 ne les parse plus seul | `parse_dates=None` | les trois colonnes de date restent en `object` |
| 4 | ordre jour/mois | `dayfirst=False` | **rien, la colonne sort en `datetime64` propre** |

Les trois premières se voient dans `dtypes`. La quatrième est **celle qui corrompt silencieusement**.

### Mesure de la corruption silencieuse

Le doute était réel : pandas 2 déduit un format unique à partir du premier élément non nul, puis
l'applique à toute la colonne. Si ce premier élément est non ambigu, l'inférence peut rattraper
`dayfirst=False` toute seule. Il fallait donc mesurer, pas affirmer.

Relecture sans `dayfirst`, comparaison colonne par colonne :

```python
bo_us = pd.read_csv(chemin, sep=";", decimal=",",
                    parse_dates=["trade_dt", "del_from", "del_to"])

for col in ["trade_dt", "del_from", "del_to"]:
    print(col, (bo_us[col] != bo[col]).sum())
```

| Colonne | Lignes divergentes | Avertissement pandas |
|---|---|---|
| `trade_dt` | 0 | oui |
| `del_from` | **8 249** | **non** |
| `del_to` | 0 | oui |

Deux avertissements seulement pour trois colonnes. Le message `Parsing dates in %d/%m/%Y format when
dayfirst=False (the default) was specified` signale les colonnes où pandas a deviné le format français
malgré le défaut, donc celles qui vont bien. **L'avertissement se lève là où il n'y a pas de problème
et se tait sur la colonne fausse.**

**Mécanique.** L'inférence dépend du premier élément de chaque colonne.

- `trade_dt` commence par `23/10/2025`. 23 ne peut pas être un mois, l'ambiguïté est levée, format
  `%d/%m/%Y` retenu.
- `del_to` est une fin de période, `30/11/2028`, `31/07/2026` : le jour dépasse 12, même résolution.
- `del_from` est un début de période, donc toujours le 1er du mois : `01/12/2027`. Le premier nombre
  vaut 01, strictement ambigu. Pandas retient `%m/%d/%Y` et lit **12 janvier 2027** au lieu du
  **1er décembre 2027**.

Le modèle se ferme sans résidu :

```python
len(bo), (bo["del_from"].dt.day == 1).mean(), bo["del_from"].dt.month.value_counts().sort_index()
```

| Grandeur | Valeur |
|---|---|
| Lignes | 9 010 |
| Part des `del_from` au 1er du mois | **1,0**, sans exception |
| `del_from` en janvier | **761** |
| Lignes intactes sous lecture américaine | 9 010 - 8 249 = **761** |

Les seules lignes épargnées sont exactement celles de janvier, où `01/01` est invariant par permutation
du jour et du mois. Les douze mois sont quasi uniformes, entre 722 et 783 lignes.

### Pourquoi cette corruption est la plus grave possible

La permutation envoie **toutes** les lignes corrompues en janvier de la même année, le jour prenant la
valeur du vrai mois. Trois contrôles usuels sont aveugles à cette signature :

- le **contrôle de type** ne voit rien, la colonne est un `datetime64` valide ;
- l'**invariant `del_from <= del_to`** ne voit rien non plus, puisque la date corrompue recule toujours
  vers janvier et reste donc antérieure à la fin de livraison ;
- la **comparaison front / back office** sur les autres colonnes ne voit rien, elles sont justes.

Seul un **contrôle de distribution** l'attrape : 100 % des livraisons débutant en janvier est
impossible pour un portefeuille. C'est la leçon transposable, et elle vaut au-delà de ce fichier. Sur
une colonne de date, vérifier le type et vérifier l'ordre ne suffit pas à détecter une inversion
jour/mois ; il faut regarder la forme de la distribution.

L'enjeu est direct : `del_from` porte le début de la période de livraison, c'est-à-dire l'axe
d'agrégation de la Mission 2. Une position mensuelle construite sur la lecture par défaut serait fausse
sur 91,6 % des lignes sans qu'aucun contrôle de type ne bronche.

### Observations de format à reprendre dans les questions suivantes

Relevées à la lecture de `bo.head()`, sans mesure à ce stade, donc à confirmer là où elles servent.

| Champ back office | Champ `trd_deal` | Écart apparent |
|---|---|---|
| `cpty_code` : `TOTALE`, `EEX_CL`, `STATKR`, `VITOL` | `counterparty` : `TOTALENERGIES`, `EEX_CLEARED`, `STATKRAFT`, `VITOL` | troncature à 6 caractères, à confirmer, et injectivité à démontrer - question 7 |
| `buy_sell` : `B`, `S` | `direction` : `BUY`, `SELL` | codage abrégé - question 6 |
| `product` : `PWR_FR`, `NG_PEG` | `commodity` : `POWER`, `GAS` | commodité et place de cotation fusionnées |
| `deal_ref` : `D2605829` | `deal_id` : `D2605829` | même forme apparente sur les 5 premières lignes - question 2 |

## 2. Clé de réconciliation et fonction de normalisation

*« Sur quelle clé réconcilies-tu ? Elle n'est pas propre. Formalise une fonction de normalisation, puis
mesure combien de faux écarts tu élimines à chaque étape. Si tu ne fais pas cette mesure, tu ne sais
pas si ta normalisation est trop laxiste. »*

### Choix de la clé

Le rapprochement se fait sur `bo.deal_ref` contre `trd_deal.deal_id`. Aucune autre paire de colonnes ne
porte d'identifiant commun : `confirmation_id` est produit par le back office et n'a pas de contrepartie
au front, et les colonnes de fond, dates, quantités, prix, ne sont pas des identifiants.

Distinguer les deux rôles est nécessaire à la suite. `confirmation_id` est la clé du **document** de
confirmation, `deal_ref` est une clé **étrangère** pointant vers le deal du front. Rien n'oblige une clé
étrangère à être unique.

### Cardinalités de départ

| Grandeur | Valeur |
|---|---|
| Lignes du back office | 9 010 |
| `deal_ref` distincts | **8 945** |
| Lignes en doublon sur `deal_ref` | **65** |
| `deal_id` distincts, front | 9 000 |
| Lignes de `trd_deal` | 9 580 |

8 945 + 65 = 9 010. Les deux clés sont non uniques, mais pas du même ordre : 65 lignes en doublon côté
back office contre 580 lignes remplacées côté front. Le back office n'a donc **pas** recopié la
structure de versions du front, il émet une confirmation par deal et non par version.

### Rapprochement brut, avant toute normalisation

```python
deal_ids = set(df["deal_id"])
refs = set(bo["deal_ref"])

len(refs & deal_ids), len(refs - deal_ids), len(deal_ids - refs)
```

| Population | Effectif |
|---|---|
| Références appariées telles quelles | 8 665 |
| Orphelines back office, référence sans deal | **280** |
| Deals du front sans confirmation | **335** |

8 665 + 280 = 8 945. Le compte boucle.

### L'identité qui structure toute la question

Les deux anti-jointures ne sont pas indépendantes. Chaque identifiant d'un côté est soit apparié, soit
seul, et le paquet des appariés est le même vu des deux côtés :

```
9 000 = appariés + non confirmés
8 945 = appariés + orphelines
```

Par soustraction, le terme commun disparaît :

```
non confirmés - orphelines = 9 000 - 8 945 = 55
```

**Conséquences.** Il n'y a qu'un seul nombre libre, pas trois : prédire les orphelines détermine les non
confirmés. Et surtout, la normalisation sort une référence de chaque côté à la fois, donc **l'écart de 55
est invariant**. Il ne dépend pas de la qualité de la clé, c'est une propriété de volumétrie.

**55 est donc le plancher des deals du front sans confirmation.** Même si toutes les orphelines
s'expliquaient, il resterait 55 deals que le fichier back office ne contient tout simplement pas.

### Caractérisation de la saleté avant d'écrire la fonction

Écrire une normalisation sans avoir vu la saleté, c'est risquer d'être trop laxiste. Recensement des 280
orphelines par longueur, la forme canonique du front étant `D` suivi de 7 chiffres, soit 8 caractères :

| Longueur | Effectif | Canoniques `^D\d{7}$` |
|---|---|---|
| 8 | 155 | 95 |
| 9 | 125 | 0 |

**Piège d'échantillonnage écarté.** Un premier coup d'oeil par `sorted(refs - deal_ids)[:20]` ne montre
que des espaces en tête. C'est un artefact : l'espace vaut 32 en ASCII, `D` vaut 68, `d` vaut 100, donc
toute chaîne commençant par un blanc se range avant toutes les autres. Ce n'est pas un échantillon, c'est
un extremum. Les inspections suivantes utilisent `sample` ou la population entière.

### La fonction de normalisation

Trois barreaux, appliqués dans cet ordre, et seulement du côté back office.

```python
norm = (serie.str.strip()
             .str.upper()
             .str.replace(r"^D0+", "D", regex=True))
```

| Barreau | Corrige | Nature du défaut |
|---|---|---|
| `strip` | blancs en bord de chaîne | négligence de saisie |
| `upper` | `d` minuscule | négligence de saisie |
| `^D0+` | zéro de remplissage, `D02605532` pour `D2605532` | choix de format, partie numérique calée sur 8 chiffres |

Le troisième est d'une autre nature : il **supprime** de l'information au lieu de l'uniformiser. Il tient
parce que les 9 000 `deal_id` du front sont tous `D` suivi de 7 chiffres et qu'aucun ne commence par
`D0` : retirer un zéro en tête ne peut créer aucune collision avec une référence valide. L'ancre `^` est
ce qui rend l'opération sûre, sans elle le motif frapperait n'importe où dans la chaîne.

### Gain mesuré à chaque barreau

La distinction est essentielle : `str.match` teste la **forme**, `isin(deal_ids)` teste l'**existence**.
Les deux ne coïncident pas, et c'est le second qui compte.

```python
print("existent brut        :", orph.isin(deal_ids).sum())
print("existent apres strip :", orph.str.strip().isin(deal_ids).sum())
print("existent + upper     :", orph.str.strip().str.upper().isin(deal_ids).sum())
print("existent + D0        :", orph.str.strip().str.upper()
                                    .str.replace(r"^D0+", "D", regex=True).isin(deal_ids).sum())
```

| Barreau | Forme canonique | Existent au front | Gain réel |
|---|---|---|---|
| brut | 95 | 0 | - |
| `strip` | 175 | 80 | **+80** |
| `upper` | 235 | 140 | **+60** |
| `^D0+` | 280 | 185 | **+45** |

Les huit valeurs des deux colonnes sont **mesurées**. Une première version de ce tableau ne mesurait
que 140 et 185 et reportait le 80 depuis la colonne de forme. Le raisonnement qui le justifiait était
correct : après `strip` et `upper`, 235 canoniques pour 140 existantes laissent 95 canoniques absentes,
or les 95 canoniques dès le brut sont absentes et saturent ce compte, donc toutes les références
gagnées par les deux premiers barreaux existent. Mais un nombre qui boucle arithmétiquement n'est pas
un nombre compté, et la mesure directe l'a donc remplacé.

**À chaque barreau, le gain en existence égale exactement le gain en forme.** Aucun barreau n'est
inutile, et aucun ne fabrique de faux appariement. Les 280 sont toutes canoniques après le troisième
barreau, il n'existe aucune quatrième forme aberrante.

### Les 95 qui ne se récupèrent jamais

95 références sont **canoniques dès le départ**, longueur 8, `D` suivi de 7 chiffres, aucun caractère
parasite, et pourtant absentes du front. Il n'y a rien à nettoyer, donc la normalisation ne peut rien
leur apporter : 235 - 140 = 95, et ce sont les mêmes 95.

Ce n'est pas un défaut de clé, c'est un **écart métier**, et le plus sérieux du lot. Le back office
détient une confirmation pour une transaction que le front n'a jamais enregistrée. Soit le front a perdu
un deal, soit le back a confirmé quelque chose qui n'a pas été traité.

### Le front est propre : la saleté est unilatérale

Contrôle indispensable, et il manquait à une première version de cette analyse. `isin(deal_ids)` compare
la référence normalisée à un référentiel **brut**. Si `deal_id` était sale, une orpheline canonique
pourrait correspondre à un `deal_id` valant `" D2600031"`, et les 95 seraient un artefact.

```python
dids = pd.Series(sorted(deal_ids))
dids.str.len().value_counts(), dids.str.match(r"^D\d{7}$").sum()
```

Résultat : 9 000 identifiants, **tous de longueur 8, tous canoniques**, sans exception. La réserve est
levée, les 95 et les 185 tiennent.

Enseignement à retenir : **toute la dégradation est du côté de l'extrait back office.** Il ne s'agit pas
d'une divergence de conventions entre deux systèmes qui auraient chacun leur norme, mais d'une altération
à la production du fichier. Normaliser un seul côté d'une comparaison symétrique est une faute, et elle
n'est rattrapée ici que parce que l'autre côté s'est révélé propre.

### Contrôle de laxisme

Le sujet demande explicitement de savoir si la normalisation est trop laxiste. La définition opératoire :
elle l'est si elle **fusionne deux références qui étaient distinctes**.

```python
r = pd.Series(list(refs))
r.nunique(), r.str.strip().str.upper().str.replace(r"^D0+", "D", regex=True).nunique()
```

Résultat : `(8945, 8945)`. Aucune fusion, le cardinal est conservé.

**Attention à ne pas prendre une tautologie pour un contrôle.** Vérifier que `150 - 95 = 55` après
normalisation ne teste rien : les deux nombres ont été obtenus en retranchant 185 à 335 et à 280, leur
différence vaut donc nécessairement 335 - 280. Seule la mesure de `nunique` ci-dessus est un vrai
contrôle.

### État final de la clé

| Population | Brut | Normalisé |
|---|---|---|
| Références appariées | 8 665 | **8 850** |
| Orphelines back office | 280 | **95** |
| Deals du front sans confirmation | 335 | **150** |

185 faux écarts éliminés sur 280, soit 66,1 %. Le tiers restant n'est pas un problème de format.

### Ce que cette question lègue aux suivantes

- **95 confirmations sans deal**, irréductibles. Candidat de famille d'écart.
- **150 deals sans confirmation**, dont **55 d'excédent structurel** que rien ne pourra expliquer par la
  clé.
- **Hypothèse à tester** : les 95 orphelines et 95 des 150 non confirmés sont-ils les mêmes transactions,
  avec un identifiant corrompu au-delà de ce que la normalisation répare ? Le test ne passe pas par la
  clé mais par les autres colonnes, date, quantité, prix, contrepartie. Cinq colonnes concordantes
  valent identification.
- **65 lignes en doublon** sur `deal_ref` face à 580 lignes remplacées sur `deal_id` : les deux clés sont
  non uniques, une jointure naïve fait donc exploser le nombre de lignes. Matériau direct de la
  question 3.

## 3. Mécanique de l'explosion de jointure

*« Une jointure naïve sur `deal_id` produit plus de lignes qu'il n'y a de deals. Explique la mécanique
exacte, puis dis-moi quel indicateur de reporting cette erreur gonfle, et de combien. »*

Dépend directement de la clé primaire réelle établie plus haut.

### Le fait brut

```python
jointure_naive = bo.merge(fo, left_on="deal_key", right_on="deal_id", how="inner")
len(jointure_naive)
```

**9 495 lignes** pour **8 850** deals appariés, soit **645 lignes en trop**.

La référence est 8 850 et non 9 010 ou 9 580 : la réconciliation compare des transactions, donc un deal
apparié doit produire exactement une ligne de comparaison, celle qui met face à face l'état du front et
la confirmation du back office. Cette référence découle de la sélection de version déjà tranchée : une
seule version fait foi.

### La mécanique

Une jointure n'apparie pas une ligne avec une ligne. Elle apparie **toutes les combinaisons** partageant
la clé. Pour une clé `k`, elle produit donc `n_bo(k) × n_fo(k)` lignes.

| Cas | Lignes produites | En trop |
|---|---|---|
| 1 confirmation, 1 version | 1 | 0 |
| 1 confirmation, 2 versions | 2 | 1 |
| 2 confirmations, 1 version | 2 | 1 |
| 2 confirmations, 2 versions | **4** | **3** |

**Un doublon d'un seul côté suffit.** Il n'est pas nécessaire que les deux systèmes soient dégradés
simultanément pour qu'une transaction soit comptée deux fois.

Démonstration sur les données, sans passer par la jointure :

```python
n_fo = fo["deal_id"].value_counts()
n_bo = bo["deal_key"].value_counts()

produit = n_bo.mul(n_fo, fill_value=0)
produit.sum(), len(jointure_naive)
```

Résultat : **9 495,0 contre 9 495**. La formule `Σ n_bo(k) × n_fo(k)` est vérifiée, pas seulement
énoncée.

`mul` aligne les deux Series **par leur index**, ici l'identifiant, et `fill_value=0` annule les clés
présentes d'un seul côté, ce qui reproduit exactement une jointure interne. L'index du résultat est
l'union des deux, soit 9 095 étiquettes, dont 245 nulles : les 150 non confirmés et les 95 orphelines.

### Décomposition de l'excédent

Pose `a = n_bo(k) - 1` et `b = n_fo(k) - 1`, les lignes **en trop** de chaque côté. Alors

```
n_bo × n_fo - 1  =  (a+1)(b+1) - 1  =  a + b + ab
```

Le `-1` est la ligne légitime, la seule que la réconciliation devrait produire. En quatre blocs :

| Bloc | Effectif | Ce que c'est |
|---|---|---|
| `1 × 1` | 1 | la ligne à conserver |
| `1 × b` | `b` | confirmation légitime contre versions en trop |
| `a × 1` | `a` | confirmations en trop contre version légitime |
| `a × b` | `ab` | les deux dégradés en même temps |

**`a × b` seul est une erreur fréquente et fausse.** Il ne compte que le dernier bloc et ignore les deux
blocs mixtes, où un doublon d'un seul côté suffit à créer une ligne parasite. Sur le cas
`2 confirmations, 2 versions`, `a × b` vaut 1 là où l'excédent réel vaut 3.

### Attribution mesurée

```python
cles_appariees = sorted(ids_front & cles_bo)

a = n_bo[n_bo.index.isin(cles_appariees)] - 1
b = n_fo[n_fo.index.isin(cles_appariees)] - 1

a.sum(), b.sum(), (a * b).sum(), a.sum() + b.sum() + (a * b).sum()
```

| Cause | Lignes en trop | Part | Responsable |
|---|---|---|---|
| Versions multiples au front | **576** | 89,3 % | front office |
| Doublons de confirmation | **65** | 10,1 % | back office |
| Les deux à la fois | **4** | 0,6 % | les deux |
| **Total** | **645** | | |

Le total retombe sur 645, valeur obtenue indépendamment par `9 495 - 8 850`. Ce n'est pas une
tautologie : si le filtrage avait laissé tomber une clé, la somme n'aurait pas atteint la bonne valeur.

**Le terme croisé est un taux de coïncidence, pas une magnitude.** Sous indépendance, le nombre de clés
dégradées des deux côtés vaut `65 × 570 / 8 850 = 4,2`. Mesuré : **4**. Les deux dégradations sont donc
statistiquement indépendantes, le doublonnage du back office et l'amendement au front n'ont aucun lien
de cause à effet.

Les 4 clés concernées portent toutes `a = 1, b = 1` : `D2601918`, `D2604606`, `D2607974`, `D2608273`.
Ce sont les cas à examiner un par un lors de la réconciliation ligne à ligne, puisqu'ils demandent de
trancher deux ambiguïtés à la fois.

### Conclusion opératoire

**89 % du gonflement vient du front, et ce n'est pas une anomalie.** Un deal amendé a légitimement deux
versions dans `trd_deal`, c'est de l'historisation normale. Le tort n'est pas dans la donnée mais dans
la jointure qui omet de sélectionner la version en vigueur.

Seules les **65 lignes** du back office relèvent d'un défaut à remonter, et elles pèsent 10 % du
problème. Les corriger ne réglerait donc presque rien : la correction est à faire côté requête, pas
côté fichier.

### L'indicateur gonflé, et de combien

C'est le **volume traité**, et le notionnel qui en découle.

```python
volume_naif = jointure_naive["volume_mwh"].sum()

fo_appariee = fo_derniere_version[fo_derniere_version["deal_id"].isin(cles_bo)]
volume_correct = fo_appariee["volume_mwh"].sum()
```

| Grandeur | Jointure naïve | Correct | Écart | Gonflement |
|---|---|---|---|---|
| Volume | 2 987 513,8 MWh | 2 790 477,6 MWh | **197 036,2 MWh** | **7,06 %** |
| Notionnel | 177 141 863,71 EUR | 165 672 694,97 EUR | **11 469 168,74 EUR** | **6,92 %** |

Le taux se rapporte à la **valeur correcte**, convention à annoncer explicitement : rapporté au chiffre
naïf, le même écart de volume donnerait 6,60 %, et deux personnes calculeraient deux taux différents
sur les mêmes données.

Le gonflement de 7,06 % est proche du ratio de lignes, `645 / 8 850 = 7,29 %`. L'écart de 0,23 point
signifie que les deals dupliqués portent un volume environ 3 % inférieur à la moyenne. **Le gonflement
est donc proportionnel, il ne se concentre pas sur les gros deals.**

**Notionnel n'est pas P&L.** Ces 11,5 M EUR sont un volume multiplié par un prix de transaction, ni une
perte ni une valorisation de marché. Une erreur de jointure ne fait pas perdre d'argent, elle fait
publier un chiffre faux.

### Réserve : volume brut contre position nette

Ce qui est sommé ici est un **volume brut**. Additionner `volume_mwh` sans tenir compte de `direction`
mélange achats et ventes, alors qu'une position nette les compense.

Le taux de gonflement reste valable, puisqu'il compare deux sommes construites de la même façon. Mais
**2 790 477 MWh n'est pas la position du portefeuille**, c'est le volume traité. La position nette exige
la convention de signe, question 6, encore ouverte.

## 4. Seuil de matérialité sur les prix

*« Un écart de prix de 0,004 EUR/MWh et un écart de 3 % ne sont pas le même objet. Où places-tu le
seuil, et sur quelle base ? Le seuil en valeur absolue et le seuil en relatif ne classent pas les mêmes
lignes : montre-le. »*

> à remplir

## 5. Détection d'unité sans la colonne d'unité

*« Certaines quantités sont dans une autre unité. Comment le détectes-tu sans que la colonne d'unité te
le dise ? Cette colonne peut mentir, et sur un vrai extrait elle mentira. »*

> à remplir

## 6. Convention de signe inversée

*« Certaines lignes ont une convention de signe inversée. Quel contrôle la révèle ? Ce n'est pas la
comparaison du sens : c'est un invariant qui doit tenir même quand le sens est mal renseigné. »*

> à remplir

## 7. Mapping des codes contrepartie

*« Les deux systèmes n'utilisent pas les mêmes codes contrepartie. Reconstitue le mapping, et dis-moi
ce qui te garantit qu'il est injectif. »*

### Les deux domaines

```python
fo["counterparty"].value_counts(), bo["cpty_code"].value_counts()
```

**12 codes distincts de chaque côté.** Prédiction confirmée, et le raisonnement qui la fondait tient :
le back office ne confirme que des deals existants, il ne peut donc pas voir de contrepartie inconnue
du front.

Les effectifs ne concordent pas et n'ont pas à concorder, 9 580 lignes au front contre 9 010 au back
office. Les rangs sont d'ailleurs différents, `RWE` en tête au front et `VITOL` au back office.

### Le mapping

Troncature aux **6 premiers caractères**, sans exception.

| Front | Back office | | Front | Back office |
|---|---|---|---|---|
| `TOTALENERGIES` | `TOTALE` | | `GUNVOR` | `GUNVOR` |
| `EDF_TRADING` | `EDF_TR` | | `AXPO` | `AXPO` |
| `STATKRAFT` | `STATKR` | | `RWE` | `RWE` |
| `SHELL_ENERGY` | `SHELL_` | | `VITOL` | `VITOL` |
| `MERCURIA` | `MERCUR` | | `UNIPER` | `UNIPER` |
| `ICE_ENDEX` | `ICE_EN` | | `EEX_CLEARED` | `EEX_CL` |

Les codes de 6 caractères ou moins sont inchangés, ce qui explique que `AXPO`, `RWE`, `VITOL`,
`UNIPER` et `GUNVOR` soient identiques des deux côtés.

### Le contrôle d'injectivité

```python
mapping = fo["counterparty"].drop_duplicates().to_frame()
mapping["code_bo"] = mapping["counterparty"].str[:6]

len(mapping), mapping["code_bo"].nunique(), set(bo["cpty_code"]) - set(mapping["code_bo"])
```

| Contrôle | Résultat | Ce qu'il teste |
|---|---|---|
| Contreparties du front | **12** | nombre d'entrées de la fonction |
| Codes tronqués distincts | **12** | **injectivité** : conservation du cardinal |
| Codes back office non couverts | **ensemble vide** | **exhaustivité** : la règle engendre tout l'observé |

Les deux contrôles sont nécessaires et ne se remplacent pas. Le premier vérifie que la fonction ne
confond rien, le second qu'elle couvre tout. C'est la même mécanique que le contrôle de laxisme de la
question 2 : **la conservation du cardinal est la définition opératoire de l'injectivité.**

### Ce qui garantit l'injectivité : rien

C'est la vraie réponse à la question posée, et elle est négative.

L'injectivité n'est **pas une propriété de la troncature**, c'est une propriété du domaine observé au
24 juillet 2026. Elle tient parce qu'aucune des 12 contreparties ne partage ses 6 premiers caractères
avec une autre, ce qui relève de la chance et non de la construction.

Une entrée future suffit à la détruire. `TOTALENERGIES_GAS` donnerait `TOTALE`, en collision avec
`TOTALENERGIES`, et les deux contreparties deviendraient indiscernables **dans le sens qui compte**.
Le sens front vers back office reste calculable, mais le sens inverse, celui dont la réconciliation a
besoin, perd sa réponse : le fichier affiche `TOTALE` et rien ne permet plus de trancher. La perte est
définitive, l'information n'est pas dégradée mais détruite.

**À remonter** : un mapping par troncature est une bombe à retardement. Il doit être remplacé par une
table de correspondance explicite, ou à défaut le contrôle d'injectivité doit être rejoué à chaque
entrée d'une nouvelle contrepartie en référentiel.

### Vérification sur les données

La table de base de la réconciliation se construit ici, en joignant sur `fo_derniere_version` pour ne
pas reproduire l'explosion de la question 3.

```python
rec = bo.merge(fo_derniere_version, left_on="deal_key", right_on="deal_id", how="inner")

rec["cpty_ok"] = rec["cpty_code"] == rec["counterparty"].str[:6]
len(rec), rec["cpty_ok"].value_counts()
```

**8 915 lignes, 8 915 concordances, 0 écart.**

Le passage de 9 495 à 8 915 lignes vérifie une fois de plus la formule de la question 3. Dédoublonner
le front force `b = 0`, donc les deux termes qui contiennent `b` disparaissent :

```
excedent = a + b + ab  =  65 + 0 + 0  =  65
9 495 - 576 - 4 = 8 915       et       8 850 + 65 = 8 915
```

Les 65 confirmations en double subsistent : `drop_duplicates` a nettoyé le front, pas le back office.
Elles restent une famille d'écart à traiter dans le moteur.

**La question 7 ne livre aucune anomalie**, et c'est un résultat. Un contrôle qui passe intégralement
élimine une hypothèse et restreint le champ des 13 familles annoncées.

## 8. Sélection de version

*« Un même deal peut exister en plusieurs versions. Laquelle est la bonne, et qu'est-ce qu'une
agrégation naïve produit si tu ne tranches pas ? »*

Lié à la question de la clé primaire réelle.

### Laquelle est la bonne

Tranché lors du cadrage de `trd_deal` : **dernière version par `deal_id`, puis filtre
`status = 'CONFIRMED'`**, soit **8 337** deals en vigueur.

```python
fo_trie = fo.sort_values(["deal_id", "version"])
fo_derniere_version = fo_trie.drop_duplicates("deal_id", keep="last")
fo_en_vigueur = fo_derniere_version[fo_derniere_version["status"] == "CONFIRMED"]
```

`MAX(trade_ts)` est la seconde façon évidente de sélectionner l'état courant. **Elle est interdite
ici** : `trade_ts` vaut, sur une ligne amendée, l'horodatage de l'original augmenté d'exactement 24 h.
Il donnerait le bon résultat, mais sur une valeur inventée, et il ne départagerait pas les deux lignes
identiques d'un doublon strict.

### Ce que produit une agrégation naïve

```python
for nom, table in [("toutes les lignes", fo),
                   ("premiere version", fo_trie.drop_duplicates("deal_id", keep="first")),
                   ("derniere version", fo_derniere_version),
                   ("en vigueur", fo_en_vigueur)]:
    print(f"{nom:20} {len(table):6} lignes   {table['volume_mwh'].sum():14,.1f} MWh")
```

| Règle | Lignes | Volume MWh |
|---|---|---|
| Aucune, toutes les lignes | 9 580 | **3 010 338,7** |
| Première version | 9 000 | 2 834 460,4 |
| Dernière version | 9 000 | 2 835 528,3 |
| **En vigueur** | **8 337** | **2 616 247,1** |

Décomposition de l'erreur, **toutes les parts rapportées au chiffre naïf**, base unique pour qu'elles
s'additionnent :

| Correction | MWh | Part du naïf |
|---|---|---|
| Sélection de version | -174 810,4 | **5,81 %** |
| Filtre `CONFIRMED` | -219 281,2 | **7,28 %** |
| **Total** | **-394 091,6** | **13,09 %** |

5,81 + 7,28 = 13,09 exactement. Une décomposition n'est vérifiable que si ses parts partagent une base
et somment au total ; mélanger les bases interdit au lecteur de contrôler que les causes couvrent tout
l'écart.

Exprimée au sens usuel de l'erreur relative, écart sur valeur vraie, **l'agrégation naïve surestime la
position de 15,1 %**, soit `394 091,6 / 2 616 247,1`. Les deux lectures sont la même information : 13,09 %
du chiffre publié est du vent, ce qui place la vérité 15,1 % plus bas.

**Le résultat contre-intuitif est dans la répartition.** Le filtre de statut coûte plus cher que la
sélection de version, 219 GWh contre 175 GWh. Quelqu'un qui prendrait `MAX(version)` en se croyant
rigoureux, sans filtrer le statut, commettrait encore la plus grosse des deux erreurs.

### Ce que change un amendement

```python
change = paires.groupby("deal_id").nunique()
change.gt(1).sum().sort_values(ascending=False)
```

| Colonne | Deals où la valeur varie |
|---|---|
| `trade_ts`, `volume_mwh`, `price_eur_mwh`, `version` | **540** |
| `trade_date`, `commodity`, `direction`, `delivery_start`, `delivery_end`, `counterparty`, `book`, `status` | **0** |

Le 540 referme le modèle structurel par un chemin indépendant : sur 575 `deal_id` multi-lignes, 540
varient et 35 ne varient sur rien, ce sont exactement les 35 doublons stricts. Et 540 = 535 amendements
purs + 5 cas mixtes.

**Un amendement change toujours le volume ET le prix, jamais rien d'autre.** Pas une répartition entre
les deux : 540 sur 540 pour chacun, simultanément. C'est anormal. Dans un système réel, un amendement
corrige ce qui était faux, parfois une date de livraison, parfois une contrepartie mal saisie, parfois
le sens. Ici jamais, pas même `status`, alors que 13 deals sont annulés puis amendés.

Ampleur de la perturbation, sur les 575 deals multi-lignes :

| | Volume MWh | Prix EUR/MWh |
|---|---|---|
| Moyenne | 1,86 | 0,079 |
| Écart-type | 63,4 | 2,55 |
| Q1 / médiane / Q3 | -15,95 / 0 / 19,70 | -1,31 / 0 / 1,29 |
| Min / max | -396,4 / 530,9 | -11,79 / 9,86 |

**Aucun biais.** L'erreur type de la moyenne vaut `63,4 / racine(575) = 2,64` pour le volume : une
moyenne de 1,86 est à 0,7 erreur type de zéro, donc indiscernable de zéro. Idem pour le prix, 0,74
erreur type. La médiane exactement nulle vient du bloc central des 35 doublons, environ 270 deltas
négatifs, 35 nuls, 270 positifs.

L'amendement est donc une **perturbation symétrique**, d'environ 5 % en volume et 2 % en prix, dans un
sens ou dans l'autre. Combinée au `trade_ts` fabriqué à exactement +24 h, elle ressemble à une
génération mécanique et non à un événement métier.

### Pourquoi cette symétrie est un piège

Sur l'agrégat, la perturbation ne coûte presque rien : 1 068 MWh sur 2,83 TWh, soit **0,04 %**. Un
contrôle de position ne verrait strictement rien.

Sur la ligne, elle coûte tout. Se tromper de version fait apparaître un écart sur environ **540 lignes**,
d'une vingtaine de MWh et d'un euro et demi chacune, soit **6 % des 8 915 lignes** de la réconciliation.

C'est le premier réflexe du projet vu à l'envers : ici **l'agrégat est juste alors que presque toutes
les lignes sont fausses**, parce que des erreurs symétriques se compensent parfaitement au total. Un
contrôle qui ne regarde que la somme validerait un fichier intégralement faux.

---

# Classification des écarts

13 familles annoncées. Les catégories doivent être **exclusives et exhaustives** : chaque ligne
rapprochée tombe dans une et une seule, et leur somme couvre l'intégralité des deux sources.

| # | Catégorie | Définition | Lignes | Impact MWh | Impact EUR |
|---|---|---|---|---|---|
| | | | | | |

Contrôle de bouclage à tenir à chaque étape : la somme des lignes par catégorie doit égaler le nombre
de lignes du front plus celui du back office, moins les lignes appariées comptées une fois.

---

# Livrables

- une table de réconciliation ligne à ligne ;
- un tableau de synthèse par catégorie, avec impact en MWh et en euros ;
- une liste d'anomalies à remonter au back office, classée par matérialité.

---

# Journal des écarts trouvés

| # | Famille | Description | Lignes | Impact | Verdict |
|---|---|---|---|---|---|
| | | | | | |
