# Contrôle des Risques Marché — B2B Supply France

## Environnement d'entraînement, 10 août – 9 septembre

---

## 1. Situation

Tu arrives au pôle Contrôle Risques de la Direction Financière. Le pôle fait cinq personnes. Ton périmètre : le portefeuille B2B France, gaz et électricité, environ 1 400 sites répartis sur 220 clients.

Le desk vend de l'énergie à des clients B2B sur des contrats pluriannuels, et couvre l'exposition résultante par des achats sur le marché de gros. Ton travail consiste à vérifier que ce qui est dans les systèmes correspond à la réalité, et que ce qui remonte au management est juste.

Trois systèmes ne se parlent pas bien :

- **TRS Front** : le système de trading. Les deals de couverture y sont saisis en temps réel.
- **Back Office** : confirme les transactions avec les contreparties. Envoie un extrait plat chaque soir. Schéma différent, conventions différentes, personne ne sait exactement pourquoi.
- **Risk DWH** : l'entrepôt de données qui alimente les reportings de position et les dashboards du management.

Il n'existe pas de spécification écrite du mapping entre ces systèmes. C'est normal. C'est ton travail de le reconstituer.

Personne ne validera tes chiffres à ta place. Si tu produis un reporting faux, il partira au management tel quel.

---

## 2. Environnement technique

```
market-risk-control/
├── README.md
├── setup_check.py
└── data/
    ├── risk.db                       SQLite : référentiels, deals front, courbes, positions
    ├── volumes_hourly/               Parquet partitionné par mois (~5,8 M lignes)
    ├── actuals_daily.parquet         Relevés de comptage (~510 k lignes)
    └── raw/
        └── bo_confirmations_20260724.csv    Extrait back office
```

Installation :

```bash
pip install numpy pandas pyarrow matplotlib duckdb pyspark
python setup_check.py
```

PySpark a besoin d'un JDK (17 recommandé). Sur les 5,8 M de lignes horaires, pandas passe encore en mémoire. C'est volontaire : tu dois pouvoir comparer les deux approches sur le même problème, et te faire un avis argumenté sur le moment où Spark devient nécessaire. Ce n'est pas une question de nombre de lignes.

Date de référence pour tout le TP : **24 juillet 2026**. Année de livraison sous suivi : **2026**.

---

## 3. Dictionnaire de données

Ce qui suit est une description des colonnes, pas une spécification. Les types réels, les conventions et les pièges ne sont pas documentés. Tu les découvres.

### `risk.db`

**`ref_customer`** — `customer_id`, `customer_name`, `sector`, `segment`, `credit_rating`

**`ref_site`** — `site_id`, `customer_id`, `commodity`, `region`, `dso`, `contracted_capacity_kw`, `profile_type`, `monitored`
> `monitored = 1` : site suivi en granularité horaire.

**`ref_contract`** — `contract_id`, `customer_id`, `commodity`, `start_date`, `end_date`, `pricing_type`, `volume_tolerance_pct`

**`trd_deal`** — `deal_id`, `trade_date`, `trade_ts`, `commodity`, `direction`, `delivery_start`, `delivery_end`, `volume_mwh`, `price_eur_mwh`, `counterparty`, `book`, `status`, `version`
> `volume_mwh` est le volume **par MWh de la période de livraison**, pas le volume total du deal. Cette phrase est ambiguë. Tranche-la toi-même et documente ton choix, il conditionne tous tes chiffres.

**`mkt_forward_curve`** — `as_of_date`, `commodity`, `delivery_month`, `price_eur_mwh`
> Marks de clôture quotidiens sur les mois de livraison cotés.

**`mkt_spot_hourly`** — `commodity`, `delivery_hour_utc`, `price_eur_mwh`

**`pos_snapshot`** — `as_of_date`, `commodity`, `delivery_month`, `book`, `position_mwh`, `source_system`
> Photo de position produite indépendamment par deux systèmes. Ils devraient être d'accord.

### Parquet

**`volumes_hourly`** — `site_id`, `delivery_date`, `hour_index`, `delivery_hour_local`, `volume_mwh`, `forecast_version`, `as_of_date`
> Prévisions de consommation. `delivery_hour_local` est une chaîne en heure locale française. `hour_index` est la position de l'heure dans la journée locale.

**`actuals_daily`** — `site_id`, `delivery_date`, `volume_mwh`, `source`
> Relevés de comptage agrégés au jour.

---

## 4. Règles du jeu

