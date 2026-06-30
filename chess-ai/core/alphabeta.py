# core/alphabeta.py

import random
from typing import Optional, Tuple, List, Dict
from core.board import Position, Move
from core.evaluate import evaluate_fen

# ---------------------------- 常量 ----------------------------
MATE_SCORE = 100000
MAX_PLY = 128
MAX_HISTORY = 64 * 64  # 历史表大小

# ---------------------------- Zobrist 哈希 ----------------------------
# 使用固定种子确保可重复性
random.seed(12345)

# 12种棋子: 大写白方, 小写黑方, 顺序同 piece_map
PIECES = ['P', 'N', 'B', 'R', 'Q', 'K', 'p', 'n', 'b', 'r', 'q', 'k']
PIECE_INDEX = {p: i for i, p in enumerate(PIECES)}

zobrist_piece = [[random.getrandbits(64) for _ in range(12)] for _ in range(64)]
zobrist_side = random.getrandbits(64)
zobrist_castling = [random.getrandbits(64) for _ in range(4)]  # K, Q, k, q
zobrist_ep = [random.getrandbits(64) for _ in range(8)]        # 过路兵文件

def zobrist_hash(pos: Position) -> int:
    """计算局面的Zobrist哈希值"""
    h = 0
    board = pos.board
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p is not None:
                idx = r * 8 + c
                h ^= zobrist_piece[idx][PIECE_INDEX[p]]
    # 走棋方
    if pos.side_to_move == 'w':
        h ^= zobrist_side
    # 易位权限
    if not pos.white_king_moved and not pos.white_rook_h_moved:
        h ^= zobrist_castling[0]   # K
    if not pos.white_king_moved and not pos.white_rook_a_moved:
        h ^= zobrist_castling[1]   # Q
    if not pos.black_king_moved and not pos.black_rook_h_moved:
        h ^= zobrist_castling[2]   # k
    if not pos.black_king_moved and not pos.black_rook_a_moved:
        h ^= zobrist_castling[3]   # q
    # 过路兵
    if pos.en_passant_target is not None:
        _, file = pos.en_passant_target
        h ^= zobrist_ep[file]
    return h

# ---------------------------- 评估函数 ----------------------------


# ---------------------------- 走法子力价值 ----------------------------
PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000
}

def get_piece_value(piece: str) -> int:
    return PIECE_VALUES.get(piece, 0)

# ---------------------------- 全局搜索数据结构 ----------------------------
transposition_table: Dict[int, dict] = {}
history_table = [[[0] * 64 for _ in range(64)] for _ in range(2)]  # [side][from][to]
killer_moves = [[None for _ in range(MAX_PLY)] for _ in range(2)]  # [killer_index][ply]

# ---------------------------- 走法排序 ----------------------------
def move_ordering_key(move: Move, pos: Position, ply: int, tt_move: Optional[Move]) -> int:
    """为走法生成排序键（越大越优先）"""
    key = 0
    # 1. 置换表最佳走法（最高优先级）
    if tt_move is not None and move == tt_move:
        key += 1000000
    # 2. 吃子走法 (MVV-LVA)
    target = pos.board[move.to_row][move.to_col]
    if target is not None:
        attacker = pos.board[move.from_row][move.from_col]
        victim_value = get_piece_value(target)
        attacker_value = get_piece_value(attacker)
        key += 100000 + victim_value * 10 - attacker_value
    # 3. 升变走法
    if move.promotion is not None:
        prom_value = get_piece_value(move.promotion.upper())
        key += 9000 + prom_value
    # 4. 杀手走法
    if move == killer_moves[0][ply] or move == killer_moves[1][ply]:
        key += 8000
    # 5. 历史表分数
    side_idx = 0 if pos.side_to_move == 'w' else 1
    from_idx = move.from_row * 8 + move.from_col
    to_idx = move.to_row * 8 + move.to_col
    key += history_table[side_idx][from_idx][to_idx]
    return key

def sort_moves(moves: List[Move], pos: Position, ply: int, tt_move: Optional[Move]) -> List[Move]:
    """对走法列表排序（降序）"""
    return sorted(moves, key=lambda m: move_ordering_key(m, pos, ply, tt_move), reverse=True)

# ---------------------------- 核心搜索 ----------------------------
# core/alphabeta.py

import random
import torch
from typing import Optional, Tuple, List, Dict
from core.board import Position, Move


# ---------------------------- 常量 ----------------------------
MATE_SCORE = 100000
MAX_PLY = 128
MAX_HISTORY = 64 * 64  # 历史表大小

# ---------------------------- Zobrist 哈希 ----------------------------
# 使用固定种子确保可重复性
random.seed(12345)

# 12种棋子: 大写白方, 小写黑方, 顺序同 piece_map
PIECES = ['P', 'N', 'B', 'R', 'Q', 'K', 'p', 'n', 'b', 'r', 'q', 'k']
PIECE_INDEX = {p: i for i, p in enumerate(PIECES)}

