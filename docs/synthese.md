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
| 1 | Réconciliation front / back office | en cours, questions 1 et 2 tranchées sur 8 |
| 2 à 6 | Position, courbes, volumes, spot, restitution | non ouvertes |

Deux points laissés ouverts en Mission 0 : le verdict sur les 899 sites sans contrat, et les
familles 3 et 4 d'anomalies du référentiel, jamais identifiées.

## Référentiel

| Table | Lignes | Clé primaire | Historisation |
|---|---|---|---|
| `ref_customer` | **220** | `customer_id` | non, état courant |
| `ref_site` | **1 400** | `site_id` | non, état courant |
| `ref_contract` | **260** | `contract_id` | oui, contrats successifs |

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
