import json
import random
import sys
import time
from collections import deque

import pygame

# ---------------- Configuration ----------------
DIFFICULTIES = {"beginner": (9, 9, 10), "intermediate": (16, 16, 40)}
CELL = 32
HUD = 60
MAX_TIMER = 999
MAX_ATTEMPTS = 2000
NUM_COLOURS = {1: (0, 0, 255), 2: (0, 128, 0), 3: (255, 0, 0), 4: (0, 0, 128),
               5: (128, 0, 0), 6: (0, 128, 128), 7: (0, 0, 0), 8: (100, 100, 100)}


# ---------------- Cell ----------------
class Cell:
    def __init__(self, row, col):
        self.row, self.col = row, col
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0

    def toggle_flag(self):
        if not self.is_revealed:
            self.is_flagged = not self.is_flagged


# ---------------- Board ----------------
class Board:
    def __init__(self, rows, cols, total_mines):
        self.rows, self.cols, self.total_mines = rows, cols, total_mines
        self.grid = [[Cell(r, c) for c in range(cols)] for r in range(rows)]
        self.revealed_safe_count = 0

    def get_neighbors(self, row, col):
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and 0 <= row + dr < self.rows and 0 <= col + dc < self.cols:
                    result.append(self.grid[row + dr][col + dc])
        return result

    def place_mines(self, safe_row, safe_col):
        banned = {(safe_row, safe_col)} | {(n.row, n.col) for n in self.get_neighbors(safe_row, safe_col)}
        placed = 0
        while placed < self.total_mines:
            r, c = random.randint(0, self.rows - 1), random.randint(0, self.cols - 1)
            if (r, c) not in banned and not self.grid[r][c].is_mine:
                self.grid[r][c].is_mine = True
                placed += 1

    def calculate_adjacency(self):
        for row in self.grid:
            for cell in row:
                if not cell.is_mine:
                    cell.adjacent_mines = sum(n.is_mine for n in self.get_neighbors(cell.row, cell.col))

    def reveal(self, row, col):
        """Returns True if a mine was hit. Uses iterative BFS flood fill."""
        start = self.grid[row][col]
        if start.is_revealed or start.is_flagged:
            return False
        if start.is_mine:
            start.is_revealed = True
            return True
        queue = deque([start])
        start.is_revealed = True
        self.revealed_safe_count += 1
        while queue:
            cur = queue.popleft()
            if cur.adjacent_mines == 0:
                for n in self.get_neighbors(cur.row, cur.col):
                    if not n.is_revealed and not n.is_flagged and not n.is_mine:
                        n.is_revealed = True
                        self.revealed_safe_count += 1
                        queue.append(n)
        return False

    def chord(self, row, col):
        """Returns True if a mine was hit."""
        cell = self.grid[row][col]
        if not cell.is_revealed or cell.adjacent_mines == 0:
            return False
        neighbors = self.get_neighbors(row, col)
        if sum(n.is_flagged for n in neighbors) != cell.adjacent_mines:
            return False
        hit = False
        for n in neighbors:
            if not n.is_flagged and not n.is_revealed:
                if self.reveal(n.row, n.col):
                    hit = True
        return hit

    def check_win(self):
        return self.revealed_safe_count == self.rows * self.cols - self.total_mines

    def flags_placed(self):
        return sum(c.is_flagged for row in self.grid for c in row)


