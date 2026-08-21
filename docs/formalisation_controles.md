# Formalisation des contrôles

Ce document énonce, sous forme mathématique, les propriétés que testent les contrôles écrits dans les
notebooks. Il ne raconte aucune mission : il donne les outils, leur énoncé exact, et la raison pour
laquelle une variante voisine ne teste pas la même chose.

Il grossit au fil des missions. À ce stade il couvre les contrôles des sections 1 et 2 de la
Mission 4, qui reprennent ceux des Missions 0 et 1.

---

# Notations

Une table $T$ est un **multi-ensemble** de lignes : une même ligne peut y figurer plusieurs fois.
C'est toute la différence avec un ensemble, et c'est la source de la moitié des pièges.

| Notation | Signification |
|---|---|
| $\lvert T \rvert$ | nombre de lignes de $T$, doublons compris |
| $\pi_K(T)$ | projection **distincte** de $T$ sur les colonnes $K$, donc un ensemble |
| $\sigma_\varphi(T)$ | lignes de $T$ satisfaisant le prédicat $\varphi$ |
| $n_T(k)$ | multiplicité : nombre de lignes de $T$ portant la valeur $k$ sur $K$ |

En PySpark, $\lvert T \rvert$ s'écrit `T.count()` et $\lvert \pi_K(T) \rvert$ s'écrit
`T.select(K).distinct().count()`, ou `F.countDistinct(K)` à l'intérieur d'un `agg`.

---

# 1. Clé et injectivité

## Énoncé

Soit $K$ un ensemble de colonnes de $T$. Considérons l'application qui à une ligne associe sa
projection sur $K$ :

$$p_K : T \longrightarrow \pi_K(T), \qquad t \longmapsto t_{\vert K}$$

$K$ est une **clé** de $T$ si et seulement si $p_K$ est injective.

## Le test

Toute application d'un ensemble fini vers un autre vérifie $\lvert \pi_K(T) \rvert \le \lvert T \rvert$,
puisque chaque ligne produit exactement une image. L'égalité a lieu si et seulement si aucune image
n'est atteinte deux fois. D'où :

$$K \text{ est une clé de } T \iff \lvert \pi_K(T) \rvert = \lvert T \rvert$$

C'est un test **exact**, pas une heuristique. La quantité $\lvert T \rvert - \lvert \pi_K(T) \rvert$
compte les lignes en excès, c'est-à-dire le nombre de doublons à retirer pour rendre $K$ injective.

## Formulation équivalente : l'injectivité relative

On teste souvent qu'une colonne $c$ identifie une ligne **à l'intérieur** d'un groupe défini par des
colonnes $G$. Notons $T_g = \sigma_{G = g}(T)$ le groupe de valeur $g$. La propriété s'écrit :

$$\forall g \in \pi_G(T), \quad \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert$$

Elle est **équivalente** à dire que $G \cup \{c\}$ est une clé de $T$ :

$$\left( \forall g, \ \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert \right)
\iff \lvert \pi_{G \cup \{c\}}(T) \rvert = \lvert T \rvert$$

La démonstration tient en une ligne : les groupes partitionnent $T$, donc
$\lvert T \rvert = \sum_g \lvert T_g \rvert$, et de même
$\lvert \pi_{G \cup \{c\}}(T) \rvert = \sum_g \lvert \pi_c(T_g) \rvert$. Deux sommes de termes
positifs sont égales terme à terme si et seulement si elles sont égales globalement, dès lors que
chaque terme de gauche majore celui de droite.

**Conséquence pratique.** Les deux écritures donnent le même verdict. La version par groupes coûte un
regroupement mais nomme les groupes fautifs ; la version globale tient en une ligne et convient mieux
à un harnais quotidien.

---

# 2. Contiguïté d'un rang

## Énoncé

Soit $S \subset \mathbb{N}^*$ un ensemble fini non vide. On veut tester que $S$ est l'intervalle
entier $\{1, \dots, n\}$ pour un certain $n$, c'est-à-dire que $S$ est le domaine d'un
rang qui commence à 1 et ne saute aucune valeur.

## Le test correct

$$S = \{1, \dots, \lvert S \rvert\}
\iff \min S = 1 \ \text{ et } \ \max S = \lvert S \rvert$$

Sens direct immédiat. Réciproque : si $\min S = 1$ et $\max S = \lvert S \rvert$, alors
$S \subseteq \{1, \dots, \lvert S \rvert\}$, et ces deux ensembles ont le même cardinal,
donc ils sont égaux.

