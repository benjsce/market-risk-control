# Formalisation des contrôles

Ce document énonce, sous forme mathématique, les propriétés que testent les contrôles écrits dans ce
dépôt. Il ne raconte aucune mission : il donne les outils, leur énoncé exact, la démonstration quand
elle tient en trois lignes, et la raison pour laquelle une variante voisine ne teste pas la même
chose.

Chaque outil est ensuite traduit en SQL, en pandas et en PySpark. Le tableau de correspondance est en
fin de document.

Il grossit au fil des missions. À ce stade il couvre les contrôles des Missions 0, 1 et 4.

---

# Notations

Une table $T$ est un **multi-ensemble** de lignes : une même ligne peut y figurer plusieurs fois.
C'est toute la différence avec un ensemble, et c'est la source de la moitié des pièges.

| Notation | Signification |
|---|---|
| $\lvert T \rvert$ | nombre de lignes de $T$, doublons compris |
| $\pi_K(T)$ | projection **distincte** de $T$ sur les colonnes $K$, donc un ensemble |
| $\sigma_\varphi(T)$ | lignes de $T$ satisfaisant le prédicat $\varphi$ |
| $\gamma_G(T)$ | regroupement de $T$ par les colonnes $G$, une ligne par groupe |
| $T_g$ | le groupe de valeur $g$, c'est-à-dire $\sigma_{G = g}(T)$ |
| $n_T(k)$ | multiplicité : nombre de lignes de $T$ portant la valeur $k$ sur $K$ |

Les groupes partitionnent la table : $T = \bigsqcup_{g \in \pi_G(T)} T_g$. Cette égalité sert dans
presque toutes les démonstrations qui suivent.

---

---

# Partie I. Structure : clés, dépendances, mailles

---

## 1. Clé et injectivité

### Énoncé

Soit $K$ un ensemble de colonnes de $T$. Considérons l'application qui à une ligne associe sa
projection sur $K$ :

$$p_K : T \longrightarrow \pi_K(T), \qquad t \longmapsto t_{\vert K}$$

$K$ est une **clé** de $T$ si et seulement si $p_K$ est injective.

### Le test

Toute application d'un ensemble fini vers un autre vérifie $\lvert \pi_K(T) \rvert \le \lvert T \rvert$,
puisque chaque ligne produit exactement une image. L'égalité a lieu si et seulement si aucune image
n'est atteinte deux fois. D'où :

$$K \text{ est une clé de } T \iff \lvert \pi_K(T) \rvert = \lvert T \rvert$$

C'est un test **exact**, pas une heuristique. La quantité $\lvert T \rvert - \lvert \pi_K(T) \rvert$
compte les lignes en excès, c'est-à-dire le nombre de doublons à retirer pour rendre $K$ injective.

### Formulation équivalente : l'injectivité relative

On teste souvent qu'une colonne $c$ identifie une ligne **à l'intérieur** d'un groupe défini par des
colonnes $G$. La propriété s'écrit :

$$\forall g \in \pi_G(T), \quad \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert$$

Elle est **équivalente** à dire que $G \cup \{c\}$ est une clé de $T$ :

$$\left( \forall g, \ \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert \right)
\iff \lvert \pi_{G \cup \{c\}}(T) \rvert = \lvert T \rvert$$

Démonstration : les groupes partitionnent $T$, donc $\lvert T \rvert = \sum_g \lvert T_g \rvert$, et
de même $\lvert \pi_{G \cup \{c\}}(T) \rvert = \sum_g \lvert \pi_c(T_g) \rvert$. Chaque terme de la
seconde somme minore le terme correspondant de la première ; deux sommes ainsi ordonnées sont égales
globalement si et seulement si elles le sont terme à terme.

**Conséquence pratique.** Les deux écritures donnent le même verdict. La version par groupes coûte un
regroupement mais nomme les groupes fautifs ; la version globale tient en une ligne et convient mieux
à un harnais quotidien.

---

## 2. Dépendance fonctionnelle

### Énoncé

$X$ **détermine fonctionnellement** $Y$, noté $X \to Y$, si la valeur de $Y$ est entièrement fixée par
celle de $X$ : il existe une application $f$ telle que toute ligne vérifie
$t_{\vert Y} = f(t_{\vert X})$.

### Le test

$$X \to Y \iff \lvert \pi_{X \cup Y}(T) \rvert = \lvert \pi_X(T) \rvert$$

Démonstration : le nombre de couples distincts $(x, y)$ vaut $\lvert \pi_X(T) \rvert$ si et seulement
si chaque $x$ n'est associé qu'à un seul $y$.

Formulation équivalente, plus lisible en pratique :

$$X \to Y \iff \max_{x \, \in \, \pi_X(T)} \ \lvert \pi_Y(T_x) \rvert = 1$$