1. **Aucune correction ne sera fournie.** Ce n'est pas de la rétention pédagogique, c'est la situation réelle du poste : personne ne connaît la bonne réponse avant toi.
2. **Chaque mission se termine par un artefact exécutable**, pas par des notes. Un script, un notebook propre, une requête versionnée.
3. **Toute anomalie détectée se documente** : quelle règle est violée, combien de lignes, quel impact chiffré en MWh et en euros, quelle hypothèse tu retiens pour la traiter.
4. **Un nombre d'anomalies est annoncé pour chaque mission.** Pas leur nature. Tu sais donc quand arrêter de chercher, jamais quoi chercher. Si tu en trouves plus, tant mieux, il y a du bruit statistique dans les données et distinguer le bruit de l'anomalie fait partie du travail.
5. **Tout finit dans un dépôt Git public**, un commit par jour minimum. Le repo est le livrable, pas les résultats.

---

## Mission 0 — Cartographie

**2 jours. Outils : SQL, pandas.**

Tu arrives, tu ne connais rien. Avant de contrôler quoi que ce soit, il faut savoir ce que contiennent ces bases.

Produis un profiling systématique : volumétrie, cardinalités, unicité des clés candidates, taux de nullité, plages de valeurs, distributions. Puis reconstitue le modèle relationnel : quelles tables se joignent à quelles tables, sur quelles colonnes, avec quelle cardinalité de part et d'autre.

Questions à trancher :

- Quelle est la clé primaire réelle de `trd_deal` ? Ce n'est pas `deal_id`. Pourquoi, et qu'est-ce que ça implique pour toute jointure future ?
- Le lien entre un site et un contrat n'est pas matérialisé par une clé étrangère. Sur quoi le reconstruis-tu, et combien de lignes ton choix laisse-t-il de côté ?
- Combien de sites relèvent d'un contrat inexistant ou expiré ? Est-ce une anomalie de données ou une réalité métier ? Argumente les deux positions avant de conclure.

**Anomalies de référentiel plantées : 4 familles.**

---

## Mission 1 — Réconciliation front / back office

**5 jours. Outils : SQL, pandas.**

C'est le cœur du poste. Le back office a envoyé son extrait du 24 juillet. Il doit correspondre au contenu de `trd_deal`. Il ne correspond pas.

Construis un moteur de réconciliation qui classe chaque transaction dans une catégorie d'écart exclusive et exhaustive, avec un montant d'impact.

Questions à trancher :

- Le fichier back office ne se lit pas correctement avec les paramètres par défaut de `read_csv`. Quatre caractéristiques du format s'y opposent. Lesquelles, et laquelle des quatre corrompt les données silencieusement plutôt que de lever une erreur ?
- Sur quelle clé réconcilies-tu ? Elle n'est pas propre. Formalise une fonction de normalisation, puis mesure combien de faux écarts tu élimines à chaque étape de normalisation. Si tu ne fais pas cette mesure, tu ne sais pas si ta normalisation est trop laxiste.
- Une jointure naïve sur `deal_id` produit plus de lignes qu'il n'y a de deals. Explique la mécanique exacte, puis dis-moi quel indicateur de reporting cette erreur gonfle, et de combien.
- Un écart de prix de 0,004 EUR/MWh et un écart de 3 % ne sont pas le même objet. Où places-tu le seuil, et sur quelle base ? Le seuil en valeur absolue et le seuil en relatif ne classent pas les mêmes lignes : montre-le.
- Certaines quantités sont dans une autre unité. Comment le détectes-tu **sans** que la colonne d'unité te le dise ? La question est sérieuse : cette colonne peut mentir, et sur un vrai extrait elle mentira.
- Certaines lignes ont une convention de signe inversée. Quel contrôle la révèle ? Ce n'est pas la comparaison du sens : c'est un invariant qui doit tenir même quand le sens est mal renseigné.
- Les deux systèmes n'utilisent pas les mêmes codes contrepartie. Reconstitue le mapping, et dis-moi ce qui te garantit qu'il est injectif.
- Un même deal peut exister en plusieurs versions. Laquelle est la bonne, et qu'est-ce qu'une agrégation naïve produit si tu ne tranches pas ?

**Familles d'écarts plantées : 13.**

Livrable : une table de réconciliation ligne à ligne, un tableau de synthèse par catégorie avec impact en MWh et en euros, et une liste d'anomalies à remonter au back office, classée par matérialité.

---

## Mission 2 — Position nette par mois de livraison

**4 jours. Outils : SQL, pandas.**

