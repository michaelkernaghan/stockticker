from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

from .engine import (
	GameConfig,
	GameState,
	Player,
	StockState,
	StockSymbol,
	DieAction,
)


class StockTickerApp(tk.Tk):
	def __init__(self) -> None:
		super().__init__()
		self.title("Stock Ticker")
		self.geometry("1100x720")

		self.state: Optional[GameState] = None
		self.selected_player_index: int = 0

		self._build_menu()
		self._build_start_screen()

	def _build_menu(self) -> None:
		menubar = tk.Menu(self)
		game_menu = tk.Menu(menubar, tearoff=False)
		game_menu.add_command(label="New Game", command=self._new_game_dialog)
		game_menu.add_command(label="Save Game", command=self._save_game)
		game_menu.add_command(label="Load Game", command=self._load_game)
		game_menu.add_separator()
		game_menu.add_command(label="Settings", command=self._open_settings)
		game_menu.add_command(label="End Game", command=self._open_scoreboard)
		game_menu.add_separator()
		game_menu.add_command(label="Quit", command=self.destroy)
		menubar.add_cascade(label="Game", menu=game_menu)
		self.config(menu=menubar)

	def _build_start_screen(self) -> None:
		self.start_frame = ttk.Frame(self)
		self.start_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

		title = ttk.Label(self.start_frame, text="Stock Ticker", font=("TkDefaultFont", 20, "bold"))
		title.pack(pady=12)

		prompt = ttk.Label(self.start_frame, text="Enter player names (comma separated):")
		prompt.pack(pady=(8, 4))

		self.name_entry = ttk.Entry(self.start_frame, width=60)
		self.name_entry.insert(0, "Player 1, Player 2")
		self.name_entry.pack()

		controls = ttk.Frame(self.start_frame)
		controls.pack(pady=12)

		start_btn = ttk.Button(controls, text="Start Game", command=self._start_game_from_entry)
		start_btn.grid(row=0, column=0, padx=6)

		seed_lbl = ttk.Label(controls, text="Seed (optional):")
		seed_lbl.grid(row=0, column=1, padx=(18, 6))
		self.seed_var = tk.StringVar()
		seed_entry = ttk.Entry(controls, textvariable=self.seed_var, width=10)
		seed_entry.grid(row=0, column=2)

	def _new_game_dialog(self) -> None:
		if hasattr(self, "main_frame"):
			if not messagebox.askyesno("New Game", "Start a new game? Current progress will be lost."):
				return
			self.main_frame.destroy()
			self.log_text = None
			self.state = None
			self.selected_player_index = 0
			self._build_start_screen()

	def _start_game_from_entry(self) -> None:
		names_raw = self.name_entry.get()
		names = [n.strip() for n in names_raw.split(",") if n.strip()]
		seed_val = self.seed_var.get().strip()
		seed: Optional[int] = None
		if seed_val:
			try:
				seed = int(seed_val)
			except ValueError:
				messagebox.showerror("Invalid Seed", "Seed must be an integer.")
				return

		if len(names) < 1:
			messagebox.showerror("Players", "Please enter at least one player name.")
			return
		self.start_frame.destroy()
		self._create_new_game(names, seed)

	def _create_new_game(self, player_names: List[str], seed: Optional[int]) -> None:
		config = GameConfig(seed=seed)
		self.state = GameState.new_game(player_names, config=config)
		self._build_main_ui()
		self._refresh_all()

	def _build_main_ui(self) -> None:
		self.main_frame = ttk.Frame(self)
		self.main_frame.pack(fill=tk.BOTH, expand=True)

		# Left: market and dice
		left = ttk.Frame(self.main_frame)
		left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

		# Right: players and log
		right = ttk.Frame(self.main_frame)
		right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

		# Market table
		market_group = ttk.LabelFrame(left, text="Market")
		market_group.pack(fill=tk.BOTH, expand=False)

		cols = ("Stock", "Price")
		self.market_tree = ttk.Treeview(market_group, columns=cols, show="headings", height=8)
		for c in cols:
			self.market_tree.heading(c, text=c)
			self.market_tree.column(c, width=140 if c == "Stock" else 80, anchor=tk.CENTER)
		self.market_tree.pack(fill=tk.X, padx=8, pady=8)

		# Dice + trading controls
		controls = ttk.Frame(left)
		controls.pack(fill=tk.X, pady=8)

		self.roll_label = ttk.Label(controls, text="Last roll: -")
		self.roll_label.grid(row=0, column=0, sticky=tk.W)

		roll_btn = ttk.Button(controls, text="Roll Dice", command=self._on_roll)
		roll_btn.grid(row=0, column=1, padx=8)

		self.trade_phase_var = tk.StringVar(value="Trading: Open")
		trade_phase_lbl = ttk.Label(controls, textvariable=self.trade_phase_var)
		trade_phase_lbl.grid(row=0, column=2, padx=8)

		self.rolls_until_var = tk.StringVar(value="")
		rolls_until_lbl = ttk.Label(controls, textvariable=self.rolls_until_var)
		rolls_until_lbl.grid(row=0, column=3, padx=8)

		end_trade_btn = ttk.Button(controls, text="End Trading", command=self._on_end_trading)
		end_trade_btn.grid(row=0, column=4, padx=8)

		# Trading panel
		trade_group = ttk.LabelFrame(left, text="Trade")
		trade_group.pack(fill=tk.X, pady=8)

		self.trade_stock_var = tk.StringVar(value=StockSymbol.GOLD.name)
		self.trade_action_var = tk.StringVar(value="Buy")
		self.trade_block_var = tk.StringVar(value="500")

		stocks = [s.name for s in StockSymbol.all_symbols()]
		blocks = [str(b) for b in self.state.config.block_sizes]

		row = 0
		ttk.Label(trade_group, text="Player:").grid(row=row, column=0, padx=6, pady=6, sticky=tk.E)
		self.player_selector = ttk.Combobox(trade_group, state="readonly", values=[p.name for p in self.state.players])
		self.player_selector.current(self.selected_player_index)
		self.player_selector.grid(row=row, column=1, padx=6, pady=6, sticky=tk.W)
		self.player_selector.bind("<<ComboboxSelected>>", self._on_player_select)

		row += 1
		ttk.Label(trade_group, text="Stock:").grid(row=row, column=0, padx=6, pady=6, sticky=tk.E)
		self.stock_selector = ttk.Combobox(trade_group, state="readonly", values=stocks, textvariable=self.trade_stock_var)
		self.stock_selector.grid(row=row, column=1, padx=6, pady=6, sticky=tk.W)

		row += 1
		ttk.Label(trade_group, text="Action:").grid(row=row, column=0, padx=6, pady=6, sticky=tk.E)
		self.action_selector = ttk.Combobox(trade_group, state="readonly", values=["Buy", "Sell"], textvariable=self.trade_action_var)
		self.action_selector.grid(row=row, column=1, padx=6, pady=6, sticky=tk.W)

		row += 1
		ttk.Label(trade_group, text="Block size:").grid(row=row, column=0, padx=6, pady=6, sticky=tk.E)
		self.block_selector = ttk.Combobox(trade_group, state="readonly", values=blocks, textvariable=self.trade_block_var)
		self.block_selector.grid(row=row, column=1, padx=6, pady=6, sticky=tk.W)

		row += 1
		self.trade_btn = ttk.Button(trade_group, text="Execute Trade", command=self._on_trade)
		self.trade_btn.grid(row=row, column=0, columnspan=2, pady=8)

		# Players panel
		players_group = ttk.LabelFrame(right, text="Players")
		players_group.pack(fill=tk.BOTH, expand=True)

		pcols = ("Player", "Cash", "Net Worth")
		self.players_tree = ttk.Treeview(players_group, columns=pcols, show="headings", height=6)
		for c in pcols:
			self.players_tree.heading(c, text=c)
			self.players_tree.column(c, anchor=tk.CENTER)
		self.players_tree.pack(fill=tk.X, padx=8, pady=8)

		# Holdings for selected player
		hold_group = ttk.LabelFrame(right, text="Holdings (Selected Player)")
		hold_group.pack(fill=tk.BOTH, expand=False, pady=8)

		hcols = ("Stock", "Shares")
		self.holdings_tree = ttk.Treeview(hold_group, columns=hcols, show="headings", height=6)
		for c in hcols:
			self.holdings_tree.heading(c, text=c)
			self.holdings_tree.column(c, anchor=tk.CENTER)
		self.holdings_tree.pack(fill=tk.X, padx=8, pady=8)

		# Log panel
		log_group = ttk.LabelFrame(right, text="Game Log")
		log_group.pack(fill=tk.BOTH, expand=True)
		self.log_text = tk.Text(log_group, height=12, state=tk.DISABLED)
		self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

	def _refresh_all(self) -> None:
		if not self.state:
			return
		# Market
		for i in self.market_tree.get_children():
			self.market_tree.delete(i)
		for sym in StockSymbol.all_symbols():
			stk = self.state.market[sym]
			self.market_tree.insert("", tk.END, values=(sym.display_name(), f"${stk.price_cents/100:.2f}"))

		# Players
		for i in self.players_tree.get_children():
			self.players_tree.delete(i)
		for idx, p in enumerate(self.state.players):
			net = p.total_net_worth_cents(self.state.market)
			self.players_tree.insert("", tk.END, values=(p.name, f"${p.cash_cents/100:.2f}", f"${net/100:.2f}"))

		# Holdings for selected player
		self._refresh_holdings()

		# Last roll and phase
		if self.state.last_roll:
			s, a, amt = self.state.last_roll
			self.roll_label.config(text=f"Last roll: {s.display_name()} {a.value} {amt}¢")
		else:
			self.roll_label.config(text="Last roll: -")
		self.trade_phase_var.set("Trading: Open" if self.state.in_trading_phase else "Trading: Closed")

		# Rolls until next trading
		rem = self.state.rolls_until_next_trading()
		if rem is None:
			self.rolls_until_var.set("")
		else:
			self.rolls_until_var.set(f"Rolls until trading: {rem}")

		# Player selector
		self.player_selector["values"] = [p.name for p in self.state.players]
		self.player_selector.current(self.selected_player_index)

		# Log
		self._append_log(None)

	def _refresh_holdings(self) -> None:
		for i in self.holdings_tree.get_children():
			self.holdings_tree.delete(i)
		if not self.state:
			return
		player = self.state.players[self.selected_player_index]
		for sym in StockSymbol.all_symbols():
			shares = player.holdings.get(sym, 0)
			self.holdings_tree.insert("", tk.END, values=(sym.display_name(), shares))

	def _append_log(self, line: Optional[str]) -> None:
		if not self.log_text:
			return
		self.log_text.configure(state=tk.NORMAL)
		if line is None:
			# refresh from state
			self.log_text.delete("1.0", tk.END)
			for entry in self.state.log[-200:]:
				self.log_text.insert(tk.END, entry + "\n")
		else:
			self.log_text.insert(tk.END, line + "\n")
		self.log_text.see(tk.END)
		self.log_text.configure(state=tk.DISABLED)

	def _on_roll(self) -> None:
		if not self.state:
			return
		if self.state.in_trading_phase:
			if not messagebox.askyesno("Trading Open", "Trading is open. End trading before rolling?"):
				return
			self.state.end_trading_phase()
		roll = self.state.roll_dice()
		self.state.apply_roll(roll)
		self._refresh_all()

	def _on_end_trading(self) -> None:
		if not self.state:
			return
		self.state.end_trading_phase()
		self._refresh_all()

	def _on_player_select(self, _evt=None) -> None:
		self.selected_player_index = self.player_selector.current()
		self._refresh_holdings()

	def _on_trade(self) -> None:
		if not self.state:
			return
		if not self.state.in_trading_phase:
			messagebox.showwarning("Trading Closed", "Open trading (it opens automatically after rolls per rules).")
			return
		p_idx = self.player_selector.current()
		try:
			block = int(self.block_selector.get())
		except Exception:
			messagebox.showerror("Block Size", "Invalid block size.")
			return
		try:
			sym = StockSymbol[self.stock_selector.get()]
		except Exception:
			messagebox.showerror("Stock", "Invalid stock selection.")
			return
		action = self.action_selector.get()
		ok = False
		if action == "Buy":
			ok = self.state.buy(p_idx, sym, block)
		else:
			ok = self.state.sell(p_idx, sym, block)
		if not ok:
			messagebox.showerror("Trade", "Trade failed (check block size, funds, or holdings).")
		self._refresh_all()

	def _save_game(self) -> None:
		if not self.state:
			messagebox.showinfo("Save Game", "No game to save.")
			return
		path = filedialog.asksaveasfilename(
			title="Save Stock Ticker Game",
			defaultextension=".json",
			filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
		)
		if not path:
			return
		try:
			with open(path, "w", encoding="utf-8") as f:
				f.write(self.state.to_json())
			messagebox.showinfo("Saved", f"Game saved to:\n{path}")
		except Exception as e:
			messagebox.showerror("Save Failed", str(e))

	def _load_game(self) -> None:
		path = filedialog.askopenfilename(
			title="Load Stock Ticker Game",
			defaultextension=".json",
			filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
		)
		if not path:
			return
		try:
			with open(path, "r", encoding="utf-8") as f:
				data = f.read()
			loaded = GameState.from_json(data)
			self.state = loaded
			self.selected_player_index = 0
			if hasattr(self, "start_frame") and self.start_frame.winfo_exists():
				self.start_frame.destroy()
			if hasattr(self, "main_frame") and self.main_frame.winfo_exists():
				self.main_frame.destroy()
			self._build_main_ui()
			self._refresh_all()
			messagebox.showinfo("Loaded", f"Game loaded from:\n{path}")
		except Exception as e:
			messagebox.showerror("Load Failed", str(e))

	def _open_settings(self) -> None:
		if not self.state:
			messagebox.showinfo("Settings", "Start a game first.")
			return
		win = tk.Toplevel(self)
		win.title("Settings")
		win.grab_set()

		row = 0
		ttk.Label(win, text="Trading interval (rolls between trading phases; 0 to disable)").grid(row=row, column=0, padx=8, pady=8, sticky=tk.W)
		ival_var = tk.StringVar(value=str(self.state.config.trading_interval_rolls))
		ival_entry = ttk.Entry(win, textvariable=ival_var, width=10)
		ival_entry.grid(row=row, column=1, padx=8, pady=8)

		def save():
			try:
				ival = int(ival_var.get())
			except Exception:
				messagebox.showerror("Settings", "Trading interval must be an integer.")
				return
			if ival < 0:
				messagebox.showerror("Settings", "Trading interval cannot be negative.")
				return
			self.state.config.trading_interval_rolls = ival
			messagebox.showinfo("Settings", "Saved.")
			win.destroy()
			self._refresh_all()

		btns = ttk.Frame(win)
		btns.grid(row=row+1, column=0, columnspan=2, pady=8)
		ttk.Button(btns, text="Save", command=save).pack(side=tk.LEFT, padx=6)
		ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.LEFT, padx=6)

	def _open_scoreboard(self) -> None:
		if not self.state:
			messagebox.showinfo("End Game", "Start a game first.")
			return
		standings = self.state.standings()
		win = tk.Toplevel(self)
		win.title("Final Standings")
		cols = ("Rank", "Player", "Net Worth")
		tree = ttk.Treeview(win, columns=cols, show="headings", height=min(8, len(standings)))
		for c in cols:
			tree.heading(c, text=c)
			tree.column(c, anchor=tk.CENTER)
		tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
		for idx, (name, cents) in enumerate(standings, start=1):
			tree.insert("", tk.END, values=(idx, name, f"${cents/100:.2f}"))
		btn = ttk.Button(win, text="Close", command=win.destroy)
		btn.pack(pady=6)

