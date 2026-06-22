import pygame
import time

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


BG_COLOR = (14, 17, 24)

PANEL_BG = (24, 28, 37)

GRID_LINE_COLOR = (30, 35, 48)

ALIVE_COLOR = (0, 229, 255)

ALIVE_COLOR_SPARSE = (57, 255, 20)

ALIVE_COLOR_NUMPY = (0, 229, 255)

ALIVE_COLOR_DENSE = (255, 110, 196)

TEXT_COLOR = (220, 224, 235)
TEXT_DIM = (120, 130, 150)
BORDER_COLOR = (45, 52, 70)
ACTIVE_BORDER = (0, 229, 255)


_font_cache = {}

def get_font(path_or_default, size):
    key = (path_or_default, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = pygame.font.Font(path_or_default, size)
        except Exception:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


class Button:
    def __init__(self, x, y, width, height, text, action, font, color=BORDER_COLOR, hover_color=(58, 67, 90), text_color=TEXT_COLOR):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.current_color = color
        self.border_color = (70, 80, 105)

    def draw(self, screen):

        is_hovered = self.current_color == self.hover_color

        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=6)

        pygame.draw.rect(screen, self.border_color if not is_hovered else ACTIVE_BORDER, self.rect, 2, border_radius=6)

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                self.current_color = self.hover_color
            else:
                self.current_color = self.color
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                if self.action:
                    return self.action()
        return None