### Ce que ça unifie

Une clé est le cas particulier $K \to \text{toutes les colonnes}$. Une dépendance fonctionnelle est
donc le même outil appliqué à un sous-ensemble de colonnes, et les deux tests se réduisent à une
seule comparaison entre un nombre de lignes et un nombre de combinaisons distinctes.

### Le piège

Une dépendance fonctionnelle **mesurée** n'est pas une dépendance fonctionnelle **garantie**. Elle
vaut sur les données observées et peut tomber à la ligne suivante. Elle doit être rejouée, jamais
convertie en hypothèse.

C'est le même défaut de robustesse qu'un mapping par troncature : jamais injectif par construction,
parfois injectif par mesure sur un domaine donné, et fragile à toute entrée nouvelle.

---

## 3. Indépendance de deux variables catégorielles

### Énoncé

Deux colonnes $A$ et $B$ sont indépendantes dans $T$ si connaître $A$ n'apprend rien sur $B$ :

$$\mathbb{P}(A = a, \ B = b) = \mathbb{P}(A = a) \cdot \mathbb{P}(B = b)$$

En effectifs, en notant $n_{ab}$ le croisement, $n_{a\cdot}$ et $n_{\cdot b}$ les marges et $n$ le
total :

$$n_{ab} \ \approx \ e_{ab} = \frac{n_{a\cdot} \cdot n_{\cdot b}}{n}$$

### Le point neutre

La formulation opérationnelle est plus simple. L'indépendance équivaut à dire que la distribution
**conditionnelle** de $B$ sachant $A = a$ ne dépend pas de $a$, et vaut donc la distribution
**marginale** de $B$ :

$$\mathbb{P}(B = b \mid A = a) = \mathbb{P}(B = b)$$

Cette marginale est le **point neutre** : la valeur qu'affiche un croisement dépourvu d'information.
Un croisement qui colle au point neutre sur toutes ses lignes établit l'indépendance ; un croisement
qui s'en écarte fortement établit une relation.

Annoncer le point neutre **avant** de mesurer est ce qui rend la prédiction réfutable. Sans lui, tout
pourcentage observé paraît significatif.

### Pourquoi c'est un contrôle et pas une curiosité

Une colonne censée être déterminée par une autre et qui s'en révèle indépendante ne porte **aucune
information**. La lecture correcte n'est alors pas « $x$ % des valeurs sont fausses » mais « la
colonne est inexploitable ». La différence commande la recommandation : on ne corrige pas une colonne
aléatoire, on la reconstruit.

### Le piège du plancher

Un test de contradiction ne réfute que sur le sous-domaine où l'on dispose d'une connaissance
externe. Le nombre de lignes réfutées est donc un **plancher**, jamais une mesure de l'anomalie :

$$\lvert \text{lignes réfutées} \rvert \ \le \ \lvert \text{lignes fausses} \rvert$$

Les lignes non réfutées ne sont pas validées, elles sont hors de portée du test.

---

## 4. Contiguïté d'un rang

### Énoncé

Soit $S \subset \mathbb{N}^*$ un ensemble fini non vide. On veut tester que $S$ est l'intervalle
entier $\{1, \dots, n\}$ pour un certain $n$, c'est-à-dire que $S$ est le domaine d'un rang qui
commence à 1 et ne saute aucune valeur.

### Le test correct

$$S = \{1, \dots, \lvert S \rvert\}
\iff \min S = 1 \ \text{ et } \ \max S = \lvert S \rvert$$

Sens direct immédiat. Réciproque : si $\min S = 1$ et $\max S = \lvert S \rvert$, alors
$S \subseteq \{1, \dots, \lvert S \rvert\}$, et ces deux ensembles ont le même cardinal, donc ils sont
égaux.

Deux quantités suffisent. Ni la moyenne, ni la somme, ni l'écart type ne sont nécessaires.

### Pourquoi l'identité de l'étendue ne suffit pas

Pour tout ensemble fini d'entiers, $\lvert S \rvert$ valeurs distinctes tiennent dans l'intervalle
$\{\min S, \dots, \max S\}$, d'où :

$$\lvert S \rvert \le \max S - \min S + 1, \qquad
\text{avec égalité} \iff S = \{\min S, \dots, \max S\}$$

Cette identité teste la **contiguïté**, mais elle est invariante par translation : elle est vérifiée
par $\{0,1,2,3\}$ comme par $\{1,2,3,4\}$. Elle ne dit rien sur l'origine du rang. Il faut lui
adjoindre $\min S = 1$.

### Pourquoi ne pas figer le maximum

Écrire $\max S = 24$ paraît naturel pour des heures. C'est faux dès que la table contient une journée
de changement d'heure, où le nombre d'heures livrées vaut 23 ou 25. La formulation
$\max S = \lvert S \rvert$ s'adapte d'elle-même : elle ne suppose pas la longueur du rang, elle la
déduit.

