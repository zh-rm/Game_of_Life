import os
import sys


sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from game_logic import GameOfLife, HAS_NUMPY

def test_glider_loop_boundary():

    game = GameOfLife(rows=10, cols=10, boundary_type="loop", algorithm_type="sparse")
    game.reset_clear()
    

    glider = {(7, 8), (8, 9), (9, 7), (9, 8), (9, 9)}
    game.sparse_grid = glider.copy()
    game.sync_all()
    

    for _ in range(4):
        game.update_grid()
        
    game.sync_all()

    expected_cells = {(8, 9), (9, 0), (0, 8), (0, 9), (0, 0)}
    assert game.sparse_grid == expected_cells


def test_algorithm_consistency():
    rows, cols = 20, 20
    

    game_sparse = GameOfLife(rows=rows, cols=cols, boundary_type="dead", algorithm_type="sparse")
    game_dense = GameOfLife(rows=rows, cols=cols, boundary_type="dead", algorithm_type="dense")
    

    initial_cells = {(2, 3), (3, 4), (4, 2), (4, 3), (4, 4), (10, 11), (11, 10), (12, 12)}
    
    game_sparse.sparse_grid = initial_cells.copy()
    game_sparse.sync_all()
    
    game_dense.dense_grid = [[0]*cols for _ in range(rows)]
    for r, c in initial_cells:
        game_dense.dense_grid[r][c] = 1
    game_dense.sync_all()
    
    if HAS_NUMPY:
        game_numpy = GameOfLife(rows=rows, cols=cols, boundary_type="dead", algorithm_type="numpy")
        game_numpy.numpy_grid = game_numpy.numpy_grid * 0
        for r, c in initial_cells:
            game_numpy.numpy_grid[r, c] = 1
        game_numpy.sync_all()
    else:
        game_numpy = None


    for step in range(30):
        game_sparse.update_grid()
        game_dense.update_grid()
        if game_numpy:
            game_numpy.update_grid()


        game_sparse.sync_all()
        game_dense.sync_all()
        if game_numpy:
            game_numpy.sync_all()


        assert game_sparse.sparse_grid == game_dense.sparse_grid, f"Mismatch at step {step} (Sparse vs Dense)"
        

        if game_numpy:
            assert game_sparse.sparse_grid == game_numpy.sparse_grid, f"Mismatch at step {step} (Sparse vs Numpy)"


def test_save_load_layout():
    filename = "test_layout_temp.txt"
    game = GameOfLife(rows=15, cols=15, boundary_type="dead", algorithm_type="sparse")
    game.reset_clear()
    
    test_pattern = {(1, 2), (5, 5), (10, 12), (14, 14)}
    game.sparse_grid = test_pattern.copy()
    game.sync_all()
    

    success, msg = game.save_layout(filename)
    assert success
    assert os.path.exists(filename)
    

    game.reset_clear()
    assert len(game.sparse_grid) == 0
    
    success, msg = game.load_layout(filename)
    assert success
    assert game.sparse_grid == test_pattern
    

    if os.path.exists(filename):
        os.remove(filename)


if __name__ == "__main__":
    tests = [
        test_glider_loop_boundary,
        test_algorithm_consistency,
        test_save_load_layout
    ]
    passed = 0
    print("--- 运行测试用例 ---")
    for t in tests:
        print(f"运行 {t.__name__}...", end="")
        try:
            t()
            print(" [通过]")
            passed += 1
        except Exception as e:
            print(" [失败]")
            import traceback
            traceback.print_exc()
    print(f"\n结果: 共 {len(tests)} 个测试，通过 {passed} 个。")
    if passed < len(tests):
        sys.exit(1)
