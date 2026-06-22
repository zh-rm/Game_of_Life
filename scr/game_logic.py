import time
import random

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

class GameOfLife:
    def __init__(self, rows=80, cols=100, boundary_type="dead", speed=0.1, algorithm_type="sparse"):
        self.rows = rows
        self.cols = cols
        self.boundary_type = boundary_type

        self.speed = speed

        self.algorithm_type = algorithm_type

        self.running = False
        
        self.generation = 0
        self.last_step_time_ms = 0.0
        

        self.sparse_grid = set()

        self.dense_grid = [[0] * cols for _ in range(rows)]
        if HAS_NUMPY:
            self.numpy_grid = np.zeros((rows, cols), dtype=np.uint8)
            if self.algorithm_type == "numpy":
                pass
        else:
            self.numpy_grid = None
            if self.algorithm_type == "numpy":
                self.algorithm_type = "sparse"



        self.reset_random()

    def set_algorithm(self, alg):
        """Switch the active algorithm and synchronize representations."""
        if alg == "numpy" and not HAS_NUMPY:
            return False

        
        if alg == self.algorithm_type:
            return True


        if self.algorithm_type == "sparse":
            self._sync_from_sparse()
        elif self.algorithm_type == "dense":
            self._sync_from_dense()
        elif self.algorithm_type == "numpy":
            self._sync_from_numpy()

        self.algorithm_type = alg
        return True


    def _sync_from_sparse(self):

        self.dense_grid = [[0] * self.cols for _ in range(self.rows)]
        for r, c in self.sparse_grid:
            self.dense_grid[r][c] = 1

        if HAS_NUMPY:
            self.numpy_grid = np.zeros((self.rows, self.cols), dtype=np.uint8)
            for r, c in self.sparse_grid:
                self.numpy_grid[r, c] = 1

    def _sync_from_dense(self):

        self.sparse_grid = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.dense_grid[r][c] == 1:
                    self.sparse_grid.add((r, c))

        if HAS_NUMPY:
            self.numpy_grid = np.array(self.dense_grid, dtype=np.uint8)

    def _sync_from_numpy(self):
        if not HAS_NUMPY:
            return

        self.dense_grid = self.numpy_grid.tolist()

        self.sparse_grid = set()
        nonzero = np.transpose(np.nonzero(self.numpy_grid))
        for r, c in nonzero:
            self.sparse_grid.add((r, c))

    def sync_all(self):
        """Synchronize all representations based on the current active algorithm."""
        if self.algorithm_type == "sparse":
            self._sync_from_sparse()
        elif self.algorithm_type == "dense":
            self._sync_from_dense()
        elif self.algorithm_type == "numpy":
            self._sync_from_numpy()


    def reset_random(self, density=0.2):
        """Reset grid with random cell placement."""
        self.generation = 0
        self.last_step_time_ms = 0.0
        
        self.sparse_grid = set()
        self.dense_grid = [[0] * self.cols for _ in range(self.rows)]
        
        for r in range(self.rows):
            for c in range(self.cols):
                if random.random() < density:
                    self.dense_grid[r][c] = 1
                    self.sparse_grid.add((r, c))
        
        if HAS_NUMPY:
            self.numpy_grid = np.zeros((self.rows, self.cols), dtype=np.uint8)
            for r, c in self.sparse_grid:
                self.numpy_grid[r, c] = 1

    def reset_clear(self):
        """Clear the entire grid."""
        self.generation = 0
        self.last_step_time_ms = 0.0
        self.sparse_grid = set()
        self.dense_grid = [[0] * self.cols for _ in range(self.rows)]
        if HAS_NUMPY:
            self.numpy_grid = np.zeros((self.rows, self.cols), dtype=np.uint8)

    def toggle_cell(self, r, c):
        """Toggle a cell's alive state. Updates all representations to keep them in sync."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            is_alive = (r, c) in self.sparse_grid
            if is_alive:
                self.sparse_grid.discard((r, c))
                self.dense_grid[r][c] = 0
                if HAS_NUMPY:
                    self.numpy_grid[r, c] = 0
            else:
                self.sparse_grid.add((r, c))
                self.dense_grid[r][c] = 1
                if HAS_NUMPY:
                    self.numpy_grid[r, c] = 1

    def is_alive(self, r, c):
        """Check if a cell is alive in the active algorithm's grid."""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return False
        if self.algorithm_type == "sparse":
            return (r, c) in self.sparse_grid
        elif self.algorithm_type == "dense":
            return self.dense_grid[r][c] == 1
        elif self.algorithm_type == "numpy":
            if HAS_NUMPY:
                return self.numpy_grid[r, c] == 1
            return False
        return False

    @property
    def alive_count(self):
        """Return the number of currently alive cells."""
        if self.algorithm_type == "sparse":
            return len(self.sparse_grid)
        elif self.algorithm_type == "dense":
            return sum(sum(row) for row in self.dense_grid)
        elif self.algorithm_type == "numpy":
            if HAS_NUMPY:
                return int(self.numpy_grid.sum())
            return 0
        return 0


    def update_grid(self):
        """Execute one simulation step using the active algorithm and measure time."""
        t_start = time.perf_counter()

        if self.algorithm_type == "sparse":
            self._update_sparse()
        elif self.algorithm_type == "dense":
            self._update_dense()
        elif self.algorithm_type == "numpy":
            self._update_numpy()

        t_end = time.perf_counter()
        self.last_step_time_ms = (t_end - t_start) * 1000.0
        self.generation += 1

    def _update_sparse(self):
        """Sparse update algorithm using a hash map/dictionary of neighbor counts."""
        neighbor_counts = {}
        for r, c in self.sparse_grid:

            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    
                    nr = r + dr
                    nc = c + dc

                    if self.boundary_type == "loop":
                        nr = nr % self.rows
                        nc = nc % self.cols
                        neighbor_counts[(nr, nc)] = neighbor_counts.get((nr, nc), 0) + 1
                    else:

                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            neighbor_counts[(nr, nc)] = neighbor_counts.get((nr, nc), 0) + 1

        new_alive = set()
        for cell, count in neighbor_counts.items():
            if count == 3:
                new_alive.add(cell)
            elif count == 2 and cell in self.sparse_grid:
                new_alive.add(cell)

        self.sparse_grid = new_alive

    def _update_dense(self):
        """Dense matrix update using a double-buffered 2D array."""
        new_grid = [[0] * self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):

                live_neighbors = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        
                        nr = r + dr
                        nc = c + dc

                        if self.boundary_type == "loop":
                            nr = nr % self.rows
                            nc = nc % self.cols
                            live_neighbors += self.dense_grid[nr][nc]
                        else:

                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                live_neighbors += self.dense_grid[nr][nc]


                if self.dense_grid[r][c] == 1:
                    if live_neighbors == 2 or live_neighbors == 3:
                        new_grid[r][c] = 1
                else:
                    if live_neighbors == 3:
                        new_grid[r][c] = 1
        self.dense_grid = new_grid

    def _update_numpy(self):
        """Vectorized NumPy update using 2D array shifting."""
        if not HAS_NUMPY:
            return

        if self.boundary_type == "loop":
            neighbors = (
                np.roll(np.roll(self.numpy_grid, -1, 0), -1, 1) +
                np.roll(np.roll(self.numpy_grid, -1, 0), 0, 1) +
                np.roll(np.roll(self.numpy_grid, -1, 0), 1, 1) +
                np.roll(np.roll(self.numpy_grid, 0, 0), -1, 1) +
                np.roll(np.roll(self.numpy_grid, 0, 0), 1, 1) +
                np.roll(np.roll(self.numpy_grid, 1, 0), -1, 1) +
                np.roll(np.roll(self.numpy_grid, 1, 0), 0, 1) +
                np.roll(np.roll(self.numpy_grid, 1, 0), 1, 1)
            )
        else:

            p = np.pad(self.numpy_grid, ((1, 1), (1, 1)), mode='constant', constant_values=0)
            neighbors = (
                p[0:-2, 0:-2] + p[0:-2, 1:-1] + p[0:-2, 2:] +
                p[1:-1, 0:-2] + p[1:-1, 2:] +
                p[2:, 0:-2] + p[2:, 1:-1] + p[2:, 2:]
            )

        survive = ((self.numpy_grid == 1) & ((neighbors == 2) | (neighbors == 3)))
        born = ((self.numpy_grid == 0) & (neighbors == 3))
        self.numpy_grid = (survive | born).astype(np.uint8)


    def save_layout(self, filename):
        """Save the current coordinates of alive cells to a text file."""
        self.sync_all()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# Conway's Game of Life Layout - Rows={self.rows}, Cols={self.cols}\n")
                for r, c in sorted(self.sparse_grid):
                    f.write(f"{r},{c}\n")
            return True, f"已成功保存布局到 {filename}"
        except Exception as e:
            return False, f"保存失败: {str(e)}"

    def load_layout(self, filename):
        """Load coordinates from a layout file, matching coordinates within grid boundaries."""
        try:
            temp_sparse = set()
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        r = int(parts[0])
                        c = int(parts[1])
                        if 0 <= r < self.rows and 0 <= c < self.cols:
                            temp_sparse.add((r, c))
            
            self.generation = 0
            self.last_step_time_ms = 0.0
            self.sparse_grid = temp_sparse
            self._sync_from_sparse()
            return True, f"已成功从 {filename} 加载布局"
        except Exception as e:
            return False, f"加载失败: {str(e)}"