**Règle générale.** Un contrôle qui code en dur une valeur attendue devient faux dès que la valeur
légitime varie. Préférer une relation entre grandeurs mesurées.

---

## 5. La maille, ou pourquoi un contrôle grossier passe au vert

### L'énoncé du piège

Soit $T = \bigsqcup_{s} T_s$ une partition de la table. La projection distincte commute avec la
réunion :

$$\pi_c\left( \bigsqcup_s T_s \right) = \bigcup_s \pi_c(T_s)$$

Un contrôle posé à la maille grossière teste donc la propriété de la **réunion**, alors que la
propriété visée porte sur **chaque part**. L'implication ne va que dans un sens :

$$\left( \forall s, \ \pi_c(T_s) = \{1, \dots, n\} \right)
\implies \bigcup_s \pi_c(T_s) = \{1, \dots, n\}$$

et la réciproque est fausse.

### Le contre-exemple minimal

Deux parts, quatre valeurs.

$$\pi_c(T_1) = \{1, 2, 4\}, \qquad \pi_c(T_2) = \{1, 2, 3, 4\}$$

La réunion vaut $\{1,2,3,4\}$ : le contrôle grossier est vert. La part $T_1$ n'a pourtant pas la
valeur 3, et c'est $T_2$ qui **comble** le trou de sa voisine.

Si de plus $T_1$ porte deux lignes de valeur 2, alors $\lvert T_1 \rvert = 4$ tandis que
$\lvert \pi_c(T_1) \rvert = 3$ : le compte de lignes est celui d'une part saine, et seule la
comparaison des deux quantités révèle le défaut.

### Ce qu'il faut en retenir

**Un contrôle n'existe pas dans l'absolu, il existe à une maille.** Posé à une maille plus grossière
que la propriété visée, il teste une condition strictement plus faible, et son vert ne prouve rien.

La maille correcte se lit dans la phrase française qui décrit ce qu'est une ligne. Les colonnes citées
dans cette phrase forment la clé, et tout contrôle d'unicité se pose à cette maille.

---

## 6. Normalisation d'une clé

### Énoncé

Rapprocher deux sources exige souvent d'appliquer une fonction de normalisation $f$ aux clés :
suppression des espaces, passage en majuscules, retrait d'un remplissage. Chaque transformation est un
**barreau**, et la normalisation complète est leur composée $f = f_p \circ \dots \circ f_1$.

Deux effets se mesurent séparément, barreau par barreau.

**Le gain en forme** : le nombre de clés qui deviennent conformes au motif attendu.

**Le gain en existence** : l'accroissement de $\lvert \pi_K(T_1) \cap \pi_K(T_2) \rvert$, c'est-à-dire
le nombre de clés qui trouvent effectivement une correspondance.

### Le contrôle de laxisme

Une normalisation trop agressive fabrique de faux appariements en fusionnant des clés distinctes. Le
test est la **conservation du cardinal** :

$$\lvert f(\pi_K(T)) \rvert = \lvert \pi_K(T) \rvert
\iff f \text{ est injective sur } \pi_K(T)$$

Si l'égalité tombe, $f$ a confondu au moins deux clés qui étaient distinctes.

### La règle de lecture

Un barreau dont le gain en existence est **inférieur** à son gain en forme fabrique des identifiants
bien formés qui ne correspondent à rien :

$$x \text{ vérifie le motif} \quad \not\Longrightarrow \quad x \in \pi_K(T_2)$$

**La forme n'est pas l'existence.** Tester l'appartenance, jamais le motif seul.

### La symétrie

Ne jamais normaliser un seul côté d'une comparaison symétrique sans avoir vérifié que l'autre est déjà
propre. Sinon on mesure la saleté d'une source avec un instrument déformé par la saleté de l'autre.

---

---

# Partie II. Mise en correspondance : les jointures

---

## 7. Jointure interne et explosion

### La formule

$$\lvert T_1 \bowtie_K T_2 \rvert
= \sum_{k \, \in \, \pi_K(T_1) \, \cap \, \pi_K(T_2)} n_{T_1}(k) \cdot n_{T_2}(k)$$

Le résultat n'a le cardinal de $T_1$ que si $K$ est une clé de $T_2$ **et** si toute valeur de $T_1$
trouve une correspondance. Sinon, il enfle.

### L'excédent sur une clé donnée

Si une clé porte $1 + a$ lignes à gauche et $1 + b$ lignes à droite, la jointure en produit
$(1+a)(1+b)$ là où une seule était attendue. L'excédent vaut donc :

$$(1+a)(1+b) - 1 = a + b + ab$$

