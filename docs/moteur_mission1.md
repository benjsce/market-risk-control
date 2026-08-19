# Moteur de réconciliation - Mission 1

Documentation de `notebooks/moteur_mission1.ipynb`, chaîne reproductible allant des deux sources brutes
aux trois livrables de la Mission 1.

Les huit questions à trancher sont documentées dans `mission1_reconciliation.md`. Ce fichier ne les
rejoue pas : il décrit l'assemblage, les décisions de conception, et les résultats.

---

# Principes

**Autonome.** Aucune variable héritée du notebook d'exploration. La chaîne repart de la base SQLite pour
le front et du CSV pour le back office.

**Linéaire et rejouable.** Redémarrage du kernel puis exécution complète doit rendre le même résultat.

**Chaque section se termine par son contrôle.** Une volumétrie fausse détectée à la section 3 coûte cinq
minutes ; détectée à la section 7, elle invalide tout ce qui précède.

**Le moteur classe, il ne nettoie pas.** Les lignes défectueuses ne sont jamais supprimées, elles sont
catégorisées. Un moteur qui corrige en silence prive le back office de l'information qui lui permettrait
de ne pas reproduire le défaut.

---

# Le périmètre

| Population | Effectif |
|---|---|
| Lignes du back office trouvant un deal au front | **8 915** |
| Confirmations sans deal | **95** |
| Deals du front sans confirmation | **150** |
| **Total** | **9 160** |

Contrôlé par deux chemins indépendants :

```
lignes du back office (9 010)  +  deals sans confirmation (150)                             = 9 160
deals du front (9 000)  +  confirmations sans deal (95)  +  lignes dupliquees (65)          = 9 160
```

Le premier vérifie que toute ligne du back office est classée, le second que tout deal du front l'est
aussi. Aucun des deux n'est une tautologie : une jointure qui multiplierait des lignes, faute d'avoir
dédoublonné le front par version, ferait échouer le premier.

---

# Architecture

| Section | Contenu | Contrôle de sortie |
|---|---|---|
| 0 | configuration, chemins, date de référence | |
| 1 | lecture des deux sources | volumétries, types de date, absence de valeurs manquantes |
| 2 | normalisation de la clé, sélection de version | cardinal conservé (8 945), une ligne par deal (9 000) |
| 3 | table du périmètre par jointure externe tracée | périmètre (9 160) par deux chemins |
| 4 | sept colonnes de contrôle booléennes | les sept effectifs, aucune valeur manquante, types booléens |
| 5 | catégorie unique par cascade | somme égale au périmètre, absorptions cohérentes |
| 6 | impact en MWh et en euros | |
| 7 | les trois livrables | |

---

# Décisions de conception

## Le front joint est la dernière version, tous statuts

Le fichier back office enregistre **tout le cycle de vie**, pas seulement les transactions vivantes : ses
lignes marquées `CXL` (271) font face aux deals annulés au front, et ses lignes `MATCHED` couvrent les
confirmés (8 265) comme les en attente (379).

Joindre le front restreint aux deals confirmés (8 337) transformerait donc 650 lignes en fausses
confirmations sans deal, soit 87 % d'une catégorie qui n'en compte réellement que 95.

**Une réconciliation compare des périmètres comparables.** Le statut sort du périmètre et entre dans le
calcul de l'impact.

## Règle B pour l'exclusivité, par ordre de correction

Les familles se recoupent : 6 lignes portent deux défauts, une en porte trois. Les catégories devant
être exclusives, une règle d'arbitrage est nécessaire.

| Rang | Catégorie | Pourquoi à ce rang |
|---|---|---|
| 1 | ligne dupliquée dans l'extrait | dédoublonner avant toute mesure, sinon tout compte double |
| 2 | confirmation sans deal, deal sans confirmation | sans rapprochement, aucune comparaison n'existe |
| 3 | quantité en kWh | unité fausse, donc volume et impact faux d'un facteur 1 000 |
| 4 | sens contradictoire | affecte la position, donc l'agrégat |
| 5 | écart de prix matériel | n'affecte ni volume ni position, seulement la valorisation |
| 6 | écart de prix par arrondi | n'est pas un écart |
| 7 | concordante | aucun défaut |

Chaque rang est une **condition préalable au suivant**, ce qui rend l'ordre justifiable plutôt que
décrété.

**Alternative écartée : la règle A, par gravité décroissante.** Elle classerait chaque ligne dans la
famille de plus fort impact. Écartée pour deux raisons : elle compare des grandeurs hétérogènes, des MWh
pour une unité fausse et des euros pour un écart de prix ; et le classement d'une ligne changerait avec
les prix, rendant la synthèse non reproductible d'un mois sur l'autre.

## Le statut se lit dans la source qui porte la ligne

