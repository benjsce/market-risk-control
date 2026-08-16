# Synthèse

Document de relecture. Il ne contient que des **résultats arrêtés** et des **réflexes**, jamais le
chemin qui y mène. Pour savoir *comment* un nombre a été obtenu, ouvrir le journal de la mission
concernée : `mission0_cartographie.md`, `mission1_reconciliation.md`.

Plafond : **150 lignes**. S'il est dépassé, le document a manqué son but et doit être élagué, pas
étendu.

Date de référence du TP : **24 juillet 2026**. Année de livraison sous suivi : **2026**.

---

# Partie A - Chiffres arrêtés

Tout nombre en gras est **mesuré**. Les autres sont dérivés et à recompter avant toute remontée.

## État des missions

| Mission | Objet | État |
|---|---|---|
| 0 | Cartographie du référentiel | close, 2 familles d'anomalies sur 4 |
| 1 | Réconciliation front / back office | en cours, questions 1, 2, 3, 7, 8 tranchées sur 8 |
| 2 à 6 | Position, courbes, volumes, spot, restitution | non ouvertes |

Deux points laissés ouverts en Mission 0 : le verdict sur les 899 sites sans contrat, et les
familles 3 et 4 d'anomalies du référentiel, jamais identifiées.

## Référentiel

`ref_customer` **220** lignes, clé `customer_id`. `ref_site` **1 400**, clé `site_id`. `ref_contract`
**260**, clé `contract_id`, seule table historisée, les contrats successifs y coexistent.

- `dso`, `monitored`, `profile_type` sont **inexploitables** : affectation aléatoire. Ne jamais
  joindre, filtrer ni regrouper dessus.
- `credit_rating` code l'absence de notation par `NR`, pas par `NULL`. **31** clients sur 220.
  À exclure explicitement de toute statistique conditionnée.
- `contracted_capacity_kw` est la seule grandeur numérique du référentiel, donc la seule mesure de
  taille disponible par site.
- Le lien site vers contrat n'existe pas au schéma. Il se reconstruit sur `(customer_id, commodity)`
  filtré sur les dates d'effet.

## `trd_deal`

| Grandeur | Valeur |
|---|---|
| Lignes | **9 580** |
| `deal_id` distincts | **9 000** |
| Deals en vigueur, dernière version confirmée | **8 337** |
| Lignes remplacées | 580 |

**Pas de clé primaire.** 40 lignes strictement identiques sur toutes les colonnes : aucun
sous-ensemble de colonnes ne peut donc être une clé. La sélection de l'état courant se fait par
`MAX(version)` par `deal_id`, puis filtre sur `status = 'CONFIRMED'`.

Modèle structurel, sans résidu : 8 425 deals à ligne unique + 535 amendés + 35 à doublon strict +
5 mixtes = **9 000** deals pour **9 580** lignes.

`trade_ts` est **inexploitable** pour dater ou ordonner : sur une ligne amendée il vaut l'horodatage
de l'original plus exactement 24 heures, heure de la journée conservée à la seconde.

## Fichier back office `bo_confirmations_20260724.csv`

| Grandeur | Valeur |
|---|---|
| Lignes | **9 010** |
| `deal_ref` distincts | **8 945** |
| Lignes en doublon sur `deal_ref` | **65** |

Lecture correcte, quatre paramètres non par défaut :

```python
pd.read_csv(chemin, sep=";", decimal=",",
            parse_dates=["trade_dt", "del_from", "del_to"], dayfirst=True)
```

`dayfirst` est celui qui corrompt en silence : **8 249** lignes sur 9 010 sur `del_from`, sans erreur
ni type invalide. Encodage ASCII pur, aucun `NaN`, aucun jeton manquant.

## Clé de réconciliation

Normalisation, côté back office uniquement, le front étant propre sur les 9 000 identifiants :

```python
serie.str.strip().str.upper().str.replace(r"^D0+", "D", regex=True)
```

| Population | Brut | Normalisé |
|---|---|---|
| Références appariées | **8 665** | **8 850** |
| Orphelines back office | **280** | **95** |
| Deals du front sans confirmation | **335** | **150** |

