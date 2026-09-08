# Splatt2 — DIY Target Shooting Trainer

A computer-vision dry-fire and live-fire training tool for air rifle and air pistol. It uses a webcam mounted to the barrel (or stock) to track where the rifle is pointing, detects shots by audio click, and scores them on a digital target in real time.

No special hardware required — just a webcam, a microphone, a printer, and a computer.

---

## Version 1.2 — Community integration

This community integration version combines all community pull requests that were open in `Nonkeydonk/splatt2` when the `v1.2` branch was assembled: #2, #3, #4, #5, #6, #7, #8 and #11. It includes voice feedback, cross-platform packaging, UI and performance improvements, trace playback, camera zoom and tracker view, marker-sheet DPI metadata, the NSRA 25-yard prone rifle target, and configurable target colours and ring-score labels.

Merge conflicts have been resolved to combine these contributions. This branch also includes Auto marker selection and a voice-feedback checkbox adjustment. This is a community integration version, not an official upstream release; pull requests opened later are not automatically included.

## How It Works

1. Print the **ArUco marker sheet** from within the app and stick it behind your target.
2. Mount a small USB webcam to your rifle so the lens points at the target.
3. Start Splatt2 — it detects ArUco markers on the sheet (4, 6, or 8 depending on your setup) and establishes a live millimetre-accurate coordinate system.
4. As you aim, a crosshair tracks your hold on the digital target in real time.
5. When a shot fires (air-gun click detected by microphone), the position at the **exact moment of audio detection** is recorded — not the position when the software processes it, eliminating software lag.
6. The shot is scored and displayed instantly.

### Why ArUco markers?

ArUco markers are small square patterns (like QR codes) that OpenCV can detect and locate with sub-pixel accuracy. By placing four markers at the corners of a known-size sheet, the software computes a **homography** — a perspective transform that converts raw pixel coordinates into millimetres relative to the target centre, correcting for camera angle, tilt, and distance automatically.

### Scoring model

Scoring is purely geometric and independent of the visual ring boundaries drawn on the target:

- **R** = `card_diameter / 2 + pellet_diameter / 2` (e.g. 22.75 + 2.25 = **25.0 mm** for .177 on 10m air rifle)
- Any shot whose **centre** is within R of target centre scores; beyond R = 0 (miss)
- **Integer mode**: 10 equal bands of `R/10`. Band 0 = 10, band 9 = 1.
- **Decimal mode**: 99 equal bands of `R/99`. Band 0 = 10.9, band 98 = 1.0.

Changing the pellet calibre in Settings instantly shifts all scoring bands — one setting covers both .177 and .22 shooters using the same target.

---

## Requirements

- Windows 10/11, macOS 12+, or a recent 64-bit Linux desktop
- A webcam (USB recommended for barrel-mounting; built-in works for testing)
- A microphone (built-in laptop mic is fine for dry-fire; closer to the action is better for live fire)
- **Python 3.9+** is only needed when running from source — pre-built binaries bundle their own runtime

---

## Quick Start (pre-built binary)

Download the latest release for your OS from the [Releases page](../../releases/latest):

- `splatt2-windows-x64.zip`
- `splatt2-macos-arm64.zip` (Apple Silicon) or `splatt2-macos-x64.zip` (Intel)
- `splatt2-linux-x64.zip`

Unzip anywhere and launch:

- **Windows** — run `splatt2.exe`
- **macOS** — open `Splatt2.app` (right-click → Open the first time so Gatekeeper allows the unsigned bundle)
- **Linux** — `chmod +x splatt2 && ./splatt2`

User config and shooting sessions are saved to your OS-native app data folder:

| OS      | Location                                               |
| ------- | ------------------------------------------------------ |
| Windows | `%APPDATA%\Splatt2`                                    |
| macOS   | `~/Library/Application Support/Splatt2`                |
| Linux   | `~/.local/share/Splatt2` (or `$XDG_DATA_HOME/Splatt2`) |

Override with `SPLATT2_USER_DIR=/some/path` for testing or portable installs.

---

## Quick Start (run from source)

1. Install Python 3.9+ from https://python.org (Windows: tick **"Add Python to PATH"**)
2. Clone or download this repository
3. Launch:
   - **Windows** — double-click `RUN.bat`
   - **macOS / Linux** — `pip install -r requirements.txt && python main.py`

`RUN.bat` installs the Python deps (`numpy`, `opencv`, `sounddevice`, `Pillow`, `scipy`) on first run, then starts the app.

