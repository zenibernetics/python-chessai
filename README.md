# python-chessai
my first vibe coding pj after the college entrance exam
which use pure python and finally get 1500 elo

Chess AI
A chess engine with a traditional evaluation function and optional neural network scoring, alpha-beta search enhanced with history heuristic, transposition table, Zobrist hashing, and an opening book stub.

Features
Board Representation – Position class with FEN parsing, move generation, and Zobrist hashing.

Evaluation – Hybrid material + piece-square tables with game‑phase interpolation (middle‑game / end‑game). Includes pawn structure, king safety, mobility, and endgame king proximity bonuses.
Optionally, a pretrained MLP (tiny_mlp.pth) can be used for evaluation via the same evaluate_fen interface.

Search – Alpha‑beta with:

History heuristic – orders moves based on history scores.

Transposition table – caches evaluated positions using Zobrist keys.

Zobrist hashing – Position.zobrist_hash() generates a 64‑bit signature for each board state.

Late Move Reduction (LMR) – placeholder comments for future implementation.

Opening book – stub function to return predefined moves from a book file (book.bin).

Graphical Interface – simple GUI 

Usage
Run the GUI
bash
python main.py
This starts the chess board. You can play as White or Black against the AI, or let the AI play against itself.

Command‑line testing
You can evaluate a position from FEN using:

python
from core.evaluate import evaluate_fen
score = evaluate_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
print(score)   # positive = White advantage
Search depth
The AI’s search depth can be adjusted in alphabeta.py (default is 4). You can change it via the GUI settings or directly in the code.

Project Structure
text
chess-ai/
├── core/
│   ├── alphabeta.py      # Alpha‑beta search with history, TT, Zobrist, LMR stubs, opening book stub
│   ├── board.py          # Position class – board state, move generation, FEN, Zobrist hash
│   ├── evaluate.py       # Traditional evaluation + evaluate_fen wrapper (supports MLP fallback)
│   ├── gui.py            # Graphical interface (Tkinter / Pygame)
│   └── test.py           # Unit tests (if any)
├── book1.bin             # Opening book file (binary format, used by opening book stub)
├── tiny_mlp.pth          # Pretrained neural network weights (optional)
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies (recommended)
└── README.md             # This file
Key Modules
core/board.py
Position class

from_fen() / to_fen()

generate_moves() – generates legal moves for current side

zobrist_hash() – returns a 64‑bit hash of the position (Zobrist)

is_check() – tests whether the current side is in check

core/evaluate.py
evaluate(position) – returns a score in centipawns (positive = White advantage)

evaluate_fen(fen) – convenience wrapper

Traditional features: material, PST, pawn structure, mobility, king safety, endgame bonuses

If tiny_mlp.pth exists, you can swap to the MLP evaluator by modifying the import (the code currently uses the traditional one).

core/alphabeta.py
alpha_beta(position, depth, alpha, beta, maximizing) – main search function

History heuristic – uses history_table[move.from_sq][move.to_sq] to order moves

Transposition table – stores score, depth, and best move for each Zobrist key

Zobrist hashing – integrated for TT lookups

LMR – commented sections show where to apply late move reductions

Opening book – get_opening_move(position) is a placeholder; you can load book1.bin there

Configuration
Search depth – change DEPTH in alphabeta.py or pass it as an argument.

TT size – adjust TT_SIZE in alphabeta.py (default 1,000,000 entries).

History table – history_table is a 64×64 integer array; updates after each successful cut‑off.

Future Improvements
Complete LMR implementation with reduction rules based on move type and depth.

Load an actual opening book from book1.bin (polyglot format or custom).

Add more advanced evaluation terms (e.g., bishop pair, rook on open files).

Implement iterative deepening with time management.

Support UCI protocol for use with chess GUIs like Arena or Cute Chess.

License
This project is open‑source and available under the MIT License. See LICENSE for details.

Credits
Developed as a learning project for chess AI algorithms.
Traditional evaluation tables inspired by Stockfish and PeSTO.

Enjoy the game!
If you find any issues, feel free to open an issue or submit a pull request.