et non $a \times b$. Un doublon d'un **seul** côté suffit à dupliquer la transaction : si $b = 0$,
l'excédent vaut encore $a$.

### La nature du dégât

L'explosion laisse chaque ligne individuellement correcte et rend **le total** faux. C'est l'inverse
exact de la fusion par clé non injective de la section 11, où le total reste juste et la
décomposition devient fausse. Les deux défauts sont symétriques et aucun contrôle unique ne les
attrape tous les deux.

**Avant toute jointure, vérifier l'unicité de la clé des deux côtés.**

---

## 8. Anti-jointure et semi-jointure

### Définition

$$T_1 \, \triangleright_K \, T_2 = \{\, t \in T_1 \ : \ t_{\vert K} \notin \pi_K(T_2) \,\}
\qquad
T_1 \, \ltimes_K \, T_2 = \{\, t \in T_1 \ : \ t_{\vert K} \in \pi_K(T_2) \,\}$$

### La propriété de sûreté

$$\lvert T_1 \triangleright_K T_2 \rvert \ \le \ \lvert T_1 \rvert$$

La définition ne fait intervenir $T_2$ que par $\pi_K(T_2)$, c'est-à-dire par l'**ensemble** de ses
clés, jamais par leurs multiplicités. L'anti-jointure et la semi-jointure sont donc insensibles aux
doublons du côté droit et ne peuvent jamais multiplier les lignes.

**Conséquence pratique.** Pour tester une appartenance, ce sont les outils sûrs par construction. Une
jointure interne suivie d'un dédoublonnage donne le même résultat mais expose à l'explosion
intermédiaire.

### Les deux anti-jointures ne sont pas indépendantes

En posant $A = \pi_K(T_1)$ et $B = \pi_K(T_2)$ :

$$\lvert A \setminus B \rvert - \lvert B \setminus A \rvert = \lvert A \rvert - \lvert B \rvert$$

La différence entre les deux comptes d'orphelins est **fixée par les cardinaux des deux ensembles de
clés**. Un seul des deux nombres est donc libre. Les compter séparément reste utile, mais présenter
leur différence comme une découverte serait une tautologie.

---

---

# Partie III. Grandeurs et agrégation

---

## 9. Extensif et intensif

### Définition

Une grandeur $\varphi$ définie sur des ensembles de lignes est **extensive** si elle est additive sur
les réunions disjointes :

$$\varphi(A \sqcup B) = \varphi(A) + \varphi(B)$$

Elle est **intensive** sinon. Un volume, un notionnel, un nombre de lignes sont extensifs. Un prix
unitaire, un taux, une moyenne, un ratio sont intensifs.

### La règle

**Une grandeur intensive ne se somme pas.** La somme de prix unitaires n'a aucune signification
physique et son résultat ne se rapporte à rien.

Une grandeur intensive s'agrège par **moyenne pondérée** par la grandeur extensive qui lui sert de
support :

$$\bar p = \frac{\sum_i v_i \, p_i}{\sum_i v_i}$$

Ce quotient est le prix unitaire qui, appliqué au volume total, redonne le notionnel total. C'est la
seule agrégation qui conserve le sens.

### Le test de recevabilité

Avant d'agréger une colonne, se demander : **de quoi le résultat serait-il la mesure ?** Si la réponse
n'existe pas, l'agrégation est illégitime, quelle que soit la propreté du code.

---

## 10. Somme de produits contre produit de sommes

$$\sum_i v_i \, p_i \ \ne \ \left( \sum_i v_i \right) \left( \sum_i p_i \right)$$

L'égalité n'a lieu que dans des cas dégénérés. L'écart entre les deux membres tient à la covariance
empirique entre $v$ et $p$ : agréger avant de multiplier détruit l'information de l'appariement ligne
à ligne.

**Corollaire opérationnel.** Un notionnel se calcule ligne à ligne **puis** se somme. Jamais l'inverse.
La même règle vaut pour tout impact obtenu en multipliant deux colonnes.

---

## 11. Agrégation par une clé non injective

### Ce qui se conserve, ce qui se perd

Regrouper par une colonne $c$ produit $\lvert \pi_c(T) \rvert$ lignes. Si $c$ n'est pas injective sur
la maille visée, ce nombre est strictement inférieur à $\lvert T \rvert$ : des lignes distinctes
fusionnent.

Pour une grandeur extensive $v$, la somme totale est **invariante** par ce regroupement :

$$\sum_{g} \ \sum_{t \in T_g} v(t) \ = \ \sum_{t \in T} v(t)$$

Le total reste donc juste, et c'est ce qui rend le défaut indétectable par un contrôle de total.

Ce qui se perd est la **décomposition** : la ligne issue d'une collision porte la somme de plusieurs
réalités distinctes, sans que rien ne le signale.

