import multiprocessing.pool as mp
import itertools


def subprocess_setup():
    import django

    django.setup()


def optional_pool(processes=None, only_threads=False, initializer=None):
    """
    :param processes: number of processes to use.
        None will default to os.cpu_count().
        0 or 1 will not use multiprocessing.
    :param only_threads: use ThreadPool (instead of Pool)
    :return: an instance of multiprocessing.Pool, multiprocessing.ThreadPool or FakePool, depending on parameters
    """
    # leave None out to default to os.cpu_count()
    if processes in (0, 1):
        return _FakePool()

    if only_threads:
        p = mp.ThreadPool(processes=processes, initializer=initializer)
    else:
        p = mp.Pool(processes=processes, initializer=initializer or subprocess_setup)
    # tag class with custom attribute highlighting multiprocessing is enabled (not a FakePool)
    p._optional_multi = True
    return p


class _FakePool:
    _optional_multi = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()

    def imap_unordered(self, *a, **b):
        return map(*a, **b)

    def imap(self, *a, **b):
        return map(*a, **b)

    def map(self, *a, **b):
        return map(*a, **b)

    def starmap(self, *a, **b):
        return itertools.starmap(*a, **b)

    def terminate(self):
        pass
