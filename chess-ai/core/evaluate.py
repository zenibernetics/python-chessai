'''
import torch
import torch.nn as nn
from .board import Position

# ========== 模型结构定义（必须与训练时一致） ==========
class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(781, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
    def forward(self, x):
        return self.net(x)

# ========== 全局加载模型 ==========
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = MLP().to(device)

# 尝试加载模型，如果文件不存在则抛出友好错误
try:
    state_dict = torch.load("tiny_mlp.pth", map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
except FileNotFoundError:
    print("警告: tiny_mlp.pth 未找到，评估将返回 0。请放置训练好的模型文件。")
    model = None

# ========== 辅助函数：FEN → 神经网络输入向量 ==========
def fen_to_mlp_input(fen: str) -> list:
    """
    将 FEN 字符串转换为 781 维输入向量，与训练时一致。
    格式: 64个格子 × 12种棋子 (one-hot) + 1个走棋方 + 4个易位权限 + 8个过路兵文件位。
    """
    pos = Position.from_fen(fen)
    x = [0.0] * 781

    piece_map = {
        'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
        'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11
    }

    for r in range(8):
        for c in range(8):
            p = pos.board[r][c]
            if p is None:
                continue
            sq = r * 8 + c
            idx = sq * 12 + piece_map[p]
            x[idx] = 1.0

    # 走棋方
    x[768] = 1.0 if pos.side_to_move == 'w' else 0.0

    # 易位权限
    x[769] = 0.0 if pos.white_king_moved or pos.white_rook_h_moved else 1.0
    x[770] = 0.0 if pos.white_king_moved or pos.white_rook_a_moved else 1.0
    x[771] = 0.0 if pos.black_king_moved or pos.black_rook_h_moved else 1.0
    x[772] = 0.0 if pos.black_king_moved or pos.black_rook_a_moved else 1.0

    # 过路兵文件
    if pos.en_passant_target:
        _, file = pos.en_passant_target
        x[773 + file] = 1.0

    return x

# ========== 评估函数 ==========
def evaluate_fen(fen: str) -> int:
    if model is None:
        return 0
    x = fen_to_mlp_input(fen)   # 传入 fen
    with torch.no_grad():
        x_tensor = torch.tensor(x, dtype=torch.float32).unsqueeze(0).to(device)
        raw = model(x_tensor).item()
    return int(raw)
'''
from __future__ import annotations
from .board import Position

# ========== 子力基础价值 ==========
PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
    'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': 0,
}

# ========== 你提供的中局表 (mg) ==========
PAWN_MG = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]
KNIGHT_MG = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  12,  12,  10,   0, -30,
    -30,   5,  12,  15,  15,  12,   5, -30,
    -30,   0,  12,  15,  15,  12,   0, -30,
    -30,   5,  10,  12,  12,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_MG = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,  10,   5,  10,  10,   5,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_MG = [
      0,   0,   0,   0,   0,   0,   0,   0,
      5,  10,  10,  10,  10,  10,  10,   5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      0,  -5,   0,   0,   0,   0,  -5,   0,
]
QUEEN_MG = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]
KING_MG = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20,
]

# ========== 你提供的残局表 (eg) ==========
PAWN_EG = [
     0,   0,   0,   0,   0,   0,   0,   0,
    80,  80,  80,  80,  80,  80,  80,  80,
    50,  50,  50,  50,  50,  50,  50,  50,
    30,  30,  30,  30,  30,  30,  30,  30,
    20,  20,  20,  20,  20,  20,  20,  20,
    10,  10,  10,  10,  10,  10,  10,  10,
     5,   5,   5,   5,   5,   5,   5,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]