### La règle

Un contrôle de total et un contrôle de cardinal testent deux propriétés différentes. Il faut les deux :
le premier attrape l'explosion de jointure, le second attrape la fusion par clé non injective.

---

## 12. Ce qui est une fonction du groupe

### L'énoncé

Le regroupement $\gamma_G$ envoie chaque groupe sur **une** ligne de sortie. Une colonne $c$ ne peut
figurer dans cette ligne que si sa valeur est déterminée par le groupe, c'est-à-dire si :

$$G \to c$$

Sinon, $c$ prendrait plusieurs valeurs dans le groupe et la ligne de sortie n'aurait aucune valeur
légitime à porter. **C'est la raison de l'interdiction d'une colonne ni groupée ni agrégée dans un
`SELECT` avec `GROUP BY`** : ce n'est pas une règle syntaxique, c'est la condition d'existence d'une
application.

Une fonction d'agrégation résout le problème autrement : elle transforme le multi-ensemble des valeurs
du groupe en une valeur unique, donc elle **fabrique** la dépendance fonctionnelle qui manquait.

### Sélection et regroupement ne commutent pas

$$\sigma_\varphi\big(\gamma_G(T)\big) \ \ne \ \gamma_G\big(\sigma_\varphi(T)\big)$$

Les deux expressions sont valides et calculent des choses différentes. La distinction entre `WHERE` et
`HAVING` est celle de leur **domaine de définition** :

| Clause | Domaine du prédicat | Ce sur quoi il porte |
|---|---|---|
| `WHERE` | $T$ | une ligne de la table |
| `HAVING` | $\gamma_G(T)$ | un groupe, donc un agrégat |

Un prédicat portant sur un agrégat n'a pas de sens sur une ligne isolée : l'agrégat n'existe pas encore
comme objet. Ce n'est pas une question d'ordre d'exécution mais de **type de l'argument**.

### Sélection d'un représentant par groupe

Garder « la dernière version de chaque deal » n'est pas un maximum mais un **argument du maximum** :

$$t^\star_g = \mathrm{argmax}_{t \, \in \, T_g} \ v(t)$$

$\max$ rend une valeur, $\mathrm{argmax}$ rend une ligne. Confondre les deux fait perdre les
autres colonnes de la ligne retenue.

Deux pièges. L'$\mathrm{argmax}$ n'est **pas unique** si $v$ présente des ex aequo dans le
groupe : il faut un départage explicite, faute de quoi le résultat dépend de l'ordre de stockage. Et la
**maille** $G$ est un choix : un maximum pris à une maille trop grossière retient un représentant qui
ne couvre pas tout le domaine.

---

## 13. Net, brut, et compensation

### Deux agrégats d'un vecteur d'écarts

Soit $(e_i)$ les écarts ligne à ligne. Deux grandeurs, toujours à donner ensemble :

$$\text{net} = \sum_i e_i \qquad\qquad \text{brut} = \sum_i \lvert e_i \rvert$$

L'inégalité triangulaire donne :

$$\left\lvert \sum_i e_i \right\rvert \ \le \ \sum_i \lvert e_i \rvert$$

avec **égalité si et seulement si tous les $e_i$ sont de même signe**.

### La lecture

Un net faible devant le brut signale une **compensation**, pas une absence d'anomalie. Le cas extrême,
$\text{net} = 0$ avec $\text{brut}$ grand, décrit un fichier intégralement faux dont le total est
juste.

$$\frac{\lvert \text{net} \rvert}{\text{brut}} \ \in \ [0, 1]$$

Ce rapport mesure la part non compensée. Proche de zéro, il faut chercher le mécanisme qui produit des
erreurs symétriques.

### Impact réalisé et exposition

Le net mesure ce qui a **effectivement** coûté. Le brut mesure ce que le mécanisme **pouvait** coûter.
Remonter le seul net d'une anomalie compensée laisse croire qu'elle est bénigne, alors que la
compensation peut relever du hasard et ne pas se reproduire.

---

## 14. Décomposition d'un écart

### La contrainte

Décomposer un écart total en causes n'a d'intérêt que si le lecteur peut vérifier que les causes le
couvrent entièrement :

$$E = \sum_{j} E_j$$

Cela impose une **base unique**. Mélanger des dénominateurs différents dans un même tableau rend les
parts non additives et la décomposition invérifiable.

### Le dénominateur d'un taux

Un même écart absolu donne deux taux différents selon la base :

$$\frac{\lvert m - v \rvert}{v} \qquad \text{contre} \qquad \frac{\lvert m - v \rvert}{m}$$

où $v$ est la valeur correcte et $m$ la valeur mesurée. Pour un écart de réconciliation, la référence
est la **valeur correcte**. Le dénominateur doit toujours être annoncé.

