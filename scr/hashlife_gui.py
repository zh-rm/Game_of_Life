"""
hashlife_gui.py — Pygame GUI wrapper for the Hashlife ultra-fast simulator.

Screens:
  1. SETUP  — choose init mode, configure parameters
  2. DRAW   — paint / erase initial cells on the grid (or view loaded layout)
  3. SIM    — real-time progress bar + alive-count chart while simulation runs
  4. RESULT — pan / zoom view of the final state; option to save or go back

Run:
  python src/hashlife_gui.py
"""
import os
import sys
import time
import random
import threading
import queue
import math

import pygame


sys.path.insert(0, os.path.dirname(__file__))
import hashlife_runner as hl


BG          = (10,  13,  20)
PANEL       = (18,  22,  33)
BORDER      = (40,  48,  70)
TEXT        = (215, 220, 235)
TEXT_DIM    = (110, 120, 145)
NEON_CYAN   = (0,   229, 255)
NEON_GREEN  = (57,  255,  20)
NEON_PINK   = (255, 110, 196)
NEON_AMBER  = (255, 190,  30)
BTN_BASE    = (30,  40,  60)
BTN_HOVER   = (50,  65,  95)
BTN_ACTIVE  = (20,  80, 140)
RED_DIM     = (160,  40,  55)
RED_HOVER   = (210,  55,  70)


_font_cache: dict = {}

def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    candidates = []
    if sys.platform == "win32":
        candidates = ["C:/Windows/Fonts/msyh.ttc",
                      "C:/Windows/Fonts/simhei.ttf"]
    elif sys.platform == "darwin":
        candidates = ["/System/Library/Fonts/PingFang.ttc"]
    else:
        candidates = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                      "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
    for p in candidates:
        if os.path.exists(p):
            try:
                _font_cache[key] = pygame.font.Font(p, size)
                return _font_cache[key]
            except Exception:
                pass
    _font_cache[key] = pygame.font.SysFont("sans", size, bold=bold)
    return _font_cache[key]


