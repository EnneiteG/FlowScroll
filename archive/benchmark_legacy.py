import time
import concurrent.futures
import os, sys
# Ensure project root is on sys.path so local modules (workers) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import workers


def run_benchmark():
    # Benchmark heavy_work single-process vs multi-process
    N = 5
    WORK_SIZE = 500_000  # tune for a measurable CPU load

    print('Benchmark: running', N, 'tasks of heavy_work(', WORK_SIZE, ')')

    # Single-threaded (serial)
    start = time.time()
    results = [workers.heavy_work(WORK_SIZE) for _ in range(N)]
    end = time.time()
    print('Serial time: {:.3f}s'.format(end - start))

    # Multi-process using ProcessPoolExecutor
    start = time.time()
    with concurrent.futures.ProcessPoolExecutor() as ex:
        futures = [ex.submit(workers.heavy_work, WORK_SIZE) for _ in range(N)]
        results = [f.result() for f in futures]
    end = time.time()
    print('ProcessPool time: {:.3f}s'.format(end - start))

    # Multi-thread using ThreadPoolExecutor (won't speed CPU-bound due to GIL)
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(workers.heavy_work, WORK_SIZE) for _ in range(N)]
        results = [f.result() for f in futures]
    end = time.time()
    print('ThreadPool time: {:.3f}s'.format(end - start))

    print('Done')


if __name__ == '__main__':
    try:
        import multiprocessing as _mp
        _mp.freeze_support()
    except Exception:
        pass
    run_benchmark()