### Partition des anomalies

Classer des lignes en familles exige une partition : familles **exclusives et exhaustives**.

$$T = \bigsqcup_{j} C_j$$

Une construction par priorité, du type « première condition vraie l'emporte », garantit l'exclusivité
par construction, mais **l'ordre des conditions devient une décision de conception** à documenter : une
ligne qui vérifie deux conditions est classée dans la première rencontrée.

L'exhaustivité se contrôle en vérifiant $\sum_j \lvert C_j \rvert = \lvert T \rvert$.

---

---

# Partie IV. Comparaison numérique

---

## 15. Égalité des flottants

### Pourquoi l'égalité exacte échoue

Les flottants représentent les réels avec une précision relative finie. Une division qui devrait tomber
sur $1000$ rend $999{,}9999999999999$. Un test d'égalité exacte perd alors des lignes sans rien
signaler.

### Le critère de `np.isclose`

$$\lvert a - b \rvert \ \le \ \text{atol} + \text{rtol} \cdot \lvert b \rvert$$

avec par défaut $\text{rtol} = 10^{-5}$ et $\text{atol} = 10^{-8}$.

**Ce critère est asymétrique** : $b$ joue le rôle de référence et $a$ celui de mesure. Échanger les
deux arguments change le seuil, donc potentiellement le verdict. Placer la valeur de référence en
second.

### La forme du critère

Le terme absolu domine près de zéro, le terme relatif $\text{rtol} \cdot \lvert b \rvert$ domine loin
de zéro. Le critère est un compromis entre les deux, pas un seuil unique.

---

## 16. Seuils de matérialité

### Deux critères concurrents

Une ligne d'écart $e$ portant sur un prix $p$ peut être déclarée matérielle selon un seuil **absolu**
ou un seuil **relatif** :

$$\lvert e \rvert > \tau_a \qquad \text{contre} \qquad \lvert e \rvert > \tau_r \cdot p$$

### Quand les deux critères sont emboîtés

Notons $p_{\min}$ et $p_{\max}$ les prix extrêmes observés. Si $\tau_a \le \tau_r \, p_{\min}$, alors
$\tau_a \le \tau_r p$ pour tout prix observé : le critère absolu est partout le moins exigeant, donc
l'ensemble qu'il retient **contient** celui du critère relatif. Symétriquement, si
$\tau_a \ge \tau_r \, p_{\max}$, l'inclusion s'inverse.

Les deux populations sont donc **emboîtées**, sauf si :

$$\tau_r \cdot p_{\min} \ < \ \tau_a \ < \ \tau_r \cdot p_{\max}$$

C'est seulement dans cette fenêtre que les deux critères se croisent et retiennent des lignes
différentes. Hors de cette fenêtre, choisir entre les deux ne change que le nombre de lignes retenues,
jamais leur nature.

### Calibrer un seuil

Un seuil placé exactement à la borne théorique d'un mécanisme est **instable** : l'erreur de
représentation des flottants fait basculer les lignes situées sur la borne. Le placer strictement
au-delà, puis vérifier que la partition obtenue reproduit exactement la partition par mécanisme.

---

## 17. Séparation d'échelle par le logarithme

### L'idée

Un facteur multiplicatif se lit mal sur un rapport brut, dont la distribution est écrasée vers zéro. Le
logarithme le transforme en décalage additif :

$$\log_{10}(\lambda \cdot x) = \log_{10}\lambda + \log_{10}x$$

### Les décades

L'arrondi du logarithme décimal centre les classes sur les puissances de 10 :

$$\mathrm{round}\big(\log_{10} r\big) = k
\iff 10^{\,k - 1/2} \ \le \ r \ < \ 10^{\,k + 1/2}$$

soit un intervalle allant d'environ $0{,}316 \cdot 10^k$ à $3{,}162 \cdot 10^k$. La classe $k = 3$
recouvre les rapports de 316 à 3 162, ce qui isole proprement un facteur 1 000.

### L'usage

Détecter une population exprimée dans une autre unité revient à chercher **plusieurs modes** dans la
distribution du logarithme du rapport à une grandeur de référence. Un mode unique conclut à
l'homogénéité ; deux modes séparés d'un entier concluent à un facteur puissance de 10.

**Réserve.** La séparation est nette quand les deux grandeurs mesurent la même chose. Quand la grandeur
de référence mesure autre chose, le rapport est bruité et la coupure devient un choix de seuil à
justifier, non une évidence.

---

---

# Partie V. Logique, valeurs manquantes, et portée d'un contrôle

---

## 18. Le nul, ou pourquoi un filtre n'est pas un complément

### La logique ternaire

SQL, et donc Spark, évaluent les prédicats dans $\{\text{VRAI}, \text{FAUX}, \text{INCONNU}\}$. Toute
comparaison dont une opérande est nulle vaut $\text{INCONNU}$, y compris l'égalité d'un nul avec
lui-même.