class TextInput:
    def __init__(self, x, y, width, height, font, label="", text="", numeric_only=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.label = label
        self.text = text
        self.numeric_only = numeric_only
        self.active = False
        self.blink_timer = 0.0
        self.error_state = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
                self.error_state = False
            else:
                self.active = False
            self.blink_timer = time.time()
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_DELETE:
                self.text = ""
            else:
                char = event.unicode
                if self.numeric_only:

                    if char.isdigit() or (char == '.' and '.' not in self.text and len(self.text) > 0):
                        self.text += char
                else:
                    self.text += char
            self.blink_timer = time.time()
        return None

    def draw(self, screen):

        if self.label:
            label_surf = self.font.render(self.label, True, TEXT_DIM)
            screen.blit(label_surf, (self.rect.x, self.rect.y - 18))


        bg_color = (20, 24, 32)
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)
        

        border_col = BORDER_COLOR
        if self.error_state:
            border_col = (255, 64, 129)

        elif self.active:
            border_col = ACTIVE_BORDER
        pygame.draw.rect(screen, border_col, self.rect, 2, border_radius=5)


        text_surf = self.font.render(self.text, True, TEXT_COLOR)
        screen.blit(text_surf, (self.rect.x + 8, self.rect.y + (self.rect.height - text_surf.get_height()) // 2))


        if self.active and (time.time() - self.blink_timer) % 1.0 < 0.5:
            cursor_x = self.rect.x + 8 + text_surf.get_width()
            cursor_y0 = self.rect.y + 6
            cursor_y1 = self.rect.y + self.rect.height - 6
            pygame.draw.line(screen, ACTIVE_BORDER, (cursor_x, cursor_y0), (cursor_x, cursor_y1), 2)


class SelectorButton(Button):
    def __init__(self, x, y, width, height, label_prefix, options, initial_index, action, font):
        self.label_prefix = label_prefix
        self.options = options

        self.index = initial_index
        self.action_callback = action
        

        display_text = f"{self.label_prefix}: {self.options[self.index][1]}"
        super().__init__(x, y, width, height, display_text, self._toggle, font)

    def _toggle(self):
        self.index = (self.index + 1) % len(self.options)
        new_val = self.options[self.index][0]
        display_text = f"{self.label_prefix}: {self.options[self.index][1]}"
        self.text = display_text
        if self.action_callback:
            self.action_callback(new_val)

    def set_value(self, val):
        for idx, (v, _) in enumerate(self.options):
            if v == val:
                self.index = idx
                self.text = f"{self.label_prefix}: {self.options[self.index][1]}"
                break


class RealTimeChart:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.history = []
        self.max_history_len = 100

    def set_max_history_len(self, length):
        self.max_history_len = length
        if length is not None and len(self.history) > length:
            self.history = self.history[-length:]

    def add_value(self, val):
        self.history.append(val)
        if self.max_history_len is not None and len(self.history) > self.max_history_len:
            self.history.pop(0)

    def clear(self):
        self.history.clear()

    def draw(self, screen):

        pygame.draw.rect(screen, (18, 22, 30), self.rect, border_radius=6)
        pygame.draw.rect(screen, BORDER_COLOR, self.rect, 2, border_radius=6)


        title_surf = self.font.render("细胞数量演化历史", True, TEXT_DIM)
        screen.blit(title_surf, (self.rect.x + 8, self.rect.y + 6))

        if not self.history:
            empty_surf = self.font.render("暂无数据", True, (80, 90, 110))
            screen.blit(empty_surf, (self.rect.centerx - empty_surf.get_width()//2, self.rect.centery - empty_surf.get_height()//2))
            return


        margin_x = 15
        margin_y = 25
        plot_w = self.rect.width - 2 * margin_x
        plot_h = self.rect.height - margin_y - 12
        plot_x = self.rect.x + margin_x
        plot_y = self.rect.y + margin_y

        max_val = max(self.history)
        min_val = min(self.history)
        val_range = max_val - min_val
        if val_range == 0:
            val_range = 1

        points = []
        max_len = self.max_history_len if self.max_history_len is not None else len(self.history)
        divisor = max_len - 1 if max_len > 1 else 1
        for idx, val in enumerate(self.history):

            pt_x = plot_x + (idx / divisor) * plot_w if len(self.history) > 1 else plot_x
            pt_y = plot_y + plot_h - ((val - min_val) / val_range) * plot_h
            points.append((pt_x, pt_y))


        if len(points) >= 2:
            pygame.draw.lines(screen, ALIVE_COLOR, False, points, 2)
            



        elif len(points) == 1:
            pygame.draw.circle(screen, ALIVE_COLOR, (int(points[0][0]), int(points[0][1])), 3)


        max_surf = self.font.render(f"Max: {max_val}", True, ALIVE_COLOR_SPARSE)
        min_surf = self.font.render(f"Min: {min_val}", True, TEXT_DIM)
        screen.blit(max_surf, (self.rect.right - max_surf.get_width() - 8, self.rect.y + 6))
        screen.blit(min_surf, (self.rect.right - min_surf.get_width() - 8, self.rect.bottom - min_surf.get_height() - 6))


class PerformanceDisplay:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.avg_times = {"sparse": 0.0, "dense": 0.0, "numpy": 0.0}

    def update_time(self, alg, step_time_ms):

        if self.avg_times[alg] == 0.0:
            self.avg_times[alg] = step_time_ms
        else:
            self.avg_times[alg] = 0.95 * self.avg_times[alg] + 0.05 * step_time_ms

    def draw(self, screen, current_alg):
        pygame.draw.rect(screen, (18, 22, 30), self.rect, border_radius=6)
        pygame.draw.rect(screen, BORDER_COLOR, self.rect, 2, border_radius=6)

        title = self.font.render("算法单步更新耗时对比 (EMA)", True, TEXT_DIM)
        screen.blit(title, (self.rect.x + 8, self.rect.y + 6))


        rows_data = [
            ("哈希稀疏 (Sparse)", "sparse", ALIVE_COLOR_SPARSE),
            ("Numpy矢量化 (Numpy)", "numpy", ALIVE_COLOR_NUMPY),
            ("稠密矩阵 (Dense)", "dense", ALIVE_COLOR_DENSE)
        ]

        row_y = self.rect.y + 28
        for label, key, color in rows_data:

            dot_color = color
            is_active = current_alg == key
            pygame.draw.circle(screen, dot_color, (self.rect.x + 15, row_y + 10), 5 if is_active else 3)
            

            lbl_surf = self.font.render(label, True, TEXT_COLOR if is_active else TEXT_DIM)
            screen.blit(lbl_surf, (self.rect.x + 28, row_y + 2))


            val = self.avg_times[key]
            val_text = f"{val:.3f} ms" if val > 0 else "N/A"
            val_surf = self.font.render(val_text, True, color if is_active else TEXT_DIM)
            screen.blit(val_surf, (self.rect.right - val_surf.get_width() - 12, row_y + 2))
            
            row_y += 20


def draw_visible(screen, game, offset_x, offset_y, view_width, view_height, cell_size):
    if cell_size <= 0:
        return
    

    c0 = max(0, int((-offset_x) // cell_size))
    c1 = min(game.cols, int((view_width - offset_x + cell_size - 1) // cell_size))
    r0 = max(0, int((-offset_y) // cell_size))
    r1 = min(game.rows, int((view_height - offset_y + cell_size - 1) // cell_size))
    
    if r0 >= r1 or c0 >= c1:
        return


    if game.algorithm_type == "sparse":
        cell_color = ALIVE_COLOR_SPARSE
    elif game.algorithm_type == "numpy":
        cell_color = ALIVE_COLOR_NUMPY
    else:
        cell_color = ALIVE_COLOR_DENSE


    size_int = int(cell_size) if cell_size >= 1 else 1
    cell_surf = pygame.Surface((size_int, size_int))
    cell_surf.fill(cell_color)
    
    if cell_size > 5:

        pygame.draw.rect(cell_surf, (10, 12, 18), (0, 0, size_int, size_int), 1)


    if game.algorithm_type == "sparse":
        viewport_cells = (r1 - r0) * (c1 - c0)

        if len(game.sparse_grid) < viewport_cells:
            for r, c in game.sparse_grid:
                if r0 <= r < r1 and c0 <= c < c1:
                    x = offset_x + c * cell_size
                    y = offset_y + r * cell_size
                    screen.blit(cell_surf, (x, y))
        else:
            for r in range(r0, r1):
                for c in range(c0, c1):
                    if (r, c) in game.sparse_grid:
                        x = offset_x + c * cell_size
                        y = offset_y + r * cell_size
                        screen.blit(cell_surf, (x, y))
                        
    elif game.algorithm_type == "dense":
        for r in range(r0, r1):
            for c in range(c0, c1):
                if game.dense_grid[r][c] == 1:
                    x = offset_x + c * cell_size
                    y = offset_y + r * cell_size
                    screen.blit(cell_surf, (x, y))
                    
    elif game.algorithm_type == "numpy" and HAS_NUMPY:
        subgrid = game.numpy_grid[r0:r1, c0:c1]
        nz_r, nz_c = np.nonzero(subgrid)
        for i in range(len(nz_r)):
            r = r0 + nz_r[i]
            c = c0 + nz_c[i]
            x = offset_x + c * cell_size
            y = offset_y + r * cell_size
            screen.blit(cell_surf, (x, y))