Le management veut la position nette du portefeuille par commodité, par mois de livraison et par book, au 24 juillet 2026. `pos_snapshot` la contient déjà, en deux versions qui ne concordent pas.

Reconstruis-la depuis `trd_deal`. Ton chiffre est l'arbitre.

Questions à trancher :

- Un deal de tenor 3 mois ou annuel couvre plusieurs mois de livraison. Comment ventiles-tu son volume ? Il y a au moins trois conventions défendables et elles ne donnent pas le même profil de position. Choisis-en une, implémente-la, et quantifie l'écart avec les deux autres.
- `pos_snapshot` affecte chaque deal à un seul mois. Est-ce cohérent avec ta ventilation ? Si non, lequel des deux a raison, et comment le démontres-tu plutôt que de l'affirmer ?
- Une fois ta position reconstruite, elle diffère des deux snapshots. Décompose l'écart : quelle part vient d'une convention de ventilation différente, quelle part vient de deals traités différemment, quelle part reste inexpliquée ? Le résidu inexpliqué est l'indicateur qui compte, et il doit tendre vers zéro.
- Croise avec les volumes clients. Le portefeuille est-il sur-couvert ou sous-couvert, et sur quels mois ? Qu'est-ce qui, dans le profil saisonnier de ce déséquilibre, devrait alerter un risk manager ?

**Écarts plantés entre les deux systèmes de position : 5 familles.**

---

## Mission 3 — P&L explain

**3 jours. Outils : pandas, numpy.**

Le management demande pourquoi la valeur de marché du portefeuille de couverture a bougé entre deux dates. La réponse « les prix ont bougé » n'est pas une réponse.

Choisis deux dates dans l'historique de `mkt_forward_curve` séparées de plusieurs semaines. Valorise la position aux deux dates. Décompose la variation.

Questions à trancher :

- Écris la valorisation comme une somme, puis la différence entre deux dates terme à terme. Combien de termes obtiens-tu, et à quoi correspond le terme croisé ? Il ne s'annule pas et il n'est pas négligeable : mesure-le.
- Ta décomposition est-elle additive exactement, ou laisse-t-elle un résidu ? Si elle en laisse un, tu as le choix entre l'allouer et le laisser visible. Les deux options ont un coût. Lequel choisis-tu et pourquoi ?
- Certaines dates de valorisation sont absentes de la courbe. Que fais-tu : report de la dernière cotation, interpolation, exclusion ? Chaque option introduit un biais différent dans ton P&L. Nomme-les.
- Un deal nouvellement tradé entre les deux dates n'existe pas en date initiale. Dans quel terme de ta décomposition atterrit-il, et est-ce que ça a un sens économique ?
- Ta décomposition tourne sur toute la période. Y a-t-il des jours où le résidu explose ? Si oui, ce n'est pas ta décomposition qui est fausse, c'est un signal. Sur quoi ?

Livrable : une décomposition quotidienne sur l'ensemble de la période, une visualisation en cascade sur une variation notable, et une note de trois paragraphes rédigée pour quelqu'un qui ne lira pas ton code.

---

## Mission 4 — Qualité des volumes horaires

**5 jours. Outils : PySpark d'abord, pandas ensuite pour comparer.**

5,8 millions de lignes de prévisions horaires sur 500 sites. Le desk s'appuie dessus pour dimensionner ses couvertures. Personne n'a jamais vérifié cette table.

Écris une batterie de contrôles de qualité. Chaque contrôle : une règle explicite, un compte de violations, un impact volumétrique, une décision de traitement.

Questions à trancher :

- Combien d'heures compte une journée dans cette table ? Vérifie-le sur les 365 jours de 2026 avant de répondre. Deux jours n'ont pas 24 heures. Explique le mécanisme physique, puis dis-moi laquelle des deux colonnes horaires est fiable et laquelle est ambiguë.
- Un de ces deux jours contient deux lignes portant le même horodatage local. Une somme naïve sur cette journée est-elle fausse ? Et un `GROUP BY delivery_hour_local` ? Les deux réponses ne sont pas les mêmes, et c'est tout le sujet.
- Plusieurs versions de prévision coexistent. Une somme sans filtre sur l'ensemble de la table donne un total faux. De combien, et dans quel sens ? Quelle règle de sélection retiens-tu, et pourquoi le `MAX(version)` par site est un piège si tu ne réfléchis pas à la granularité à laquelle tu l'appliques.
- Certains sites sont manifestement dans une autre unité. Comment le montres-tu proprement, sachant qu'aucune colonne ne l'indique ? Indice de méthode : tu disposes d'une grandeur de référence par site dans le référentiel.
- Il y a des volumes négatifs. Un volume négatif est-il nécessairement une erreur dans un portefeuille B2B ? Réponds en distinguant les cas, ne tranche pas d'un bloc.
- Il y a des trous. Détecte-les sans supposer a priori ce que devrait être la complétude : construis un calendrier de référence et fais une anti-jointure contre lui. Combien de sites, combien d'heures, quelle période ?
- Le même contrôle en PySpark et en pandas : mesure le temps d'exécution des deux. Puis explique pourquoi le résultat te surprend, et ce que ça t'apprend sur le vrai critère de choix entre les deux.

