import os
import sys
import time
import argparse
import random


_memo = {}

_dead_memo = {}

_step_memo = {}


def get_node(level, nw, ne, sw, se):
    """Retrieve or create a canonicalized Node (Hash-consing)."""
    if level == 1:
        key = (1, nw, ne, sw, se)
    else:
        key = (level, id(nw), id(ne), id(sw), id(se))
        
    if key in _memo:
        return _memo[key]
        
    node = Node(level, nw, ne, sw, se)
    _memo[key] = node
    return node

def get_dead_node(level):
    """Retrieve or create a completely dead node of the specified level."""
    if level in _dead_memo:
        return _dead_memo[level]
    if level == 0:
        return 0
    sub = get_dead_node(level - 1)
    node = get_node(level, sub, sub, sub, sub)
    _dead_memo[level] = node
    return node

class Node:
    __slots__ = ('level', 'nw', 'ne', 'sw', 'se', 'count')
    def __init__(self, level, nw, ne, sw, se):
        self.level = level
        self.nw = nw
        self.ne = ne
        self.sw = sw
        self.se = se
        

        if level == 1:
            self.count = nw + ne + sw + se
        else:
            self.count = nw.count + ne.count + sw.count + se.count


def step_level2(node):
    nw, ne, sw, se = node.nw, node.ne, node.sw, node.se
    

    a, b, c, d = nw.nw, nw.ne, nw.sw, nw.se
    e, f, g, h = ne.nw, ne.ne, ne.sw, ne.se
    i, j, k, l = sw.nw, sw.ne, sw.sw, sw.se
    m, n, o, p = se.nw, se.ne, se.sw, se.se
    

    def next_state(current, neighbors):
        if current == 1:
            return 1 if (neighbors == 2 or neighbors == 3) else 0
        else:
            return 1 if neighbors == 3 else 0

    n_d = next_state(d, a + b + e + c + g + i + j + m)
    n_g = next_state(g, b + e + f + d + h + j + m + n)
    n_j = next_state(j, c + d + g + i + m + k + l + o)
    n_m = next_state(m, d + g + h + j + n + l + o + p)
    
    return get_node(1, n_d, n_g, n_j, n_m)


def step(node):
    """Step a node of level k forward by 2^(k-2) generations."""
    if node in _step_memo:
        return _step_memo[node]
        
    if node.count == 0:
        res = get_dead_node(node.level - 1)
        _step_memo[node] = res
        return res
        
    if node.level == 2:
        res = step_level2(node)
        _step_memo[node] = res
        return res
        

    nw, ne, sw, se = node.nw, node.ne, node.sw, node.se
    

    n11 = nw
    n12 = get_node(node.level - 1, nw.ne, ne.nw, nw.se, ne.sw)
    n13 = ne
    
    n21 = get_node(node.level - 1, nw.sw, nw.se, sw.nw, sw.ne)
    n22 = get_node(node.level - 1, nw.se, ne.sw, sw.ne, se.nw)
    n23 = get_node(node.level - 1, ne.sw, ne.se, se.nw, se.ne)
    
    n31 = sw
    n32 = get_node(node.level - 1, sw.ne, se.nw, sw.se, se.sw)
    n33 = se
    

    c11 = step(n11)
    c12 = step(n12)
    c13 = step(n13)
    c21 = step(n21)
    c22 = step(n22)
    c23 = step(n23)
    c31 = step(n31)
    c32 = step(n32)
    c33 = step(n33)
    

    m_nw = get_node(node.level - 1, c11, c12, c21, c22)
    m_ne = get_node(node.level - 1, c12, c13, c22, c23)
    m_sw = get_node(node.level - 1, c21, c22, c31, c32)
    m_se = get_node(node.level - 1, c22, c23, c32, c33)
    

    res_nw = step(m_nw)
    res_ne = step(m_ne)
    res_sw = step(m_sw)
    res_se = step(m_se)
    

    res = get_node(node.level - 1, res_nw, res_ne, res_sw, res_se)
    
    _step_memo[node] = res
    return res