Deux quantités suffisent. Ni la moyenne, ni la somme, ni l'écart type ne sont nécessaires.

## Pourquoi l'identité de l'étendue ne suffit pas

Pour tout ensemble fini d'entiers, $\lvert S \rvert$ valeurs distinctes tiennent dans l'intervalle
$\{\min S, \dots, \max S\}$, d'où :

$$\lvert S \rvert \le \max S - \min S + 1, \qquad
\text{avec égalité} \iff S = \{\min S, \dots, \max S\}$$

Cette identité teste la **contiguïté**, mais elle est invariante par translation : elle est vérifiée
par $\{0,1,2,3\}$ comme par $\{1,2,3,4\}$. Elle ne dit rien sur l'origine du rang. Il faut lui
adjoindre $\min S = 1$, et le couple ainsi obtenu est équivalent au test de la section précédente.

## Pourquoi ne pas figer le maximum

Écrire $\max S = 24$ paraît naturel pour des heures. C'est faux dès que la table contient une journée
de changement d'heure, où le nombre d'heures livrées vaut 23 ou 25. La formulation
$\max S = \lvert S \rvert$ s'adapte d'elle-même : elle ne suppose pas la longueur du rang, elle la
déduit.

**Règle générale.** Un contrôle qui code en dur une valeur attendue devient faux dès que la valeur
légitime varie. Préférer une relation entre grandeurs mesurées.

---

# 3. La maille, ou pourquoi un contrôle grossier passe au vert

## L'énoncé du piège

Soit $T = \bigsqcup_{s} T_s$ une partition de la table par site. La projection distincte commute avec
la réunion :

$$\pi_c\left( \bigsqcup_s T_s \right) = \bigcup_s \pi_c(T_s)$$

Un contrôle posé à la maille grossière teste donc la propriété de gauche, celle de la **réunion**,
alors que la propriété qui nous intéresse porte sur **chaque part**. Or l'implication ne va que dans
un sens :

$$\left( \forall s, \ \pi_c(T_s) = \{1, \dots, n\} \right)
\implies \bigcup_s \pi_c(T_s) = \{1, \dots, n\}$$

et la réciproque est fausse.

## Le contre-exemple minimal

Deux sites, quatre heures, un jour, une version.

$$\pi_h(T_{S_1}) = \{1, 2, 4\}, \qquad \pi_h(T_{S_2}) = \{1, 2, 3, 4\}$$

La réunion vaut $\{1,2,3,4\}$, donc le contrôle à la maille du jour est vert. Le site $S_1$ n'a
pourtant pas l'heure 3. Le site $S_2$ **comble** le trou de son voisin.

Si de plus $S_1$ porte deux lignes d'indice 2, alors $\lvert T_{S_1} \rvert = 4$ tandis que
$\lvert \pi_h(T_{S_1}) \rvert = 3$ : le compte de lignes est celui d'un site sain, et seule la
comparaison des deux quantités révèle le défaut.

## Ce qu'il faut en retenir

**Un contrôle n'existe pas dans l'absolu, il existe à une maille.** Un contrôle posé à une maille
plus grossière que la propriété visée teste une condition strictement plus faible, et son vert ne
prouve rien.

La maille correcte se lit dans la phrase française qui décrit ce qu'est une ligne. Si une ligne porte
« le volume prévu pour un site, une heure de livraison, dans une version donnée », alors les colonnes
citées forment la clé, et tout contrôle d'unicité se pose à cette maille.

---

# 4. Jointures : ce qui multiplie et ce qui ne multiplie pas

## Jointure interne

$$\lvert T_1 \bowtie_K T_2 \rvert = \sum_{k \, \in \, \pi_K(T_1) \cap \pi_K(T_2)} n_{T_1}(k) \cdot n_{T_2}(k)$$

Le résultat n'a le cardinal de $T_1$ que si $K$ est une clé de $T_2$ et si toute valeur de $T_1$
trouve une correspondance. Sinon, il enfle. C'est l'explosion de jointure de la Mission 1 : le total
agrégé devient faux tandis que chaque ligne prise isolément reste correcte.

## Anti-jointure