```python
EN_VIGUEUR = pd.Series(
    np.where(perimetre["sans_deal"],
             perimetre["state"]  == "MATCHED",
             perimetre["status"] == "CONFIRMED"),
    index=perimetre.index)
```

Une confirmation sans deal n'a pas de statut au front. La juger par le front l'exclurait entièrement du
chiffrage, ce qui donnerait un impact nul à l'anomalie la plus grave du lot. Elle est donc jugée par la
colonne `state` du back office.

Quatre des 95 y sont marquées annulées, pour 861,4 MWh. Les compter reviendrait à reprocher au back
office une transaction qu'il a lui-même rétractée.

**Asymétrie assumée et à déclarer.** Les deux systèmes n'ont pas la même finesse : `MATCHED` ne sépare
pas un deal confirmé d'un deal en attente. Le critère appliqué aux confirmations sans deal est donc plus
permissif que celui appliqué au reste. On ne peut pas faire mieux faute d'information, mais quelqu'un
qui filtrerait partout sur `CONFIRMED` trouverait un total différent et croirait à une erreur.

## L'impact

**Définition unique : l'écart entre le chiffre que produirait quelqu'un utilisant l'extrait tel quel et
le chiffre correct.**

Elle se décline en deux natures d'erreur.

| Nature | Catégories | Formule |
|---|---|---|
| Erreur de **volume** | dupliquée, sans deal, sans confirmation, kWh | le volume fautif, valorisé à un prix |
| Erreur de **prix** | prix matériel, prix par arrondi | écart de prix multiplié par le volume |

Les erreurs de prix ont un **impact en MWh nul** : une erreur de prix ne déplace pas la position d'un
mégawattheure. Leur attribuer un impact en volume compterait deux fois la même anomalie.

**On valorise avec la source qui détient l'information.** Le front quand il existe, le back office quand
il est seul. Sur une ligne dupliquée les deux existent et le front fait autorité sur ses propres
transactions : c'est un choix, pas une évidence.

## Le sens contradictoire est une indétermination, pas un écart

Aucune source ne fait autorité sur le sens, l'invariant qui aurait permis d'arbitrer n'ayant pas été
trouvé. Il n'y a donc **pas d'erreur mesurable** mais une fourchette, égale à deux fois le volume signé.

Elle est portée par une colonne séparée, `indetermination_mwh`, pour ne pas mélanger deux natures dans
la colonne d'impact.

---

# Résultats

## Synthèse par catégorie

| Catégorie | Lignes | En vigueur | Impact MWh | Impact EUR net | Impact EUR brut |
|---|---|---|---|---|---|
| quantité en kWh | 70 | 61 | **15 863 121** | **994 187 337** | 994 187 337 |
| deal sans confirmation | 150 | 133 | 35 636,5 | 2 298 106 | 2 298 106 |
| confirmation sans deal | 95 | 91 | 34 098,8 | 1 751 654 | 1 751 654 |
| ligne dupliquée dans l'extrait | 65 | 61 | 20 192,9 | 1 146 076 | 1 146 076 |
| écart de prix matériel | 89 | 81 | 0 | **-9 376** | **43 616** |
| écart de prix par arrondi | 102 | 91 | 0 | -30 | 86 |
| sens contradictoire | 54 | 49 | 0 | 0 | 0 |
| concordante | 8 535 | 7 922 | 0 | 0 | 0 |
| **TOTAL** | **9 160** | **8 489** | | | |

**Une seule famille pèse 99,5 % de l'impact.** Les 70 lignes en kWh valent 994 M EUR, toutes les autres
réunies 5,2 M EUR. Le chiffre est arithmétiquement juste mais dépasse de six fois le notionnel du
portefeuille réconcilié (168 M EUR), ce qui appelle une phrase d'explication : il mesure ce que
produirait une somme brute sans conversion d'unité, pas une perte.

**La colonne brute justifie son existence sur les écarts de prix.** Net -9 376 EUR pour un brut de
43 616 EUR, soit 78 % de compensation. Une synthèse limitée au net rangerait cette famille derrière le
bruit d'arrondi.

**Le sens contradictoire** ne figure pas dans les colonnes d'impact par construction. Sur les lignes en
vigueur (49), l'indétermination vaut **85,6 MWh** pour une exposition brute de **14 409,4 MWh**.

## Les trois livrables

**Table ligne à ligne**, 9 160 lignes, portant la clé unifiée, la provenance, les sept booléens, la
catégorie et les impacts. Les booléens sont ce qui rend le classement contestable donc défendable : ils
montrent qu'un défaut de rang inférieur a bien été détecté, simplement qu'il n'a pas gagné.

**Synthèse par catégorie**, avec ligne de total servant de contrôle visible d'exhaustivité.