La sélection ne conserve que le vrai :

$$\sigma_\varphi(T) = \{\, t \in T \ : \ \varphi(t) = \text{VRAI} \,\}$$

### La conséquence

$$\lvert \sigma_\varphi(T) \rvert + \lvert \sigma_{\neg\varphi}(T) \rvert \ \le \ \lvert T \rvert$$

avec égalité si et seulement si $\varphi$ ne vaut $\text{INCONNU}$ sur aucune ligne. Les lignes
« inconnues » sont absentes des deux côtés : **un filtre et sa négation ne partitionnent pas**.

### Pourquoi c'est un piège de contrôle

Un contrôle de la forme « compter les lignes où $a \ne b$, attendu zéro » retourne zéro dans deux
situations opposées : lorsque $a$ et $b$ coïncident partout, et lorsque l'une des colonnes est
entièrement nulle. Il ne les distingue pas.

### Les deux réparations

**Comparaison sûre au nul.** L'opérateur `eqNullSafe`, `IS NOT DISTINCT FROM` en SQL, évalue l'égalité
sur le domaine étendu par le nul, donc à valeurs dans $\{\text{VRAI}, \text{FAUX}\}$ seulement :

$$a \doteq b \ \iff \ (a = b) \ \text{ ou } \ (a \text{ et } b \text{ tous deux nuls})$$

**Contrôle de complétude séparé.** Vérifier d'abord l'absence de nuls, puis comparer.

La première garantit qu'aucune anomalie ne passe, la seconde dit où elle est. Dans un harnais
quotidien, la garantie prime : un contrôle qui rate une anomalie est pire qu'un contrôle qui la signale
sans l'expliquer.

### Le nul déguisé

Une absence encodée par une **valeur du domaine**, du type `NR` pour une notation absente, rend tout
contrôle de complétude inopérant : la colonne n'a aucun nul et se déclare complète. Avant de contrôler
la complétude, vérifier que l'absence est encodée comme une absence.

---

## 19. Ce qu'un contrôle peut prouver

### Un contrôle doit pouvoir échouer

Une identité qui découle de la façon dont on a calculé ses termes est vraie par construction et ne
vérifie rien. Avant de traiter un rapprochement comme un contrôle, se poser la question :

**existe-t-il un état des données pour lequel ce test échouerait ?**

Si la réponse est non, le test est une tautologie. Il rassure sans rien établir.

### Mesuré et dérivé

Un nombre obtenu par une identité arithmétique à partir d'autres nombres n'est pas un nombre compté. Il
boucle nécessairement. Marquer systématiquement la distinction, et **recompter** avant toute remontée
un nombre qui n'a été que dérivé.

### Un extrait trié n'est pas un échantillon

Trier puis prendre les premières lignes rend les **statistiques d'ordre extrêmes**, jamais un tirage
représentatif :

$$\text{trier puis prendre } n \text{ lignes} \ \longrightarrow \ \{x_{(1)}, \dots, x_{(n)}\}$$

Toute conclusion sur la population tirée d'un tel extrait est invalide. Utiliser un échantillon
aléatoire pour l'intuition, et la population entière pour l'affirmation.

### Un résultat correct ne valide pas le raisonnement

Un agrégat qui tombe juste peut recouvrir des lignes toutes fausses, par compensation. Redescendre à la
maille inférieure et vérifier la structure, jamais le seul total.

### Un avertissement n'est pas un contrôle

Un avertissement d'outil peut se lever là où il n'y a pas de problème et se taire sur la colonne
fausse. L'absence d'alerte n'est pas une validation.

### Sans arbitre, une fourchette et non une erreur

Quand deux sources divergent et qu'aucune ne fait autorité, l'écart entre elles mesure la **largeur de
l'indétermination**, pas une erreur :

$$\text{indétermination} = \lvert v_1 - v_2 \rvert \qquad
\text{et non} \qquad \text{erreur} = \lvert v_{\text{mesuré}} - v_{\text{vrai}} \rvert$$

La seconde formule exige de connaître $v_{\text{vrai}}$. Publier un net dans ce cas revient à choisir un
côté sans le dire.

---

## 20. L'alignement par index en pandas

Spécifique à pandas, sans équivalent en SQL ni en PySpark, et source d'erreurs silencieuses.

Les opérations arithmétiques entre deux `Series` sont définies sur la **réunion des index**, et non
terme à terme :

$$(u + v)_i = u_i + v_i \quad \text{pour } i \in I_u \cup I_v,
\qquad \text{avec un nul dès que } i \notin I_u \cap I_v$$

Deux séries de même longueur mais d'index différents ne se multiplient donc pas terme à terme.