KNIGHT_EG = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_EG = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,  10,  10,  10,  10,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_EG = [
      0,   0,   0,   0,   0,   0,   0,   0,
     10,  15,  15,  15,  15,  15,  15,  10,
      0,   5,   5,   5,   5,   5,   5,   0,
      0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,
]
QUEEN_EG = [
    -40, -30, -20, -10, -10, -20, -30, -40,
    -30, -20,   0,   0,   0,   0, -20, -30,
    -20,   0,  10,  10,  10,  10,   0, -20,
    -10,   0,  10,  15,  15,  10,   0, -10,
    -10,   0,  10,  15,  15,  10,   0, -10,
    -20,   0,  10,  10,  10,  10,   0, -20,
    -30, -20,   0,   0,   0,   0, -20, -30,
    -40, -30, -20, -10, -10, -20, -30, -40,
]
KING_EG = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

def _init_pst():
    pst = {}
    pst['P'] = (PAWN_MG, PAWN_EG)
    pst['N'] = (KNIGHT_MG, KNIGHT_EG)
    pst['B'] = (BISHOP_MG, BISHOP_EG)
    pst['R'] = (ROOK_MG, ROOK_EG)
    pst['Q'] = (QUEEN_MG, QUEEN_EG)
    pst['K'] = (KING_MG, KING_EG)
    return pst

PST = _init_pst()

# ========== 兵结构奖惩 ==========
DOUBLED_PAWN_PENALTY = -20
ISOLATED_PAWN_PENALTY = -15
PASSED_PAWN_BONUS = 30
PAWN_CHAIN_BONUS = 6
CENTER_PAWN_ADVANCE_BONUS = 12

# ========== 王安全 ==========
KING_SHIELD_BONUS = 20
KING_OPEN_FILE_PENALTY = -25

# ========== 残局将杀辅助 ==========
KING_PROXIMITY_BONUS = 8
CORNER_PENALTY = 4

# ---------- 辅助函数 ----------
def _piece_square_value(piece: str, sq: int, mg_phase: float, eg_phase: float) -> int:
    if piece == '.' or piece == ' ':
        return 0
    upper = piece.upper()
    if upper not in PST:
        return 0
    mg_table, eg_table = PST[upper]
    val_mg = mg_table[sq]
    val_eg = eg_table[sq]
    if piece.isupper():
        return int(val_mg * mg_phase + val_eg * eg_phase)
    else:
        flipped = sq ^ 56
        return -int(val_mg * mg_phase + val_eg * eg_phase)

def _is_passed_pawn(board, row: int, col: int, color: str) -> bool:
    step = -1 if color == 'w' else 1
    r = row + step
    while 0 <= r < 8:
        for dc in (-1, 0, 1):
            c = col + dc
            if 0 <= c < 8 and board[r][c] and board[r][c].lower() == 'p':
                return False
        r += step
    return True

def _pawn_structure_and_chain(board, color: str) -> int:
    pawns = [(r, c) for r in range(8) for c in range(8)
             if board[r][c] == ('P' if color == 'w' else 'p')]
    if not pawns:
        return 0
    score = 0
    from collections import Counter
    files = [c for (_, c) in pawns]
    for f, cnt in Counter(files).items():
        if cnt > 1:
            score += DOUBLED_PAWN_PENALTY * (cnt - 1)
    pawn_set = set(pawns)
    for r, c in pawns:
        has_neighbor = any((r, c + dc) in pawn_set for dc in (-1, 1) if 0 <= c + dc < 8)
        if not has_neighbor:
            score += ISOLATED_PAWN_PENALTY
        if _is_passed_pawn(board, r, c, color):
            score += PASSED_PAWN_BONUS
        if color == 'w':
            if (r - 1, c - 1) in pawn_set or (r - 1, c + 1) in pawn_set:
                score += PAWN_CHAIN_BONUS
        else:
            if (r + 1, c - 1) in pawn_set or (r + 1, c + 1) in pawn_set:
                score += PAWN_CHAIN_BONUS
    return score

def _center_pawn_advance(board, color: str, mg_factor: float) -> int:
    if mg_factor <= 0.3:
        return 0
    score = 0
    if color == 'w':
        for r in range(4, 8):
            for c in (2, 3, 4, 5):
                if board[r][c] == 'P':
                    score += CENTER_PAWN_ADVANCE_BONUS
                    break
    else:
        for r in range(4, -1, -1):
            for c in (2, 3, 4, 5):
                if board[r][c] == 'p':
                    score -= CENTER_PAWN_ADVANCE_BONUS
                    break
    return score