**Liste d'anomalies, organisée par famille.** 476 lignes en vigueur, hors concordantes et hors écarts par
arrondi, ces derniers ne constituant pas des écarts et plafonnant à 86 EUR au total.

Le tri global par impact décroissant a été **écarté** : il fait remonter une seule famille et enterre les
autres, un doublon de confirmation à 30 000 EUR arrivant après une soixantaine de lignes d'unité.
Surtout, il ignore le coût de correction : les 61 lignes en kWh se corrigent par une règle unique
appliquée en masse, alors que les 91 confirmations sans deal demandent 91 investigations distinctes.

Chaque famille est donc triée par impact absolu décroissant, avec part cumulée interne.

---

# Découverte : les 95 confirmations sans deal forment un bloc contigu

```
prefixe : D95 sur les 95
plage   : D9500000 a D9500094
```

**95 identifiants consécutifs sans aucun trou**, dans une plage que le front n'utilise pas : ses propres
identifiants vont de `D2600000` à `D2608999`, et cet espace est saturé, sans lacune.

Ce ne sont donc pas des deals perdus par le front. Un deal perdu porterait un identifiant de la plage du
front, avec un trou correspondant.

**Ces confirmations viennent d'ailleurs** : autre système, autre entité, jeu de test, book absent de
`trd_deal`. On ne peut pas trancher, mais la question posée au back office change de nature. Sans cette
observation on lui écrivait « vous avez confirmé 95 transactions qui n'existent pas chez nous », ce qui
l'envoyait chercher des erreurs de saisie. Avec elle : « votre extrait contient un bloc de 95 références
consécutives issues d'une plage de numérotation que nous n'utilisons pas, d'où viennent-elles ? »

C'est le meilleur résultat du moteur, et il est apparu à la mise en forme, pas par une mesure
supplémentaire.

---

# Pièges rencontrés dans la construction

**`duplicated()` traite les valeurs manquantes comme une valeur.** Sur la clé du back office, absente sur
les deals sans confirmation (150), il en marquait 149 comme doublons : 214 au lieu de 65.

**Une comparaison entre deux sources exige les deux côtés, pas un seul.** Protéger uniquement `direction`
laissait passer les 150 deals sans confirmation, dont le `buy_sell` vide comparé par `!=` rend `True` :
205 sens contradictoires au lieu de 55.

**Une définition juste dans son contexte devient fausse une fois déplacée.** Le test d'arrondi, écrit en
exploration sur une table déjà restreinte aux lignes divergentes, marquait 1 041 lignes sur la table
complète, toutes celles dont le prix front a deux décimales et coïncide donc avec son propre arrondi. La
condition « les deux prix diffèrent » était implicite dans le filtre et devait devenir explicite.

**Un seuil ne se pose jamais sur une borne théorique.** Posé à 0,005, la borne exacte d'un arrondi au
centime, il classait 4 lignes d'arrondi comme matérielles à cause de l'imprécision binaire. Recalibré à
0,006, il reproduit exactement la partition par mécanisme, 92 contre 92.

**Une somme de produits n'est pas le produit des sommes.** Le notionnel se calcule ligne à ligne puis se
somme. Multiplier un volume total par une colonne de prix produisait 1 516 milliards d'euros.

**Sommer des prix n'a aucun sens.** `price_eur_mwh` est une grandeur intensive, exprimée par MWh. Seul le
notionnel, extensif, s'additionne.

**L'indexage en chaîne perd l'affectation.** `bo.iloc[lignes]["colonne"] = valeur` écrit dans une copie
jetée aussitôt, sans erreur, avec un simple avertissement. Un seul crochet, `loc[lignes, "colonne"]`.

---

# Limites et points ouverts

**L'invariant de la question 6 n'a pas été trouvé.** Le moteur identifie et borne les 55 sens
contradictoires, il ne les arbitre pas.

**La détection d'unité repose sur le rapport, pas sur la colonne déclarative**, ce qui est le
comportement voulu. Une assertion vérifie que les deux coïncident : le jour où elle échoue, le classement
reste juste et c'est la source qui doit être signalée. Cette assertion ne se corrige pas en la
supprimant.

**Les valeurs de référence sont celles de l'extrait du 24 juillet 2026.** Les assertions en majuscules
échoueront sur un nouvel extrait, et c'est voulu. Les invariants, eux, doivent continuer de passer :
conservation du cardinal par la normalisation, somme des catégories égale au périmètre, absorptions
égales aux défauts en excès.

**Piste non traitée, renvoyée à la Mission 2** : 454 deals logés dans un book de la commodité opposée,
soit 5,1 %, répartis de façon quasi uniforme, ce qui suggère une affectation aléatoire. `book` étant un
axe d'agrégation de la position, la question s'y posera de toute façon.