**185 faux écarts éliminés sur 280**, aucune fusion de références distinctes. Gains par barreau :
`strip` +80, `upper` +60, retrait du zéro de remplissage +45.

**Identité invariante :** non confirmés - orphelines = 9 000 - 8 945 = **55**. C'est le plancher des
deals que le fichier back office ne contient tout simplement pas.

## Jointure naïve sur la clé

Une jointure interne rend `Σ n_bo(k) × n_fo(k)` lignes, vérifié : **9 495** pour **8 850** deals
appariés, donc **645 en trop**. Décomposition avec `a = n_bo - 1` et `b = n_fo - 1` :
excédent = `a + b + ab`, soit **576** dus au front, **65** au back office, **4** aux deux à la fois.
Le terme croisé attendu sous indépendance valait 4,2 : les deux dégradations sont sans lien.

89 % du gonflement n'est pas une anomalie mais une jointure qui omet de sélectionner la version en
vigueur. La correction est à faire côté requête, pas côté fichier.

| Grandeur | Naïf | Correct | Gonflement |
|---|---|---|---|
| Volume traité | 2 987 513,8 MWh | 2 790 477,6 MWh | **7,06 %** |
| Notionnel | 177 141 863,71 EUR | 165 672 694,97 EUR | **6,92 %** |

Volume **brut**, pas position nette : la convention de signe n'est pas encore tranchée. Et le notionnel
n'est ni une perte ni une valorisation de marché.

## Contrepartie et sélection de version

**Mapping contrepartie** : `counterparty.str[:6]`, 12 codes des deux côtés, injectif et exhaustif par
mesure. Aucun écart sur les 8 915 lignes. Mais rien ne garantit l'injectivité : elle tient sur le
domaine du 24 juillet 2026, pas par construction. À remplacer par une table explicite.

**Table de base de la réconciliation** : `rec`, 8 915 lignes, `bo` joint sur `fo_derniere_version`.

**Sélection de version** : dernière version par `deal_id`, puis `status = 'CONFIRMED'`, soit **8 337**
deals et **2 616 247,1 MWh**. Interdit d'arbitrer par `MAX(trade_ts)`, la colonne est fabriquée.

Coût de ne pas trancher, parts rapportées au chiffre naïf de 3 010 338,7 MWh :

| Correction | MWh | Part |
|---|---|---|
| Sélection de version | -174 810,4 | 5,81 % |
| Filtre `CONFIRMED` | -219 281,2 | 7,28 % |
| Total | **-394 091,6** | **13,09 %** |

Soit **+15,1 %** de surestimation rapportée à la valeur vraie. Le filtre de statut coûte plus cher que
la sélection de version.

**Un amendement ne change que `volume_mwh`, `price_eur_mwh` et `trade_ts`**, sur 540 deals, jamais les
dates, le sens, la contrepartie ni le statut. Perturbation symétrique et centrée sur zéro, environ 5 %
en volume et 2 % en prix. Elle ne coûte que 0,04 % sur l'agrégat mais fausse environ 540 lignes, soit
6 % de la réconciliation.

## Anomalies et candidats

| Source | Anomalie | Volume | Chiffre |
|---|---|---|---|
| `ref_site` | contradiction physique `dso` / `commodity` | 267 sites, 1 125 523 kW | mesuré |
| `ref_contract` | couples client-commodité doublement couverts | 35 couples, 41 contrats en excès | mesuré |
| `ref_contract` | contrat en vigueur sans site | 8 couples | non tranché |
| `ref_site` | sites sans contrat valide | 899 sites, 3 402 619 kW | mesuré, verdict non rendu |
| `trd_deal` | doublons de saisie stricts | 40 lignes | mesuré |
| `trd_deal` | `trade_ts` fabriqué | 543 lignes | mesuré |
| `trd_deal` | deals amendés après annulation | 13 lignes | dérivé |
| back office | confirmations sans deal au front | 95 | mesuré |
| back office | deals du front sans confirmation | 150 | mesuré |

Le sujet annonce **13 familles plantées** pour la Mission 1. Calibre observé des familles : de la
dizaine à quelques centaines, jamais 3 lignes, jamais 5 000.

