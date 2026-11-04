# TradingView et relais de signaux

`regime_rotation.pine` calcule le système complet directement dans TradingView, à partir du code original des scripts publics, et envoie chaque bloc au relais à la clôture de sa bougie. Le tableau de bord affiche alors les signaux TradingView (badge **TV**) à la place de ceux du moteur Python (**Py**).

```
TradingView (1 script, 1 alerte) ──webhook──▶ relais Cloudflare (relay/) ──▶ tableau de bord
                                                      │
                          mise à jour GitHub quotidienne ┘ archive et compare au moteur Python
```

## Installer le script

1. Ouvrir un graphique `CRYPTOCAP:TOTAL` en unité **1 jour**.
2. Éditeur Pine → nouvel indicateur → coller `regime_rotation.pine` → enregistrer → ajouter au graphique.

Le script récupère lui-même ETHBTC, OTHERS.D et les unités de 2 jours, 3 jours et hebdomadaire. Le graphique est en 1 jour parce que toutes ces bougies se clôturent un jour donné : chaque bloc est envoyé le jour même de sa clôture. Le délai d'exécution compte (voir le test de robustesse).

## Créer l'alerte

1. Alerte → condition : `Crypto Regime Rotation` → **Any alert() function call**.
2. Expiration : illimitée.
3. Notifications → **Webhook URL** : l'adresse `/hook/<SECRET>` du relais (le secret n'est pas versionné).

## Z-Score Deviation Fusion

Cet indicateur (RAKIQUANT) est protégé : son code n'est pas public. Il est remplacé par un z-score standard. Pour utiliser l'original sur le bloc régime : graphique TOTAL en 2 jours, ajouter Z-Score Deviation Fusion, puis cocher « utiliser le vrai Z-Score » dans les paramètres du script et choisir sa sortie dans **Source Z-Score**.

## Vérifier

- `GET /state` sur le relais : état combiné reçu de TradingView.
- `GET /log` : dernières alertes reçues.
- Chaque nuit, la mise à jour GitHub ajoute les états TradingView à `seed/parity.csv`, ce qui alimente la mesure de concordance du moteur Python.

`relay_manual.pine` permet de brancher ses propres instances d'indicateurs une par une, à la place du script tout-en-un.
