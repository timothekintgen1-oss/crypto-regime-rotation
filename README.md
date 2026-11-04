# Crypto Regime Rotation

[![Daily update](https://github.com/timothekintgen1-oss/crypto-regime-rotation/actions/workflows/daily.yml/badge.svg)](https://github.com/timothekintgen1-oss/crypto-regime-rotation/actions/workflows/daily.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
[![License: MPL 2.0](https://img.shields.io/badge/license-MPL%202.0-lightgrey)](LICENSE)

Un système de suivi de tendance sur les crypto-actifs. Chaque jour, il répond à trois questions :

1. **Régime** : faut-il être investi, ou en stablecoins ?
2. **Rotation** : si l'on est investi, faut-il surpondérer Ethereum ou Bitcoin ?
3. **Alts** : faut-il ouvrir une petite poche d'altcoins, et lesquels ?

Le moteur Python recalcule tout chaque nuit sur données réelles, publie un tableau de bord (GitHub Pages), backteste le système et mesure sa concordance avec les signaux TradingView.

> **Statut** : projet de recherche personnel. Je ne l'utilise pas pour investir en réel ; mon investissement personnel repose sur un DCA piloté par mon [indice de valorisation du Bitcoin](https://github.com/timothekintgen1-oss/btc-valuation-index). Ce n'est pas un conseil en investissement.

**Origine.** La méthode (filtre de régime, rotation ETH/BTC, poche spéculative) vient d'une formation en investissement crypto. Le système est le mien : le choix et le réglage des indicateurs, leur portage en Python, les données, les backtests, les tests de robustesse et l'automatisation.

---

## Le système

Chaque bloc est la moyenne des signaux (−1 baissier / +1 haussier) de ses indicateurs, chacun calculé sur sa propre unité de temps puis ramené en quotidien.

| Bloc | Série | Indicateurs | Règle |
|---|---|---|---|
| Régime | `CRYPTOCAP:TOTAL` (2 et 3 jours) | 10 | investi si score > +0,1, stablecoins si < −0,1, inchangé entre les deux (hystérésis) |
| Rotation | `ETHBTC` (2 jours) | 5 | ETH 80 / BTC 20 si score > 0, sinon BTC 80 / ETH 20 |
| Alts | `OTHERS.D` (3 jours) | 5 | poche autorisée si score > 0 et régime investi, au plus 20 % × force du signal |

La sélection des alts applique cinq filtres à une liste de tokens suivis (capitalisation, bêta face au BTC, tendance face au BTC, à l'ETH et en dollars) et retient ceux qui en valident au moins quatre, à poids égaux.

## Architecture

```
GitHub Actions (00:15 UTC)
  ├─ tests unitaires
  ├─ runner.py         données → régime, rotation, alts → docs/state.json
  │    ├─ data_sources.py   historiques TradingView (seed/) + mise à jour quotidienne Binance / CoinGecko
  │    ├─ indicators.py     indicateurs portés depuis leurs scripts Pine
  │    ├─ strategy.py       spécification du système et allocation
  │    ├─ alts.py           sélection des alts
  │    └─ backtest.py       courbes de performance → docs/backtest.json
  ├─ robustness.py     tests de robustesse → docs/robustness.json
  └─ commit des résultats

docs/index.html        tableau de bord (GitHub Pages), lit les JSON
tradingview/           le même système en Pine Script, avec envoi des signaux par webhook
relay/                 Cloudflare Worker qui reçoit ces signaux et les expose au tableau de bord
```

## Ce que j'ai vérifié

**Aucune donnée future.** Les tests unitaires modifient les bougies après une date donnée et vérifient qu'aucun signal antérieur ne change, pour chacun des trois blocs. Dans les backtests, chaque signal est appliqué avec un jour de retard.

**Un biais trouvé et corrigé.** Ma première réplique Python faisait deux fois mieux que les résultats de référence sur la même période. En l'auditant, j'ai trouvé que TradingView date chaque bougie à son ouverture : associées à des prix de clôture, les bougies de 2 jours donnaient au backtest un jour d'avance sur le marché. Une fois les bougies redatées à leur clôture (`data_sources._label_at_close`, testé), les résultats rejoignent la référence : même Sharpe, même pire baisse.

**Robustesse** (`robustness.py`, historique réel de 2018 à mi-2026, système sans alts) :

| | Système | BTC conservé |
|---|---|---|
| Rendement annualisé | 43 % | 18 % |
| Sharpe | 1,0 | 0,6 |
| Pire baisse | −61 % | −81 % |
| Sharpe 2018–2021 | 1,38 | |
| Sharpe 2022–2026 | 0,52 | |

- **Réglages** : 60 variantes avec chaque paramètre déplacé de ±25 % au hasard. Les réglages actuels tombent au 40ᵉ centile : le résultat ne dépend pas d'un réglage chanceux.
- **Exécution** : multiplier les frais par 5 coûte peu (Sharpe 1,0 → 0,95) ; exécuter avec deux bougies de retard au lieu d'une coûte davantage (Sharpe → 0,84). Le délai d'exécution compte.
- **Indicateurs** : retirer n'importe lequel des 10 indicateurs du bloc régime améliore légèrement le Sharpe, et la plupart des sous-ensembles de 5 indicateurs font au moins aussi bien. Le bloc régime est redondant : c'est la prochaine simplification.
- **Dans le temps** : la performance est nettement plus faible depuis 2022, et le système reste derrière le BTC en 2023 et 2024.

**Concordance avec TradingView.** `strategy.reciprocity()` compare les signaux recalculés en Python aux relevés TradingView de `seed/parity.csv`. L'échantillon est encore petit (4 sur 5 concordants).

## Limites

- C'est un backtest : il ne garantit rien sur la suite, et la performance a nettement baissé depuis 2022.
- La liste d'alts suivis est celle d'aujourd'hui : le backtest de la poche alts est optimiste (biais du survivant).
- La capitalisation totale de CoinGecko n'a pas exactement le même univers que `CRYPTOCAP` de TradingView ; un trou dans les exports TradingView (juillet à septembre 2026) a été reconstitué à partir des prix Binance.
- L'indicateur Z-Score Deviation Fusion est protégé sur TradingView : il est remplacé par un z-score standard.

## Lancer en local

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v   # tests
python runner.py                          # calcul du jour, écrit state/ et docs/
python robustness.py                      # tests de robustesse (quelques minutes)
python -m http.server -d docs 8000        # tableau de bord sur http://localhost:8000
```

La mise en place des scripts TradingView et du relais est décrite dans [tradingview/README.md](tradingview/README.md).

## Indicateurs tiers

Les indicateurs sont des scripts TradingView publics, publiés par leurs auteurs sous licence Mozilla Public License 2.0. Ce dépôt les réutilise (Pine) et les porte en Python (`indicators.py`), avec leur crédit en tête de chaque section :

| Indicateur | Auteur |
|---|---|
| Elliott Wave Oscillator | Koryu |
| Sebastine Trend Catcher | sebastinecc |
| DFT Overlay | wbburgin (noyaux : jdehorty/KernelFunctions) |
| Trend Change Indicator | QuantitativeAlpha |
| DEGA RMA | QuantEdgeB |
| LNL Trend System | lnlcapital |
| Trend Strength Gauge | VanHe1sing |
| Kalman Hull Supertrend | BackQuant |
| MA Band Distance Monitor | HasanRifat |
| 4-Colored EMA Difference & Stochastic Traffic Light | shalsak |
| WonderTrend | accutrades_net |
| Adaptive Gaussian Moving Average | LeafAlgo |
| Z-Score Deviation Fusion (code protégé, remplacé par un proxy) | RAKIQUANT |

## Licence

[Mozilla Public License 2.0](LICENSE), la licence des scripts dont dérivent les indicateurs.