---

# Partie B - Méthode

Ce qui se transporte hors du TP. Les chiffres ci-dessus sont synthétiques ; ces réflexes, non.

1. **Un résultat correct ne valide pas le raisonnement qui l'a produit.** Il faut redescendre à la
   maille inférieure et vérifier la structure, pas seulement le total.

2. **Deux défauts opposés s'annulent et fabriquent un contrôle vert sur des données fausses.** Vu
   trois fois dans ce projet. Un écart net faible n'est pas un écart faible.

3. **Une identité qui découle de la façon dont on a calculé ses termes ne vérifie rien.** Avant de
   traiter un rapprochement comme un contrôle, se demander s'il pouvait échouer.

4. **Un extrait trié n'est pas un échantillon, c'est un extremum.** `sorted(...)[:20]` montre les
   plus petites valeurs, jamais la variété. Utiliser `sample` ou recenser la population entière.

5. **La forme n'est pas l'existence.** Un identifiant peut être parfaitement bien formé et ne
   correspondre à rien. Tester l'appartenance, pas le motif.

6. **Ne jamais normaliser un seul côté d'une comparaison symétrique.** Vérifier que le référentiel
   de référence est propre avant de s'y comparer.

7. **Mesurer le gain de chaque barreau de normalisation, en forme et en existence.** Un barreau dont
   le gain en existence est inférieur à son gain en forme fabrique de faux appariements. Le contrôle
   de laxisme est la conservation du cardinal : `nunique` avant et après.

8. **Un contrôle de type et un contrôle d'ordre sont aveugles à une inversion jour/mois.** Seule la
   distribution la révèle. Regarder la forme d'une colonne de dates, pas seulement son type.

9. **Un avertissement peut se lever là où il n'y a pas de problème et se taire sur la colonne
   fausse.** L'absence d'alerte n'est pas une validation.

10. **Distinguer systématiquement mesuré et dérivé.** Un nombre qui boucle arithmétiquement n'est pas
    un nombre compté. Le marquer, et le recompter avant toute remontée.

11. **Écrire une prédiction avant chaque exécution, et la fonder.** Les quatre gisements : les
    identités arithmétiques du problème, le sujet, le calibre des familles déjà observées, le métier.
    Quand il n'y a vraiment aucune matière, l'écrire plutôt que de fabriquer un chiffre : une
    devinette réfutée n'apprend rien.

12. **Les deux anti-jointures se comptent séparément.** Leur différence est fixée par les cardinaux,
    donc un seul des deux nombres est libre.

13. **Une jointure apparie toutes les combinaisons, pas une ligne avec une ligne.** Un doublon d'un
    seul côté suffit à dupliquer une transaction : l'excédent vaut `a + b + ab`, pas `a × b`. Avant
    toute jointure, vérifier l'unicité de la clé des deux côtés.

14. **Annoncer le dénominateur d'un taux.** Rapporté à la valeur correcte ou à la valeur affichée, le
    même écart donne deux chiffres différents. Pour un écart de réconciliation, la référence est la
    valeur correcte.

15. **Un agrégat juste peut recouvrir des lignes toutes fausses.** Des erreurs symétriques se
    compensent parfaitement au total. Un contrôle qui ne regarde que la somme valide un fichier
    intégralement faux. Le corollaire du réflexe 1, dans l'autre sens.

16. **Une décomposition doit partager une base unique et sommer au total.** Sinon le lecteur ne peut
    pas vérifier que les causes couvrent tout l'écart, ce qui est le seul intérêt de la décomposition.

17. **Un mapping par troncature n'est jamais injectif par construction.** Il peut l'être par mesure
    sur un domaine donné, ce qui est une propriété fragile, à rejouer à chaque entrée nouvelle.

18. **En pandas, l'arithmétique aligne par index, silencieusement.** `+`, `*`, `mul`, `reindex`
    travaillent sur l'index ; `isin`, `==`, `str.*` sur les valeurs de l'objet appelé. Deux Series de
    même longueur mais d'index différents ne se multiplient pas terme à terme.
