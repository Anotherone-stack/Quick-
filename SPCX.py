
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from zoneinfo import ZoneInfo

from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed

SYMBOL = "SPCX"
LARGE_TRADE_SHARES = 1_000
ET = ZoneInfo("America/New_York")


class SPXCMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("SPCX Live Market Monitor")
        self.root.geometry("1050x680")
        self.root.minsize(800, 520)

        self.events = queue.Queue()
        self.worker = None
        self.stream = None
        self.running = False
        self.latest_quote = None
        self.trade_count = 0
        self.large_count = 0

        self.setup_ui()
        self.root.after(100, self.process_events)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def setup_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Helvetica", 20, "bold"))
        style.configure("Price.TLabel", font=("Helvetica", 17, "bold"))
        style.configure("Header.TLabel", font=("Helvetica", 11, "bold"))
        style.configure("Start.TButton", font=("Helvetica", 11, "bold"))

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 14))

        ttk.Label(
            top, text="SPCX MARKET MONITOR",
            style="Title.TLabel"
        ).pack(side="left")

        self.status = ttk.Label(top, text="● DISCONNECTED")
        self.status.pack(side="right", padx=8)

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(0, 16))

        self.start_btn = ttk.Button(
            controls, text="▶ Start Feed", command=self.start
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ttk.Button(
            controls, text="■ Stop Feed",
            command=self.stop, state="disabled"
        )
        self.stop_btn.pack(side="left")

        ttk.Label(
            controls, text="Feed: IEX  |  Time zone: New York"
        ).pack(side="right")

        quotes = ttk.Frame(main)
        quotes.pack(fill="x", pady=(0, 14))

        bid_box = ttk.LabelFrame(quotes, text="BID", padding=12)
        bid_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ask_box = ttk.LabelFrame(quotes, text="ASK", padding=12)
        ask_box.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.bid_label = ttk.Label(
            bid_box, text="—", style="Price.TLabel", foreground="#16a34a"
        )
        self.bid_label.pack(anchor="w")

        self.bid_size = ttk.Label(bid_box, text="Size: —")
        self.bid_size.pack(anchor="w", pady=(5, 0))

        self.ask_label = ttk.Label(
            ask_box, text="—", style="Price.TLabel", foreground="#dc2626"
        )
        self.ask_label.pack(anchor="w")

        self.ask_size = ttk.Label(ask_box, text="Size: —")
        self.ask_size.pack(anchor="w", pady=(5, 0))

        stats = ttk.Frame(main)
        stats.pack(fill="x", pady=(0, 14))

        self.trades_stat = ttk.Label(stats, text="Trades: 0")
        self.trades_stat.pack(side="left", padx=(0, 24))

        self.large_stat = ttk.Label(stats, text="Large trades: 0")
        self.large_stat.pack(side="left", padx=(0, 24))

        self.last_stat = ttk.Label(stats, text="Last trade: —")
        self.last_stat.pack(side="left")

        ttk.Label(
            main, text="LIVE TRADE TAPE", style="Header.TLabel"
        ).pack(anchor="w", pady=(0, 6))

        tape_frame = ttk.Frame(main)
        tape_frame.pack(fill="both", expand=True)

        columns = ("time", "symbol", "price", "size", "side", "flag")
        self.tape = ttk.Treeview(
            tape_frame, columns=columns, show="headings", height=15
        )

        headings = {
            "time": "TIME (ET)",
            "symbol": "SYMBOL",
            "price": "PRICE",
            "size": "SHARES",
            "side": "ESTIMATED SIDE",
            "flag": "ALERT",
        }
        widths = {
            "time": 130, "symbol": 80, "price": 100,
            "size": 110, "side": 230, "flag": 160
        }

        for col in columns:
            self.tape.heading(col, text=headings[col])
            self.tape.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(
            tape_frame, orient="vertical", command=self.tape.yview
        )
        self.tape.configure(yscrollcommand=scrollbar.set)

        self.tape.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tape.tag_configure("buy", foreground="#16a34a")
        self.tape.tag_configure("sell", foreground="#dc2626")
        self.tape.tag_configure("large", background="#fff0cc")

        self.footer = ttk.Label(
            main, text="Ready. Start the feed to receive live market data."
        )
        self.footer.pack(anchor="w", pady=(10, 0))

    def start(self):
        if self.running:
            return

        # Validate credentials before launching the worker.
        if not os.environ.get("APCA_API_KEY_ID") or not os.environ.get(
            "APCA_API_SECRET_KEY"
        ):
            messagebox.showerror(
                "Missing API credentials",
                "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
                "in your environment before starting."
            )
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.configure(text="● CONNECTING")
        self.footer.configure(text="Connecting to Alpaca...")

        self.worker = threading.Thread(
            target=self.run_stream, daemon=True
        )
        self.worker.start()

    def run_stream(self):
        try:
            stream = StockDataStream(
                os.environ["APCA_API_KEY_ID"],
                os.environ["APCA_API_SECRET_KEY"],
                feed=DataFeed.IEX,
            )
            self.stream = stream

            async def on_quote(quote):
                self.events.put((
                    "quote",
                    float(quote.bid_price),
                    int(quote.bid_size),
                    float(quote.ask_price),
                    int(quote.ask_size),
                ))

            async def on_trade(trade):
                price = float(trade.price)
                size = int(trade.size)

                # Use the most recently received quote.
                quote = self.latest_quote
                side = "UNKNOWN"

                if quote:
                    bid, ask = quote[0], quote[2]
                    if ask > 0 and price >= ask:
                        side = "BUY-INITIATED (EST.)"
                    elif bid > 0 and price <= bid:
                        side = "SELL-INITIATED (EST.)"
                    else:
                        side = "MID-SPREAD / UNCERTAIN"

                timestamp = trade.timestamp.astimezone(ET).strftime(
                    "%H:%M:%S.%f"
                )[:-3]

                self.events.put((
                    "trade", timestamp, price, size, side
                ))

            stream.subscribe_quotes(on_quote, SYMBOL)
            stream.subscribe_trades(on_trade, SYMBOL)

            self.events.put(("status", "connected"))
            stream.run()

        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            self.events.put(("ended",))

    def stop(self):
        self.running = False
        stream = self.stream

        if stream is not None:
            try:
                stream.stop()
            except Exception as exc:
                self.events.put(("log", f"Stop notice: {exc}"))

        self.stream = None
        self.status.configure(text="● STOPPING")
        self.footer.configure(text="Stopping market feed...")

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "quote":
                    _, bid, bid_size, ask, ask_size = event
                    self.latest_quote = (bid, bid_size, ask, ask_size)

                    self.bid_label.configure(text=f"${bid:,.2f}")
                    self.bid_size.configure(text=f"Size: {bid_size:,}")
                    self.ask_label.configure(text=f"${ask:,.2f}")
                    self.ask_size.configure(text=f"Size: {ask_size:,}")

                elif kind == "trade":
                    _, timestamp, price, size, side = event
                    self.trade_count += 1
                    large = size >= LARGE_TRADE_SHARES

                    if large:
                        self.large_count += 1

                    tag = (
                        "large" if large else
                        "buy" if side.startswith("BUY") else
                        "sell" if side.startswith("SELL") else ""
                    )

                    flag = "<<< LARGE TRADE" if large else ""

                    self.tape.insert(
                        "", 0,
                        values=(
                            timestamp, SYMBOL, f"${price:,.2f}",
                            f"{size:,}", side, flag
                        ),
                        tags=(tag,) if tag else ()
                    )

                    # Keep the UI responsive during heavy traffic.
                    children = self.tape.get_children()
                    for item in children[500:]:
                        self.tape.delete(item)

                    self.trades_stat.configure(
                        text=f"Trades: {self.trade_count:,}"
                    )
                    self.large_stat.configure(
                        text=f"Large trades: {self.large_count:,}"
                    )
                    self.last_stat.configure(
                        text=f"Last trade: ${price:,.2f}"
                    )

                elif kind == "status":
                    self.status.configure(text="● LIVE")
                    self.footer.configure(
                        text=f"Receiving live {SYMBOL} data."
                    )

                elif kind == "error":
                    self.status.configure(text="● ERROR")
                    self.footer.configure(text="Stream error occurred.")
                    messagebox.showerror("Alpaca stream error", event[1])

                elif kind == "log":
                    self.footer.configure(text=event[1])

                elif kind == "ended":
                    self.running = False
                    self.stream = None
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if self.status.cget("text") != "● ERROR":
                        self.status.configure(text="● DISCONNECTED")
                        self.footer.configure(text="Feed stopped.")

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)

    def close(self):
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SPXCMonitor(root)
    root.mainloop()
