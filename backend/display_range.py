"""Exact shared percentiles without concatenating every dated raster in RAM.

Small populations retain NumPy's linear percentile path. Larger populations use
byte-wise rank selection over ordered IEEE float keys, rereading bounded raster
windows at most four times (float32), or eight times (float64). No sampling,
histogram-bin approximation, temporary science files or persisted range cache.
"""
from contextlib import ExitStack
import numpy as np
import rasterio
from rasterio.windows import Window
from .execution import checkpoint

WINDOW_SIDE = 256
IN_MEMORY_VALUES = 262_144


def _keys(values, dtype):
    unsigned = np.dtype('uint32' if dtype.itemsize == 4 else 'uint64')
    bits = values.view(unsigned)
    sign = np.array(1 << (dtype.itemsize * 8 - 1), dtype=unsigned)
    return np.where(bits & sign, ~bits, bits ^ sign)


def exact_percentiles(blocks, dtype, quantiles=(2, 98)):
    """`blocks()` must replay the same finite/nonfinite real values on each pass.

    Working arrays are bounded by caller block size plus IN_MEMORY_VALUES. The
    dtype must be the common NumPy dtype of all sources to preserve interpolation.
    """
    dtype = np.dtype(dtype).newbyteorder('=')
    if dtype not in (np.dtype('float32'), np.dtype('float64')):
        raise ValueError('Display ranges require float32 or float64 rasters.')
    q = np.asarray(quantiles, dtype='float64')
    if q.ndim != 1 or not q.size or not np.isfinite(q).all() or np.any((q < 0) | (q > 100)):
        raise ValueError('Percentiles must be finite values from 0 to 100.')
    total = 0
    retained = []
    counts = np.zeros(256, dtype='int64')
    shift = dtype.itemsize * 8 - 8
    for block in blocks():
        checkpoint()
        a = np.asarray(block, dtype=dtype).ravel()
        a = a[np.isfinite(a)]
        total += a.size
        if total <= IN_MEMORY_VALUES:
            retained.append(a)
        else:
            retained.clear()
        keys = _keys(a, dtype)
        counts += np.bincount((keys >> shift).astype('uint8'), minlength=256)
    if not total:
        raise ValueError('No finite measurements for the display range.')
    if total <= IN_MEMORY_VALUES:
        return np.percentile(np.concatenate(retained), q)

    positions = (total - 1) * (q / 100)
    lower = np.floor(positions).astype('int64')
    upper = np.minimum(lower + 1, total - 1)
    ranks = sorted(set(lower.tolist() + upper.tolist()))
    # Each requested order statistic carries its prefix and residual rank.
    states = {}
    cumulative = np.cumsum(counts)
    for rank in ranks:
        bucket = int(np.searchsorted(cumulative, rank, side='right'))
        states[rank] = (bucket, rank - (int(cumulative[bucket - 1]) if bucket else 0))
    for shift in range(shift - 8, -1, -8):
        prefixes = {prefix for prefix, _ in states.values()}
        histograms = {prefix: np.zeros(256, dtype='int64') for prefix in prefixes}
        for block in blocks():
            checkpoint()
            a = np.asarray(block, dtype=dtype).ravel()
            keys = _keys(a[np.isfinite(a)], dtype)
            parents = keys >> (shift + 8)
            for prefix in prefixes:
                selected = keys[parents == prefix]
                histograms[prefix] += np.bincount(((selected >> shift) & 255).astype('uint8'), minlength=256)
        for rank, (prefix, residual) in states.items():
            cumulative = np.cumsum(histograms[prefix])
            if not cumulative.size or residual >= cumulative[-1]:
                raise ValueError('Saved measurements changed while resolving the display range. Retry the map.')
            bucket = int(np.searchsorted(cumulative, residual, side='right'))
            states[rank] = ((prefix << 8) | bucket, residual - (int(cumulative[bucket - 1]) if bucket else 0))
    unsigned = np.dtype('uint32' if dtype.itemsize == 4 else 'uint64')
    sign = 1 << (dtype.itemsize * 8 - 1)
    mask = (1 << (dtype.itemsize * 8)) - 1
    def value(rank):
        key = states[int(rank)][0]
        bits = key ^ sign if key & sign else (~key & mask)
        return np.array(bits, dtype=unsigned).view(dtype)[()]
    a = np.array([value(rank) for rank in lower], dtype=dtype)
    b = np.array([value(rank) for rank in upper], dtype=dtype)
    fraction = positions - lower
    # Match NumPy's linear interpolation, including float32 subtraction and
    # its upper-end branch, rather than silently promoting the subtraction.
    difference = b - a
    result = a + difference * fraction
    np.subtract(b, difference * (1 - fraction), out=result, where=fraction >= .5)
    return result


def raster_percentiles(paths, quantiles=(2, 98), max_cells=4_000_000):
    """Keep datasets open across passes; each decoded window is <=256×256."""
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(path)) for path in paths]
        if not sources:
            raise ValueError('No saved maps were supplied for the display range.')
        if any(source.width * source.height > max_cells for source in sources):
            raise ValueError('Preview grid is too large.')
        dtype = np.result_type(*[source.dtypes[0] for source in sources])
        def blocks():
            for source in sources:
                for row in range(0, source.height, WINDOW_SIDE):
                    for col in range(0, source.width, WINDOW_SIDE):
                        yield source.read(1, window=Window(col, row, min(WINDOW_SIDE, source.width-col), min(WINDOW_SIDE, source.height-row)))
        return exact_percentiles(blocks, dtype, quantiles)
