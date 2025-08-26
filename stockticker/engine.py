from __future__ import annotations

import enum
import json
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional


class StockSymbol(enum.Enum):
	GOLD = 0
	SILVER = 1
	BONDS = 2
	OIL = 3
	INDUSTRIALS = 4
	GRAIN = 5

	@staticmethod
	def all_symbols() -> List["StockSymbol"]:
		return [
			StockSymbol.GOLD,
			StockSymbol.SILVER,
			StockSymbol.BONDS,
			StockSymbol.OIL,
			StockSymbol.INDUSTRIALS,
			StockSymbol.GRAIN,
		]

	def display_name(self) -> str:
		return {
			StockSymbol.GOLD: "Gold",
			StockSymbol.SILVER: "Silver",
			StockSymbol.BONDS: "Bonds",
			StockSymbol.OIL: "Oil",
			StockSymbol.INDUSTRIALS: "Industrials",
			StockSymbol.GRAIN: "Grain",
		}[self]


class DieAction(enum.Enum):
	UP = "Up"
	DOWN = "Down"
	DIVIDEND = "Dividend"


STEP_VALUES_CENTS: Tuple[int, int, int] = (5, 10, 20)
START_PRICE_CENTS: int = 100
SPLIT_PRICE_CENTS: int = 200
BANKRUPT_PRICE_CENTS: int = 0
BLOCK_SIZES: Tuple[int, ...] = (500, 1000, 2000, 5000)


@dataclass
class StockState:
	symbol: StockSymbol
	price_cents: int = START_PRICE_CENTS

	def as_display_price(self) -> str:
		return f"${self.price_cents / 100:.2f}"


@dataclass
class Player:
	name: str
	cash_cents: int
	holdings: Dict[StockSymbol, int] = field(default_factory=dict)

	def total_net_worth_cents(self, market: Dict[StockSymbol, StockState]) -> int:
		portfolio_cents = 0
		for sym, shares in self.holdings.items():
			portfolio_cents += shares * market[sym].price_cents
		return self.cash_cents + portfolio_cents

	def ensure_holding_key(self, symbol: StockSymbol) -> None:
		if symbol not in self.holdings:
			self.holdings[symbol] = 0


@dataclass
class GameConfig:
	starting_cash_cents: int = 5000 * 100
	trading_interval_rolls: int = 1  # After how many rolls to open a trading phase
	block_sizes: Tuple[int, ...] = BLOCK_SIZES
	seed: Optional[int] = None


