import tkinter as tk
from tkinter import ttk, simpledialog
from tkinter import scrolledtext
import threading
import chess
import chess.polyglot
from typing import Optional, Tuple

from core.board import Position, Move
from core.evaluate import evaluate_fen
from core.alphabeta import (
    search_best_move,
    set_stop_flag,
    clear_stop_flag,
    get_nodes,
    get_root_progress,
    init_root_progress,
    reset_progress,
)

LIGHT = "#F0D9B5"
DARK = "#B58863"
HIGHLIGHT = "#829769"
SELECTED = "#6464C8"
WHITE_PIECE = "#FFFFFF"
BLACK_PIECE = "#000000"

PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}


class ChessGUI:
    def __init__(self, square_size: int = 80):
        self.square_size = square_size
        self.board_size = square_size * 8
        self.width = self.board_size + 340
        self.height = self.board_size

        self.root = tk.Tk()
        self.root.title("Chess AI")
        self.root.resizable(True, True)
        self.root.geometry(f"{self.width}x{self.height}")

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧面板
        left_panel = tk.Frame(main_frame, width=100, bg="#f0f0f0")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)

        self.turn_color_canvas = tk.Canvas(left_panel, width=60, height=30, bg="#f0f0f0", highlightthickness=0)
        self.turn_color_canvas.pack(pady=(20, 10))

        self.score_number_label = tk.Label(left_panel, text="0.00", font=("Arial", 16, "bold"), bg="#f0f0f0")
        self.score_number_label.pack()

        self.bar_canvas = tk.Canvas(left_panel, width=40, height=400, bg="#f0f0f0", highlightthickness=0)
        self.bar_canvas.pack(pady=10)

        self.flip_button = tk.Button(left_panel, text="🔄 翻转", font=("Arial", 10), command=self._flip_board)
        self.flip_button.pack(side=tk.BOTTOM, pady=(5, 0))

        self.toggle_button = tk.Button(left_panel, text="▶", font=("Arial", 12), command=self._toggle_right_panel)
        self.toggle_button.pack(side=tk.BOTTOM, pady=5)

        # 棋盘
        self.canvas = tk.Canvas(main_frame, width=self.board_size, height=self.board_size, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT)
        self.canvas.bind("<Button-1>", self._on_click)

        # 右侧面板
        self.right_frame = tk.Frame(main_frame, width=200, bg="#f0f0f0")
        self.right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.right_frame.pack_propagate(False)
        self.right_visible = True

        self.right_inner = tk.Frame(self.right_frame, bg="#f0f0f0")
        self.right_inner.pack(fill=tk.BOTH, expand=True)

        control_frame = tk.Frame(self.right_inner, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, pady=5)

        tk.Label(control_frame, text="AI 深度", font=("Arial", 10), bg="#f0f0f0").pack()
        self.depth_var = tk.IntVar(value=5)
        self.depth_scale = tk.Scale(control_frame, from_=1, to=7, orient=tk.HORIZONTAL,
                                    variable=self.depth_var, length=150, command=self._on_depth_changed)
        self.depth_scale.pack()

        self.undo_button = tk.Button(control_frame, text="悔棋", font=("Arial", 10), command=self._undo_move)
        self.undo_button.pack(pady=5)

        self.new_game_button = tk.Button(control_frame, text="♻️ 新游戏", font=("Arial", 10), command=self._new_game)
        self.new_game_button.pack(pady=5)

        mode_frame = tk.Frame(self.right_inner, bg="#f0f0f0")
        mode_frame.pack(fill=tk.X, pady=5)

        tk.Label(mode_frame, text="白方", font=("Arial", 9, "bold"), bg="#f0f0f0").grid(row=0, column=0, padx=5)
        self.white_control_var = tk.StringVar(value="人类")
        self.white_control_menu = tk.OptionMenu(mode_frame, self.white_control_var, "人类", "AI", command=self._on_control_changed)
        self.white_control_menu.config(width=6)
        self.white_control_menu.grid(row=0, column=1, padx=5)

        tk.Label(mode_frame, text="黑方", font=("Arial", 9, "bold"), bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5)
        self.black_control_var = tk.StringVar(value="AI")
        self.black_control_menu = tk.OptionMenu(mode_frame, self.black_control_var, "人类", "AI", command=self._on_control_changed)
        self.black_control_menu.config(width=6)
        self.black_control_menu.grid(row=1, column=1, padx=5, pady=5)

        # 进度条
        self.progress_bar = ttk.Progressbar(self.right_inner, orient='horizontal', length=180, mode='determinate')
        self.progress_bar.pack(pady=(5, 0))
        self.progress_bar['value'] = 0
        self.progress_label = tk.Label(self.right_inner, text="", font=("Arial", 9), bg="#f0f0f0")
        self.progress_label.pack(pady=(0, 5))

        tk.Label(self.right_inner, text="记谱", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(10, 0))
        self.move_list = scrolledtext.ScrolledText(self.right_inner, width=22, height=13, font=("Consolas", 10))
        self.move_list.pack(fill=tk.BOTH, expand=True)

        # 游戏状态
        self._ignore_control_change = False
        self.search_id = 0
        self.search_in_progress = False
        self.progress_after_id: Optional[str] = None
        self.locked = False          # AI 思考时锁定界面
        self._init_game()

        self.ai_thread: Optional[threading.Thread] = None
        self.stop_ai_flag = False

        # 开局库
        self.book_reader = None
        try:
            self.book_reader = chess.polyglot.open_reader("book.bin")
            print("✅ 成功加载开局库")
        except FileNotFoundError:
            print("⚠️ 未找到 book.bin，将不使用开局库")
        except Exception as e:
            print(f"⚠️ 开局库加载失败: {e}")

        self._update_display()
        self._draw()
        self._auto_ai_if_needed()
        self.root.mainloop()

    # ---------- 开局库转换 ----------
    def _custom_move_to_chess(self, move: Move) -> chess.Move:
        from_sq = (7 - move.from_row) * 8 + move.from_col
        to_sq = (7 - move.to_row) * 8 + move.to_col
        promotion = None
        if move.promotion:
            promo_map = {'Q': chess.QUEEN, 'R': chess.ROOK, 'B': chess.BISHOP, 'N': chess.KNIGHT}
            promotion = promo_map.get(move.promotion.upper())
        return chess.Move(from_sq, to_sq, promotion=promotion)

    def _chess_move_to_custom(self, chess_move: chess.Move) -> Move:
        from_sq = chess_move.from_square
        to_sq = chess_move.to_square
        from_row = 7 - (from_sq // 8)
        from_col = from_sq % 8
        to_row = 7 - (to_sq // 8)
        to_col = to_sq % 8
        promotion = None
        if chess_move.promotion:
            rev_map = {chess.QUEEN: 'Q', chess.ROOK: 'R', chess.BISHOP: 'B', chess.KNIGHT: 'N'}
            promotion = rev_map.get(chess_move.promotion)
        return Move(from_row, from_col, to_row, to_col, promotion=promotion)

    def _position_to_chess_board(self, pos: Position) -> chess.Board:
        board = chess.Board()
        for record in pos.move_history:
            custom_move = record['move']
            chess_move = self._custom_move_to_chess(custom_move)
            board.push(chess_move)
        return board

    def _opening_book_move(self, position: Position) -> Optional[Move]:
        if self.book_reader is None:
            return None
        try:
            chess_board = self._position_to_chess_board(position)
        except Exception:
            return None
        try:
            entry = self.book_reader.weighted_choice(chess_board)
            if entry is None:
                return None
            return self._chess_move_to_custom(entry.move)
        except IndexError:
            return None
        except Exception:
            return None

    # ---------- 游戏重置 ----------
    def _init_game(self):
        self.last_ai_score = None
        self.search_id += 1
        self.position = Position()
        self.selected = None
        self.legal_targets = []
        self.game_over = False
        self.winner = None
        self.last_ai_move = None
        self.move_count = 0
        self.history_text = ""
        self.depth = self.depth_var.get()
        self.flipped = False
        self.move_list.delete(1.0, tk.END)
        self.fen_history = [self.position.to_fen()]
        set_stop_flag(False)
        reset_progress()
        self._clear_progress()
        self.locked = False

    def _new_game(self):
        self._cancel_ai()
        self._set_control_mode("人类", "AI")
        self._init_game()
        self._update_display()
        self._draw()
        self._auto_ai_if_needed()

    # ---------- 坐标转换 ----------
    def _board_to_canvas(self, r: int, c: int) -> Tuple[int, int]:
        disp_r = 7 - r if self.flipped else r
        disp_c = 7 - c if self.flipped else c
        x = disp_c * self.square_size + self.square_size // 2
        y = disp_r * self.square_size + self.square_size // 2
        return x, y

    def _flip_board(self):
        self.flipped = not self.flipped
        self._draw()

    def _toggle_right_panel(self):
        RIGHT_PANEL_WIDTH = 170
        if self.right_visible:
            self.right_frame.pack_forget()
            self.toggle_button.config(text="◀")
            self.right_visible = False
            new_width = self.root.winfo_width() - RIGHT_PANEL_WIDTH
            self.root.geometry(f"{new_width}x{self.height}")
        else:
            self.right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            self.toggle_button.config(text="▶")
            self.right_visible = True
            new_width = self.root.winfo_width() + RIGHT_PANEL_WIDTH
            self.root.geometry(f"{new_width}x{self.height}")

    # ---------- 用户交互 ----------
    def _on_click(self, event: tk.Event):
        if self.game_over or self.locked:
            return
        col = event.x // self.square_size
        row = event.y // self.square_size
        if self.flipped:
            col = 7 - col
            row = 7 - row
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        if self._current_control() != "人类":
            return
        if self.selected is None:
            self._try_select(row, col)
        else:
            self._try_move(row, col)

    def _try_select(self, row: int, col: int):
        piece = self.position.board[row][col]
        if piece and self.position.piece_color(piece) == self.position.side_to_move:
            self.selected = (row, col)
            all_moves = self.position.generate_moves()
            self.legal_targets = [(m.to_row, m.to_col) for m in all_moves if m.from_row == row and m.from_col == col]
            self._draw()

    def _try_move(self, row: int, col: int):
        if (row, col) in self.legal_targets:
            fr, fc = self.selected
            candidates = [m for m in self.position.generate_moves() if m.from_row == fr and m.from_col == fc and m.to_row == row and m.to_col == col]
            if not candidates:
                return
            if len(candidates) > 1:
                promo = self._ask_promotion()
                if promo is None:
                    return
                move = next((m for m in candidates if m.promotion == promo), None)
                if move is None:
                    return
            else:
                move = candidates[0]
            # 传递 trusted=True，表示此走法已经过合法筛选
            self._execute_human_move(move, trusted=True)
        else:
            piece = self.position.board[row][col]
            if piece and self.position.piece_color(piece) == self.position.side_to_move:
                self.selected = (row, col)
                all_moves = self.position.generate_moves()
                self.legal_targets = [(m.to_row, m.to_col) for m in all_moves if m.from_row == row and m.from_col == col]
            else:
                self.selected = None
                self.legal_targets = []
            self._draw()

    def _ask_promotion(self):
        choice = simpledialog.askstring("升变选择", "请选择升变棋子 (Q/R/B/N):", parent=self.root)
        if choice and choice.upper() in ('Q', 'R', 'B', 'N'):
            return choice.upper()
        return None

    # ---------- 走棋核心 ----------
    def _execute_human_move(self, move: Move, trusted: bool = False):
        if self.game_over:
            return
        # 非信任走法才进行合法性检查（例如通过其他途径调用的）
        if not trusted and move not in self.position.generate_moves():
            print(f"非法人类走法被阻止: {move}")
            return
        self._cancel_ai()
        self.last_ai_move = None
        self._add_to_history(move)
        self.position.make_move(move)
        self.fen_history.append(self.position.to_fen())
        self.last_ai_score = evaluate_fen(self.position.to_fen())
        self.selected = None
        self.legal_targets = []
        self._check_game_over()
        self._update_display()
        self._draw()
        if not self.game_over:
            self._auto_ai_if_needed()

    def _ai_move(self, retry_count: int = 0):
        """启动 AI 走法，最多重试 1 次"""
        if self.locked:
            return
        if retry_count > 1:
            print("AI 多次失败，切换为人类模式")
            self._set_control_mode("人类", "人类")
            self.locked = False
            return

        self.locked = True
        self.selected = None
        self.legal_targets = []
        self._draw()

        self._cancel_ai()
        moves = self.position.generate_moves()
        if not moves:
            self._check_game_over()
            self._update_display()
            self._draw()
            self.locked = False
            return

        # 开局库优先
        book_move = self._opening_book_move(self.position)
        if book_move is not None:
            print(f"[开局库] 命中！走法: {book_move}")
            self.root.after(0, lambda: self._apply_ai_move(book_move, None, self.position.side_to_move, self.search_id, retry_count))
            return

        pos_copy = self._copy_position()
        depth = self.depth
        ai_side = pos_copy.side_to_move

        all_moves = pos_copy.generate_moves()
        init_root_progress(depth, len(all_moves))
        self.search_in_progress = True
        self._start_progress_timer()

        self.search_id += 1
        current_id = self.search_id
        clear_stop_flag()
        set_stop_flag(False)

        def search_and_move():
            try:
                move, score = search_best_move(pos_copy, depth)
                if self.stop_ai_flag or self.search_id != current_id:
                    return
                self.root.after(0, lambda: self._apply_ai_move(move, score, ai_side, current_id, retry_count))
            except Exception as e:
                if not self.stop_ai_flag:
                    print(f"AI 搜索出错: {e}")
                    self.root.after(0, lambda: self._ai_move(retry_count + 1))

        self.ai_thread = threading.Thread(target=search_and_move, daemon=True)
        self.ai_thread.start()

    def _apply_ai_move(self, move: Optional[Move], score: Optional[int], ai_side: str, search_id: int, retry_count: int):
        if search_id != self.search_id:
            return
        self.search_in_progress = False
        self._stop_progress_timer()
        self.progress_bar['value'] = 100
        self.progress_label.config(text="完成")
        self.root.after(1500, self._clear_progress)

        self._add_to_history(move)
        self.position.make_move(move)
        self.fen_history.append(self.position.to_fen())
        if score is not None:
            self.last_ai_score = score if ai_side == 'w' else -score
        else:
            self.last_ai_score = evaluate_fen(self.position.to_fen())
        self.last_ai_move = move
        self._check_game_over()
        self._update_display()
        self._draw()

        self.locked = False
        if not self.game_over:
            self._auto_ai_if_needed()

    def _check_game_over(self):
        current_fen = self.position.to_fen()
        if self.fen_history.count(current_fen) >= 3:
            self.game_over = True
            self.winner = None
            return
        if not self.position.generate_moves():
            self.game_over = True
            if self.position.is_check():
                self.winner = 'w' if self.position.side_to_move == 'b' else 'b'
            else:
                self.winner = None

    # ---------- 悔棋 ----------
    def _undo_move(self):
        if self.locked:
            return
        self._cancel_ai()
        self._set_control_mode("人类", "人类")
        if self.game_over:
            self.game_over = False
            self.winner = None
        self.selected = None
        self.legal_targets = []
        if self.position.move_history:
            self.position.undo_move()
            self.fen_history.pop()
            self.last_ai_move = None
            self.last_ai_score = evaluate_fen(self.position.to_fen())
            self._rebuild_history_text()
            self._check_game_over()
            self._update_display()
            self._draw()
            self._auto_ai_if_needed()

    def _rebuild_history_text(self):
        self.history_text = ""
        self.move_count = 0
        for record in self.position.move_history:
            move = record['move']
            uci = f"{chr(move.from_col+97)}{8-move.from_row}{chr(move.to_col+97)}{8-move.to_row}"
            if move.promotion:
                uci += f"={move.promotion.lower()}"
            self.move_count += 1
            prefix = f"{self.move_count}. " if self.move_count % 2 == 1 else "     "
            self.history_text += f"{prefix}{uci}\n"
        self.move_list.delete(1.0, tk.END)
        self.move_list.insert(tk.END, self.history_text)
        self.move_list.see(tk.END)

    def _add_to_history(self, move: Move):
        uci = f"{chr(move.from_col+97)}{8-move.from_row}{chr(move.to_col+97)}{8-move.to_row}"
        if move.promotion:
            uci += f"={move.promotion.lower()}"
        self.move_count += 1
        prefix = f"{self.move_count}. " if self.move_count % 2 == 1 else "     "
        self.history_text += f"{prefix}{uci}\n"
        self.move_list.delete(1.0, tk.END)
        self.move_list.insert(tk.END, self.history_text)
        self.move_list.see(tk.END)

    # ---------- 控制模式 ----------
    def _current_control(self) -> str:
        return self.white_control_var.get() if self.position.side_to_move == 'w' else self.black_control_var.get()

    def _on_control_changed(self, *args):
        if self._ignore_control_change or self.locked:
            return
        self._cancel_ai()
        self.selected = None
        self.legal_targets = []
        self._update_display()
        self._draw()
        self._auto_ai_if_needed()

    def _set_control_mode(self, white: str, black: str):
        self._ignore_control_change = True
        self.white_control_var.set(white)
        self.black_control_var.set(black)
        self._ignore_control_change = False

    def _auto_ai_if_needed(self):
        if self.game_over or self.locked:
            return
        if self._current_control() == "AI":
            if self.ai_thread and self.ai_thread.is_alive():
                return
            self.selected = None
            self.legal_targets = []
            self.root.after(100, self._ai_move)

    def _on_depth_changed(self, value):
        self._cancel_ai()
        self.depth = self.depth_var.get()

    # ---------- 多线程与打断 ----------
    def _cancel_ai(self):
        """安全取消 AI 线程"""
        self.search_in_progress = False
        self._stop_progress_timer()
        if self.ai_thread and self.ai_thread.is_alive():
            set_stop_flag(True)
            self.ai_thread.join(timeout=1.0)
            set_stop_flag(False)
        self.ai_thread = None
        self._clear_progress()
        self.locked = False

    def _copy_position(self) -> Position:
        """深拷贝当前局面"""
        new_pos = Position.__new__(Position)
        new_pos.board = [row[:] for row in self.position.board]
        new_pos.side_to_move = self.position.side_to_move
        new_pos.move_history = []
        new_pos.white_king_moved = self.position.white_king_moved
        new_pos.black_king_moved = self.position.black_king_moved
        new_pos.white_rook_a_moved = self.position.white_rook_a_moved
        new_pos.white_rook_h_moved = self.position.white_rook_h_moved
        new_pos.black_rook_a_moved = self.position.black_rook_a_moved
        new_pos.black_rook_h_moved = self.position.black_rook_h_moved
        new_pos.en_passant_target = self.position.en_passant_target
        return new_pos

    # ---------- 进度显示 ----------
    def _start_progress_timer(self):
        self._stop_progress_timer()
        self.progress_bar['value'] = 0
        self.progress_label.config(text="")
        self._update_progress()

    def _update_progress(self):
        if self.search_in_progress:
            idx, total = get_root_progress()
            pct = min(100, int((idx + 1) * 100 / total)) if total > 0 else 0
            self.progress_bar['value'] = pct
            nodes = get_nodes()
            self.progress_label.config(text=f"搜索中... {pct}% (节点: {nodes})")
            self.progress_after_id = self.root.after(200, self._update_progress)

    def _stop_progress_timer(self):
        if self.progress_after_id:
            self.root.after_cancel(self.progress_after_id)
            self.progress_after_id = None

    def _clear_progress(self):
        self.progress_bar['value'] = 0
        self.progress_label.config(text="")

    # ---------- 图形绘制 ----------
    def _draw(self):
        self.canvas.delete("all")
        self._draw_board()
        self._draw_highlights()
        self._draw_arrow()
        self._draw_pieces()
        if self.game_over:
            self._draw_game_over()

    def _draw_board(self):
        for r in range(8):
            for c in range(8):
                color = LIGHT if (r + c) % 2 == 0 else DARK
                x1, y1, x2, y2 = self._square_coords(r, c)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        for i in range(8):
            col_label = chr(ord('h') - i) if self.flipped else chr(ord('a') + i)
            x = i * self.square_size + self.square_size // 2
            self.canvas.create_text(x, self.board_size - 8, text=col_label, fill="gray", font=("Arial", 10, "bold"))
            row_label = str(i + 1) if self.flipped else str(8 - i)
            y = i * self.square_size + self.square_size // 2
            self.canvas.create_text(10, y, text=row_label, fill="gray", font=("Arial", 10, "bold"))

    def _square_coords(self, r: int, c: int):
        disp_r = 7 - r if self.flipped else r
        disp_c = 7 - c if self.flipped else c
        x1 = disp_c * self.square_size
        y1 = disp_r * self.square_size
        return x1, y1, x1 + self.square_size, y1 + self.square_size

    def _draw_highlights(self):
        if self.selected:
            r, c = self.selected
            x1, y1, x2, y2 = self._square_coords(r, c)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=SELECTED, outline="")
        for r, c in self.legal_targets:
            x1, y1, x2, y2 = self._square_coords(r, c)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=HIGHLIGHT, outline="")

    def _draw_arrow(self):
        if self.last_ai_move:
            fr, fc = self.last_ai_move.from_row, self.last_ai_move.from_col
            tr, tc = self.last_ai_move.to_row, self.last_ai_move.to_col
            x1, y1 = self._board_to_canvas(fr, fc)
            x2, y2 = self._board_to_canvas(tr, tc)
            self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=4, fill="orange")

    def _draw_pieces(self):
        for r in range(8):
            for c in range(8):
                piece = self.position.board[r][c]
                if piece:
                    symbol = PIECE_SYMBOLS[piece]
                    color = WHITE_PIECE if piece.isupper() else BLACK_PIECE
                    x, y = self._board_to_canvas(r, c)
                    outline = "#000000" if piece.isupper() else "#FFFFFF"
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        self.canvas.create_text(x + dx, y + dy, text=symbol, fill=outline, font=("Segoe UI Symbol", self.square_size - 20))
                    self.canvas.create_text(x, y, text=symbol, fill=color, font=("Segoe UI Symbol", self.square_size - 20))

    def _draw_game_over(self):
        msg = "白方胜" if self.winner == 'w' else "黑方胜" if self.winner == 'b' else "逼和"
        self.canvas.create_text(self.board_size // 2, self.board_size // 2, text=msg, fill="red", font=("Arial", 36, "bold"))

    # ---------- 左侧分数显示 ----------
    def _update_display(self):
        score = self.last_ai_score if self.last_ai_score is not None else 0
        self.score_number_label.config(text=f"{score / 100:.2f}")
        color = "white" if self.position.side_to_move == 'w' else "black"
        self.turn_color_canvas.delete("all")
        self.turn_color_canvas.create_rectangle(5, 5, 55, 25, fill=color, outline="gray")
        self.bar_canvas.delete("all")
        self.bar_canvas.create_rectangle(0, 0, 40, 400, fill="#cccccc", outline="")
        max_val = 1500
        white_score = max(-max_val, min(max_val, score))
        mid_y = 200
        white_height = int((white_score / max_val) * 200)
        black_height = int((-white_score / max_val) * 200)
        if white_height > 0:
            self.bar_canvas.create_rectangle(5, mid_y - white_height, 35, mid_y, fill="white", outline="gray")
        if black_height > 0:
            self.bar_canvas.create_rectangle(5, mid_y, 35, mid_y + black_height, fill="black", outline="gray")
        self.bar_canvas.create_line(0, mid_y, 40, mid_y, fill="gray")


if __name__ == "__main__":
    ChessGUI()