| Aligne par index | Travaille sur les valeurs |
|---|---|
| `+`, `-`, `*`, `/`, `mul`, `add` | `isin` |
| `reindex`, `align` | comparaison à un scalaire |
| affectation d'une `Series` à une colonne | `str.*` |

SQL et PySpark n'ont pas d'index : toute mise en correspondance y est une jointure explicite. C'est plus
verbeux, et cette classe d'erreurs y disparaît.

---

---

# Tableau de correspondance

$T$ désigne la table, $K$ un ensemble de colonnes, $G$ les colonnes de regroupement.

| Propriété | Formule | SQL | pandas | PySpark |
|---|---|---|---|---|
| $K$ est une clé | $\lvert \pi_K(T) \rvert = \lvert T \rvert$ | `count(*) = count(distinct K)` | `len(df) == len(df[K].drop_duplicates())` | `T.count() == T.select(K).distinct().count()` |
| $c$ unique dans chaque groupe | $\forall g,\ \lvert \pi_c(T_g) \rvert = \lvert T_g \rvert$ | `group by G having count(*) <> count(distinct c)` | `df.groupby(G)[c].agg(['size','nunique'])` | `groupBy(G).agg(F.count("*"), F.countDistinct(c))` |
| $X \to Y$ | $\max_x \lvert \pi_Y(T_x) \rvert = 1$ | `group by X having count(distinct Y) > 1` | `df.groupby(X)[Y].nunique().max() == 1` | `groupBy(X).agg(F.countDistinct(Y)).agg(F.max(...))` |
| rang de 1 à $n$ | $\min = 1$ et $\max = \lvert \pi_c \rvert$ | `min(c), max(c), count(distinct c)` | `s.min(), s.max(), s.nunique()` | `agg(F.min, F.max, F.countDistinct)` |
| absence d'orphelin | $\pi_K(T_1) \subseteq \pi_K(T_2)$ | `where not exists (...)` | `~df1[K].isin(df2[K])` | `T1.join(T2, K, "left_anti").count() == 0` |
| indépendance | $n_{ab} \approx n_{a\cdot} n_{\cdot b} / n$ | `group by A, B` puis marges | `pd.crosstab(a, b, normalize="index")` | `groupBy(A).pivot(B).count()` |
| égalité sûre au nul | $a \doteq b$ | `a is not distinct from b` | `(a == b) \| (a.isna() & b.isna())` | `F.col("a").eqNullSafe(F.col("b"))` |
| comparaison de flottants | $\lvert a-b \rvert \le \text{atol} + \text{rtol}\lvert b \rvert$ | `abs(a - b) <= tol` | `np.isclose(a, b)` | `F.abs(F.col("a") - F.col("b")) <= tol` |
| moyenne pondérée | $\sum v_i p_i / \sum v_i$ | `sum(v * p) / sum(v)` | `(v * p).sum() / v.sum()` | `F.sum(v * p) / F.sum(v)` |
| net et brut | $\sum e_i$ et $\sum \lvert e_i \rvert$ | `sum(e), sum(abs(e))` | `e.sum(), e.abs().sum()` | `F.sum(e), F.sum(F.abs(e))` |
| représentant par groupe | $\mathrm{argmax}_{T_g} v$ | `row_number() over (partition by G order by v desc)` | `sort_values(v).drop_duplicates(G, keep="last")` | `Window.partitionBy(G).orderBy(F.col(v).desc())` |
| filtre sur agrégat | $\sigma_\varphi(\gamma_G(T))$ | `having` | `groupby(...).agg(...)` puis masque | `groupBy(...).agg(...).filter(...)` |

---

# Les six erreurs que ces formules préviennent

**Confondre compte et compte distinct.** Ce sont deux grandeurs différentes, et c'est leur
**comparaison**, jamais l'une des deux prise seule, qui teste une unicité.

**Poser un contrôle à la mauvaise maille.** La réunion peut être complète alors qu'aucune part ne l'est.
Le vert d'un contrôle grossier ne se transmet pas aux parts.

**Croire qu'un filtre partitionne.** En logique ternaire, une ligne peut échapper à un prédicat et à sa
négation. Un contrôle écrit sans y penser passe au vert sur des données absentes.

**Ne regarder que le total.** L'explosion de jointure fausse le total en laissant les lignes justes ; la
fusion par clé non injective fausse la décomposition en laissant le total juste. Il faut un contrôle de
cardinal **et** un contrôle de total.

**Sommer une grandeur intensive.** Un prix, un taux, une moyenne ne s'additionnent pas. Ils s'agrègent
par moyenne pondérée par leur support extensif.

**Confondre le net et le brut.** Leur rapport mesure la compensation. Un net faible ne dit rien de la
gravité du mécanisme qui l'a produit.