def _king_safety_one(board, color: str, king_pos) -> int:
    if king_pos is None:
        return 0
    kr, kc = king_pos
    score = 0
    front_row = kr - 1 if color == 'w' else kr + 1
    for dc in (-1, 0, 1):
        nc = kc + dc
        if 0 <= front_row < 8 and 0 <= nc < 8:
            p = board[front_row][nc]
            if p and p.lower() == 'p' and (p.isupper() == (color == 'w')):
                score += KING_SHIELD_BONUS
    has_pawn_on_file = any(board[r][kc] and board[r][kc].lower() == 'p'
                           and (board[r][kc].isupper() == (color == 'w'))
                           for r in range(8))
    if not has_pawn_on_file:
        score += KING_OPEN_FILE_PENALTY
    return score

def _king_endgame_bonus(board, wk_pos, bk_pos, side: str, eg_factor: float) -> int:
    if eg_factor <= 0.3:
        return 0
    if side == 'w':
        my_king, opp_king = wk_pos, bk_pos
    else:
        my_king, opp_king = bk_pos, wk_pos
    if my_king is None or opp_king is None:
        return 0
    dist = abs(my_king[0] - opp_king[0]) + abs(my_king[1] - opp_king[1])
    king_prox = (14 - dist) * KING_PROXIMITY_BONUS
    opp_r, opp_c = opp_king
    center_dist = abs(opp_r - 3.5) + abs(opp_c - 3.5)
    corner_penalty = (7 - center_dist) * CORNER_PENALTY
    return (king_prox + corner_penalty) * eg_factor

# ---------- 核心评估函数（接收 Position 对象） ----------
def evaluate(position: Position) -> int:
    moves = position.generate_moves()
    if len(moves) == 0:
        if position.is_check():
            return -20000 if position.side_to_move == 'w' else 20000
        return 0

    board = position.board

    phase_total = 0
    for row in board:
        for p in row:
            if not p: continue
            up = p.upper()
            if up in ('N', 'B'): phase_total += 1
            elif up == 'R': phase_total += 2
            elif up == 'Q': phase_total += 4
    phase_total = min(24, phase_total)
    mg_factor = phase_total / 24.0
    eg_factor = 1.0 - mg_factor

    score = 0

    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if not p:
                continue
            sq = r * 8 + c
            score += PIECE_VALUES[p]
            score += _piece_square_value(p, sq, mg_factor, eg_factor)

    w_pawn = _pawn_structure_and_chain(board, 'w')
    b_pawn = _pawn_structure_and_chain(board, 'b')
    pawn_weight = 0.7 * mg_factor + 1.0 * eg_factor
    score += (w_pawn - b_pawn) * pawn_weight

    score += _center_pawn_advance(board, 'w', mg_factor)
    score -= _center_pawn_advance(board, 'b', mg_factor)

    original_side = position.side_to_move
    position.side_to_move = 'w'
    white_moves = len(position.generate_moves())
    position.side_to_move = 'b'
    black_moves = len(position.generate_moves())
    position.side_to_move = original_side
    mobility_score = (white_moves - black_moves) * 3
    score += mobility_score * (0.8 * mg_factor + 0.4 * eg_factor)

    wk_pos = position._find_king('w')
    bk_pos = position._find_king('b')
    w_safety = _king_safety_one(board, 'w', wk_pos) if wk_pos else 0
    b_safety = _king_safety_one(board, 'b', bk_pos) if bk_pos else 0
    safety_score = w_safety - b_safety
    score += safety_score * (0.5 * mg_factor)

    side = position.side_to_move
    score += _king_endgame_bonus(board, wk_pos, bk_pos, side, eg_factor)

    return int(score)


# ========== 对外接口：与 MLP 版本完全兼容 ==========
def evaluate_fen(fen: str) -> int:
    """
    输入 FEN 字符串，返回评估分数（正数表示白方有利，负数表示黑方有利）。
    """
    pos = Position.from_fen(fen)
    return evaluate(pos)