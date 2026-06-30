# board.py
from __future__ import annotations
from typing import List, Optional, Tuple

class Move:
    """表示一个走法。"""
    def __init__(self, from_row: int, from_col: int, to_row: int, to_col: int,
                 promotion: Optional[str] = None):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.promotion = promotion      # 例如 'Q' 表示升变为后

    def __eq__(self, other):
        if not isinstance(other, Position):
            return False
        return (self.board == other.board and
                self.side_to_move == other.side_to_move and
                self.white_king_moved == other.white_king_moved and
                self.black_king_moved == other.black_king_moved and
                self.white_rook_a_moved == other.white_rook_a_moved and
                self.white_rook_h_moved == other.white_rook_h_moved and
                self.black_rook_a_moved == other.black_rook_a_moved and
                self.black_rook_h_moved == other.black_rook_h_moved and
                self.en_passant_target == other.en_passant_target)

    def __repr__(self):
        promo = f"={self.promotion}" if self.promotion else ""
        return f"Move({self.from_row},{self.from_col}->{self.to_row},{self.to_col}{promo})"


class Position:
    def __init__(self, board=None, side_to_move='w',
                 white_king_moved=False, black_king_moved=False,
                 white_rook_a_moved=False, white_rook_h_moved=False,
                 black_rook_a_moved=False, black_rook_h_moved=False,
                 en_passant_target: Optional[Tuple[int, int]] = None):
        if board is None:
            self.board = self._starting_board()
        else:
            self.board = [row[:] for row in board]
        self.side_to_move = side_to_move
        self.white_king_moved = white_king_moved
        self.black_king_moved = black_king_moved
        self.white_rook_a_moved = white_rook_a_moved
        self.white_rook_h_moved = white_rook_h_moved
        self.black_rook_a_moved = black_rook_a_moved
        self.black_rook_h_moved = black_rook_h_moved
        self.en_passant_target = en_passant_target
        self.move_history: List[dict] = []

    # ---------- 初始棋盘 ----------
    @staticmethod
    def _starting_board():
        return [
            ['r','n','b','q','k','b','n','r'],
            ['p','p','p','p','p','p','p','p'],
            [None]*8,
            [None]*8,
            [None]*8,
            [None]*8,
            ['P','P','P','P','P','P','P','P'],
            ['R','N','B','Q','K','B','N','R'],
        ]

    # ---------- 工具方法 ----------
    def is_white(self, piece): return piece.isupper()
    def piece_color(self, piece): return 'w' if piece.isupper() else 'b'
    def in_bounds(self, r, c): return 0 <= r < 8 and 0 <= c < 8

    # ---------- 将军检测 ----------
    def is_check(self, color=None):
        if color is None: color = self.side_to_move
        kp = self._find_king(color)
        if kp is None: return False
        return self._is_square_attacked(kp[0], kp[1], color)

    def _find_king(self, color):
        king_char = 'K' if color == 'w' else 'k'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == king_char:
                    return (r, c)
        return None

    def _is_square_attacked(self, r: int, c: int, defender_color: str) -> bool:
        attacker_color = 'b' if defender_color == 'w' else 'w'

        # 马攻击
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc):
                piece = self.board[nr][nc]
                if piece and self.piece_color(piece) == attacker_color and piece.upper() == 'N':
                    return True

        # 王攻击
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    piece = self.board[nr][nc]
                    if piece and self.piece_color(piece) == attacker_color and piece.upper() == 'K':
                        return True

        # 兵攻击（防守方视角）
        if defender_color == 'w':  # 白王，黑兵攻击：黑兵向下（行号增大）
            for dc in (-1, 1):
                nr, nc = r - 1, c + dc
                if self.in_bounds(nr, nc) and self.board[nr][nc] == 'p':
                    return True
        else:  # 黑王，白兵攻击：白兵向上（行号减小）
            for dc in (-1, 1):
                nr, nc = r + 1, c + dc
                if self.in_bounds(nr, nc) and self.board[nr][nc] == 'P':
                    return True

        # 滑行棋子
        directions = {
            'Q': [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)],
            'R': [(1,0),(-1,0),(0,1),(0,-1)],
            'B': [(1,1),(1,-1),(-1,1),(-1,-1)],
        }
        for piece_type, dirs in directions.items():
            for dr, dc in dirs:
                for step in range(1, 8):
                    nr, nc = r + dr * step, c + dc * step
                    if not self.in_bounds(nr, nc):
                        break
                    piece = self.board[nr][nc]
                    if piece is None:
                        continue
                    if self.piece_color(piece) == attacker_color and piece.upper() == piece_type:
                        return True
                    break
        return False

    # ---------- 合法着法生成 ----------
    def generate_moves(self):
        legal = []
        original_side = self.side_to_move
        for m in self._generate_pseudo_moves():
            self.make_move(m)
            if not self.is_check(original_side):
                legal.append(m)
            self.undo_move()
        return legal

    def _generate_pseudo_moves(self, include_castling=True):
        moves = []
        col = self.side_to_move
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and self.piece_color(p) == col:
                    if p.upper() == 'P': moves += self._pawn_moves(r,c,p)
                    elif p.upper() == 'N': moves += self._knight_moves(r,c,p)
                    elif p.upper() == 'B': moves += self._bishop_moves(r,c,p)
                    elif p.upper() == 'R': moves += self._rook_moves(r,c,p)
                    elif p.upper() == 'Q': moves += self._queen_moves(r,c,p)
                    elif p.upper() == 'K':
                        moves += self._king_moves(r,c,p)
                        if include_castling:
                            moves += self._castling_moves(r,c,p)
        return moves

    def _pawn_moves(self, r, c, p):
        moves = []
        d = -1 if p == 'P' else 1
        start = 6 if p == 'P' else 1
        prom_row = 0 if p == 'P' else 7
        opp = 'b' if self.side_to_move == 'w' else 'w'

        nr = r + d
        if self.in_bounds(nr, c) and self.board[nr][c] is None:
            if nr == prom_row:
                for promo in ['Q', 'R', 'B', 'N']:
                    moves.append(Move(r, c, nr, c, promotion=promo))
            else:
                moves.append(Move(r, c, nr, c))
                if r == start:
                    nr2 = r + 2 * d
                    if self.in_bounds(nr2, c) and self.board[nr2][c] is None:
                        moves.append(Move(r, c, nr2, c))

        for dc in (-1, 1):
            nc = c + dc
            nr = r + d
            if not self.in_bounds(nr, nc):
                continue
            tgt = self.board[nr][nc]
            if tgt and self.piece_color(tgt) == opp:
                # 不允许吃王
                if tgt.upper() == 'K':
                    continue
                if nr == prom_row:
                    for promo in ['Q', 'R', 'B', 'N']:
                        moves.append(Move(r, c, nr, nc, promotion=promo))
                else:
                    moves.append(Move(r, c, nr, nc))
            elif self.en_passant_target == (nr, nc):
                moves.append(Move(r, c, nr, nc))
        return moves

    def _castling_moves(self, r: int, c: int, piece: str) -> List[Move]:
        moves = []
        if piece == 'K' and not self.white_king_moved and r == 7 and c == 4:
            if (not self.white_rook_h_moved and
                    self.board[7][5] is None and self.board[7][6] is None and
                    not self._is_square_attacked(7, 4, 'w') and
                    not self._is_square_attacked(7, 5, 'w') and
                    not self._is_square_attacked(7, 6, 'w')):
                moves.append(Move(7, 4, 7, 6))
            if (not self.white_rook_a_moved and
                    self.board[7][3] is None and self.board[7][2] is None and
                    self.board[7][1] is None and
                    not self._is_square_attacked(7, 4, 'w') and
                    not self._is_square_attacked(7, 3, 'w') and
                    not self._is_square_attacked(7, 2, 'w')):
                moves.append(Move(7, 4, 7, 2))
        elif piece == 'k' and not self.black_king_moved and r == 0 and c == 4:
            if (not self.black_rook_h_moved and
                    self.board[0][5] is None and self.board[0][6] is None and
                    not self._is_square_attacked(0, 4, 'b') and
                    not self._is_square_attacked(0, 5, 'b') and
                    not self._is_square_attacked(0, 6, 'b')):
                moves.append(Move(0, 4, 0, 6))
            if (not self.black_rook_a_moved and
                    self.board[0][3] is None and self.board[0][2] is None and
                    self.board[0][1] is None and
                    not self._is_square_attacked(0, 4, 'b') and
                    not self._is_square_attacked(0, 3, 'b') and
                    not self._is_square_attacked(0, 2, 'b')):
                moves.append(Move(0, 4, 0, 2))
        return moves

    def _knight_moves(self, r, c, p):
        moves = []
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc):
                tgt = self.board[nr][nc]
                if tgt is None:
                    moves.append(Move(r, c, nr, nc))
                else:
                    # 不允许吃王
                    if tgt.upper() == 'K':
                        continue
                    if self.piece_color(tgt) != self.side_to_move:
                        moves.append(Move(r, c, nr, nc))
        return moves

    def _bishop_moves(self, r, c, p):
        return self._sliding_moves(r,c,[(1,1),(1,-1),(-1,1),(-1,-1)])

    def _rook_moves(self, r, c, p):
        return self._sliding_moves(r,c,[(1,0),(-1,0),(0,1),(0,-1)])

    def _queen_moves(self, r, c, p):
        return self._sliding_moves(r,c,[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)])

    def _sliding_moves(self, r, c, dirs):
        moves = []
        for dr, dc in dirs:
            for step in range(1, 8):
                nr, nc = r + dr * step, c + dc * step
                if not self.in_bounds(nr, nc):
                    break
                tgt = self.board[nr][nc]
                if tgt is None:
                    moves.append(Move(r, c, nr, nc))
                else:
                    # 不允许吃王
                    if tgt.upper() == 'K':
                        break
                    if self.piece_color(tgt) != self.side_to_move:
                        moves.append(Move(r, c, nr, nc))
                    break
        return moves

    def _king_moves(self, r, c, p):
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    tgt = self.board[nr][nc]
                    if tgt is None:
                        moves.append(Move(r, c, nr, nc))
                    else:
                        # 不允许吃王
                        if tgt.upper() == 'K':
                            continue
                        if self.piece_color(tgt) != self.side_to_move:
                            moves.append(Move(r, c, nr, nc))
        return moves

    # ---------- 走子 / 悔棋 ----------
    def make_move(self, move: Move) -> None:
        fr, fc = move.from_row, move.from_col
        tr, tc = move.to_row, move.to_col
        piece = self.board[fr][fc]
        if piece is None:
            raise ValueError(f"Illegal move from empty square: {move}")
        target_captured = self.board[tr][tc]

        record = {
            'move': move,
            'piece': piece,
            'target_captured': target_captured,
            'ep_captured': None,
            'prev_side': self.side_to_move,
            'prev_white_king_moved': self.white_king_moved,
            'prev_black_king_moved': self.black_king_moved,
            'prev_white_rook_a_moved': self.white_rook_a_moved,
            'prev_white_rook_h_moved': self.white_rook_h_moved,
            'prev_black_rook_a_moved': self.black_rook_a_moved,
            'prev_black_rook_h_moved': self.black_rook_h_moved,
            'prev_en_passant_target': self.en_passant_target,
            'castling_rook_move': None,
        }

        # 吃过路兵
        if piece.upper() == 'P' and self.en_passant_target == (tr, tc):
            cap_r = tr + 1 if piece == 'P' else tr - 1
            cap_c = tc
            record['ep_captured'] = (cap_r, cap_c, self.board[cap_r][cap_c])
            self.board[cap_r][cap_c] = None

        # 易位处理
        if piece.upper() == 'K' and abs(fc - tc) == 2:
            kingside = tc > fc
            rook_fc = 7 if kingside else 0
            rook_tc = 5 if kingside else 3
            row = fr
            rook = self.board[row][rook_fc]
            self.board[row][rook_fc] = None
            self.board[row][rook_tc] = rook
            record['castling_rook_move'] = (row, rook_fc, row, rook_tc, rook)

        # 执行移动
        self.board[fr][fc] = None
        if move.promotion:
            prom = move.promotion if self.side_to_move == 'w' else move.promotion.lower()
            self.board[tr][tc] = prom
        else:
            self.board[tr][tc] = piece

        # 更新易位权限
        if piece == 'K':
            self.white_king_moved = True
        elif piece == 'k':
            self.black_king_moved = True
        elif piece == 'R':
            if fr == 7 and fc == 0:
                self.white_rook_a_moved = True
            elif fr == 7 and fc == 7:
                self.white_rook_h_moved = True
        elif piece == 'r':
            if fr == 0 and fc == 0:
                self.black_rook_a_moved = True
            elif fr == 0 and fc == 7:
                self.black_rook_h_moved = True

        # 过路兵目标格
        self.en_passant_target = None
        if piece.upper() == 'P' and abs(fr - tr) == 2:
            self.en_passant_target = ((fr + tr) // 2, fc)

        self.side_to_move = 'b' if self.side_to_move == 'w' else 'w'
        self.move_history.append(record)

    def undo_move(self) -> None:
        if not self.move_history:
            raise ValueError("No move to undo")
        rec = self.move_history.pop()
        move = rec['move']
        fr, fc = move.from_row, move.from_col
        tr, tc = move.to_row, move.to_col

        self.board[fr][fc] = rec['piece']
        self.board[tr][tc] = rec['target_captured']

        if rec['castling_rook_move']:
            r_fr, r_fc, r_tr, r_tc, rook_char = rec['castling_rook_move']
            self.board[r_fr][r_fc] = rook_char
            self.board[r_tr][r_tc] = None

        if rec['ep_captured']:
            cap_r, cap_c, cap_piece = rec['ep_captured']
            self.board[cap_r][cap_c] = cap_piece

        self.white_king_moved = rec['prev_white_king_moved']
        self.black_king_moved = rec['prev_black_king_moved']
        self.white_rook_a_moved = rec['prev_white_rook_a_moved']
        self.white_rook_h_moved = rec['prev_white_rook_h_moved']
        self.black_rook_a_moved = rec['prev_black_rook_a_moved']
        self.black_rook_h_moved = rec['prev_black_rook_h_moved']
        self.en_passant_target = rec['prev_en_passant_target']
        self.side_to_move = rec['prev_side']

    # ---------- FEN 解析与导出 ----------
    @classmethod
    def from_fen(cls, fen: str):
        """从 FEN 字符串创建 Position 实例。"""
        parts = fen.strip().split()
        if len(parts) < 4:
            raise ValueError(f"Invalid FEN: {fen}")

        board_part = parts[0]
        side = parts[1]
        castling_part = parts[2]
        ep_part = parts[3]

        # 解析棋盘
        rows = board_part.split('/')
        board = []
        for r in range(8):
            row = []
            col = 0
            for ch in rows[r]:
                if ch.isdigit():
                    empty = int(ch)
                    row.extend([None] * empty)
                    col += empty
                else:
                    row.append(ch)
                    col += 1
            if col != 8:
                raise ValueError(f"Invalid FEN row {r}: {rows[r]}")
            board.append(row)

        # 解析易位权限
        white_king_moved = 'K' not in castling_part
        white_rook_h_moved = 'K' not in castling_part
        white_rook_a_moved = 'Q' not in castling_part
        black_king_moved = 'k' not in castling_part
        black_rook_h_moved = 'k' not in castling_part
        black_rook_a_moved = 'q' not in castling_part

        # 注意：如果 castling_part 为 '-'，所有易位权限都不可用
        if castling_part == '-':
            white_king_moved = white_rook_h_moved = white_rook_a_moved = True
            black_king_moved = black_rook_h_moved = black_rook_a_moved = True

        # 解析过路兵目标格
        en_passant_target = None
        if ep_part != '-':
            file = ord(ep_part[0]) - ord('a')
            rank = 8 - int(ep_part[1])
            en_passant_target = (rank, file)

        return cls(board, side,
                   white_king_moved, black_king_moved,
                   white_rook_a_moved, white_rook_h_moved,
                   black_rook_a_moved, black_rook_h_moved,
                   en_passant_target)

    def to_fen(self) -> str:
        """导出当前局面的 FEN 字符串。"""
        rows = []
        for r in range(8):
            row = ""
            empty = 0
            for c in range(8):
                p = self.board[r][c]
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += p
            if empty:
                row += str(empty)
            rows.append(row)
        board_part = "/".join(rows)

        # 易位权限
        castling = ""
        if not self.white_king_moved:
            if not self.white_rook_h_moved:
                castling += "K"
            if not self.white_rook_a_moved:
                castling += "Q"
        if not self.black_king_moved:
            if not self.black_rook_h_moved:
                castling += "k"
            if not self.black_rook_a_moved:
                castling += "q"
        if castling == "":
            castling = "-"

        # 过路兵
        ep = "-"
        if self.en_passant_target:
            r, c = self.en_passant_target
            file_char = "abcdefgh"[c]
            rank_char = str(8 - r)
            ep = file_char + rank_char

        # 半回合和全回合数暂未实现，默认 0 1
        return f"{board_part} {self.side_to_move} {castling} {ep} 0 1"


def get_all_move_fens(fen: str) -> List[str]:
    """输入一个 FEN，输出所有合法走法对应的 FEN 列表（标准化）。"""
    pos = Position.from_fen(fen)
    fens = []
    for move in pos.generate_moves():
        pos.make_move(move)
        fens.append(pos.to_fen())
        pos.undo_move()
    return fens