# ---------------- Solver (no-guess validation) ----------------
class Solver:
    """Simulates a perfect logical player using single-cell and subset rules.
    Works on its own sets, so it never alters the Board's cells."""

    def __init__(self, board):
        self.board = board
        self.revealed = set()
        self.mines = set()

    def _reveal(self, r, c):
        stack = [(r, c)]
        while stack:
            r, c = stack.pop()
            if (r, c) in self.revealed or (r, c) in self.mines:
                continue
            self.revealed.add((r, c))
            if self.board.grid[r][c].adjacent_mines == 0:
                for n in self.board.get_neighbors(r, c):
                    if (n.row, n.col) not in self.revealed:
                        stack.append((n.row, n.col))

    def _constraints(self):
        cons = []
        for (r, c) in self.revealed:
            cell = self.board.grid[r][c]
            if cell.adjacent_mines == 0:
                continue
            unknown = frozenset((n.row, n.col) for n in self.board.get_neighbors(r, c)
                                if (n.row, n.col) not in self.revealed and (n.row, n.col) not in self.mines)
            need = cell.adjacent_mines - sum((n.row, n.col) in self.mines for n in self.board.get_neighbors(r, c))
            if unknown:
                cons.append((r, c, unknown, need))
        return cons

    def single_cell_pass(self, cons):
        progress = False
        for (_, _, unknown, need) in cons:
            if need == 0:
                for (r, c) in unknown:
                    if (r, c) not in self.revealed:
                        self._reveal(r, c)
                        progress = True
            elif need == len(unknown):
                new = unknown - self.mines
                if new:
                    self.mines |= new
                    progress = True
        return progress

    def subset_pass(self, cons):
        progress = False
        for a in cons:
            for b in cons:
                if a is b or abs(a[0] - b[0]) > 2 or abs(a[1] - b[1]) > 2:
                    continue
                if a[2] < b[2]:  # proper subset
                    diff, dn = b[2] - a[2], b[3] - a[3]
                    if dn == 0:
                        for (r, c) in diff:
                            if (r, c) not in self.revealed:
                                self._reveal(r, c)
                                progress = True
                    elif dn == len(diff) and not diff <= self.mines:
                        self.mines |= diff
                        progress = True
            if progress:
                return True
        return progress

    def is_board_solvable(self, start_row, start_col):
        self._reveal(start_row, start_col)
        while True:
            cons = self._constraints()
            if self.single_cell_pass(cons):
                continue
            if self.subset_pass(cons):
                continue
            break
        safe_total = self.board.rows * self.board.cols - self.board.total_mines
        return len(self.revealed) == safe_total


def generate_no_guess_board(rows, cols, mines, sr, sc):
    board = None
    for _ in range(MAX_ATTEMPTS):
        board = Board(rows, cols, mines)
        board.place_mines(sr, sc)
        board.calculate_adjacency()
        if Solver(board).is_board_solvable(sr, sc):
            return board, True
    return board, False  # fallback: last candidate


# ---------------- Score Manager ----------------
class ScoreManager:
    def __init__(self, filepath="stats.json"):
        self.filepath = filepath
        self.stats = self.load_stats()

    @staticmethod
    def _default():
        return {d: {"games_played": 0, "games_won": 0, "best_time_seconds": None,
                    "current_streak": 0, "longest_streak": 0} for d in DIFFICULTIES}

    def _valid(self, data):
        if not isinstance(data, dict):
            return False
        for d in DIFFICULTIES:
            if d not in data or not isinstance(data[d], dict):
                return False
            if set(data[d].keys()) != set(self._default()[d].keys()):
                return False
        return True

    def load_stats(self):
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
            if self._valid(data):
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        data = self._default()
        self.stats = data
        self.save_stats()
        return data

    def save_stats(self):
        with open(self.filepath, "w") as f:
            json.dump(self.stats, f, indent=2)

    def record_game(self, difficulty, won, time_taken):
        s = self.stats[difficulty]
        s["games_played"] += 1
        if won:
            s["games_won"] += 1
            s["current_streak"] += 1
            s["longest_streak"] = max(s["longest_streak"], s["current_streak"])
            if s["best_time_seconds"] is None or time_taken < s["best_time_seconds"]:
                s["best_time_seconds"] = time_taken
        else:
            s["current_streak"] = 0
        self.save_stats()


