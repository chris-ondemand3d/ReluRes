# ReluRes — Dental CT Result Viewer

A desktop application for reviewing, visualizing, and annotating dental CT scan segmentation results stored in MongoDB. Built on PySide6 + VTK, it loads DICOM series, renders 3D volumes, displays AI segmentation outputs, and exports YOLO-format bounding-box annotations from screenshot captures.

---

## Architecture Overview

```
main.py          → QApplication entry point; loads .env into os.environ
DBwin.py         → Main window (MAINApp), table model, 3D scene management
ScanDirectory.py → DICOM loading (GDCM), NIfTI export, VTK volume construction
dicom2nifti/     → DICOM-to-NIfTI conversion library (pydicom/nibabel based)
dbwin.qml        → QML patient-list UI (TableView + control buttons)
QVTKRenderWindowInteractor.py → Qt/VTK interactor bridge
.env             → Local secrets (MONGO_URI); gitignored
```

### DBwin.py — key internals

| Symbol | Kind | Purpose |
|---|---|---|
| `_STL_MODELS` | module dict | Maps button name → `(mongo_field, btn_idx, opacity)` for all 8 STL structures |
| `_cleanup_scene()` | method | Removes volume, box widgets, and all STL actors when a new row is selected |
| `_setup_camera()` | method | Sets anterior view + parallel projection; called once after first model loads |
| `_toggle_stl()` | method | Generic STL load/unload driven by `_STL_MODELS`; replaces 8 copy-paste blocks |
| `_apply_bone_tf()` | method | Shared CT Bone1/Bone2 transfer function; `include_soft_tissue` flag controls peak |
| `_apply_composite_shading()` | method | Sets shade, blend mode, and material for composite render |
| `_VIEW_CORNERS` | class dict | Maps render direction → `(min_vertex_idx, max_vertex_idx)` for bbox projection |
| `_get_corner_display()` | method | Projects world-space extent corners to display coordinates |
| `_crop_margins()` | method | Computes symmetric crop margins from projected volume corners |

---

## Data Flow

```
MongoDB (KorGuide/ReluRes)
  └─ Query: cases with ≤6 missing teeth where tooth #35 or #45 is missing
       └─ Patient TableView (patient_id, patient_name, study_uid, study_date, comment)
            └─ Row selected → check available model paths → enable buttons
                 ├─ CT button   → load_dicom({path}/cvt) → VTK vtkVolume
                 ├─ Model buttons → load STL → vtkActor (mandible / maxilla / etc.)
                 ├─ Segment     → nnUNetv2_predict → {path}/output/Dental_0001.nii.gz
                 │                  └─ compute 3D extents → vtkBoxWidget overlays
                 └─ Capture     → screenshot PNG + YOLO .txt bounding-box file
```

---

## MongoDB Document Schema

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Document ID |
| `path` | string | Root directory for this case |
| `patient_id` | string | Patient identifier |
| `patient_name` | string | Patient name |
| `study_uid` | string | DICOM Study Instance UID |
| `study_date` | date | Study date |
| `comment` | string | Free-text annotation (editable in UI) |
| `mandible_path` | string | Path to `mandible.stl` |
| `maxilla_path` | string | Path to `maxilla.stl` |
| `upper_path` | string | Path to upper dentition STL |
| `lower_path` | string | Path to lower dentition STL |
| `left_sinus_path` | string | Path to left sinus STL |
| `right_sinus_path` | string | Path to right sinus STL |
| `left_nerve_path` | string | Path to left IAN STL |
| `right_nerve_path` | string | Path to right IAN STL |
| `teeth[]` | array | Per-tooth records: `{number, missing, tooth_path}` |

### Directory layout per case

```
{path}/
  cvt/        DICOM series files
  segment/    NIfTI input for nnUNet  (Dental_0001_0000.nii.gz)
  output/     nnUNet prediction output (Dental_0001.nii.gz)
```

---

## DICOM Loading — `ScanDirectory.load_dicom()`

Uses GDCM to scan a directory, auto-detects single-file multiframe or multi-file series.

**Extracted DICOM tags:**

| Tag | Description |
|---|---|
| `(0028,0030)` Pixel Spacing | In-plane pixel spacing (dx, dy) |
| `(0020,0037)` Image Orientation Patient | Direction cosines (row, col vectors) |
| `(0020,0032)` Image Position Patient | Slice origin in patient coords |
| `(0028,1052)/(1053)` Rescale Intercept/Slope | HU calibration |
| `(0028,1050)/(1051)` Window Center/Width | Display window |
| `(5200,9229)/(9230)` Shared/Per-Frame Functional Groups | Multiframe metadata |

**Processing steps:**
1. Sort slices by projected position along the slice-normal vector
2. Stack into a 3D `numpy` array, apply flip if slice order is reversed
3. Apply `threshold_multiotsu(4)` on a normalized copy to compute 3 adaptive thresholds (`adjThresholds[0..2]`) used by transfer functions
4. Import into VTK via `vtkImageImport` with correct spacing, origin, and direction matrix
5. Apply `vtkImageShiftScale` (RescaleSlope / RescaleIntercept)
6. Attach `vtkOpenGLGPUVolumeRayCastMapper` and `vtkVolumeProperty`

### NIfTI export (for nnUNet input)

When `makenifti=True`:
- Transposes volume to (I, J, K) order
- Constructs NIfTI affine from direction cosines, pixel spacing, and slice step
- Saves as `{path}/segment/Dental_0001_0000.nii.gz`

---

