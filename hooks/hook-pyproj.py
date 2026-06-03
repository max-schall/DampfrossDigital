# Custom hook for pyproj: include only proj.db (the projection database).
# Datum shift grids (*.tif files, ~770 MB) are for high-precision geodetic
# transformations and are not needed for LAEA projection used in this app.

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, is_module_satisfies

hiddenimports = ['pyproj.datadir', 'pyproj._compat']

datas = collect_data_files('pyproj')

# Add only proj.db from the system PROJ data directory, not the full ~770 MB
root_path = getattr(sys, 'real_prefix', sys.prefix)
src_proj_db = os.path.join(root_path, 'share', 'proj', 'proj.db')
if os.path.exists(src_proj_db):
    datas.append((src_proj_db, os.path.join('share', 'proj')))
