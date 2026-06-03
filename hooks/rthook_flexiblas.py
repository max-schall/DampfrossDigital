# Runtime hook: tell FlexiBLAS to find its OpenBLAS plugin inside the bundle.
# Without this, libflexiblas.so.3 looks for backends in /usr/lib64/flexiblas/
# which doesn't exist on the target machine.
import os
import sys

_base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FLEXIBLAS_LIBRARY_PATH', _base)
os.environ.setdefault('FLEXIBLAS', 'openblas-openmp')