---

## Step-by-Step Setup

### 1. Print the marker sheet

- Start Splatt2 and click **"Print Marker Sheet"** in the right panel
- Select your target type and shooting distance
- Save the PNG and print at **100% scale** on A4 — do **not** scale to fit
- Confirm the printed sheet is exactly **210 × 297 mm**

The dashed circles on the sheet show where each scoring ring falls at your chosen distance. A printed target placed in the centre should align with these guides.

### 2. Set up the target

Place or tape your printed target over the centre of the marker sheet. For ISSF 10m air rifle, the target card is small enough that all four ArUco markers remain visible around it.

> **Tip:** Laminate the marker sheet or put it in a transparent sleeve — it can be reused indefinitely.

### 3. Mount the camera

The camera should be mounted so it can see **all four markers** simultaneously. It does not need to be perfectly aligned — the homography corrects for any angle or offset. A small elastic band or cable tie around the barrel or scope body works well for a temporary mount.

Aim for the marker sheet to fill roughly **60–80% of the camera frame**. Closer = more accurate tracking; too close and markers may leave the frame.

### 4. Configure the camera

- Open **Settings → Camera**
- Set **Camera Index** (0 = first webcam, 1 = second, etc.)
- Press **Detect** to find available cameras automatically
- Recommended resolution: **640 × 480** (balances speed and accuracy)
- If the image is upside-down, enable **Flip image**
- Use the **↻** button in the bottom bar to rotate 90° if needed

### 5. Configure audio

- Open **Settings → Audio**
- Press **Start Camera** first, then fire a dry shot or make a click sound
- Watch the **MIC** level bar at the bottom — it should spike on each shot
- Adjust **THRESH** until only real shots trigger (not ambient noise)
- **SENS** controls how much louder than ambient the click must be — higher = more selective
- Set the audio device index if the wrong microphone is being used

### 6. Zero the rifle

- Press **◎ Zero** in the bottom bar
- Aim at the target centre and fire one shot (dry-fire or live)
- The software offsets all subsequent shots so that shot registers at (0, 0)

For fine adjustment after a sighting string:
- Press **⊕ Fine Zero**
- Click directly on the centre of your group on the target canvas
- The offset is applied immediately and saved across restarts

### 7. Start shooting

- Press **▶ Start Series** to begin recording
- Each shot is appended to a CSV file immediately — safe against crashes
- The series ends when the configured number of shots is reached, or click the button again to stop early
- Click **📋 Series Review** to analyse the series in detail

---

## The Interface

### Left panel — Camera
Live camera feed with detected markers highlighted and the aim-point crosshair overlaid. The actual delivered FPS is shown in the top-left corner of the feed.

Below the feed: a **◎ Focus assist** toggle (for manual-focus lenses) that reveals a live sharpness bar with peak-hold indicator — turn the focus ring until the bar peaks and shows green, then lock focus. Zero CPU cost when off.

The **🎛 Cam Props** button (next to Settings) opens the Windows native camera properties dialog where you can adjust brightness, contrast, saturation, sharpness, and exposure directly via the driver. Increasing contrast and sharpness in this dialog significantly improves ArUco detection.

The tracking quality bar shows what fraction of configured markers are visible. In Auto mode, the total is estimated from the highest recognised ID: 0–3 imply at least 4 markers, 4–5 at least 6, and 6–7 imply 8. The estimate only increases until the tracker restarts, so temporary occlusion does not reduce it. Hidden markers can make the initial estimate too low; select a fixed count for an exact denominator. IDs identify positions, not the total count. Sheet dimensions, marker size, margin and dictionary must still match the print.

- **Green (>60%)** — all or most markers detected, full accuracy
- **Yellow (30–60%)** — partial detection, homography being reused
- **Red (<30%)** — tracking lost, shots will be rejected

### Centre panel — Target
- **Traces** — the path of the aim point before each shot, colour-coded by time:
  - Dark grey = approach (moving onto target)
  - Green = hold (on target, early)
  - Yellow = pre-shot window (~1s before shot)
  - Red = final window (~0.2s before shot)
- **Shot holes** — filled circles scaled to actual pellet diameter, labelled with their score for the current series
- **ACP diamond** — Aim Centre Point, the mean hold position over the final fraction of each trace
- **MPI cross** — Mean Point of Impact across all shots in the series
- **Group circle** — smallest circle enclosing all shots (Extreme Spread)

