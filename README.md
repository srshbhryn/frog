# 🐸 Frog

**Frog** is an algorithmic *pair‑trading* system for crypto markets on the
[Nobitex](https://nobitex.ir) exchange, together with **Tadpoles**, a research /
backtesting toolkit for collecting market data and simulating trading strategies.

The repository is split into two complementary halves:

| Package | Role | Persistence |
| --- | --- | --- |
| **`frog/`** | The *live* trading engine — a set of microservices that watch the market, store trades, compute regressions, run the strategy and place orders. | SQLite (via Django ORM) |
| **`tadpoles/`** | The *offline* research layer — historical candle/trade collectors, price oracles and strategy simulators. | TimescaleDB (PostgreSQL) |

Both share a small common core in `frog/types` (money types, assets, pairs) and
`frog/utils` (serialization helpers).

> ⚠️ **Disclaimer.** This is experimental quantitative‑trading software that
> places real orders against a real exchange when configured to do so. It is
> provided for research and educational purposes. Trading carries substantial
> financial risk. Use the paper‑trading (`nobifake`) order manager until you
> fully understand the behaviour, and never run it with funds you cannot afford
> to lose.

---

## Table of contents

- [Concepts](#concepts)
- [Architecture](#architecture)
  - [The message bus ("highway")](#the-message-bus-highway)
  - [Services](#services)
  - [The RPC layer](#the-rpc-layer-frogsquare)
  - [Serialization & money types](#serialization--money-types)
- [The trading strategy](#the-trading-strategy)
- [Tadpoles — research & backtesting](#tadpoles--research--backtesting)
- [Getting started](#getting-started)
  - [Requirements](#requirements)
  - [Local environment](#local-environment)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Running services manually](#running-services-manually)
- [Data collection & simulation scripts](#data-collection--simulation-scripts)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Development](#development)
- [Glossary](#glossary)

---

## Concepts

Frog trades **pairs of correlated assets** (e.g. BTC and ETH) using a
*mean‑reversion* approach often called **statistical arbitrage** or **pair
trading**:

1. Two assets that historically move together (the **long asset** and the
   **short asset**) are continuously regressed against each other to estimate a
   linear relationship `long ≈ alpha + beta · short`.
2. At any moment we compute the **residual** — how far the current price
   relationship has drifted from that fitted line.
3. When the residual exceeds a configurable **threshold**, the relationship is
   assumed to be temporarily mispriced and will *revert*. Frog opens an
   offsetting position: it goes short on the asset that is relatively expensive
   and long on the asset that is relatively cheap, sized so the two legs are
   beta‑neutral.
4. Orders carry a **wait period**; if they are not filled in time they are
   cancelled.

The exchange under the hood is **Nobitex**, an Iranian exchange whose quote
currencies are **RLS** (Iranian Rial — internally called `IRT` on some of
Nobitex's endpoints) and **USDT**.

---

## Architecture

Frog is a **collection of small, single‑purpose processes** that communicate
exclusively over a ZeroMQ message bus. There is no shared in‑memory state and no
direct service‑to‑service socket: everything flows through the bus, either as
fire‑and‑forget **pub/sub events** or as **request/response RPC** built on top of
pub/sub.

```
                         ┌──────────────────────────────────────────┐
                         │                 highway                   │
                         │   ZeroMQ XSUB(:1213)  ⇄  XPUB(:1214)       │
                         │         (a zmq.proxy message bus)          │
                         └──────────────────────────────────────────┘
        publishes ▲  ▲  ▲                                  │ subscribes
                  │  │  │                                  ▼
   ┌──────────────┴┐ │ ┌┴───────────────┐      ┌───────────────────────┐
   │  orderbook    │ │ │ tradecollector │      │  eye (strategy cores)  │
   │ (bookwatch)   │ │ │                │      │  N× Eye processes      │
   │ order_<pair>  │ │ │ trade_<pair>   │      └───────────────────────┘
   └───────────────┘ │ └───────┬────────┘            │ RPC calls
                     │         │ trade_<pair>         ▼
                     │         ▼              ┌──────────────────────────┐
                     │  ┌─────────────┐       │ analyst   (topic: ptreg) │
                     │  │ tradestore  │       │ price_svc (topic: prices)│
                     │  │  SQLite     │◀──────│ nobitex / nobifake  OMS  │
                     │  └─────────────┘  RPC  └──────────────────────────┘
                     │                                  │ fill_<account>
                     │  ┌─────────────┐                 │ oms_account_<oms>
                     └─▶│  guardian   │◀────────────────┘
                        │ (P&L log)   │
                        └─────────────┘
```

### The message bus ("highway")

[`bin/highway.py`](bin/highway.py) is a tiny ZeroMQ `XPUB`/`XSUB` proxy. Every
other process connects to it:

- **Publishers** connect to the `XSUB` port (default **1213**, `HIGHWAY_XSUB_PORT`).
- **Subscribers** connect to the `XPUB` port (default **1214**, `HIGHWAY_XPUB_PORT`).

This makes the topology a classic broker‑based pub/sub: services don't know
about each other, they only know topics.

**Topic conventions** (all multipart ZeroMQ messages, payloads encoded with the
custom msgpack codec):

| Topic prefix | Published by | Payload |
| --- | --- | --- |
| `order_<pair>` | `orderbook` | `Book` (order‑book snapshot: bids/asks) |
| `trade_<pair>` | `tradecollector` | `Trade` (executed market trade) |
| `fill_<account>` | OMS | `Fill` (a fill for an account's order) |
| `oms_account_<oms>` | OMS | `Account` (balance snapshot, every ~10 s) |
| `service_<name>` | RPC clients | RPC request envelope |
| `REMINDER` | local timers | in‑process scheduled callbacks |

[`frog/utils/listener.py`](frog/utils/listener.py) provides a `Listener`
abstraction that subscribes to a set of topics on a background thread, pushes
events onto a queue, and can inject delayed `Reminder` events via
`threading.Timer` (used by the strategy to schedule order cancellations).

### Services

Each service has a thin entry point in [`bin/`](bin/) that configures logging and
launches the implementation living under [`frog/`](frog/).

| Entry point | Module | Responsibility |
| --- | --- | --- |
| [`bin/highway.py`](bin/highway.py) | — | The ZeroMQ broker that all other processes attach to. |
| [`bin/orderbook.py`](bin/orderbook.py) | [`frog/bookwatch`](frog/bookwatch) | Polls Nobitex's `/v2/orderbook/all` once a second, deduplicates unchanged books, and publishes `order_<pair>` snapshots. |
| [`bin/tradecollector.py`](bin/tradecollector.py) | [`frog/tradecollector`](frog/tradecollector) | Async (Tornado) poller of Nobitex `/v2/trades/<symbol>`; deduplicates and publishes `trade_<pair>` events. |
| [`bin/tradestore.py`](bin/tradestore.py) | [`frog/tradestore`](frog/tradestore) | Subscribes to `trade_` and persists every trade into a SQLite DB through the Django ORM. |
| [`bin/price_service.py`](bin/price_service.py) | [`frog/tradestore`](frog/tradestore) (`rpc`) | RPC service `prices`: serves volume‑weighted prices and per‑minute price series computed from stored trades. |
| [`bin/analyst.py`](bin/analyst.py) | [`frog/analyst`](frog/analyst) | RPC service `ptreg`: fits a linear regression (`alpha`, `beta`, price normalizers) between two pairs over a time window. Results are LRU‑cached. |
| [`bin/nobitex_oms.py`](bin/nobitex_oms.py) | [`frog/ordermanager/nobitex`](frog/ordermanager/nobitex) | **Live** order management — places/cancels orders against Nobitex margin *positions*, tracks fills and per‑account balances. |
| [`bin/nobifake_oms.py`](bin/nobifake_oms.py) | [`frog/ordermanager/nobifake`](frog/ordermanager/nobifake) | **Paper‑trading** OMS — simulates fills from the live `trade_`/`order_` streams instead of touching the exchange. Same RPC interface as the real OMS. |
| [`bin/eye.py`](bin/eye.py) | [`frog/cores/eye`](frog/cores/eye) | The strategy core. Spawns a grid of `Eye` processes, each an independent pair‑trading bot with its own config (regression length, threshold, asset pair, quote, trade size). |
| [`bin/guardian.py`](bin/guardian.py) | [`frog/ordermanager/guardian`](frog/ordermanager/guardian) | Subscribes to `oms_account_` and `order_` and logs each account's mark‑to‑market value in both USDT and RLS. |

### The RPC layer (`frog/square`)

[`frog/square/rpc.py`](frog/square/rpc.py) implements request/response semantics
on top of the pub/sub bus.

- A **service** subclasses `RpcService`, declares a `topic`, and registers
  methods with the `@RpcService.register` decorator. `run_server()` spins up a
  pool of worker threads (`concurrency`, default 4) behind a ZeroMQ `DEALER`
  socket; it subscribes to its topic on `XPUB`, dispatches calls, and publishes
  responses on `XSUB`.
- A **client** subclasses `RpcClient` and declares service instances as class
  attributes. Each registered method becomes a blocking call that serializes its
  arguments, publishes a request keyed by a per‑client identity, and waits on a
  response queue. The `client_identity` is automatically threaded through to
  methods that accept `**kwargs`, so an OMS knows which account placed an order.

Example client (from the strategy core):

```python
class Client(RpcClient):
    analyst        = analyst_rpc.Service()
    trade_store    = tradestore_rpc.Service()
    nobitex_client = nobitex_rpc.Service()

# later:
regression = client.analyst.get_regression(long_pair, short_pair, start, end)
price      = client.trade_store.get(long_pair, end_time)
order_id   = client.nobitex_client.place_order(pair, side, amount, price)
```

| RPC service | Topic | Key methods |
| --- | --- | --- |
| Price service | `prices` | `get(pair, timestamp)`, `get_timerange_price(pair, start, end)` |
| Analyst | `ptreg` | `get_regression(long_pair, short_pair, start, end)` |
| Order managers | `nobitex` / `nobifake` | `place_order(...)`, `cancel_order(id)`, `get_order(id)` |

### Serialization & money types

- [`frog/utils/msgpack.py`](frog/utils/msgpack.py) is a thin wrapper over
  [`msgpack`](https://msgpack.org) with an extension‑type registry. Decorate a
  slotted dataclass with `@msgpack.dataclass` (or subclass `msgpack.Enum`) and it
  becomes wire‑serializable. Custom encoders/decoders are registered for
  `datetime` and `Decimal`.
- [`frog/types/_money.py`](frog/types/_money.py) defines `Price`, `Amount` and
  `Value` — `Decimal`‑backed money types quantized to 16 decimal places. They
  carry dimensional semantics: `Price · Amount = Value`, `Value / Amount = Price`,
  `Value / Price = Amount`. This prevents accidentally adding a price to a
  quantity.
- [`frog/types/__init__.py`](frog/types/__init__.py) defines the core domain
  vocabulary: `Asset` (RLS, USDT, BTC, ETH, DOGE, SHIB, TON, FTM, BNB, SOL,
  PAXG), `Pair` (`base`/`quote`), `Side` (LONG/SHORT, with negation), `OrderBook`,
  `PriceAmountPair` and `Regression`.

---

## The trading strategy

The strategy lives in [`frog/cores/eye/_main.py`](frog/cores/eye/_main.py) and is
modelled as an **event‑driven state machine** per `Eye` instance.

**State.** Each `Eye` tracks whether it currently has an open order on the long
leg, the short leg, both, or neither (`NN`, `YN`, `NY`, `YY`).

**Event loop.** The `Eye` subscribes to three topics — the long pair's order
book, the short pair's order book, and its own account fills — plus internal
reminders. It then reacts:

- **Flat (`NN`) + order‑book tick → `CheckResidual`.** It asks the price service
  for the latest VWAP of both legs and the analyst for the regression over the
  last `regression_len` minutes, then computes:

  ```
  residual = long_price / long_normalizer
             - alpha
             - beta · (short_price / short_normalizer)
  ```

  If `|residual| <= trade_threshold`, do nothing. Otherwise, enqueue two
  `PlaceOrder` actions sized so the short leg is scaled by `beta`
  (beta‑neutral), with prices nudged by `pricing_factor`. The sign of the
  residual decides which leg is sold and which is bought.

- **Order placed → reminder.** Every placed order schedules a `CancelOrder`
  reminder after `wait_period`, so stale unfilled orders are cleaned up.

- **Fill event → `UpdateOrderFill`.** Accumulates filled amount; when an order
  is fully filled, the corresponding leg transitions back toward flat.

**Grid search.** [`bin/eye.py`](bin/eye.py) doesn't run a single bot — it
constructs a **Cartesian grid** of configs (regression lengths × thresholds ×
asset pairs × quote currencies) and launches each as its own daemon process via
`multiprocessing`. This lets many parameterizations trade in parallel (against
the paper OMS by default) so their behaviour can be compared from the logs.

> By default `bin/eye.py` wires its `Client` to the **nobifake** (paper) OMS via
> `frog.ordermanager.nobifake`. Point it at `frog.ordermanager.nobitex` to trade
> live.

---

## Tadpoles — research & backtesting

`tadpoles/` is an independent research stack built on **TimescaleDB** (a
PostgreSQL extension for time‑series). It does not depend on the live message
bus; it reuses `frog`'s money/asset types.

- [`tadpoles/timescaledb`](tadpoles/timescaledb) — SQLAlchemy engine/session
  factory pointed at `timescaledb://db:db@127.0.0.1:5477/db`.
- [`tadpoles/prices/models.py`](tadpoles/prices/models.py) — hypertable models:
  `Candle` (multi‑exchange OHLC candles), `BinanceCandle` / `BinanceCandleFile`
  (Binance kline imports), and `Trade`.
- [`tadpoles/prices/oracle.py`](tadpoles/prices/oracle.py) — `Oracle`, a
  per‑(exchange, pair) price reader: point‑in‑time prices, min/max over a range,
  price series, and minute returns (as NumPy arrays).
- [`tadpoles/prices/utils.py`](tadpoles/prices/utils.py) — candle/price loaders
  that **fill missing minutes** by linear interpolation (so simulators see a
  gap‑free series) and report how many points were missing.
- [`tadpoles/railer`](tadpoles/railer) — `simulation_zero`, a cross‑exchange
  arbitrage simulator that walks two exchanges' price series and trades when the
  ratio crosses configurable thresholds. Results are persisted to the `SimZero`
  hypertable. `SimParams` / `SimResult` / `SimPriceQuality` describe the run.
- [`tadpoles/pairtrading`](tadpoles/pairtrading) — a richer pair‑trading
  backtester: `regression.py` (alpha/beta via `scipy`), `pairtrading.py`
  (`PairTradingSimulation`), and `Algorithm`/`Result` entities.
- [`tadpoles/types.py`](tadpoles/types.py) — the `Exchange` enum (Wallex,
  Ompfinex, Nobitex).

`Exchange` candle data is sourced from Wallex / Ompfinex UDF endpoints and from
Binance's public data dumps; Nobitex trades captured live can be migrated in via
[`scripts/move_frog_tradestore_data_to_timescaledb.py`](scripts/move_frog_tradestore_data_to_timescaledb.py).

---

## Getting started

### Requirements

- **Python 3.10** (the Docker image uses `python:3.10-slim`).
- A running **ZeroMQ** broker — provided by the `highway` service.
- **TimescaleDB / PostgreSQL** for the Tadpoles research layer (provided by the
  `timescaledb` service in `docker-compose.yml`).
- A **Nobitex API token** if you want to collect live data or trade for real.

Python dependencies are pinned in [`requirements.txt`](requirements.txt)
(`pyzmq`, `msgpack`, `Django`, `numpy`, `scipy`, `SQLAlchemy`,
`sqlalchemy-timescaledb`, `tornado`, `requests`, `psycopg2`, plus tooling).

> Note: the analyst service imports `scikit-learn` (`sklearn.linear_model`). If
> you run the analyst, install `scikit-learn` in addition to the pinned
> requirements.

### Local environment

A convenience shell snippet is provided in [`source`](source):

```bash
# load env vars from .local.env and put the repo on PYTHONPATH
source ./source        # defines an `activate`-style block
```

It exports the variables from `.local.env` (copy it from
[`.local.env.example`](.local.env.example) and set `NOBITEX_TOKEN`), sets `PYTHONPATH=$(pwd)` and
`PYTHONHASHSEED=0` (deterministic hashing is required because the msgpack codec
keys extension types on `hash(type_name)`).

Typical manual setup:

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install scikit-learn        # needed by the analyst

cp .local.env.example .local.env   # then set NOBITEX_TOKEN
set -a; source .local.env; set +a
export PYTHONPATH=$(pwd)
export PYTHONHASHSEED=0
```

### Running with Docker Compose

The full live stack is described in
[`docker-compose.yml`](docker-compose.yml). It builds a single `frog_image` and
runs each service as its own container, plus a TimescaleDB instance.

```bash
docker compose build
docker compose up        # starts highway, orderbook, tradecollector,
                         # tradestore, price_service, analyst, nobifake,
                         # eye, guardian and timescaledb
```

Services share `ENV=PROD`, `LOG_LEVEL=INFO`, `PYTHONHASHSEED=0`. In `PROD` mode
`frog/config.py` writes SQLite data to `/data/` (mounted from `./data`).

> The compose file runs the **paper** OMS (`nobifake`) by default — no live
> orders. The live `nobitex_oms` is intentionally not wired in.

### Running services manually

With the environment activated, start the broker first, then any combination of
services (order matters only in that everything needs `highway`):

```bash
python bin/highway.py          # 1. message bus (start this first)
python bin/orderbook.py        # 2. order-book snapshots
python bin/tradecollector.py   # 3. live trades
python bin/tradestore.py       # 4. persist trades to SQLite
python bin/price_service.py    # 5. price RPC
python bin/analyst.py          # 6. regression RPC
python bin/nobifake_oms.py     # 7. paper order manager
python bin/eye.py              # 8. strategy grid
python bin/guardian.py         # 9. P&L monitor
```

---

## Data collection & simulation scripts

The [`scripts/`](scripts/) directory holds standalone research utilities (run
with the Tadpoles / TimescaleDB stack up):

| Script | Purpose |
| --- | --- |
| [`collect_candles.py`](scripts/collect_candles.py) | Fetch OHLC candles from Wallex / Ompfinex UDF history endpoints into the `Candle` hypertable. |
| [`collect_binance_candles.py`](scripts/collect_binance_candles.py) | Download Binance public kline dumps and load them into `BinanceCandle`. |
| [`fix_missing_candles_data.py`](scripts/fix_missing_candles_data.py) | Detect and (optionally) backfill gaps in the candle series. |
| [`fix_missing_binance_candles.py`](scripts/fix_missing_binance_candles.py) | Same idea for the Binance candle tables. |
| [`run_simulation_000.py`](scripts/run_simulation_000.py) | Parallel grid of cross‑exchange arbitrage simulations (`simulation_zero`), persisted to `SimZero`. |
| [`run_simulation_001.py`](scripts/run_simulation_001.py) | A single‑exchange market‑making / grid simulation `Core`. |
| [`move_frog_tradestore_data_to_timescaledb.py`](scripts/move_frog_tradestore_data_to_timescaledb.py) | Migrate trades captured by the live `tradestore` (SQLite) into the TimescaleDB `Trade` table. |
| [`draw_residuals.py`](scripts/draw_residuals.py) | Plot regression residuals between two assets with `matplotlib` (visual sanity check of the pair‑trading signal). |

---

## Configuration

Configuration is environment‑variable driven, read in
[`frog/config.py`](frog/config.py). Defaults live in [`.local.env.example`](.local.env.example);
copy it to `.local.env`, which git ignores.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENV` | `DEV` | `PROD` switches `DATA_DIR` to `/data/` and raises the default log level. |
| `LOG_LEVEL` | `DEBUG` (dev) / `INFO` (prod) | Python logging level. |
| `HIGHWAY_HOST` | `highway` (or `127.0.0.1` locally) | Hostname of the ZeroMQ broker. |
| `HIGHWAY_XSUB_PORT` | `1213` | Broker port that publishers connect to. |
| `HIGHWAY_XPUB_PORT` | `1214` | Broker port that subscribers connect to. |
| `NOBITEX_TOKEN` | — | API token for live Nobitex requests. |
| `NOBITEX_LEVERAGE` | `1` | Margin leverage for the live OMS. |
| `PYTHONHASHSEED` | `0` | **Must be fixed** — the msgpack codec hashes type names. |

The strategy parameters themselves (regression length, thresholds, asset pairs,
quote currencies, trade sizes, wait period) are defined as the grid in
[`bin/eye.py`](bin/eye.py) and the `EyeConfig` dataclass.

PostgreSQL tuning for the analysis DB lives in
[`configs/analysisdb/`](configs/analysisdb/) and is applied on first container
init.

---

## Project layout

```
frog/                        # Live trading engine
├── config.py                # env-driven configuration & ALL_PAIRS
├── square/rpc.py            # pub/sub-based RPC framework
├── types/                   # Asset, Pair, Side, Regression, money types
├── utils/                   # msgpack codec, Listener, shortcuts
├── bookwatch/               # order-book poller  → order_<pair>
├── tradecollector/          # trade poller       → trade_<pair>
├── tradestore/              # Django/SQLite trade store + price RPC
├── analyst/                 # linear-regression RPC (ptreg)
├── ordermanager/
│   ├── types.py             # OrderManger base, Account/Position/Fill
│   ├── nobitex/             # live exchange OMS
│   ├── nobifake/            # paper-trading OMS
│   └── guardian/            # account P&L monitor
└── cores/eye/               # the pair-trading strategy state machine

tadpoles/                    # Research & backtesting (TimescaleDB)
├── timescaledb/             # SQLAlchemy engine/session
├── types.py                 # Exchange enum
├── prices/                  # candle/trade models, Oracle, gap-filling
├── railer/                  # simulation_zero cross-exchange simulator
├── pairtrading/             # pair-trading backtester + regression
└── indices/                 # (placeholder)

bin/                         # Service entry points (one per process)
scripts/                     # Data collection & simulation utilities
configs/                     # TimescaleDB / pg tuning
tests/                       # pytest suite
docker-compose.yml           # Full live stack + TimescaleDB
Dockerfile                   # python:3.10-slim image
```

---

## Development

The project is configured for a strict linting/typing workflow in
[`pyproject.toml`](pyproject.toml):

```bash
# tests
pytest

# type checking
mypy frog tadpoles

# lint (ruff is configured with a very broad rule set)
ruff check .

# formatting (black, single-quote-preserving) and import sorting (isort)
black .
isort .
```

Notable conventions:

- **Single quotes** for inline strings, double quotes for docstrings (`ruff`
  `flake8-quotes`).
- `black` runs with `skip-string-normalization` so quote style is preserved.
- `isort` uses the `black` profile.
- Wire‑serializable types are **slotted dataclasses** decorated with
  `@msgpack.dataclass`, or enums subclassing `msgpack.Enum`.
- `PYTHONHASHSEED=0` everywhere, because the serializer identifies types by
  `hash(type_name)` and that hash must be stable across processes.

Tests live under [`tests/`](tests/) and cover the msgpack codec, the listener,
the regression helper, and the price oracle. Some oracle tests depend on
previously collected candle data being present in TimescaleDB.

---

## Glossary

| Term | Meaning |
| --- | --- |
| **highway** | The central ZeroMQ XPUB/XSUB proxy that all services talk through. |
| **eye** | One instance of the pair‑trading strategy state machine. |
| **bookwatch** | Service that polls and republishes order books. |
| **OMS** | Order Management System (`nobitex` = live, `nobifake` = paper). |
| **guardian** | Watchdog that reports per‑account mark‑to‑market value. |
| **residual** | Deviation of the current price relationship from the fitted regression line; the trading signal. |
| **alpha / beta** | Intercept and slope of the long‑vs‑short regression; `beta` also sizes the hedge. |
| **tadpole** | A research/backtesting component (vs. `frog`, the live engine). |
| **RLS / IRT** | Iranian Rial (Nobitex uses `IRT` on some endpoints; Frog uses `RLS` internally). |
```