@dataclass
class GameState:
	players: List[Player]
	market: Dict[StockSymbol, StockState]
	config: GameConfig = field(default_factory=GameConfig)
	roll_count: int = 0
	last_roll: Optional[Tuple[StockSymbol, DieAction, int]] = None
	in_trading_phase: bool = True
	log: List[str] = field(default_factory=list)

	@staticmethod
	def new_game(player_names: List[str], config: Optional[GameConfig] = None) -> "GameState":
		cfg = config or GameConfig()
		if cfg.seed is not None:
			random.seed(cfg.seed)
		players = [
			Player(name=n.strip(), cash_cents=cfg.starting_cash_cents) for n in player_names if n.strip()
		]
		market = {sym: StockState(symbol=sym) for sym in StockSymbol.all_symbols()}
		state = GameState(players=players, market=market, config=cfg)
		state.log.append("New game created. Players: " + ", ".join(p.name for p in players))
		return state

	def rolls_until_next_trading(self) -> Optional[int]:
		interval = self.config.trading_interval_rolls
		if interval <= 0:
			return None
		rem = interval - (self.roll_count % interval)
		return 0 if rem == interval else rem

	def roll_dice(self) -> Tuple[StockSymbol, DieAction, int]:
		stock = random.choice(StockSymbol.all_symbols())
		action = random.choice([DieAction.UP, DieAction.DOWN, DieAction.DIVIDEND])
		amount_cents = random.choice(STEP_VALUES_CENTS)
		return stock, action, amount_cents

	def apply_roll(self, roll: Optional[Tuple[StockSymbol, DieAction, int]] = None) -> None:
		if roll is None:
			roll = self.roll_dice()
		stock, action, amount_cents = roll
		self.last_roll = roll

		stock_state = self.market[stock]
		before = stock_state.price_cents

		if action == DieAction.UP:
			stock_state.price_cents += amount_cents
			self.log.append(f"Roll: {stock.display_name()} Up {amount_cents}¢ => {before/100:.2f} -> {stock_state.price_cents/100:.2f}")
			self._check_split(stock)
		elif action == DieAction.DOWN:
			stock_state.price_cents -= amount_cents
			self.log.append(f"Roll: {stock.display_name()} Down {amount_cents}¢ => {before/100:.2f} -> {stock_state.price_cents/100:.2f}")
			self._check_bankrupt(stock)
		elif action == DieAction.DIVIDEND:
			self._pay_dividend(stock, amount_cents)
		else:
			raise ValueError("Unknown die action")

		self.roll_count += 1
		if self.config.trading_interval_rolls > 0 and (self.roll_count % self.config.trading_interval_rolls == 0):
			self.in_trading_phase = True
			self.log.append("Trading phase opened.")

	def _check_split(self, symbol: StockSymbol) -> None:
		stk = self.market[symbol]
		if stk.price_cents >= SPLIT_PRICE_CENTS:
			for p in self.players:
				p.ensure_holding_key(symbol)
				if p.holdings[symbol] > 0:
					p.holdings[symbol] *= 2
			self.log.append(f"Split: {symbol.display_name()} split at ${stk.price_cents/100:.2f}. Shares doubled for holders; price reset to $1.00")
			stk.price_cents = START_PRICE_CENTS

	def _check_bankrupt(self, symbol: StockSymbol) -> None:
		stk = self.market[symbol]
		if stk.price_cents <= BANKRUPT_PRICE_CENTS:
			for p in self.players:
				p.ensure_holding_key(symbol)
				if p.holdings[symbol] > 0:
					p.holdings[symbol] = 0
			self.log.append(f"Bankrupt: {symbol.display_name()} hit $0.00. All shares lost; price reset to $1.00")
			stk.price_cents = START_PRICE_CENTS

	def _pay_dividend(self, symbol: StockSymbol, amount_cents: int) -> None:
		stk = self.market[symbol]
		if stk.price_cents >= START_PRICE_CENTS:
			paid_total = 0
			for p in self.players:
				shares = p.holdings.get(symbol, 0)
				if shares > 0:
					p.cash_cents += amount_cents * shares
					paid_total += amount_cents * shares
			self.log.append(
				f"Dividend: {symbol.display_name()} pays {amount_cents}¢/share; total paid ${paid_total/100:.2f}"
			)
		else:
			self.log.append(
				f"Dividend: {symbol.display_name()} below $1.00, no dividend paid"
			)

	def can_trade_block(self, shares: int) -> bool:
		return shares in self.config.block_sizes

	def buy(self, player_index: int, symbol: StockSymbol, shares: int) -> bool:
		if not self.can_trade_block(shares):
			return False
		player = self.players[player_index]
		price = self.market[symbol].price_cents
		cost = price * shares
		if player.cash_cents < cost:
			return False
		player.cash_cents -= cost
		player.ensure_holding_key(symbol)
		player.holdings[symbol] += shares
		self.log.append(
			f"Trade: {player.name} bought {shares} {symbol.display_name()} @ ${price/100:.2f} for ${cost/100:.2f}"
		)
		return True

	def sell(self, player_index: int, symbol: StockSymbol, shares: int) -> bool:
		if not self.can_trade_block(shares):
			return False
		player = self.players[player_index]
		player.ensure_holding_key(symbol)
		if player.holdings[symbol] < shares:
			return False
		price = self.market[symbol].price_cents
		proceeds = price * shares
		player.holdings[symbol] -= shares
		player.cash_cents += proceeds
		self.log.append(
			f"Trade: {player.name} sold {shares} {symbol.display_name()} @ ${price/100:.2f} for ${proceeds/100:.2f}"
		)
		return True

	def end_trading_phase(self) -> None:
		self.in_trading_phase = False
		self.log.append("Trading phase ended.")

	def standings(self) -> List[Tuple[str, int]]:
		return sorted(
			[(p.name, p.total_net_worth_cents(self.market)) for p in self.players],
			key=lambda x: x[1],
			reverse=True,
		)

	def to_json(self) -> str:
		def encode(obj):
			if isinstance(obj, enum.Enum):
				return {"__enum__": f"{obj.__class__.__name__}.{obj.name}"}
			if isinstance(obj, StockState):
				return {"symbol": obj.symbol.name, "price_cents": obj.price_cents}
			if isinstance(obj, Player):
				return {
					"name": obj.name,
					"cash_cents": obj.cash_cents,
					"holdings": {k.name: v for k, v in obj.holdings.items()},
				}
			if isinstance(obj, GameConfig):
				return asdict(obj)
			if isinstance(obj, GameState):
				return {
					"players": obj.players,
					"market": {k.name: v for k, v in obj.market.items()},
					"config": obj.config,
					"roll_count": obj.roll_count,
					"last_roll": (
						(obj.last_roll[0].name, obj.last_roll[1].value, obj.last_roll[2])
						if obj.last_roll
						else None
					),
					"in_trading_phase": obj.in_trading_phase,
					"log": obj.log,
				}
			raise TypeError

		return json.dumps(self, default=encode, indent=2)

	@staticmethod
	def from_json(data: str) -> "GameState":
		obj = json.loads(data)
		cfg = GameConfig(**obj["config"]) if isinstance(obj.get("config"), dict) else GameConfig()
		players: List[Player] = []
		for p in obj["players"]:
			holdings = {StockSymbol[k]: v for k, v in p.get("holdings", {}).items()}
			players.append(Player(name=p["name"], cash_cents=p["cash_cents"], holdings=holdings))
		market: Dict[StockSymbol, StockState] = {}
		for k, v in obj["market"].items():
			market[StockSymbol[k]] = StockState(symbol=StockSymbol[k], price_cents=v["price_cents"])
		state = GameState(
			players=players,
			market=market,
			config=cfg,
			roll_count=obj.get("roll_count", 0),
			last_roll=(
				(StockSymbol[obj["last_roll"][0]], DieAction(obj["last_roll"][1]), obj["last_roll"][2])
				if obj.get("last_roll")
				else None
			),
			in_trading_phase=obj.get("in_trading_phase", True),
			log=list(obj.get("log", [])),
		)
		return state