### Right panel — Scores
Series total at top, then per-shot statistics (Mean Radius, Extreme Spread, CEP, standard deviations). The shot log lists every shot with score, coordinates, hold time, and flags.

**Display toggles** (two rows of buttons):
- **◈ ACP** — show/hide aim centre points
- **⊡ Shots** — show/hide shot bounding box
- **◇ ACP Box** — show/hide ACP bounding box
- **● Dot** — switch shot holes to tiny dots (less clutter)
- **○ Group** — show/hide the group circle and MPI cross

### Bottom bar
Left to right: Pause, Zero, Fine Zero, decimal scoring toggle (DEC), camera rotation, microphone level, trigger threshold slider, sensitivity slider, on-target indicator.

---

## Settings Reference

### Camera
| Setting | Description |
|---------|-------------|
| Camera Index | 0 = first webcam, 1 = second, etc. |
| Resolution | 640×480 recommended; higher for better accuracy at expense of speed |
| FPS | 30 is standard; reduce if CPU is struggling |
| Rotation | 0/90/180/270° — use if camera is mounted sideways |
| Flip | Enable if image appears mirrored |
| ArUco Dictionary | DICT_4X4_50 works well for most setups; must match the printed sheet |
| Marker size / Margin | Must match the values used when printing the sheet |
| CLAHE | Adaptive contrast enhancement — improves tracking under uneven lighting (recommended ON) |
| CLAHE clip limit | Aggressiveness of contrast enhancement (2=mild, 4=balanced, 8=aggressive, 12=extreme). Quick buttons in Settings. |
| Brightness target | Software gain normalisation target (0–255). Frame brightness is scaled to this value before CLAHE, compensating automatically for lighting changes. Default 128. |
| Marker count | Auto (default) / 4 / 6 / 8. Auto uses all recognised positions on supported sheets. Fixed counts must match the printed sheet. Printing still lets you choose 4, 6 or 8. |
| Pixel format | Auto / MJPEG / YUY2. MJPEG prevents fps throttling on static scenes on some cameras. |
| Smoothing | EMA (fast) or Savitzky-Golay (smoother shape) — affects trace appearance only, not shot position |

### Audio
| Setting | Description |
|---------|-------------|
| Threshold | Absolute peak floor (0.01–1.0). Start at 0.4 for air rifle click. |
| Sensitivity | Peak must be this many × louder than ambient. Higher = fewer false triggers. |
| Audio Cooldown | Minimum ms between registered shots (~800ms typical). |
| Post-shot Cooldown | Seconds to ignore audio after a shot fires (prevents echo re-triggering). |
| Device | Leave blank for system default; set index if wrong mic is selected. |

### Target
| Setting | Description |
|---------|-------------|
| Target type | Loaded from `targets/` folder — add your own CSV to extend |
| Real range (m) | Shooting distance, used for marker sheet scaling |
| Pellet diameter | **Drives all scoring geometry** — change this for .22 vs .177 |
| Shot circle dia | Visual size of the shot hole on screen (cosmetic only) |
| Zero offset | Current persistent zero — reset here if needed |
| Ignore misses | Discard score-0 shots from statistics (useful in competition training) |

#### Ring Scores — Settings → Target

| Setting | Default | Description |
|---------|---------|-------------|
| Number labels from inside | 5 | Number of ring entries to label, counting from the centre outward. `0` hides all numbers. |
| Show scores: top | False | Show numbers above the centre. |
| Show scores: right | True | Show numbers to the right. |
| Show scores: bottom | False | Show numbers below the centre. |
| Show scores: left | False | Show numbers to the left. |

Directions are independent. Counts include a separate inner-10 CSV entry,
and are capped at the available ring count. Multi-mark targets display
numbers on the first mark only. Small rings can have overlapping labels
at low zoom, especially with multiple directions enabled.

### Colours

Open **Settings → Colours** to customise trace, shot and target colours.
Click **Pick…** to open the colour picker, or enter a hex colour.
Click **Apply** to save changes and refresh the main target.

#### Target Appearance

| Setting | Default | Description |
|---------|---------|-------------|
| Inner-colour rings | 5 | Number of innermost ring entries using the inner fill. `0` uses the outer fill throughout. |
| Inner colour | `#0f0f0f` | Inner fill colour. |
| Outer colour | `#fbe2a9` | Outer fill colour. |
| Inner line colour | `#ffffff` | Outlines and score labels on the inner fill. |
| Outer line colour | `#000000` | Outlines and score labels on the outer fill. |

