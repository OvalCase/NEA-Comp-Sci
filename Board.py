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