zobrist_piece = [[random.getrandbits(64) for _ in range(12)] for _ in range(64)]
zobrist_side = random.getrandbits(64)
zobrist_castling = [random.getrandbits(64) for _ in range(4)]  # K, Q, k, q
zobrist_ep = [random.getrandbits(64) for _ in range(8)]        # 过路兵文件

def zobrist_hash(pos: Position) -> int:
    """计算局面的Zobrist哈希值"""
    h = 0
    board = pos.board
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p is not None:
                idx = r * 8 + c
                h ^= zobrist_piece[idx][PIECE_INDEX[p]]
    # 走棋方
    if pos.side_to_move == 'w':
        h ^= zobrist_side
    # 易位权限
    if not pos.white_king_moved and not pos.white_rook_h_moved:
        h ^= zobrist_castling[0]   # K
    if not pos.white_king_moved and not pos.white_rook_a_moved:
        h ^= zobrist_castling[1]   # Q
    if not pos.black_king_moved and not pos.black_rook_h_moved:
        h ^= zobrist_castling[2]   # k
    if not pos.black_king_moved and not pos.black_rook_a_moved:
        h ^= zobrist_castling[3]   # q
    # 过路兵
    if pos.en_passant_target is not None:
        _, file = pos.en_passant_target
        h ^= zobrist_ep[file]
    return h

# ---------------------------- 走法子力价值 ----------------------------
PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000
}

def get_piece_value(piece: str) -> int:
    return PIECE_VALUES.get(piece, 0)

# ---------------------------- 全局搜索数据结构 ----------------------------
transposition_table: Dict[int, dict] = {}
history_table = [[[0] * 64 for _ in range(64)] for _ in range(2)]  # [side][from][to]
killer_moves = [[None for _ in range(MAX_PLY)] for _ in range(2)]  # [killer_index][ply]

# ---------------------------- 走法排序 ----------------------------
def move_ordering_key(move: Move, pos: Position, ply: int, tt_move: Optional[Move]) -> int:
    """为走法生成排序键（越大越优先）"""
    key = 0
    # 1. 置换表最佳走法（最高优先级）
    if tt_move is not None and move == tt_move:
        key += 1000000
    # 2. 吃子走法 (MVV-LVA)
    target = pos.board[move.to_row][move.to_col]
    if target is not None:
        attacker = pos.board[move.from_row][move.from_col]
        victim_value = get_piece_value(target)
        attacker_value = get_piece_value(attacker)
        key += 100000 + victim_value * 10 - attacker_value
    # 3. 升变走法
    if move.promotion is not None:
        prom_value = get_piece_value(move.promotion.upper())
        key += 9000 + prom_value
    # 4. 杀手走法
    if move == killer_moves[0][ply] or move == killer_moves[1][ply]:
        key += 8000
    # 5. 历史表分数
    side_idx = 0 if pos.side_to_move == 'w' else 1
    from_idx = move.from_row * 8 + move.from_col
    to_idx = move.to_row * 8 + move.to_col
    key += history_table[side_idx][from_idx][to_idx]
    return key

def sort_moves(moves: List[Move], pos: Position, ply: int, tt_move: Optional[Move]) -> List[Move]:
    """对走法列表排序（降序）"""
    return sorted(moves, key=lambda m: move_ordering_key(m, pos, ply, tt_move), reverse=True)