The manual inner-ring count controls the digital target's fill boundary;
`bull_dia_mm` does not override it. Rings and labels render at 3× resolution
before downsampling. Appearance settings do not change scoring geometry
or printed marker-sheet colours.

Defaults live in `core/config.py`; saved settings in the user data directory
override them. On Windows this is `%APPDATA%\Splatt2\splatt2_config.json`.
Set `SPLATT2_USER_DIR` to use a different directory. Legacy config files
beside `main.py` are copied on first use when no new config exists; old
black/paper keys are migrated to inner/outer names when loaded. Explicit
new names take priority.

### Camera zoom and tracker view

Use the camera panel's **Tracker view** toggle to inspect the greyscale
image passed to marker detection. The camera zoom slider digitally crops
and enlarges the centre of the captured image from 1× to 8×. Detection also
supports sharpening and configurable maximum detection dimensions.

### Advanced
| Setting | Description |
|---------|-------------|
| ACP fraction | What fraction of the hold is used for the Aim Centre Point (0.1–0.8) |
| Approach zone | How far outside the target the software tracks approach (× scoring radius) |
| Pre-shot window | How many seconds before the shot the trace turns yellow |
| Final window | How many seconds before the shot the trace turns red |
| Voice enabled | Enable offline spoken scores and clock positions after shots. Enabled by default; configured under Advanced → Voice Feedback. |

### Spike Filter (Settings → Camera)
| Setting | Description |
|---------|-------------|
| Spike velocity (mm/frame) | Minimum speed to flag a position as a spike candidate. Lower = more sensitive. Default 25mm/frame. |
| Reversal ratio (0–1) | How sharply the direction must reverse to confirm a spike. 0.7 = default. 0.9 = strict. |

---

## Target Files

Targets live in the `targets/` folder as CSV files. The app reads all `.csv` files at startup — drop a new file in and restart to add a new target.

### CSV format

```
# Comment lines start with #
key,my_target                    ← unique identifier, no spaces
name,My Custom Target            ← display name
gauging,outward                  ← outward (hole touches ring) or inward (hole inside ring)
calibre_mm,4.5                   ← default pellet diameter
reference_dist_m,10.0            ← nominal shooting distance
aiming_mark_dia_mm,30.5          ← diameter of the black bull (for marker sheet)
card_diameter_mm,45.5            ← outer edge of the scoring card

score,ring_diameter_mm           ← data section header
10,0.5                           ← 10-ring: 0.5mm diameter visual boundary
9,5.5
8,10.5
...
1,45.5
```

> **Important:** the ring diameters here are **visual only** — they control how the target looks on screen and on the printed sheet. The scoring bands are computed purely from `card_diameter_mm` and the pellet calibre set in Settings, independent of these visual rings.

### Built-in targets
| File | Target |
|------|--------|
| `10m_air_rifle.csv` | ISSF 10m Air Rifle — 45.5mm card, .177 |
| `10m_air_pistol.csv` | ISSF 10m Air Pistol — 155.5mm card, .177 |
| `6yd_air_rifle.csv` | NSRA 6 Yard Air Rifle — 31mm card, .22, inward gauging |
| `25yd_prone_rifle.csv` | NSRA 25 Yard Prone Rifle |

### Target Creator

Open **Print Marker Sheet → Target Creator** tab to create or edit targets without editing CSV files directly. A live preview shows the computed scoring geometry (R, band widths) as you type.

---

## Session Files

Series recordings are saved to the `sessions/` folder inside your user data directory (see *Quick Start (pre-built binary)* for the per-OS path), or in a custom location configured in Settings → Session. Each day of shooting creates a subfolder named `YYYY-MM-DD/`. Within each day, each series is a separate file named `HH-MM-SS_name_series1.csv`.

Each `.csv` has a companion `.json` file with full trace data for the Series Review window.

> Splatt2 versions before this one stored the config and `sessions/` folder next to `main.py`. On first launch of a newer build, the config is migrated into the per-user app data directory automatically. The original is left in place.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| P | Pause / resume |
| Space | Undo last shot |
| R | Reset all (clears shots, preserves zero) |
| S | Save shots to CSV |
| Q | Quit |

---

## Troubleshooting

**Tracking quality is 0% / no markers detected**
- Check that all configured markers are visible in the camera frame
- Improve lighting — ArUco detection needs good contrast (avoid glare on the sheet)
- Enable CLAHE in Settings → Camera and raise the clip limit (try 6 or 8 for difficult lighting)
- Use 🎛 Cam Props to boost contrast and sharpness in the camera driver — this often helps significantly
- Make sure the printed sheet is flat and undamaged
- Verify the ArUco dictionary in Settings matches the one used to print the sheet
- Select Auto for marker count in Settings, or match the number printed on the sheet

