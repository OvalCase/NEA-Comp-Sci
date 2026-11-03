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