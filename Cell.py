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