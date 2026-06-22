import pygame
import sys
import os
import time

from game_logic import GameOfLife, HAS_NUMPY
import gui


def get_sys_font_path():
    if sys.platform == "win32":

        paths = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
        for p in paths:
            if os.path.exists(p):
                return p
    elif sys.platform == "darwin":
        p = "/System/Library/Fonts/PingFang.ttc"
        if os.path.exists(p):
            return p
    else:
        paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    return None

def main():
    pygame.init()
    

    display_width = 1120
    display_height = 800
    screen = pygame.display.set_mode((display_width, display_height), pygame.RESIZABLE)
    pygame.display.set_caption("Conway's Game of Life - Pro Edition")
    
    clock = pygame.time.Clock()
    font_path = get_sys_font_path()
    

    font_title = gui.get_font(font_path, 22)
    font_body = gui.get_font(font_path, 16)
    font_small = gui.get_font(font_path, 14)
    font_stat = gui.get_font(font_path, 18)


    game = GameOfLife(rows=80, cols=100, boundary_type="dead", speed=0.1, algorithm_type="sparse")


    offset_x = 30.0
    offset_y = 30.0
    cell_size = 8.0


    def center_grid():
        nonlocal offset_x, offset_y, cell_size
        game_area_w = display_width - 320
        game_area_h = display_height
        

        scale_x = (game_area_w - 60) / game.cols
        scale_y = (game_area_h - 60) / game.rows
        cell_size = max(2.0, min(scale_x, scale_y))
        

        offset_x = (game_area_w - game.cols * cell_size) / 2.0
        offset_y = (game_area_h - game.rows * cell_size) / 2.0

    center_grid()


    panning = False
    pan_start = (0, 0)
    

    draw_mode = None

    dragged_cells = set()


    status_msg = ""
    status_msg_time = 0.0
    
    def set_status(msg):
        nonlocal status_msg, status_msg_time
        status_msg = msg
        status_msg_time = time.time()


    buttons = []
    text_inputs = []
    
    panel_x = display_width - 320


    def toggle_play():
        game.running = not game.running
        set_status("模拟启动" if game.running else "模拟暂停")

    btn_play = gui.Button(0, 0, 135, 32, "开始 / 暂停 (Space)", toggle_play, font_small, color=(35, 55, 85))
    
    def step_once():
        if not game.running:
            game.update_grid()
            set_status(f"单步演化 | 耗时: {game.last_step_time_ms:.2f}ms")
            
    btn_step = gui.Button(0, 0, 135, 32, "单步演化 (X)", step_once, font_small)
    

    def randomize_grid():
        game.reset_random()
        chart.clear()
        set_status("随机初始化网格")
        
    btn_random = gui.Button(0, 0, 135, 32, "随机初始化 (R)", randomize_grid, font_small)
    
    def clear_grid():
        game.reset_clear()
        chart.clear()
        set_status("网格已清空 (C)")
        
    btn_clear = gui.Button(0, 0, 135, 32, "清空网格", clear_grid, font_small, color=(100, 35, 55))


    def change_algorithm(val):
        ok = game.set_algorithm(val)
        if ok:
            set_status(f"算法已切换: {val.upper()}")
        else:
            set_status("该算法不可用(缺失NumPy)")

            sel_alg.set_value(game.algorithm_type)

    sel_alg = gui.SelectorButton(0, 0, 280, 32, "更新算法", 
                                 [("sparse", "哈希稀疏优化"), ("numpy", "Numpy 矢量化"), ("dense", "稠密矩阵")],
                                 0 if game.algorithm_type == "sparse" else (1 if game.algorithm_type == "numpy" else 2),
                                 change_algorithm, font_small)

    def change_boundary(val):
        game.boundary_type = val
        set_status(f"边界条件已切换: {'循环边界' if val == 'loop' else '死亡边界'}")
        
    sel_bound = gui.SelectorButton(0, 0, 280, 32, "边界条件",
                                   [("dead", "死亡边界 (Dead)"), ("loop", "循环边界 (Loop)")],
                                   0 if game.boundary_type == "dead" else 1,
                                   change_boundary, font_small)


    txt_speed = gui.TextInput(0, 0, 90, 28, font_small, label="速度 (秒/代):", text=str(game.speed), numeric_only=True)
    
    def apply_speed():
        try:
            val = float(txt_speed.text)
            if val > 0:
                game.speed = val
                set_status(f"速度已更新为: {val} s/代")
            else:
                txt_speed.error_state = True
                set_status("速度必须大于 0")
        except ValueError:
            txt_speed.error_state = True
            set_status("无效的速度数值")
            
    btn_apply_speed = gui.Button(0, 0, 70, 28, "应用", apply_speed, font_small, color=(35, 75, 55))

    txt_rows = gui.TextInput(0, 0, 50, 28, font_small, label="网格大小:", text=str(game.rows), numeric_only=True)
    txt_cols = gui.TextInput(0, 0, 50, 28, font_small, text=str(game.cols), numeric_only=True)
    
    def apply_grid_size():
        try:
            r = int(txt_rows.text)
            c = int(txt_cols.text)
            if r > 0 and c > 0:

                new_game = GameOfLife(rows=r, cols=c, boundary_type=game.boundary_type, speed=game.speed, algorithm_type=game.algorithm_type)
                game.__dict__.update(new_game.__dict__)
                chart.clear()
                center_grid()
                set_status(f"网格重置为: {r} x {c}")
            else:
                txt_rows.error_state = True
                txt_cols.error_state = True
                set_status("行和列必须大于 0")
        except ValueError:
            txt_rows.error_state = True
            txt_cols.error_state = True
            set_status("无效的行列数值")
            
    btn_apply_grid = gui.Button(0, 0, 70, 28, "应用", apply_grid_size, font_small, color=(35, 75, 55))


    txt_file = gui.TextInput(0, 0, 140, 28, font_small, label="保存/加载文件名:", text="layout.txt")
    
    def save_file():
        filename = txt_file.text.strip()
        if not filename:
            txt_file.error_state = True
            set_status("文件名不能为空")
            return
        success, msg = game.save_layout(filename)
        set_status(msg)
        if not success:
            txt_file.error_state = True
            
    btn_save = gui.Button(0, 0, 60, 28, "保存", save_file, font_small)
    
    def load_file():
        filename = txt_file.text.strip()
        if not filename:
            txt_file.error_state = True
            set_status("文件名不能为空")
            return
        success, msg = game.load_layout(filename)
        set_status(msg)
        if success:
            chart.clear()
        else:
            txt_file.error_state = True
            
    btn_load = gui.Button(0, 0, 60, 28, "加载", load_file, font_small, color=(35, 75, 55))


    def change_chart_window(val):
        chart.set_max_history_len(val)
        set_status(f"图表窗口已设置为: {'无限/全量' if val is None else str(val) + '代'}")
        
    sel_chart_window = gui.SelectorButton(0, 0, 280, 32, "演化历史窗口",
                                         [(50, "50 世代"), (100, "100 世代"), (200, "200 世代"), (500, "500 世代"), (None, "无限 (全量)")],
                                         1,

                                         change_chart_window, font_small)


    buttons.extend([
        btn_play, btn_step, btn_random, btn_clear, 
        sel_alg, sel_bound, btn_apply_speed, btn_apply_grid,
        btn_save, btn_load, sel_chart_window
    ])
    text_inputs.extend([
        txt_speed, txt_rows, txt_cols, txt_file
    ])


    chart = gui.RealTimeChart(0, 0, 280, 105, font_small)

    perf_disp = gui.PerformanceDisplay(0, 0, 280, 105, font_small)


    def reposition_ui(w, h):
        nonlocal panel_x
        panel_x = w - 320
        

        btn_play.rect.topleft = (panel_x + 15, 95)
        btn_step.rect.topleft = (panel_x + 165, 95)
        

        btn_random.rect.topleft = (panel_x + 15, 135)
        btn_clear.rect.topleft = (panel_x + 165, 135)
        

        sel_alg.rect.topleft = (panel_x + 15, 175)
        sel_bound.rect.topleft = (panel_x + 15, 215)
        

        txt_speed.rect.topleft = (panel_x + 110, 260)
        btn_apply_speed.rect.topleft = (panel_x + 210, 260)
        

        txt_rows.rect.topleft = (panel_x + 110, 310)
        txt_cols.rect.topleft = (panel_x + 170, 310)
        btn_apply_grid.rect.topleft = (panel_x + 230, 310)
        

        txt_file.rect.topleft = (panel_x + 15, 365)
        btn_save.rect.topleft = (panel_x + 165, 365)
        btn_load.rect.topleft = (panel_x + 235, 365)
        

        sel_chart_window.rect.topleft = (panel_x + 15, 410)
        chart.rect.topleft = (panel_x + 15, 448)
        perf_disp.rect.topleft = (panel_x + 15, 560)

    reposition_ui(display_width, display_height)


    last_gen_time = time.time()
    frame_rate = 60
    

    chart.add_value(game.alive_count)


    running = True
    while running:
        current_time = time.time()
        

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                

            for ti in text_inputs:
                ti.handle_event(event)
                

            active_input = any(ti.active for ti in text_inputs)
            if not active_input:
                for btn in buttons:
                    btn.handle_event(event)


            if event.type == pygame.KEYDOWN and not active_input:
                if event.key == pygame.K_SPACE:
                    toggle_play()
                elif event.key == pygame.K_x:
                    step_once()
                elif event.key == pygame.K_r:
                    randomize_grid()
                elif event.key == pygame.K_c:
                    clear_grid()
                elif event.key == pygame.K_f:
                    center_grid()
                    set_status("视图已自适应居中")
                elif event.key == pygame.K_ESCAPE:
                    running = False


            elif event.type == pygame.VIDEORESIZE:
                display_width, display_height = event.size
                screen = pygame.display.set_mode((display_width, display_height), pygame.RESIZABLE)
                reposition_ui(display_width, display_height)
                

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[0] < panel_x:
                    if event.button == 1:

                        grid_x = int((event.pos[0] - offset_x) / cell_size)
                        grid_y = int((event.pos[1] - offset_y) / cell_size)
                        
                        if 0 <= grid_x < game.cols and 0 <= grid_y < game.rows:

                            is_alive = game.is_alive(grid_y, grid_x)
                            draw_mode = "erase" if is_alive else "paint"
                            game.toggle_cell(grid_y, grid_x)
                            dragged_cells = {(grid_y, grid_x)}
                            chart.add_value(game.alive_count)
                            
                    elif event.button in (2, 3):

                        panning = True
                        pan_start = event.pos
                        
                    elif event.button == 4:

                        mouse_x, mouse_y = event.pos
                        zoom_center_grid_x = (mouse_x - offset_x) / cell_size
                        zoom_center_grid_y = (mouse_y - offset_y) / cell_size

                        cell_size = min(100.0, cell_size * 1.15)
                        
                        offset_x = mouse_x - zoom_center_grid_x * cell_size
                        offset_y = mouse_y - zoom_center_grid_y * cell_size
                        
                    elif event.button == 5:

                        mouse_x, mouse_y = event.pos
                        zoom_center_grid_x = (mouse_x - offset_x) / cell_size
                        zoom_center_grid_y = (mouse_y - offset_y) / cell_size

                        cell_size = max(1.0, cell_size * 0.85)
                        
                        offset_x = mouse_x - zoom_center_grid_x * cell_size
                        offset_y = mouse_y - zoom_center_grid_y * cell_size

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    panning = False
                elif event.button == 1:
                    draw_mode = None
                    dragged_cells = set()

            elif event.type == pygame.MOUSEMOTION:

                if draw_mode is not None and event.pos[0] < panel_x:
                    grid_x = int((event.pos[0] - offset_x) / cell_size)
                    grid_y = int((event.pos[1] - offset_y) / cell_size)
                    
                    if 0 <= grid_x < game.cols and 0 <= grid_y < game.rows:
                        if (grid_y, grid_x) not in dragged_cells:
                            is_alive = game.is_alive(grid_y, grid_x)
                            if draw_mode == "paint" and not is_alive:
                                game.toggle_cell(grid_y, grid_x)
                            elif draw_mode == "erase" and is_alive:
                                game.toggle_cell(grid_y, grid_x)
                            dragged_cells.add((grid_y, grid_x))
                            chart.add_value(game.alive_count)
                            

                elif panning:
                    dx = event.pos[0] - pan_start[0]
                    dy = event.pos[1] - pan_start[1]
                    offset_x += dx
                    offset_y += dy
                    pan_start = event.pos


        if game.running:

            if current_time - last_gen_time >= game.speed:

                game.update_grid()
                last_gen_time = current_time
                

                chart.add_value(game.alive_count)
                perf_disp.update_time(game.algorithm_type, game.last_step_time_ms)


        screen.fill(gui.BG_COLOR)



        gui.draw_visible(screen, game, offset_x, offset_y, panel_x, display_height, cell_size)


        pygame.draw.rect(screen, gui.PANEL_BG, (panel_x, 0, 320, display_height))
        pygame.draw.line(screen, gui.BORDER_COLOR, (panel_x, 0), (panel_x, display_height), 2)


        title_surf = font_title.render("康威生命游戏 (Conway's)", True, gui.ACTIVE_BORDER)
        screen.blit(title_surf, (panel_x + 15, 18))
        edition_surf = font_small.render("数算B 大作业优化版 v4.0", True, gui.TEXT_DIM)
        screen.blit(edition_surf, (panel_x + 15, 42))
        

        gen_surf = font_stat.render(f"当前世代: {game.generation}", True, gui.TEXT_COLOR)
        alive_surf = font_stat.render(f"存活细胞: {game.alive_count}", True, gui.TEXT_COLOR)
        screen.blit(gen_surf, (panel_x + 15, 68))
        screen.blit(alive_surf, (panel_x + 165, 68))


        for btn in buttons:
            btn.draw(screen)
        
        for ti in text_inputs:
            ti.draw(screen)


        lbl_x = font_small.render("x", True, gui.TEXT_DIM)
        screen.blit(lbl_x, (panel_x + 163, 316))


        chart.draw(screen)
        perf_disp.draw(screen, game.algorithm_type)



        if status_msg and (time.time() - status_msg_time < 3.0):
            msg_surf = font_small.render(status_msg, True, gui.ALIVE_COLOR_SPARSE)
            screen.blit(msg_surf, (panel_x + 15, display_height - 65))
            

        tip1 = font_small.render("提示: [鼠标中键/右键]拖拽平移 | [滚轮]缩放", True, gui.TEXT_DIM)
        tip2 = font_small.render("按 [F] 自动居中 | 双击或拖拽可手工编辑细胞", True, gui.TEXT_DIM)
        screen.blit(tip1, (panel_x + 15, display_height - 42))
        screen.blit(tip2, (panel_x + 15, display_height - 24))


        dot_color = gui.ALIVE_COLOR_SPARSE if game.running else (255, 64, 129)
        pygame.draw.circle(screen, dot_color, (panel_x + 288, 30), 6)
        status_text_surf = font_small.render("运行" if game.running else "暂停", True, gui.TEXT_COLOR)
        screen.blit(status_text_surf, (panel_x + 258, 22))

        pygame.display.flip()
        clock.tick(frame_rate)

    pygame.quit()

if __name__ == "__main__":
    main()
