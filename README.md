<div align="center">

# STRUCTURAL SUITE Pro
### Post-Tensioned Prestressed Concrete I-Girder Bridge Design

*A parametric desktop application that designs, checks, visualises and reports a 33 m simply supported PSC I-girder bridge from a single calculation engine.*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52)
![Codes](https://img.shields.io/badge/Codes-IRC%3A6--2017%20%7C%20IRC%3A112--2011-orange)
![Course](https://img.shields.io/badge/Course-CE60258-lightgrey)

**Ranvir Kumar** · Roll No. 23CE36016 · Department of Civil Engineering, IIT Kharagpur

</div>

---

## Table of contents

1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Screenshots](#3-screenshots)
4. [Views](#4-views)
5. [Analysis diagrams](#5-analysis-diagrams)
6. [Repository structure](#6-repository-structure)
7. [Requirements](#7-requirements)
8. [Installation and running](#8-installation-and-running)
   - [Option A: PowerShell (Windows)](#option-a-powershell-windows)
   - [Option B: Visual Studio Code](#option-b-visual-studio-code)
   - [Option C: Visual Studio 2022](#option-c-visual-studio-2022)
   - [macOS / Linux](#macos--linux)
9. [Using the application](#9-using-the-application)
10. [Design methodology](#10-design-methodology)
11. [Testing](#11-testing)
12. [Troubleshooting](#12-troubleshooting)
13. [Assumptions and limitations](#13-assumptions-and-limitations)
14. [Author and acknowledgements](#14-author-and-acknowledgements)

---

## 1. Overview

Structural Suite Pro is the big-problem project for **CE60258** (due 31 October 2026). It designs a simply supported, post-tensioned PSC I-girder bridge for a 33 m span.

The central idea is **one engine, every page**. All numbers, drawings and diagrams come from `bridge_engine.py`. The user interface only collects inputs and displays results, so any valid input gives a consistent geometry, 3D model, set of diagrams, design checks and report.

| Item | Default case |
|---|---|
| Effective span | 33.0 m |
| Deck width / carriageway | 14.5 m / 10.5 m |
| Girders | 5 at 2.9 m spacing, 1.45 m overhang |
| Girder depth / slab | 2.0 m / 250 mm |
| Prestress | 3 cables x 17 strands (7,140 mm²) |
| Governing live load | IRC Class 70R Wheeled |

## 2. Features

- **Home page** to start a new project or open a saved one (JSON project files).
- **Guided workflow** with Next and Back buttons: Project, Geometry and Materials, Loads, 3D Model, Analysis, Results, Report.
- **IRC:6-2017 loading**: Class A, Class B, 70R wheeled, 70R tracked, and a Governing envelope; impact, lane reduction and Courbon distribution factor.
- **Post-tensioning model**: friction, anchorage slip, elastic shortening, creep, shrinkage and relaxation losses; parabolic tendon profile; two ducts in the bottom flange and the rest in the web below the centroid.
- **Limit-state checks** to IRC:112-2011: flexure (strain compatibility), shear (variable strut), staged stresses, and long-term deflection.
- **Interactive 3D model** with element checkboxes, per-girder toggles, mouse rotate and zoom, axes gizmo and full-screen view.
- **Dimensioned 2D views**: elevation, plan, cross-section and girder section with duct positions.
- **Five analysis diagrams**: bending moment, shear force, deflection, concrete stresses, prestress force and eccentricity.
- **Results page** with KPI cards, a 14-row check table and a clickable step-by-step calculation panel.
- **Report export** to PDF, CSV and text, with a written description and neat calculation pages.

## 3. Screenshots

| Home | Project |
|:--:|:--:|
| ![Home](Screenshots/Home%20page.png) | ![Project](Screenshots/Project%20Page.png) |

| Geometry and Materials | Loads |
|:--:|:--:|
| ![Geometry](Screenshots/Geometry%20%26%20Material%20Page_01.png) | ![Loads](Screenshots/Load%20Page.png) |

| 3D Model | Analysis |
|:--:|:--:|
| ![3D](Screenshots/3D%20model%20Page.png) | ![Analysis](Screenshots/Analysis%20Page.png) |

| Results | Report |
|:--:|:--:|
| ![Results](Screenshots/Result%20Page.png) | ![Report](Screenshots/Report%20Page.png) |

## 4. Views

Dimensioned 3D and 2D views generated from the same engine (Views/ folder).

| 3D view | Elevation |
|:--:|:--:|
| ![3D](Views/3D%20View.png) | ![Elevation](Views/Elevation%20View.png) |

| Plan | Bridge cross-section |
|:--:|:--:|
| ![Plan](Views/Plan%20View.png) | ![Cross-section](Views/Bridge%20Cross%20Section%20View.png) |

| Girder section with tendon ducts |
|:--:|
| ![Girder](Views/Girder%20View.png) |

## 5. Analysis diagrams

| Bending moment | Shear force |
|:--:|:--:|
| ![BM](Diagram/Bending%20Moment%20Diagram.png) | ![SF](Diagram/Shear%20Force%20Diagram.png) |

| Deflection | Concrete stresses |
|:--:|:--:|
| ![Defl](Diagram/Deflection%20Diagram.png) | ![Stress](Diagram/Concrete%20Stress%20Diagram.png) |

| Prestress force and eccentricity |
|:--:|
| ![PS](Diagram/Prestress%20force%20and%20eccentricity%20diagram.png) |

Key default-case results: Mu = 16,032 kNm against 19,939 kNm capacity; design shear 1,348 kN against 1,561 kN; P0 = 9,960 kN, Pe at midspan 7,981 kN (19.9 % total loss); long-term deflection 28.1 mm against a 132 mm limit. 13 of 14 checks pass. The transfer maximum compression check is slightly over (22.78 against 22.50 MPa) and is shown honestly.

## 6. Repository structure

```text
Post-tensioned-prestressed-concrete-I-girder/
├── main.py                 # Application window and page navigation (run this)
├── bridge_engine.py        # The calculation engine (all numbers come from here)
├── ui_analysis.py          # Analysis diagrams
├── ui_3d_model.py          # 3D model and 2D dimensioned views
├── ui_results.py           # KPI cards, check table, calculation panel
├── ui_report.py            # Report text, PDF, CSV export
├── ui_common.py            # Shared zoom/pan and full-screen helpers
├── test_engine.py          # Engine unit tests
├── bridge_project.json     # Sample saved project
├── bridge_report.pdf       # Sample generated report
├── requirements.txt        # Python dependencies
├── Diagram/                # Analysis diagram images
├── Screenshots/            # Application page screenshots
└── Views/                  # 3D, elevation, plan, cross-section, girder views
```

## 7. Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or newer (3.13 tested) |
| PySide6 | 6.6 or newer |
| matplotlib | 3.8 or newer |
| numpy | 1.26 or newer |
| reportlab | 4.0 or newer |

A screen of at least 1280 x 720 is recommended. The app needs no internet connection once installed.

## 8. Installation and running

First get the code. Either clone with Git:

```bash
git clone https://github.com/Ranvirkgpian/Post-tensioned-prestressed-concrete-I-girder.git
cd Post-tensioned-prestressed-concrete-I-girder
```

or click **Code, Download ZIP** on GitHub and extract it.

### Option A: PowerShell (Windows)

1. **Install Python.** Download Python 3.10 or newer from <https://www.python.org/downloads/>. On the first installer screen, tick **Add python.exe to PATH**, then click Install Now.
2. **Check Python.** Open PowerShell (Start menu, type *PowerShell*) and run:
   ```powershell
   python --version
   ```
   It should print `Python 3.x.x`.
3. **Go to the project folder.**
   ```powershell
   cd "C:\path\to\Post-tensioned-prestressed-concrete-I-girder"
   ```
4. **Create a virtual environment.**
   ```powershell
   python -m venv .venv
   ```
5. **Activate it.**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks the script ("running scripts is disabled"), run this once and try again:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```
   The prompt now starts with `(.venv)`.
6. **Install the dependencies.**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
7. **Run the application.**
   ```powershell
   python main.py
   ```
8. **Next time**, only steps 3, 5 and 7 are needed.

### Option B: Visual Studio Code

1. Install **Python** (see Option A, step 1) and **Visual Studio Code** from <https://code.visualstudio.com/>.
2. Open VS Code, go to **Extensions** (Ctrl+Shift+X) and install **Python** (by Microsoft).
3. Choose **File, Open Folder** and select the project folder.
4. Open a terminal with **Terminal, New Terminal** (Ctrl+`).
5. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
6. Press **Ctrl+Shift+P**, type **Python: Select Interpreter**, and choose the one inside `.venv`.
7. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
8. Open `main.py` and press the **Run Python File** button (top right), or press **F5**. You can also type `python main.py` in the terminal.

### Option C: Visual Studio 2022

1. Open **Visual Studio Installer**, choose **Modify**, and tick the **Python development** workload. Install.
2. Choose **File, Open, Folder** and select the project folder. (Or **Create new project, Python Application**, then add the files.)
3. In **Solution Explorer**, right-click `main.py` and choose **Set as Startup File**.
4. Right-click **Python Environments**, choose **Add Environment**, select **Virtual environment**, point it at `requirements.txt`, and click Create. Visual Studio installs the packages for you.
5. Press **Ctrl+F5** (Start Without Debugging) or **F5** to run.
6. If a package is missing, open **View, Other Windows, Python Environments**, choose your environment, then install `PySide6`, `matplotlib`, `numpy` and `reportlab` from the **Packages** tab.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On some Linux systems, Qt needs extra libraries: `sudo apt install libxcb-cursor0 libgl1`.

## 9. Using the application

1. **Home**: click **Start a New Project**, or **Open a Saved Project** to load a `.json` file.
2. **Project**: enter the project name, author and design-code notes.
3. **Geometry and Materials**: set span, deck width, number of girders, girder depth, slab thickness, concrete and steel grades, and prestress data. A blank or invalid field shows a clear message instead of crashing.
4. **Loads**: choose the IRC live-load class (or **Governing**) and set the superimposed loads.
5. **3D Model**: choose a view (3D, Elevation, Plan, Cross-section, Girder section). Use the element checkboxes to show or hide parts, drag to rotate, scroll to zoom, and **Full screen** to enlarge.
6. **Analysis**: pick any of the five diagrams from the drop-down. Full screen is available here too.
7. **Results**: read the key figures and the check table. **Click any row** to see its full calculation in the panel below.
8. **Report**: preview the report and export it as **PDF**, **CSV** or **TXT**.
9. Use **Save Project** at the bottom to store all inputs in a JSON file, and **Back** / **Next** to move between pages.

## 10. Design methodology

| Stage | Method |
|---|---|
| Loads | IRC:6-2017 vehicles, moving-load envelope, impact, lane reduction, Courbon distribution factor |
| Prestress losses | Friction (μ, k), anchorage slip, elastic shortening, creep, shrinkage, relaxation |
| Flexure | Strain-compatibility with rectangular stress block (IRC:112) |
| Shear | Variable-strut method: VRd,s, VRd,max, VRd,c |
| Stresses | Girder alone at transfer, then composite at service (rare and quasi-permanent) |
| Deflection | Double integration of M/EI, zero at both supports |
| Minimum dimensions | SP:71 used as a reference only |

## 11. Testing

Run the engine tests from the project folder:

```powershell
python test_engine.py
```

The tests cover unit consistency, load envelopes, losses, capacity and deflection.

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognised | Reinstall Python and tick **Add python.exe to PATH**, or use `py main.py`. |
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`. |
| `No module named PySide6` | Activate the virtual environment, then run `pip install -r requirements.txt`. |
| App opens on the wrong interpreter in VS Code | **Ctrl+Shift+P, Python: Select Interpreter**, pick the `.venv` one. |
| `qt.qpa.plugin: Could not load the Qt platform plugin` | Reinstall with `pip install --force-reinstall PySide6`. |
| Window geometry warnings in PowerShell | Harmless; the minimum window size is capped in the current version. |
| 3D view feels slow | Hide elements you do not need with the checkboxes. |
| PDF text looks wrong | Make sure matplotlib is installed; the report uses its bundled DejaVu fonts. |

## 13. Assumptions and limitations

- Clause numbers, lane reductions, impact factors and partial factors are assumptions and should be **verified against the codes**.
- SP:71 is for pre-tensioned girders and is used only as a dimension reference.
- The inspection, NDT, structural health monitoring, machine-learning and maintenance stages from the course brief are **not implemented**.
- The default case shows one failing check (transfer maximum compression, 101.3 % utilisation). It needs a design change such as staged stressing or a larger bottom flange.
- This is an academic tool and not a substitute for a certified design review.

## 14. Author and acknowledgements

**Ranvir Kumar**, B.Tech Civil Engineering, IIT Kharagpur. GitHub: [@Ranvirkgpian](https://github.com/Ranvirkgpian).

Course: CE60258, AI/ML for Sustainable Infrastructure Systems, under Prof. Nirjhar Dhang.

Built with [PySide6](https://doc.qt.io/qtforpython/), [matplotlib](https://matplotlib.org/), [NumPy](https://numpy.org/) and [ReportLab](https://www.reportlab.com/).