**Familles d'anomalies plantées : 9.**

---

## Mission 5 — Prévision contre réalisé, et valorisation spot

**3 jours. Outils : PySpark, pandas.**

`volumes_hourly` contient la prévision. `actuals_daily` contient le relevé. `mkt_spot_hourly` contient le prix.

Questions à trancher :

- Les deux sources de volume ne sont pas à la même granularité temporelle. Agrège la bonne et non l'autre, et justifie le sens de l'agrégation. Attention à l'interaction avec le problème de la mission 4 : un jour de 25 heures s'agrège-t-il correctement ?
- Construis l'erreur de prévision par site et par mois. Quelle métrique choisis-tu, et pourquoi le MAPE est un mauvais choix ici pour une raison structurelle liée aux données ?
- Certains relevés sont aberrants. Quel critère utilises-tu pour les qualifier ? Un seuil en écart-type et un seuil en quantile ne retiennent pas les mêmes lignes : montre-le et prends parti.
- Le spot est en UTC, les volumes en heure locale. Valorise la consommation réalisée au prix spot horaire. Si tu joins sans convertir, quel est l'impact en euros de ton erreur ? Chiffre-le, ne dis pas « faible ».
- Les prix spot contiennent des valeurs négatives. Faut-il les corriger ? Cette question a une réponse claire sur le marché de l'électricité et elle contredit l'intuition. Cherche pourquoi.

**Familles d'anomalies plantées : 5, dont deux sont des pièges de jointure et non des anomalies de données.**

---

## Mission 6 — Monitoring et restitution

**3 jours. Outils : tous.**

Tes cinq missions sont des travaux ponctuels. Le poste est récurrent : ces contrôles doivent tourner chaque jour sans toi.

- Transforme tes contrôles en une suite exécutable, paramétrée par date, avec une sortie stable et lisible par un humain.
- Définis les indicateurs que tu suivrais chaque matin. Pas dix. Trois ou quatre, avec un seuil d'alerte chiffré et justifié.
- Rédige une note d'une page pour ton manager : ce que tu as trouvé, l'impact chiffré, ce que tu recommandes, dans cet ordre. Aucune ligne de code, aucun nom de table.
- Rédige une seconde note pour le back office : les anomalies structurelles de leur extrait, priorisées.

Deux notes, deux publics, mêmes faits. Si tu écris deux fois le même texte, tu n'as compris ni l'un ni l'autre.

---

## 5. Questions de restitution

À traiter à la fin, par écrit, dans le repo. Elles valent autant que le code.

1. Prends une opération unique : une agrégation avec filtre sur l'agrégat. Écris-la en SQL, en pandas, en PySpark. Qu'est-ce qui est invariant ? Où le filtre sur l'agrégat se place-t-il dans chacun des trois, et pourquoi cet ordre est-il contraint ?
2. Pourquoi une colonne non agrégée et non groupée est-elle interdite dans un `SELECT` avec `GROUP BY` ? Réponds en termes de fonction et d'ensemble, pas en termes de règle syntaxique.
3. Quelle est la différence sémantique entre `WHERE` et `HAVING` ? Ta réponse ne doit pas contenir le mot « après ».
4. Sur l'ensemble du TP, quelle est la classe d'erreur qui t'a coûté le plus de temps ? Quel contrôle systématique l'aurait évitée ? Ajoute-le à ton harnais.
5. Quel contrôle as-tu écrit qui passait au vert alors que les données étaient fausses ? Si tu n'en as aucun, tu ne les as pas assez testés.

---

## 6. Contrainte de sortie

Au 9 septembre, un dépôt public : README qui explique la démarche, code structuré et non un empilement de notebooks, tests sur les fonctions de contrôle, résultats reproductibles depuis les données brutes.

Ce dépôt est ce que tu montreras. Une fois. Un mois de travail dans un dossier local sur ton disque ne vaut rien.