def expand_node(node):
    """Double the spatial canvas of a node while keeping the contents centered."""
    k = node.level
    dead_sub = get_dead_node(k - 1)
    
    nw = get_node(k, dead_sub, dead_sub, dead_sub, node.nw)
    ne = get_node(k, dead_sub, dead_sub, node.ne, dead_sub)
    sw = get_node(k, dead_sub, node.sw, dead_sub, dead_sub)
    se = get_node(k, node.se, dead_sub, dead_sub, dead_sub)
    
    return get_node(k + 1, nw, ne, sw, se)

def get_center(node):
    """Retrieve the center quadrant of level k-1 from a node of level k."""
    return get_node(node.level - 1, node.nw.se, node.ne.sw, node.sw.ne, node.se.nw)


def build_quadtree(alive_cells, level):
    """Build a quadtree of a specified level bottom-up from a set of coordinates."""
    current_nodes = {(r, c): 1 for r, c in alive_cells}
    
    for k in range(1, level + 1):
        next_nodes = {}
        parent_coords = set((r // 2, c // 2) for r, c in current_nodes.keys())
        dead_sub = get_dead_node(k - 1)
        
        for pr, pc in parent_coords:
            nw = current_nodes.get((2 * pr, 2 * pc), dead_sub)
            ne = current_nodes.get((2 * pr, 2 * pc + 1), dead_sub)
            sw = current_nodes.get((2 * pr + 1, 2 * pc), dead_sub)
            se = current_nodes.get((2 * pr + 1, 2 * pc + 1), dead_sub)
            
            node = get_node(k, nw, ne, sw, se)
            if node.count > 0:
                next_nodes[(pr, pc)] = node
                
        current_nodes = next_nodes
        
    return current_nodes.get((0, 0), get_dead_node(level))

def node_to_set(node, r_offset=0, c_offset=0):
    """Extract coordinate pairs of alive cells from a quadtree node."""
    if node.count == 0:
        return set()
    if node.level == 1:
        cells = set()
        if node.nw == 1: cells.add((r_offset, c_offset))
        if node.ne == 1: cells.add((r_offset, c_offset + 1))
        if node.sw == 1: cells.add((r_offset + 1, c_offset))
        if node.se == 1: cells.add((r_offset + 1, c_offset + 1))
        return cells
        
    half = 1 << (node.level - 1)
    cells = set()
    cells.update(node_to_set(node.nw, r_offset, c_offset))
    cells.update(node_to_set(node.ne, r_offset, c_offset + half))
    cells.update(node_to_set(node.sw, r_offset + half, c_offset))
    cells.update(node_to_set(node.se, r_offset + half, c_offset + half))
    return cells


def run_hashlife_node(node, total_steps):
    """Simulate exactly `total_steps` generations starting from `node`."""
    remaining_steps = total_steps
    while remaining_steps > 0:
        step_capacity = 1 << (node.level - 2)
        if step_capacity <= remaining_steps:
            node = step(node)
            remaining_steps -= step_capacity
            node = expand_node(node)
        else:
            node = get_center(node)
    return node


def load_layout(filename, max_r, max_c):
    cells = set()
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                r = int(parts[0])
                c = int(parts[1])
                if 0 <= r < max_r and 0 <= c < max_c:
                    cells.add((r, c))
    return cells

def save_layout(filename, cells):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Conway's Game of Life Hashlife Output Layout\n")
        for r, c in sorted(cells):
            f.write(f"{r},{c}\n")


def main():
    parser = argparse.ArgumentParser(description="Conway's Game of Life - Hashlife High-Speed Simulator")
    parser.add_argument("-W", "--width", type=int, default=500, help="Grid width boundary (default: 500)")
    parser.add_argument("-H", "--height", type=int, default=500, help="Grid height boundary (default: 500)")
    parser.add_argument("-G", "--generations", type=int, default=1000000, help="Generations count to simulate (default: 1000000)")
    parser.add_argument("-I", "--input", type=str, default="layout.txt", help="Input initial coordinates file path")
    parser.add_argument("-O", "--output", type=str, default="output_result.txt", help="Output final coordinates file path")
    parser.add_argument("--density", type=float, default=0.15, help="Random density if random initialization is chosen (default: 0.15)")
    parser.add_argument("--mode", type=str, choices=["file", "random", "ask"], default="ask", help="Initialization mode (default: ask)")
    
    args = parser.parse_args()
    
    print("====================================================")
    print(" 康威生命游戏 - Hashlife 百万世代超高速模拟器 (CLI)")
    print("====================================================")
    print(f"网格边界: {args.height} x {args.width}")
    print(f"目标代数: {args.generations} 代")
    

    init_mode = args.mode
    if init_mode == "ask":
        print("\n请选择初始状态生成方式：")
        print("  1. 从布局文件加载")
        print("  2. 随机生成")
        sys.stdout.write("请输入选项 (1 或 2, 默认 1): ")
        sys.stdout.flush()
        choice = sys.stdin.readline().strip()
        if choice == "2":
            init_mode = "random"
        else:
            init_mode = "file"

    initial_cells = None
    if init_mode == "file":
        initial_cells = load_layout(args.input, args.height, args.width)
        if initial_cells is not None:
            print(f"-> 模式: 从文件加载 | 已读取 {len(initial_cells)} 个存活细胞。")
        else:
            print(f"-> 模式: 从文件加载 | 未找到布局文件 {args.input}！将自动使用随机生成。")
            init_mode = "random"

    if init_mode == "random":
        print(f"-> 模式: 随机生成 | 网格={args.height}x{args.width} | 密度={args.density:.2f}")
        initial_cells = set()
        for r in range(args.height):
            for c in range(args.width):
                if random.random() < args.density:
                    initial_cells.add((r, c))
        print(f"已随机生成了 {len(initial_cells)} 个存活细胞。")

    if not initial_cells:
        print("初始活细胞数量为 0，程序退出。")
        sys.exit(0)



    offset_r = 512 - args.height // 2
    offset_c = 512 - args.width // 2
    
    shifted_initial = set((r + offset_r, c + offset_c) for r, c in initial_cells)
    

    node = build_quadtree(shifted_initial, 10)
    


    num_chunks = min(50, args.generations)
    chunk_size = args.generations // num_chunks
    remainder = args.generations % num_chunks
    
    print("\n[开始模拟] 正在进行时空跳转演化...")
    t_start = time.perf_counter()
    
    current_generation = 0
    for i in range(1, num_chunks + 1):
        steps_to_run = chunk_size + (1 if i <= remainder else 0)
        
        t_chunk_start = time.perf_counter()
        node = run_hashlife_node(node, steps_to_run)
        t_chunk_end = time.perf_counter()
        
        current_generation += steps_to_run
        pct = (current_generation / args.generations) * 100
        

        alive_count = node.count
        chunk_dur = t_chunk_end - t_chunk_start
        print(f" 进度: {current_generation:8d} / {args.generations:8d} ({pct:5.1f}%) | 存活细胞: {alive_count:8d} | 本轮耗时: {chunk_dur:.4f}s")
        
    t_end = time.perf_counter()
    duration = t_end - t_start
    print(f"\n[模拟结束] 总耗时: {duration:.4f} 秒")
    print(f"平均速度: {args.generations / duration:.1f} 代/秒")
    

    raw_final_cells = node_to_set(node)
    
    final_cells = set()
    for r, c in raw_final_cells:
        real_r = r - offset_r
        real_c = c - offset_c

        if 0 <= real_r < args.height and 0 <= real_c < args.width:
            final_cells.add((real_r, real_c))
            
    print(f"过滤边界后存活: {len(final_cells)} 个细胞")
    

    save_layout(args.output, final_cells)
    print(f"输出结果: 已保存至 {args.output}")
    print("====================================================")

if __name__ == "__main__":
    main()