## Volume Rendering Modes

Cycling order: **3 → 5 → 1 → 3** (triggered by Render Mode button)

| Mode | Name | Description |
|---|---|---|
| `3` | CT Bone1 | Composite; soft tissue peak visible + bone. Color: blue → ivory → brown → gold → silver |
| `5` | CT Bone2 | Composite; bone-only emphasis, soft tissue peak removed |
| `1` | MIP | Maximum Intensity Projection; flat white palette |

All composite modes use:
- `ShadeOn`, Ambient 0.2, Diffuse 1.0, Specular 0.0
- `ScalarOpacityUnitDistance` 0.8919
- Adaptive color/opacity breakpoints derived from `adjThresholds`

### Render Directions

Cycling order: **Anterior (1) → Left (2) → Superior/Head (3) → Anterior**

| Value | View | Camera position |
|---|---|---|
| `1` | Anterior | `fp - dist * Y` |
| `2` | Left | `fp + dist * X` |
| `3` | Superior | `fp + dist * Z` |

All views use parallel projection and Z-up (or Y-up for Superior).

---

## Segmentation — nnUNetv2

Triggered by the Segment button. Runs `nnUNetv2_predict`:

```
nnUNetv2_predict -i {path}/segment/ -o {path}/output/
  -d Dataset111_453CT -tr nnUNetTrainer -p nnUNetPlans
  -c 3d_fullres -f 0 -npp 1 -nps 1 -step_size 0.5
  -device cuda --disable_tta
```

**Output labels in `Dental_0001.nii.gz`:**

| Label | Structure |
|---|---|
| 1 | Maxilla |
| 2 | Mandible |
| 3 | Left maxillary sinus |
| 4 | Right maxillary sinus |
| 5 | Inferior alveolar nerve (IAN) |

After prediction, per-label 3D extents are computed (filtering connected components < 5000 voxels) and displayed as `vtkBoxWidget` overlays on the CT volume.

**Extent → world-coordinate conversion:**
```
x = i * spacing[0] + origin_x
y = j * spacing[1] + origin_y
z = k * spacing[2] + origin_z
```

---

## Screenshot Capture & YOLO Annotation Export

Triggered by the Capture button. Output files are named:

```
{studyUID}_{rendermode}{renderDir}{screenshotCount}.png   ← cropped screenshot
{studyUID}_{rendermode}{renderDir}{screenshotCount}.txt   ← YOLO bounding boxes
```

**Crop logic:** The volume's world-space bounding-box vertices are projected to display coordinates. The crop margin is the minimum distance from each side to keep the volume centered and symmetric.

**YOLO format** (one line per segmentation label):
```
<label_index> <cx> <cy> <width> <height>
```
All values are normalized to `[0, 1]` relative to the cropped image dimensions.

**View-to-vertex mapping** for bounding box corners:

| View | Min corner display coord | Max corner display coord |
|---|---|---|
| Anterior (1) | vertex 0 | vertex 5 |
| Left (2) | vertex 4 | vertex 7 |
| Superior (3) | vertex 1 | vertex 7 |

---

## 3D Models (STL)

Loaded with `vtkSTLReader` (merging on). All 8 named structures are driven by the module-level `_STL_MODELS` registry — each entry maps a button name to its MongoDB path field, `buttonStatus` index, and opacity. Toggle calls `_toggle_stl()` generically; no per-model code paths exist.

| Button name | `buttonStatus` index | Opacity | Structure |
|---|---|---|---|
| `Mandible` | 1 | 0.3 | Lower jaw bone |
| `Maxiilary` | 2 | 0.3 | Upper jaw bone |
| `Upper` | 3 | 0.3 | Upper dentition |
| `Left Sinus` | 4 | 1.0 | Left maxillary sinus |
| `Right Sinus` | 5 | 1.0 | Right maxillary sinus |
| `Lower` | 6 | 0.3 | Lower dentition |
| `Left Nerve` | 7 | 1.0 | Left inferior alveolar nerve |
| `Right Nerve` | 8 | 1.0 | Right inferior alveolar nerve |
| Tooth buttons (×32) | 9–40 | — | Individual tooth models |

Button state: `0` = not available, `1` = available/hidden, `2` = visible.

---

## Requirements

```
vtk==9.3.1
pymongo==3.11.0
pyside6==6.7.2
nibabel==5.2.1
nnunetv2==2.5.1
scikit-image==0.24.0
scipy
gdcm          (system package or conda)
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root (gitignored):

```
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=<app>
```

`main.py` loads this file into `os.environ` before importing `DBwin`. The variable is required — the app exits with an error if it is unset.

---

## Running

```bash
python main.py
```

Two windows open:
- **Left (640×960):** QML patient list at position (40, 40)
- **Right (960×960):** VTK 3D viewport at position (680, 10)

---

## `dicom2nifti/` Module

Bundled vendor-converter library supporting Siemens, GE, Philips, Hitachi, and generic DICOM series. Used as a fallback conversion path; the primary path is the direct numpy→NIfTI export in `ScanDirectory.py`.

| File | Purpose |
|---|---|
| `convert_dicom.py` | Top-level `dicom_series_to_nifti()` dispatcher |
| `convert_dir.py` | Directory-level batch conversion |
| `convert_siemens/ge/philips/hitachi/generic.py` | Vendor-specific converters |
| `common.py` | Shared DICOM reading utilities |
| `image_reorientation.py` | LAS reorientation |
| `resample.py` | Isotropic resampling |
| `settings.py` | Global flags (validation toggles) |
