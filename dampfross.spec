# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for DampfrossDigital2.

Build with:
  pyinstaller dampfross.spec

Output: dist/DampfrossDigital/
"""
import sys
import os

block_cipher = None

# FlexiBLAS is a BLAS dispatcher used on Fedora/Nobara Linux.
# It is not present on macOS or Windows (those use their own BLAS from wheels).
def _flexiblas_binaries():
    if sys.platform != 'linux':
        return []
    candidates = [
        '/usr/lib64/flexiblas/libflexiblas_netlib.so',
        '/usr/lib64/flexiblas/libflexiblas_fallback_lapack.so',
        '/usr/lib64/flexiblas/libflexiblas_openblas-openmp.so',
        '/lib64/libopenblaso.so.0',
        '/lib64/libgfortran.so.5',
    ]
    return [(p, '.') for p in candidates if os.path.exists(p)]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_flexiblas_binaries(),
    datas=[
        # Audio assets bundled inside the package directory
        ('dampfross/music', 'dampfross/music'),
        ('dampfross/sfx',   'dampfross/sfx'),
        # Bundled maps shipped with the game
        ('maps', 'maps'),
    ],
    hiddenimports=[
        # scipy / numpy lazy submodules that PyInstaller can miss
        'scipy._lib.messagestream',
        'scipy.special._ufuncs',
        'scipy.spatial.transform._rotation_groups',
        'numpy.core._multiarray_umath',
        # shapely sometimes needs its C extensions named explicitly
        'shapely._geometry',
        # pyngrok deferred imports
        'pyngrok.conf',
        'pyngrok.ngrok',
        # pygame mixer backend
        'pygame.mixer',
        'pygame.mixer_music',
        # platformdirs
        'platformdirs',
    ],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/rthook_flexiblas.py'],
    excludes=[
        # Design hand-off files are not runtime code
        'design_handoff_dampfrossdigital',
        # Test suite is not shipped
        'tests',
        'pytest',
        '_pytest',
        # IPython / Jupyter not needed
        'IPython',
        'jupyter',
        # ML/AI frameworks — not used at runtime, but installed on the build machine
        'torch',
        'torchvision',
        'torchaudio',
        'tensorflow',
        'keras',
        'jax',
        'flax',
        'nvidia',
        'triton',
        'transformers',
        'diffusers',
        'accelerate',
        'bitsandbytes',
        'xformers',
        'sklearn',
        'sklearn',
        'lightgbm',
        'xgboost',
        # Notebook / interactive tooling
        'notebook',
        'ipykernel',
        'ipywidgets',
        'nbformat',
        'nbconvert',
        # Linting / dev tools
        'black',
        'pylint',
        'mypy',
        'ruff',
        'flake8',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir mode — all libs go in _internal/
    name='DampfrossDigital',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no terminal window on Windows / macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DampfrossDigital',
)
