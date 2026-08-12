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

> à remplir après exécution

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