# ---------------------------- 核心搜索 ----------------------------
def alpha_beta(pos: Position, depth: int, alpha: int, beta: int,
               ply: int, counts: Dict[int, int]) -> Tuple[int, Optional[Move]]:
    global nodes_searched, current_move_index
    nodes_searched += 1

    # 1. 终局检测
    moves = pos.generate_moves()
    if not moves:
        if pos.is_check():
            return -(MATE_SCORE - ply), None
        else:
            return 0, None

    # 2. 叶子
    if depth <= 0:
        if pos.is_check():
            # 将军延伸，强制至少搜索1层
            depth = 1
        else:
            score = evaluate_fen(pos.to_fen())  # 使用 evaluate_fen
            if pos.side_to_move == 'b':
                score = -score
            return score, None

    # 3. 重复检测
    h = zobrist_hash(pos)
    counts[h] = counts.get(h, 0) + 1
    if counts[h] >= 3:
        counts[h] -= 1
        return 0, None

    # 4. 置换表探测
    entry = transposition_table.get(h)
    tt_move = None
    if entry is not None and entry['depth'] >= depth:
        if entry['flag'] == 'exact':
            counts[h] -= 1
            return entry['score'], entry.get('move')
        elif entry['flag'] == 'lower' and entry['score'] >= beta:
            counts[h] -= 1
            return entry['score'], entry.get('move')
        elif entry['flag'] == 'upper' and entry['score'] <= alpha:
            counts[h] -= 1
            return entry['score'], entry.get('move')
        tt_move = entry.get('move')

    # 5. 走法排序
    moves = sort_moves(moves, pos, ply, tt_move)

    best_move = None
    move_idx = 0
    for move in moves:
        # 检查停止标志
        if stop_search:
            counts[h] -= 1
            return alpha, best_move

        # 更新进度（仅根节点）
        if ply == 0:
            current_move_index = move_idx

        # 执行走法
        pos.make_move(move)
        gives_check = pos.is_check()
        # 判断是否为安静走法（非吃子、非升变）
        is_quiet = (pos.board[move.to_row][move.to_col] is None) and (move.promotion is None)
        # 注意：这里判断是否安静必须在吃子检测之后，因为吃子后目标格有棋子

        if move_idx == 0:
            # 首选走法：全窗口搜索
            score, _ = alpha_beta(pos, depth - 1, -beta, -alpha, ply + 1, counts)
            score = -score
        else:
            # LMR 条件
            lmr_condition = (move_idx >= 4 and depth >= 3 and is_quiet and not gives_check
                             and (tt_move is None or move != tt_move))
            if lmr_condition:
                reduction = 1
                if move_idx > 8:
                    reduction += 1
                if depth > 4:
                    reduction += 1
                reduction = min(reduction, depth - 1)
                score, _ = alpha_beta(pos, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, counts)
                score = -score
                if score > alpha:
                    score, _ = alpha_beta(pos, depth - 1, -beta, -alpha, ply + 1, counts)
                    score = -score
            else:
                # PVS: 零窗口搜索
                score, _ = alpha_beta(pos, depth - 1, -alpha - 1, -alpha, ply + 1, counts)
                score = -score
                if score > alpha and score < beta:
                    score, _ = alpha_beta(pos, depth - 1, -beta, -alpha, ply + 1, counts)
                    score = -score

        pos.undo_move()

        if score > alpha:
            alpha = score
            best_move = move

        # beta 剪枝
        if alpha >= beta:
            # 更新历史表（只对安静走法）
            if is_quiet and not gives_check and move.promotion is None:
                side_idx = 0 if pos.side_to_move == 'w' else 1
                from_idx = move.from_row * 8 + move.from_col
                to_idx = move.to_row * 8 + move.to_col
                history_table[side_idx][from_idx][to_idx] += depth * depth
                # 更新杀手走法
                if pos.board[move.to_row][move.to_col] is None and move.promotion is None:
                    if killer_moves[0][ply] != move:
                        killer_moves[1][ply] = killer_moves[0][ply]
                        killer_moves[0][ply] = move
            break

        move_idx += 1

    # 存储置换表
    flag = 'exact'
    if alpha >= beta:
        flag = 'lower'
    elif best_move is None:
        flag = 'upper'
    transposition_table[h] = {
        'depth': depth,
        'score': alpha,
        'flag': flag,
        'move': best_move
    }

    counts[h] -= 1
    return alpha, best_move

# ---------------------------- 对外接口 ----------------------------
def search_best_move(pos: Position, depth: int) -> Tuple[Optional[Move], int]:
    """
    搜索最佳走法
    返回 (最佳走法, 分数)
    """
    # 清空置换表、历史表、杀手表（可选择性清空，这里为简单，每次搜索重置）
    # 注意：实际中可不清空，但为了调试，我们重置
    global transposition_table, history_table, killer_moves
    transposition_table.clear()
    history_table = [[[0] * 64 for _ in range(64)] for _ in range(2)]
    killer_moves = [[None for _ in range(MAX_PLY)] for _ in range(2)]

    score, best_move = alpha_beta(pos, depth, -MATE_SCORE, MATE_SCORE, 0, {})
    return best_move, score

# 示例：如果直接运行，可进行简单测试
if __name__ == "__main__":
    # 简单的自测：初始局面深度4
    pos = Position()
    move, score = search_best_move(pos, 4)
    print(f"Best move: {move}, score: {score}")
# ---------------------------- 对外接口 ----------------------------
def search_best_move(pos: Position, depth: int) -> Tuple[Optional[Move], int]:
    """
    搜索最佳走法
    返回 (最佳走法, 分数)
    """
    # 清空置换表、历史表、杀手表（可选择性清空，这里为简单，每次搜索重置）
    # 注意：实际中可不清空，但为了调试，我们重置
    global transposition_table, history_table, killer_moves
    transposition_table.clear()
    history_table = [[[0] * 64 for _ in range(64)] for _ in range(2)]
    killer_moves = [[None for _ in range(MAX_PLY)] for _ in range(2)]

    score, best_move = alpha_beta(pos, depth, -MATE_SCORE, MATE_SCORE, 0, {})
    return best_move, score

stop_search = False
nodes_searched = 0
current_move_index = 0
total_moves = 0

def set_stop_flag(val: bool):
    global stop_search
    stop_search = val

def clear_stop_flag():
    global stop_search
    stop_search = False

def reset_progress():
    global nodes_searched, current_move_index, total_moves
    nodes_searched = 0
    current_move_index = 0
    total_moves = 0

def init_root_progress(depth: int, move_count: int):
    global total_moves, current_move_index, nodes_searched
    total_moves = move_count
    current_move_index = 0
    nodes_searched = 0

def get_root_progress():
    return current_move_index, total_moves

def get_nodes():
    return nodes_searched

