# Changelog

## 2026-05-11 — Code Cleanup & Refactoring

### DBwin.py

**STL model registry**
- Replaced 8 identical copy-paste STL toggle blocks (~180 lines) with a module-level `_STL_MODELS` dict and a single generic `_toggle_stl(name, path_field, btn_idx, opacity)` method (~25 lines)
- `_STL_MODELS` maps display name → (mongo path field, buttonStatus index, opacity)

**Scene state consolidation**
- Replaced 9 separate STL attributes (`self.mandible`, `self.maxilla`, etc. each with mapper/actor) with `self._stl_meshes = {}` and `self._stl_actors = {}`
- Replaced `self.box_widget / box_widget1 / box_widget2 / box_widget3` with `self.box_widgets = []`
- Replaced `self.nModel` counter with `self._camera_initialized = False` boolean

**Extracted methods**
- `_cleanup_scene()` — removes volume, turns off box widgets, clears STL actors; called on row selection change
- `_setup_camera()` — sets anterior view, parallel projection, resets clipping; called once after first model loads
- `_apply_bone_tf(colorFun, opacityFun, include_soft_tissue, width_s=80)` — shared transfer function for CT Bone1 and Bone2 modes; `include_soft_tissue` controls soft-tissue opacity bump
- `_apply_composite_shading(mapper, prop)` — sets shade, blend mode, ambient/diffuse/specular for composite render
- `_VIEW_CORNERS = {1: (0, 5), 2: (4, 7), 3: (1, 7)}` — maps render direction to bounding-box corner indices
- `_get_corner_display(extent)` — projects world-space extent corners to display coordinates
- `_crop_margins(disp_coords)` — computes symmetric crop margins from projected corners

**add_model() reduced from ~180 to ~20 lines**
- CT branch unchanged in behavior; STL branch is a single `_toggle_stl()` dispatch

**TableModel simplifications**
- `data()` reduced to a single return line
- `headerData()` uses a list lookup instead of if/elif chain

**Bug fixes**
- `self.wcs_extent([...])` (called as function) → `self.wcs_extent.append([...])`
- `segment()`: removed unreachable `else: print("Error")` → early return guard clause
- `box_widgets` list replaces 4 separate attributes in `segment()`

**Removed unused imports**
- `QGuiApplication`, `QWindow`, `QQmlApplicationEngine`, `qmlRegisterType`, `QFileInfo`, `QDir`, `qDebug`, `QRunnable`, `QThreadPool`, `Property`, `vtkBoxWidget2`, `vtkBoxRepresentation`, `vtkTransform`, `glob`, `json`, `matplotlib.pyplot`

---

### ScanDirectory.py

**Named DICOM tag constants**
- Renamed `t1..t28` to descriptive names: `TAG_PATIENT_ID`, `TAG_SERIES_UID`, `TAG_NUM_FRAMES`, `TAG_PIX_SPACE`, `TAG_IOP`, `TAG_RESCALE_SLP`, `TAG_RESCALE_INT`, `TAG_WIN_CENTER`, `TAG_WIN_WIDTH`, etc.

**Module-level constant**
- `_GDCM_NP_TYPES` dict (PixelFormat → numpy dtype) promoted to module level

**Helper functions**
- `_gdcm_dtype(image)` — extracts numpy dtype from GDCM PixelFormat
- `_parse_ds_values(ds_str)` — renamed from `toList`; converts DICOM DS string to float list
- `_read_pos()` nested helper in `GetSpacingDirOrigin` for cleaner tag parsing

**Dead code removed**
- `ProgressWatcher` class (unused)
- `GetZSpacing` function (unused)
- `show_mid_slice`, `show_slices` functions (debug/visualization dead code)
- `find_connected_elements_3d`, `MinConnectedVoxel` (moved to DBwin.py where actually used)
- `getKey` function → replaced with inline `lambda item: item[2]`
- `dicomfiles`, `patient_list`, `study_list` accumulators (built but never consumed)
- Unused `x`, `y`, `z` arange arrays and redundant `spacing = image.GetSpacing()` assignment
- Redundant `dataImporter = vtk.vtkImageImport()` line (immediately overwritten)

**Bug fixes**
- Series detection: `if (len(series_list)>1 and len(series_list)==0):` (always False) → `if len(series_list) != 1:`
- Multi-file branch: explicit `is_multiframe = 0` to prevent scope leak from single-file branch

**Transfer function**
- CT Bone1/Bone2 merged into single `elif blendType in (3, 5):` branch with soft-tissue conditional, matching the `_apply_bone_tf` helper in DBwin

**Removed unused imports**
- `subprocess`, `ndimage` (from scipy), `argrelextrema`, `skimage.data`, `convert_directory`, `matplotlib.pyplot`

---

### Net change

| File | Insertions | Deletions | Net |
|---|---|---|---|
| DBwin.py | +372 | −768 | −396 |
| ScanDirectory.py | +374 | −853 | −479 |
| **Total** | | | **−875 lines** |