def draw_rect_aa(surf: pygame.Surface, color, rect, radius: int = 6, border: int = 0,
                 border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

def text_surf(text: str, size: int, color=TEXT, bold: bool = False) -> pygame.Surface:
    return get_font(size, bold).render(text, True, color)


class Button:
    def __init__(self, rect, label, color=BTN_BASE, hover=BTN_HOVER, text_col=TEXT,
                 font_size=16):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.hover = hover
        self.text_col = text_col
        self.font_size = font_size
        self._hovered = False

    def draw(self, surf):
        c = self.hover if self._hovered else self.color
        draw_rect_aa(surf, c, self.rect, radius=6, border=2,
                     border_color=NEON_CYAN if self._hovered else BORDER)
        ts = text_surf(self.label, self.font_size, self.text_col)
        surf.blit(ts, ts.get_rect(center=self.rect.center))

    def update(self, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


class TextBox:
    """Single-line editable text box."""
    def __init__(self, rect, default="", numeric=False, font_size=16):
        self.rect    = pygame.Rect(rect)
        self.text    = str(default)
        self.numeric = numeric
        self.active  = False
        self.font_size = font_size
        self._blink  = 0.0

    def draw(self, surf):
        border_col = NEON_CYAN if self.active else BORDER
        draw_rect_aa(surf, (15, 18, 28), self.rect, radius=5, border=2,
                     border_color=border_col)
        ts = text_surf(self.text, self.font_size)
        surf.blit(ts, (self.rect.x + 8,
                       self.rect.y + (self.rect.h - ts.get_height()) // 2))
        if self.active and (time.time() - self._blink) % 1.0 < 0.5:
            cx = self.rect.x + 8 + ts.get_width()
            pygame.draw.line(surf, NEON_CYAN,
                             (cx, self.rect.y + 6),
                             (cx, self.rect.y + self.rect.h - 6), 2)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self._blink = time.time()
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_DELETE:
                self.text = ""
            else:
                ch = event.unicode
                if self.numeric:
                    if ch.isdigit() or (ch == '.' and '.' not in self.text):
                        self.text += ch
                else:
                    self.text += ch
            self._blink = time.time()

    @property
    def int_val(self):
        try:
            return int(self.text)
        except ValueError:
            return None

    @property
    def float_val(self):
        try:
            return float(self.text)
        except ValueError:
            return None


class RadioGroup:
    """Horizontal radio button group."""
    def __init__(self, x, y, options: list[tuple], selected=0, font_size=16, spacing=20):
        self.options  = options

        self.selected = selected
        self.rects    = []
        self.font_size = font_size
        cx = x
        for label, _ in options:
            w = get_font(font_size).size(label)[0] + 36
            self.rects.append(pygame.Rect(cx, y, w, 32))
            cx += w + spacing

    def draw(self, surf):
        for i, (rect, (label, _)) in enumerate(zip(self.rects, self.options)):
            active = (i == self.selected)
            bg = BTN_ACTIVE if active else BTN_BASE
            draw_rect_aa(surf, bg, rect, radius=6, border=2,
                         border_color=NEON_CYAN if active else BORDER)
            ts = text_surf(label, self.font_size,
                           NEON_CYAN if active else TEXT)
            surf.blit(ts, ts.get_rect(center=rect.center))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    break

    @property
    def value(self):
        return self.options[self.selected][1]



class AppState:
    def __init__(self):
        self.screen_w = 1200
        self.screen_h = 760


        self.grid_rows   = 500
        self.grid_cols   = 500
        self.generations = 1_000_000
        self.density     = 0.15
        self.input_file  = "layout.txt"
        self.output_file = "output_result.txt"
        self.init_mode   = "random"



        self.initial_cells: set = set()

        self.final_cells:   set = set()


        self.sim_progress   = 0.0

        self.sim_gen_done   = 0
        self.sim_alive      = 0
        self.sim_elapsed    = 0.0
        self.sim_speed      = 0.0
        self.sim_running    = False
        self.sim_done       = False
        self.sim_error      = ""
        self.alive_history: list[int] = []


        self.msg_q: queue.Queue = queue.Queue()




class SetupScreen:
    """Screen 1 — configure parameters & init mode."""

    def __init__(self, state: AppState):
        self.s = state
        W, H = state.screen_w, state.screen_h

        label_y = 120


        self.mode_radio = RadioGroup(
            60, label_y, [("随机生成", "random"), ("从文件加载", "file")],
            selected=0 if state.init_mode == "random" else 1,
            font_size=17)


        self.tb_rows = TextBox((60, label_y + 70, 110, 34),
                               default=str(state.grid_rows), numeric=True)
        self.tb_cols = TextBox((200, label_y + 70, 110, 34),
                               default=str(state.grid_cols), numeric=True)


        self.tb_gens = TextBox((60, label_y + 155, 200, 34),
                               default=str(state.generations), numeric=True)


        self.tb_density = TextBox((340, label_y + 70, 110, 34),
                                  default=str(state.density), numeric=True)


        self.tb_infile  = TextBox((60,  label_y + 245, 340, 34),
                                  default=state.input_file)
        self.tb_outfile = TextBox((60,  label_y + 330, 340, 34),
                                  default=state.output_file)


        self.btn_next = Button((W - 220, H - 80, 180, 46), "下一步 → 编辑初始状态",
                               color=(25, 80, 130), hover=(35, 110, 175),
                               text_col=NEON_CYAN, font_size=15)
        self.error_msg = ""

    def _textboxes(self):
        return [self.tb_rows, self.tb_cols, self.tb_gens,
                self.tb_density, self.tb_infile, self.tb_outfile]

    def handle(self, event) -> str | None:
        """Return next screen name or None."""
        for tb in self._textboxes():
            tb.handle(event)
        self.mode_radio.handle(event)

        if self.btn_next.clicked(event):
            return self._validate_and_advance()
        return None

    def _validate_and_advance(self) -> str | None:
        s = self.s
        rows = self.tb_rows.int_val
        cols = self.tb_cols.int_val
        gens = self.tb_gens.int_val
        dens = self.tb_density.float_val

        if not rows or rows < 2 or not cols or cols < 2:
            self.error_msg = "错误：网格行列数必须 ≥ 2"
            return None
        if not gens or gens < 1:
            self.error_msg = "错误：代数必须 ≥ 1"
            return None
        if dens is None or not (0 < dens < 1):
            self.error_msg = "错误：密度须在 (0, 1) 范围内"
            return None

        s.grid_rows   = rows
        s.grid_cols   = cols
        s.generations = gens
        s.density     = dens
        s.input_file  = self.tb_infile.text.strip() or "layout.txt"
        s.output_file = self.tb_outfile.text.strip() or "output_result.txt"
        s.init_mode   = self.mode_radio.value
        self.error_msg = ""


        if s.init_mode == "random":
            s.initial_cells = {
                (r, c)
                for r in range(s.grid_rows)
                for c in range(s.grid_cols)
                if random.random() < s.density
            }
        else:
            loaded = hl.load_layout(s.input_file, s.grid_rows, s.grid_cols)
            if loaded is None:
                self.error_msg = f"错误：找不到文件 {s.input_file}"
                return None
            s.initial_cells = loaded

        return "draw"

    def update(self, mouse_pos):
        self.btn_next.update(mouse_pos)

    def draw(self, surf: pygame.Surface):
        surf.fill(BG)
        s = self.s


        surf.blit(text_surf("Hashlife 超高速模拟器  —  参数配置", 26,
                            NEON_CYAN, bold=True), (60, 40))
        surf.blit(text_surf("康威生命游戏 · 百万世代 · 数算B 大作业", 16,
                            TEXT_DIM), (60, 76))

        y0 = 120

        surf.blit(text_surf("初始化方式", 16, TEXT_DIM), (60, y0 - 24))
        self.mode_radio.draw(surf)


        surf.blit(text_surf("网格大小 (行 × 列)", 16, TEXT_DIM), (60, y0 + 46))
        self.tb_rows.draw(surf)
        surf.blit(text_surf("×", 18, TEXT_DIM), (178, y0 + 78))
        self.tb_cols.draw(surf)


        surf.blit(text_surf("随机密度 (0~1)", 16, TEXT_DIM), (340, y0 + 46))
        self.tb_density.draw(surf)


        surf.blit(text_surf("演化代数", 16, TEXT_DIM), (60, y0 + 130))
        self.tb_gens.draw(surf)


        surf.blit(text_surf("输入布局文件路径 (文件加载模式)", 16, TEXT_DIM),
                  (60, y0 + 218))
        self.tb_infile.draw(surf)

        surf.blit(text_surf("输出结果文件路径", 16, TEXT_DIM), (60, y0 + 304))
        self.tb_outfile.draw(surf)


        if self.error_msg:
            surf.blit(text_surf(self.error_msg, 16, NEON_PINK), (60, y0 + 380))


        px = 520
        draw_rect_aa(surf, PANEL, (px, 100, 620, 530), radius=10,
                     border=2, border_color=BORDER)
        lines = [
            ("算法", "Hashlife  —  记忆化四叉树时空跳转"),
            ("", ""),
            ("时间复杂度", "O(log G)  （G = 目标代数）"),
            ("空间复杂度", "≤ 1 GB 记忆化缓存"),
            ("", ""),
            ("特点", "对规律性/周期性/稀疏图案极速"),
            ("", "纯随机图案在走向稳定后同样加速"),
            ("", ""),
            ("操作流程",  "① 配置参数  →  ② 绘制/查看初始状态"),
            ("",          "③ 开始模拟  →  ④ 查看/保存最终结果"),
        ]
        ty = 130
        for k, v in lines:
            if k:
                surf.blit(text_surf(k, 15, NEON_AMBER), (px + 24, ty))
                surf.blit(text_surf(v, 15, TEXT), (px + 130, ty))
            ty += 22

        self.btn_next.draw(surf)


class DrawScreen:
    """Screen 2 — paint/erase initial cells + preview."""

    def __init__(self, state: AppState):
        self.s = state
        W, H = state.screen_w, state.screen_h


        self.view_x = 20.0
        self.view_y = 60.0
        self.cell_size = 1.0
        self._fit_view()

        self._panning   = False
        self._pan_start = (0, 0)
        self._draw_mode = None

        self._dragged:  set = set()

        panel_x = W - 260
        y = 60
        self.btn_randomize = Button((panel_x, y, 230, 36), "重新随机生成",
                                    color=(35, 60, 40), hover=(50, 90, 55))
        y += 50
        self.btn_clear = Button((panel_x, y, 230, 36), "清空网格",
                                color=RED_DIM, hover=RED_HOVER)
        y += 50
        self.btn_back = Button((panel_x, y, 230, 36), "← 返回配置",
                               color=BTN_BASE, hover=BTN_HOVER)
        y += 50
        self.btn_start = Button((panel_x, y, 230, 46), "开始模拟 →",
                                color=(20, 90, 150), hover=(30, 120, 200),
                                text_col=NEON_CYAN, font_size=17)

    def _fit_view(self):
        """Auto-fit the grid into the left drawing area."""
        s = self.s
        area_w = s.screen_w - 280 - 40
        area_h = s.screen_h - 100
        self.cell_size = min(area_w / s.grid_cols, area_h / s.grid_rows)
        self.cell_size = max(1.0, min(40.0, self.cell_size))
        self.view_x = 20 + (area_w - s.grid_cols * self.cell_size) / 2
        self.view_y = 60 + (area_h - s.grid_rows * self.cell_size) / 2

    @property
    def _panel_x(self):
        return self.s.screen_w - 260

    def _game_area(self):
        return pygame.Rect(0, 0, self._panel_x, self.s.screen_h)

    def _cell_at(self, px, py):
        c = int((px - self.view_x) / self.cell_size)
        r = int((py - self.view_y) / self.cell_size)
        return r, c

    def handle(self, event) -> str | None:
        s = self.s
        game_area = self._game_area()

        self.btn_randomize.update(event.pos if hasattr(event, 'pos') else (0, 0))
        self.btn_clear.update(event.pos if hasattr(event, 'pos') else (0, 0))
        self.btn_back.update(event.pos if hasattr(event, 'pos') else (0, 0))
        self.btn_start.update(event.pos if hasattr(event, 'pos') else (0, 0))

        if event.type == pygame.MOUSEMOTION:
            if self._panning:
                dx = event.pos[0] - self._pan_start[0]
                dy = event.pos[1] - self._pan_start[1]
                self.view_x += dx
                self.view_y += dy
                self._pan_start = event.pos
            elif self._draw_mode and game_area.collidepoint(event.pos):
                r, c = self._cell_at(*event.pos)
                if 0 <= r < s.grid_rows and 0 <= c < s.grid_cols:
                    if (r, c) not in self._dragged:
                        alive = (r, c) in s.initial_cells
                        if self._draw_mode == "paint" and not alive:
                            s.initial_cells.add((r, c))
                        elif self._draw_mode == "erase" and alive:
                            s.initial_cells.discard((r, c))
                        self._dragged.add((r, c))

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3):
                self._panning   = True
                self._pan_start = event.pos
            elif event.button == 1:
                if game_area.collidepoint(event.pos):
                    r, c = self._cell_at(*event.pos)
                    if 0 <= r < s.grid_rows and 0 <= c < s.grid_cols:
                        alive = (r, c) in s.initial_cells
                        self._draw_mode = "erase" if alive else "paint"
                        if alive:
                            s.initial_cells.discard((r, c))
                        else:
                            s.initial_cells.add((r, c))
                        self._dragged = {(r, c)}
                elif self.btn_randomize.clicked(event):
                    s.initial_cells = {
                        (r, c)
                        for r in range(s.grid_rows)
                        for c in range(s.grid_cols)
                        if random.random() < s.density
                    }
                elif self.btn_clear.clicked(event):
                    s.initial_cells = set()
                elif self.btn_back.clicked(event):
                    return "setup"
                elif self.btn_start.clicked(event):
                    return "sim"
            elif event.button == 4:

                self._zoom(event.pos, 1.15)
            elif event.button == 5:

                self._zoom(event.pos, 1 / 1.15)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (2, 3):
                self._panning   = False
            elif event.button == 1:
                self._draw_mode = None
                self._dragged   = set()

        return None

    def _zoom(self, mouse_pos, factor):
        mx, my = mouse_pos
        gx = (mx - self.view_x) / self.cell_size
        gy = (my - self.view_y) / self.cell_size
        self.cell_size = max(1.0, min(80.0, self.cell_size * factor))
        self.view_x = mx - gx * self.cell_size
        self.view_y = my - gy * self.cell_size

    def update(self, mouse_pos):
        self.btn_randomize.update(mouse_pos)
        self.btn_clear.update(mouse_pos)
        self.btn_back.update(mouse_pos)
        self.btn_start.update(mouse_pos)

    def draw(self, surf: pygame.Surface):
        surf.fill(BG)
        s = self.s
        pX = self._panel_x


        pygame.draw.rect(surf, (8, 10, 16), (0, 0, pX, s.screen_h))


        cs = int(self.cell_size)
        cs = max(1, cs)
        cell_surf = pygame.Surface((cs, cs))
        cell_surf.fill(NEON_GREEN)
        if self.cell_size > 5:
            pygame.draw.rect(cell_surf, (6, 8, 14), (0, 0, cs, cs), 1)


        c0 = max(0, int(-self.view_x / self.cell_size))
        c1 = min(s.grid_cols, int((pX - self.view_x) / self.cell_size) + 2)
        r0 = max(0, int(-self.view_y / self.cell_size))
        r1 = min(s.grid_rows, int((s.screen_h - self.view_y) / self.cell_size) + 2)

        for r, c in s.initial_cells:
            if r0 <= r <= r1 and c0 <= c <= c1:
                x = int(self.view_x + c * self.cell_size)
                y = int(self.view_y + r * self.cell_size)
                surf.blit(cell_surf, (x, y))


        if self.cell_size >= 6:
            for r in range(r0, r1 + 1):
                y = int(self.view_y + r * self.cell_size)
                pygame.draw.line(surf, (20, 25, 35), (0, y), (pX, y))
            for c in range(c0, c1 + 1):
                x = int(self.view_x + c * self.cell_size)
                pygame.draw.line(surf, (20, 25, 35), (x, 0), (x, s.screen_h))


        draw_rect_aa(surf, PANEL, (pX, 0, s.screen_w - pX, s.screen_h),
                     radius=0, border=2, border_color=BORDER)

        surf.blit(text_surf("初始状态编辑", 20, NEON_CYAN, bold=True), (pX + 15, 18))
        surf.blit(text_surf(
            f"存活: {len(s.initial_cells)}  |  网格 {s.grid_rows}×{s.grid_cols}",
            15, TEXT_DIM), (pX + 15, 42))

        self.btn_randomize.draw(surf)
        self.btn_clear.draw(surf)
        self.btn_back.draw(surf)
        self.btn_start.draw(surf)


        hints = [
            "左键 拖拽 绘制/擦除细胞",
            "中键/右键 拖拽 平移画布",
            "滚轮 缩放",
            "按 F 自适应全屏",
        ]
        hy = s.screen_h - 15 - len(hints) * 22
        for h in hints:
            surf.blit(text_surf(h, 13, TEXT_DIM), (pX + 15, hy))
            hy += 22


class SimScreen:
    """Screen 3 — run simulation in background thread, show live progress."""

    def __init__(self, state: AppState):
        self.s = state
        state.sim_progress  = 0.0
        state.sim_gen_done  = 0
        state.sim_alive     = len(state.initial_cells)
        state.sim_elapsed   = 0.0
        state.sim_speed     = 0.0
        state.sim_running   = True
        state.sim_done      = False
        state.sim_error     = ""
        state.alive_history = [len(state.initial_cells)]

        W, H = state.screen_w, state.screen_h
        self.btn_result = Button((W // 2 - 130, H - 90, 260, 50),
                                 "查看演化结果 →",
                                 color=(20, 90, 150), hover=(30, 120, 200),
                                 text_col=NEON_CYAN, font_size=17)

        self._thread = threading.Thread(target=self._simulate, daemon=True)
        self._thread.start()


    def _simulate(self):
        s = self.s
        try:
            offset_r = 512 - s.grid_rows // 2
            offset_c = 512 - s.grid_cols // 2
            shifted  = {(r + offset_r, c + offset_c) for r, c in s.initial_cells}


            hl._memo.clear()
            hl._dead_memo.clear()
            hl._step_memo.clear()

            node = hl.build_quadtree(shifted, 10)
            num_chunks  = min(200, s.generations)
            chunk_size  = s.generations // num_chunks
            remainder   = s.generations % num_chunks
            done        = 0
            t_start     = time.perf_counter()

            for i in range(1, num_chunks + 1):
                steps = chunk_size + (1 if i <= remainder else 0)
                node  = hl.run_hashlife_node(node, steps)
                done += steps

                elapsed = time.perf_counter() - t_start
                s.msg_q.put({
                    "type"    : "progress",
                    "done"    : done,
                    "alive"   : node.count,
                    "elapsed" : elapsed,
                })


            raw = hl.node_to_set(node)
            final = {
                (r - offset_r, c - offset_c)
                for r, c in raw
                if 0 <= r - offset_r < s.grid_rows and 0 <= c - offset_c < s.grid_cols
            }
            s.msg_q.put({"type": "done", "final": final,
                         "elapsed": time.perf_counter() - t_start})
        except Exception as e:
            s.msg_q.put({"type": "error", "msg": str(e)})


    def _pump(self):
        s = self.s
        while not s.msg_q.empty():
            msg = s.msg_q.get_nowait()
            if msg["type"] == "progress":
                s.sim_gen_done  = msg["done"]
                s.sim_alive     = msg["alive"]
                s.sim_elapsed   = msg["elapsed"]
                s.sim_progress  = msg["done"] / s.generations
                s.sim_speed     = msg["done"] / max(msg["elapsed"], 1e-9)
                s.alive_history.append(msg["alive"])
            elif msg["type"] == "done":
                s.final_cells   = msg["final"]
                s.sim_elapsed   = msg["elapsed"]
                s.sim_progress  = 1.0
                s.sim_running   = False
                s.sim_done      = True
            elif msg["type"] == "error":
                s.sim_error     = msg["msg"]
                s.sim_running   = False

    def handle(self, event) -> str | None:
        self._pump()
        if self.s.sim_done and self.btn_result.clicked(event):
            return "result"
        return None

    def update(self, mouse_pos):
        self._pump()
        self.btn_result.update(mouse_pos)

    def draw(self, surf: pygame.Surface):
        surf.fill(BG)
        s = self.s
        W, H = s.screen_w, s.screen_h

        surf.blit(text_surf("Hashlife 模拟进行中...", 26, NEON_CYAN, bold=True),
                  (60, 36))
        if s.sim_done:
            surf.blit(text_surf("✓ 模拟完成！", 20, NEON_GREEN), (60, 74))
        elif s.sim_error:
            surf.blit(text_surf(f"✗ 错误: {s.sim_error}", 18, NEON_PINK), (60, 74))
        else:
            surf.blit(text_surf("正在时空跳转演化...", 18, TEXT_DIM), (60, 74))


        bar_x, bar_y = 60, 130
        bar_w, bar_h = W - 120, 32
        draw_rect_aa(surf, (20, 24, 35), (bar_x, bar_y, bar_w, bar_h),
                     radius=8, border=1, border_color=BORDER)
        fill_w = int(bar_w * min(s.sim_progress, 1.0))
        if fill_w > 0:

            draw_rect_aa(surf, NEON_CYAN, (bar_x, bar_y, fill_w, bar_h), radius=8)
        pct_text = f"{s.sim_progress * 100:.1f}%"
        ts = text_surf(pct_text, 16, BG if fill_w > 60 else TEXT)
        surf.blit(ts, ts.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2)))


        sy = bar_y + 50
        cols_data = [
            ("已演化代数",  f"{s.sim_gen_done:,}  /  {s.generations:,}"),
            ("当前存活细胞", f"{s.sim_alive:,}"),
            ("累计耗时",    f"{s.sim_elapsed:.3f} 秒"),
            ("平均速度",    f"{s.sim_speed:,.0f} 代/秒"),
        ]
        cx = 60
        for k, v in cols_data:
            surf.blit(text_surf(k, 14, TEXT_DIM), (cx, sy))
            surf.blit(text_surf(v, 20, NEON_AMBER), (cx, sy + 20))
            cx += 270


        chart_x, chart_y = 60, sy + 75
        chart_w, chart_h = W - 120, H - sy - 165
        draw_rect_aa(surf, (14, 17, 26), (chart_x, chart_y, chart_w, chart_h),
                     radius=8, border=1, border_color=BORDER)
        surf.blit(text_surf("存活细胞数量演化历史", 14, TEXT_DIM),
                  (chart_x + 12, chart_y + 8))

        hist = s.alive_history
        if len(hist) >= 2:
            mx_val = max(hist)
            mn_val = min(hist)
            rng    = mx_val - mn_val or 1
            margin = 28
            pw = chart_w - 2 * margin
            ph = chart_h - 2 * margin
            pts = []
            for i, v in enumerate(hist):
                px = chart_x + margin + int(i / (len(hist) - 1) * pw)
                py = chart_y + margin + ph - int((v - mn_val) / rng * ph)
                pts.append((px, py))
            if len(pts) >= 2:
                pygame.draw.lines(surf, NEON_CYAN, False, pts, 2)
            surf.blit(text_surf(f"Max {mx_val:,}", 12, NEON_GREEN),
                      (chart_x + chart_w - 90, chart_y + 10))
            surf.blit(text_surf(f"Min {mn_val:,}", 12, TEXT_DIM),
                      (chart_x + chart_w - 90, chart_y + chart_h - 24))

        if s.sim_done:
            self.btn_result.draw(surf)


class ResultScreen:
    """Screen 4 — pan/zoom result grid; save option."""

    def __init__(self, state: AppState):
        self.s = state
        W, H = state.screen_w, state.screen_h

        self.view_x = 20.0
        self.view_y = 60.0
        self.cell_size = 1.0
        self._fit_view()

        self._panning   = False
        self._pan_start = (0, 0)

        pX = W - 260
        y  = 60
        self.btn_save  = Button((pX, y, 230, 38), "保存结果到文件",
                                color=(25, 80, 40), hover=(40, 110, 60))
        y += 52
        self.btn_load_input = Button((pX, y, 230, 38), "叠加显示初始状态",
                                     color=BTN_BASE, hover=BTN_HOVER)
        y += 52
        self.btn_back  = Button((pX, y, 230, 38), "← 返回配置",
                                color=BTN_BASE, hover=BTN_HOVER)
        self._show_initial = False
        self._saved_msg = ""
        self._saved_time = 0.0

    def _fit_view(self):
        s = self.s
        pX = s.screen_w - 280
        area_w = pX - 40
        area_h = s.screen_h - 100
        self.cell_size = min(area_w / s.grid_cols, area_h / s.grid_rows)
        self.cell_size = max(1.0, min(40.0, self.cell_size))
        self.view_x = 20 + (area_w - s.grid_cols * self.cell_size) / 2
        self.view_y = 60 + (area_h - s.grid_rows * self.cell_size) / 2

    @property
    def _panel_x(self):
        return self.s.screen_w - 260

    def _zoom(self, pos, factor):
        mx, my = pos
        gx = (mx - self.view_x) / self.cell_size
        gy = (my - self.view_y) / self.cell_size
        self.cell_size = max(1.0, min(80.0, self.cell_size * factor))
        self.view_x = mx - gx * self.cell_size
        self.view_y = my - gy * self.cell_size

    def handle(self, event) -> str | None:
        s = self.s
        game_area = pygame.Rect(0, 0, self._panel_x, s.screen_h)

        if event.type == pygame.MOUSEMOTION and self._panning:
            dx = event.pos[0] - self._pan_start[0]
            dy = event.pos[1] - self._pan_start[1]
            self.view_x += dx
            self.view_y += dy
            self._pan_start = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3) and game_area.collidepoint(event.pos):
                self._panning   = True
                self._pan_start = event.pos
            elif event.button == 4:
                self._zoom(event.pos, 1.15)
            elif event.button == 5:
                self._zoom(event.pos, 1 / 1.15)
            elif event.button == 1:
                if self.btn_save.clicked(event):
                    hl.save_layout(s.output_file, s.final_cells)
                    self._saved_msg  = f"已保存 {len(s.final_cells)} 个细胞 → {s.output_file}"
                    self._saved_time = time.time()
                elif self.btn_load_input.clicked(event):
                    self._show_initial = not self._show_initial
                    self.btn_load_input.label = (
                        "隐藏初始状态叠加" if self._show_initial else "叠加显示初始状态")
                elif self.btn_back.clicked(event):
                    return "setup"

        elif event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
            self._panning = False

        return None

    def update(self, mouse_pos):
        self.btn_save.update(mouse_pos)
        self.btn_load_input.update(mouse_pos)
        self.btn_back.update(mouse_pos)

    def draw(self, surf: pygame.Surface):
        surf.fill(BG)
        s = self.s
        pX = self._panel_x


        pygame.draw.rect(surf, (7, 9, 14), (0, 0, pX, s.screen_h))

        cs = max(1, int(self.cell_size))

        def make_cell(color):
            cs_ = pygame.Surface((cs, cs))
            cs_.fill(color)
            if self.cell_size > 5:
                pygame.draw.rect(cs_, (6, 8, 14), (0, 0, cs, cs), 1)
            return cs_

        cell_final   = make_cell(NEON_CYAN)
        cell_init    = make_cell(NEON_GREEN)
        cell_both    = make_cell(NEON_AMBER)

        c0 = max(0, int(-self.view_x / self.cell_size))
        c1 = min(s.grid_cols, int((pX - self.view_x) / self.cell_size) + 2)
        r0 = max(0, int(-self.view_y / self.cell_size))
        r1 = min(s.grid_rows, int((s.screen_h - self.view_y) / self.cell_size) + 2)

        for r, c in s.final_cells:
            if r0 <= r <= r1 and c0 <= c <= c1:
                x = int(self.view_x + c * self.cell_size)
                y = int(self.view_y + r * self.cell_size)
                if self._show_initial and (r, c) in s.initial_cells:
                    surf.blit(cell_both, (x, y))
                else:
                    surf.blit(cell_final, (x, y))

        if self._show_initial:
            for r, c in s.initial_cells:
                if (r, c) not in s.final_cells and r0 <= r <= r1 and c0 <= c <= c1:
                    x = int(self.view_x + c * self.cell_size)
                    y = int(self.view_y + r * self.cell_size)
                    surf.blit(cell_init, (x, y))


        if self.cell_size >= 6:
            for r in range(r0, r1 + 1):
                y = int(self.view_y + r * self.cell_size)
                pygame.draw.line(surf, (20, 25, 35), (0, y), (pX, y))
            for c in range(c0, c1 + 1):
                x = int(self.view_x + c * self.cell_size)
                pygame.draw.line(surf, (20, 25, 35), (x, 0), (x, s.screen_h))


        draw_rect_aa(surf, PANEL, (pX, 0, s.screen_w - pX, s.screen_h),
                     radius=0, border=2, border_color=BORDER)
        surf.blit(text_surf("演化最终结果", 20, NEON_CYAN, bold=True), (pX + 15, 18))
        surf.blit(text_surf(
            f"最终存活: {len(s.final_cells):,} 个细胞", 15, TEXT_DIM), (pX + 15, 42))

        self.btn_save.draw(surf)
        self.btn_load_input.draw(surf)
        self.btn_back.draw(surf)


        if self._saved_msg and time.time() - self._saved_time < 4:
            surf.blit(text_surf(self._saved_msg, 13, NEON_GREEN),
                      (pX + 15, s.screen_h - 80))


        legend_y = s.screen_h - 160
        surf.blit(text_surf("图例", 14, TEXT_DIM), (pX + 15, legend_y))
        legend_items = [
            (NEON_CYAN, "最终存活细胞"),
        ]
        if self._show_initial:
            legend_items += [
                (NEON_GREEN, "仅初始存活"),
                (NEON_AMBER, "两代均存活"),
            ]
        ly = legend_y + 24
        for color, label in legend_items:
            pygame.draw.rect(surf, color, (pX + 15, ly, 14, 14), border_radius=3)
            surf.blit(text_surf(label, 13, TEXT), (pX + 36, ly - 1))
            ly += 22


        hints = ["鼠标中键/右键 平移", "滚轮 缩放", "按 F 自适应"]
        hy = s.screen_h - 20 - len(hints) * 20
        for h in hints:
            surf.blit(text_surf(h, 12, TEXT_DIM), (pX + 15, hy))
            hy += 20



def main():
    pygame.init()
    state = AppState()

    screen = pygame.display.set_mode((state.screen_w, state.screen_h),
                                     pygame.RESIZABLE)
    pygame.display.set_caption("Conway's Game of Life — Hashlife GUI")
    clock = pygame.time.Clock()

    screens: dict = {}
    current = "setup"

    def build_screen(name):
        if name == "setup":
            return SetupScreen(state)
        elif name == "draw":
            return DrawScreen(state)
        elif name == "sim":
            return SimScreen(state)
        elif name == "result":
            return ResultScreen(state)

    screens[current] = build_screen(current)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        active_screen = screens[current]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                state.screen_w, state.screen_h = event.size
                screen = pygame.display.set_mode(
                    (state.screen_w, state.screen_h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:

                    if hasattr(active_screen, '_fit_view'):
                        active_screen._fit_view()

            else:
                next_screen = active_screen.handle(event)
                if next_screen and next_screen != current:
                    current = next_screen
                    screens[current] = build_screen(current)
                    active_screen = screens[current]

        active_screen.update(mouse_pos)
        active_screen.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
