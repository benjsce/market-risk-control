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

| Composition | `deal_id` | Mécanisme |
|---|---|---|
| 2 lignes différentes | **535** | amendement pur |
| 2 lignes identiques | **35** | doublon strict pur |
| 3 lignes : original, amendement, copie | **5** | les deux à la fois |
| | **575** | |

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

Réparti par version : 9 037 lignes de version 1 et 543 de version 2. L'excédent de 37 lignes de
version 1 sur les 9 000 deals correspond aux 35 doublons purs et aux 2 cas mixtes dont la copie porte
sur l'original. Les 3 lignes de version 2 en excès correspondent aux 3 cas mixtes dont la copie porte
sur l'amendement. Les 40 doublons se répartissent donc en 37 sur version 1 et 3 sur version 2.

### Candidats d'écarts issus de `trd_deal`

Trois, à confronter aux treize familles annoncées, sans conclure avant la réconciliation :

| # | Candidat | Volume | Nature |
|---|---|---|---|
| 1 | Doublons de saisie stricts | 40 lignes, 40 `deal_id` | anomalie à remonter au back office |
| 2 | `trade_ts` fabriqué sur les lignes de version 2 | 543 lignes | colonne inexploitable pour dater ou ordonner |
| 3 | Deals amendés après annulation | 13 lignes `CANCELLED` non terminales | impossibilité métier |

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

> à remplir

## 2. Clé de réconciliation et fonction de normalisation

*« Sur quelle clé réconcilies-tu ? Elle n'est pas propre. Formalise une fonction de normalisation, puis
mesure combien de faux écarts tu élimines à chaque étape. Si tu ne fais pas cette mesure, tu ne sais
pas si ta normalisation est trop laxiste. »*

> à remplir

## 3. Mécanique de l'explosion de jointure

*« Une jointure naïve sur `deal_id` produit plus de lignes qu'il n'y a de deals. Explique la mécanique
exacte, puis dis-moi quel indicateur de reporting cette erreur gonfle, et de combien. »*

Dépend directement de la clé primaire réelle établie plus haut.

> à remplir

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

Le front compte 12 contreparties distinctes. C'est ici que l'échelle de normalisation écrite en
Mission 0 sera éprouvée pour la première fois.

> à remplir

## 8. Sélection de version

*« Un même deal peut exister en plusieurs versions. Laquelle est la bonne, et qu'est-ce qu'une
agrégation naïve produit si tu ne tranches pas ? »*

Lié à la question de la clé primaire réelle.

> à remplir

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