$$T_1 \, \triangleright_K \, T_2 = \{\, t \in T_1 \ : \ t_{\vert K} \notin \pi_K(T_2) \,\}
\qquad \text{d'où} \qquad
\lvert T_1 \triangleright_K T_2 \rvert \le \lvert T_1 \rvert$$

La définition ne fait intervenir $T_2$ que par $\pi_K(T_2)$, c'est-à-dire par l'**ensemble** de ses
clés, jamais par leurs multiplicités. L'anti-jointure est donc insensible aux doublons du côté droit,
et ne peut jamais multiplier les lignes.

Il en va de même pour la semi-jointure $T_1 \ltimes_K T_2$, définie avec l'appartenance au lieu de la
non-appartenance.

**Conséquence pratique.** Pour tester une appartenance, `left_anti` ou `left_semi` sont sûrs par
construction. Une jointure interne suivie d'un dédoublonnage donne le même résultat mais expose à
l'explosion intermédiaire.

---

# 5. Le nul, ou pourquoi un filtre n'est pas un complément

## La logique ternaire

SQL, et donc Spark, évaluent les prédicats dans $\{\text{VRAI}, \text{FAUX}, \text{INCONNU}\}$. Toute
comparaison dont une opérande est nulle vaut $\text{INCONNU}$, y compris l'égalité d'un nul avec
lui-même.

La sélection ne conserve que le vrai :

$$\sigma_\varphi(T) = \{\, t \in T \ : \ \varphi(t) = \text{VRAI} \,\}$$

## La conséquence

Le complément n'est pas le complément :

$$\lvert \sigma_\varphi(T) \rvert + \lvert \sigma_{\neg\varphi}(T) \rvert \le \lvert T \rvert$$

avec égalité si et seulement si $\varphi$ ne vaut $\text{INCONNU}$ sur aucune ligne. Les lignes
« inconnues » sont absentes des deux côtés.

## Pourquoi c'est un piège de contrôle

Un contrôle de la forme « compter les lignes où $a \ne b$, attendu zéro » retourne zéro dans deux
situations opposées : lorsque $a$ et $b$ coïncident partout, et lorsque l'une des deux colonnes est
entièrement nulle. Il ne les distingue pas.

## Les deux réparations

**Comparaison sûre au nul.** L'opérateur `eqNullSafe` évalue l'égalité sur le domaine étendu par le
nul, donc à valeurs dans $\{\text{VRAI}, \text{FAUX}\}$ seulement :

$$a \doteq b \ \iff \ (a = b) \ \text{ ou } \ (a \text{ et } b \text{ tous deux nuls})$$

Sa négation redevient un vrai complément, et un nul isolé déclenche le contrôle au lieu de
l'esquiver.

**Contrôle de complétude séparé.** Vérifier d'abord que les colonnes ne sont pas nulles, puis
comparer. Deux assertions au lieu d'une.

La première garantit qu'aucune anomalie ne passe, la seconde dit où elle est. Dans un harnais
quotidien, la garantie prime : un contrôle qui rate une anomalie est pire qu'un contrôle qui la
signale sans l'expliquer.

---

# Récapitulatif

| Propriété à établir | Formule | Écriture PySpark |
|---|---|---|
| $K$ est une clé | $\lvert \pi_K(T) \rvert = \lvert T \rvert$ | `T.select(K).distinct().count() == T.count()` |
| $c$ unique dans chaque groupe $G$ | $\forall g, \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert$ | `groupBy(G).agg(count, countDistinct)` puis comparaison |
| $c$ est un rang de 1 à $n$ | $\min = 1$ et $\max = \lvert \pi_c \rvert$ | `agg(F.min, F.max, F.countDistinct)` |
| absence d'orphelin | $\pi_K(T_1) \subseteq \pi_K(T_2)$ | `T1.join(T2, K, "left_anti").count() == 0` |
| égalité résistante au nul | $a \doteq b$ | `F.col("a").eqNullSafe(F.col("b"))` |

---

# Les trois erreurs que ces formules préviennent

**Confondre compte et compte distinct.** Ce sont deux grandeurs différentes, et c'est leur
**comparaison**, jamais l'une des deux prise seule, qui teste une unicité.

**Poser un contrôle à la mauvaise maille.** La réunion peut être complète alors qu'aucune part ne
l'est. Le vert d'un contrôle grossier ne se transmet pas aux parts.

**Croire qu'un filtre partitionne.** En logique ternaire, une ligne peut échapper à un prédicat et à
sa négation. Un contrôle écrit sans y penser passe au vert sur des données absentes.