**Shots not registering / "SHOT REJECTED"**
- "No tracking" — camera can't see markers when the shot fired; reposition
- "Outside approach zone" — aim point was too far from target when shot fired (false positive rejected)
- Lower the audio threshold if real shots aren't being detected
- Check the MIC bar spikes on each shot

**"Zero mode — no markers, try again"**
- The zero shot fired while markers weren't visible; reposition and try again
- Zero mode stays active — just fire again once markers are in frame

**Score seems wrong**
- Check the pellet diameter in Settings → Target matches your actual calibre
- Verify the correct target type is selected
- Note: scoring bands are wider than the visual rings — a shot visually inside the 9-ring may score 10 depending on geometry

**Camera not opening**
- Try camera index 0, 1, 2 in Settings → Camera → Detect
- Close other applications using the webcam
- On Windows, check Camera privacy settings (Settings → Privacy → Camera)

**Dependencies fail to install**
- Make sure Python 3.9+ is installed: open Command Prompt and type `python --version`
- Try manually: `pip install opencv-python sounddevice numpy Pillow scipy`
- Check your internet connection — pip downloads from pypi.org

---

## Project Structure

```
splatt2/
├── main.py                  Entry point with crash logging
├── RUN.bat                  Install dependencies & launch (Windows dev flow)
├── requirements.txt         Runtime Python dependencies
├── requirements-build.txt   Build-time dependencies (PyInstaller)
├── targets/                 Bundled target definition CSVs (read-only seeds)
│   ├── 10m_air_rifle.csv
│   ├── 10m_air_pistol.csv
│   └── 6yd_air_rifle.csv
├── build/
│   ├── splatt2.spec         PyInstaller spec
│   ├── build.py             Cross-platform build script
│   └── README.md            Build instructions
├── core/
│   ├── paths.py             Cross-platform resource and user-data paths
│   ├── config.py            Settings management and target CSV loader
│   ├── tracker.py           ArUco detection, homography, scoring geometry
│   ├── audio.py             Shot sound detection (transient detection)
│   ├── session.py           Shot data, trace recording, file I/O
│   ├── target_renderer.py   OpenCV target canvas drawing
│   ├── marker_sheet.py      Printable ArUco sheet generator
│   └── smoother.py          Aim-point smoothing (EMA / Savitzky-Golay)
├── ui/
│   └── app.py               Main tkinter UI
└── .github/workflows/
    ├── ci.yml               Syntax check on push and PR
    └── release.yml          Cross-platform PyInstaller builds on tag
```

---

## Building from Source

To produce a standalone bundle for your platform:

```
pip install -r requirements.txt -r requirements-build.txt
python build/build.py --clean
```

Output lands in `dist/splatt2-<os>-<arch>/`. See [`build/README.md`](build/README.md) for per-OS notes.

Pre-built binaries are produced automatically by GitHub Actions on every tag — see [`.github/workflows/release.yml`](.github/workflows/release.yml).

### On-demand builds via GitHub Actions

You can trigger the release workflow manually without pushing a tag:

1. Go to **Actions → Release → Run workflow**
2. Pick the branch
3. Leave **Create a GitHub Release** unticked to just produce downloadable artifacts attached to the workflow run (kept for 30 days)
4. Tick it and supply a tag (e.g. `v1.2.0-rc1`) to publish a pre-release with the zips attached

Manual-dispatch releases are flagged as pre-releases so they don't override the latest stable.

---

## Changelog

See `CHANGELOG.md` for a full history of changes since the initial release.

## Contributing

Pull requests welcome. A few guidelines:

- Target definitions belong in `targets/*.csv` — no hardcoded ring values in Python
- Scoring logic lives in `core/tracker.py:score_shot()` — keep it geometry-only
- UI code is in `ui/app.py` — it's large but structured into clear method groups
- Run a syntax check before submitting: `python -m py_compile core/*.py ui/*.py`
- Test with `python main.py` before raising a pull request

---

## Licence

MIT — do whatever you like with it, but no warranty is implied.

---

## Safety

- Only fire live rounds on an authorised range, observing all range safety rules
- The software does not know whether a round is live or blank — treat every shot as live
- Do not point any firearm at a person or animal under any circumstances