# ---------------- GUI / Game ----------------
class Game:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.big = pygame.font.SysFont("consolas", 30, bold=True)
        self.small = pygame.font.SysFont("arial", 14)
        self.scores = ScoreManager()
        self.difficulty = "beginner"
        self.new_game()

    def new_game(self):
        rows, cols, mines = DIFFICULTIES[self.difficulty]
        self.rows, self.cols, self.mines = rows, cols, mines
        self.board = Board(rows, cols, mines)  # empty until first click
        self.state = "START"  # START, PLAYING, WON, LOST
        self.start_time = 0
        self.final_time = 0
        self.screen = pygame.display.set_mode((max(cols * CELL, 300), rows * CELL + HUD + 40))
        pygame.display.set_caption("No-Guess Minesweeper")
        self.restart_rect = pygame.Rect(self.screen.get_width() // 2 - 20, 10, 40, 40)

    def elapsed(self):
        if self.state == "PLAYING":
            return min(MAX_TIMER, int(time.time() - self.start_time))
        if self.state in ("WON", "LOST"):
            return self.final_time
        return 0

    def end_game(self, won):
        self.final_time = self.elapsed()
        self.state = "WON" if won else "LOST"
        self.scores.record_game(self.difficulty, won, self.final_time)

    def handle_click(self, pos, button):
        x, y = pos
        if button == 1 and self.restart_rect.collidepoint(pos):
            self.new_game()
            return
        if self.state in ("WON", "LOST") or y < HUD:
            return
        col, row = x // CELL, (y - HUD) // CELL
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        cell = self.board.grid[row][col]

        if button == 3 and self.state == "PLAYING":
            cell.toggle_flag()
        elif button == 1:
            if self.state == "START":
                self.board, _ = generate_no_guess_board(self.rows, self.cols, self.mines, row, col)
                self.state = "PLAYING"
                self.start_time = time.time()
            hit = self.board.chord(row, col) if cell.is_revealed else self.board.reveal(row, col)
            if hit:
                self.end_game(False)
            elif self.board.check_win():
                self.end_game(True)
        elif button == 2 and self.state == "PLAYING":
            if self.board.chord(row, col):
                self.end_game(False)
            elif self.board.check_win():
                self.end_game(True)

    def draw_hud(self):
        pygame.draw.rect(self.screen, (60, 60, 60), (0, 0, self.screen.get_width(), HUD))
        flags_left = self.mines - self.board.flags_placed()
        left = self.big.render(f"{flags_left:03d}", True, (255, 40, 40))
        right = self.big.render(f"{self.elapsed():03d}", True, (255, 40, 40))
        self.screen.blit(left, (10, 12))
        self.screen.blit(right, (self.screen.get_width() - right.get_width() - 10, 12))
        pygame.draw.rect(self.screen, (200, 200, 0), self.restart_rect, border_radius=20)
        face = {"WON": "B)", "LOST": "X(", }.get(self.state, ":)")
        t = self.font.render(face, True, (0, 0, 0))
        self.screen.blit(t, t.get_rect(center=self.restart_rect.center))

    def draw_grid(self):
        for row in self.board.grid:
            for c in row:
                rect = pygame.Rect(c.col * CELL, HUD + c.row * CELL, CELL, CELL)
                lost = self.state == "LOST"
                if c.is_revealed:
                    colour = (255, 0, 0) if c.is_mine else (215, 215, 215)
                    pygame.draw.rect(self.screen, colour, rect)
                    if c.is_mine:
                        pygame.draw.circle(self.screen, (0, 0, 0), rect.center, CELL // 4)
                    elif c.adjacent_mines:
                        txt = self.font.render(str(c.adjacent_mines), True, NUM_COLOURS[c.adjacent_mines])
                        self.screen.blit(txt, txt.get_rect(center=rect.center))
                else:
                    pygame.draw.rect(self.screen, (150, 150, 150), rect)
                    if lost and c.is_mine and not c.is_flagged:
                        pygame.draw.circle(self.screen, (0, 0, 0), rect.center, CELL // 4)
                    if c.is_flagged:
                        pygame.draw.polygon(self.screen, (220, 0, 0), [
                            (rect.x + 10, rect.y + 7), (rect.x + 24, rect.y + 13), (rect.x + 10, rect.y + 19)])
                        pygame.draw.line(self.screen, (0, 0, 0), (rect.x + 10, rect.y + 7), (rect.x + 10, rect.y + 25), 2)
                        if lost and not c.is_mine:
                            pygame.draw.line(self.screen, (0, 0, 0), rect.topleft, rect.bottomright, 3)
                            pygame.draw.line(self.screen, (0, 0, 0), rect.topright, rect.bottomleft, 3)
                pygame.draw.rect(self.screen, (90, 90, 90), rect, 1)

    def draw_footer(self):
        s = self.scores.stats[self.difficulty]
        best = s["best_time_seconds"] if s["best_time_seconds"] is not None else "-"
        msg = (f"{self.difficulty.title()} | Won {s['games_won']}/{s['games_played']} | "
               f"Best {best}s | Streak {s['current_streak']}   [1] Beginner [2] Intermediate [R] Restart")
        y = HUD + self.rows * CELL + 12
        self.screen.blit(self.small.render(msg, True, (255, 255, 255)), (6, y))

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos, event.button)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.new_game()
                    elif event.key == pygame.K_1:
                        self.difficulty = "beginner"
                        self.new_game()
                    elif event.key == pygame.K_2:
                        self.difficulty = "intermediate"
                        self.new_game()
            self.screen.fill((40, 40, 40))
            self.draw_hud()
            self.draw_grid()
            self.draw_footer()
            pygame.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    Game().run()