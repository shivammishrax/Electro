<p align="center">
  <img src="assets/logo.png" alt="Electro Logo" width="160" style="border-radius: 24px; box-shadow: 0 8px 24px rgba(0, 242, 254, 0.25);" />
</p>

<h1 align="center">⚡ ELECTRO</h1>

<p align="center">
  <strong>Zero-Overhead Hardware Power Telemetry & UPS / Inverter Sizing Suite</strong><br>
  <em>Direct In-Memory C-Level Drivers (NVML & Win32 API) • 0% CPU Overhead • Seamless Desktop HUD</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Zero--Subprocess-00f2fe?style=for-the-badge" alt="Zero Subprocess" />
  <img src="https://img.shields.io/badge/GPU_Telemetry-Native_NVML_C_API-00f5a0?style=for-the-badge" alt="Native NVML" />
  <img src="https://img.shields.io/badge/Platform-Windows_11_/_10-1f6feb?style=for-the-badge" alt="Windows" />
  <img src="https://img.shields.io/badge/License-MIT-gray?style=for-the-badge" alt="License" />
</p>

---

## 📖 Overview

**Electro** is a high-precision hardware power monitoring, logging, and electrical capacity planning tool engineered for enthusiast PC builds. Unlike generic monitoring utilities that spawn resource-heavy background processes or trigger flickering console windows, Electro uses **direct in-memory C-level bindings** into NVIDIA’s driver library (`nvml.dll`) and the Windows kernel (`kernel32.dll`) via `ctypes`.

It includes:
1. **Live On-Screen Floating HUD (`electro_hud.py`):** Borderless, draggable, always-on-top desktop overlay that visualizes continuous wall draw, component breakdown, and real-time inverter load.
2. **Silent Background Logger (`measure_power.py`):** Records per-second telemetry to CSV during gaming sessions with zero system intrusion.
3. **Power Analyzer & Sizing Engine (`analyze_power.py`):** Processes session logs, calculates wall conversion efficiency, accounts for platform circuitry and 4K displays, and generates exact UPS/Inverter specifications.

---

## 🖥️ Target System Hardware Profile

Tested and calibrated against a flagship enthusiast gaming workstation:

* **CPU:** AMD Ryzen 9 9950X3D (16-Core / 32-Thread Zen 5 with 3D V-Cache, 120W TDP / 162W PPT)
* **GPU:** NVIDIA GeForce RTX 5080 16GB (360W reference board power)
* **Motherboard:** MSI MPG X870E EDGE TI WIFI (Dual Promontory 21 chipsets, PCIe 5.0, Wi-Fi 7)
* **Memory:** 64 GB DDR5 (2 × 32 GB Kingston with on-die PMIC)
* **Storage:** Samsung 990 PRO 2 TB NVMe + WD NVMe + Secondary Drives
* **Cooling & Fans:** 10 × ARGB Chassis/Radiator Fans + AIO Liquid Cooler Pump (~45W continuous under load)
* **Display:** BenQ PD2706U (27" 4K UHD Designer Display with 90W USB-C Power Delivery)

---

## 📊 Measured Benchmark Telemetry (40.4-Min Heavy Gaming Session)

| Telemetry Metric | Session Average | 90th Percentile | Peak Recorded |
| :--- | :--- | :--- | :--- |
| **GPU Board Power (RTX 5080)** | **218.6 W** | **248.2 W** | **286.8 W** |
| **GPU Core Temperature** | 59.6 °C | 63.0 °C | 65.0 °C |
| **GPU VRAM Allocation** | 14.4 GB | 14.9 GB | 15.0 GB |
| **CPU Utilization (Ryzen 9 9950X3D)** | **52.8 %** | **68.4 %** | **100.0 %** *(bursts)* |

### System Power Breakdown
* **Internal DC Load (Components):** ~384 W average | ~524 W peak
* **Wall AC Power Draw (90% PSU Efficiency):** ~427 W average | ~582 W peak
* **Scenario 1: Wall Draw + BenQ 4K Display (45W):** **~627 W – 635 W Peak**
* **Scenario 2: Wall Draw + BenQ Display + 90W USB-C Laptop Charging (135W):** **~717 W – 735 W Peak**
* **Worst-Case Synthetic Max (Full 360W GPU + 162W PPT + PD):** **~810 W**

---

## 🔋 UPS & Inverter Sizing Guide

### ⚠️ The 1000VA (600W) Trap
**Never pair a 1000VA UPS with this class of hardware.** A 1000VA unit with typical 0.6 power factor outputs a maximum of **600W**. Under active gaming scenes (~630W+) and microsecond transient spikes, a 1000VA UPS will trip into overload and shut down instantly.

### Dedicated Computer UPS
* **Minimum Spec:** **1500VA / 900W – 1000W Pure Sine Wave**
  * *Recommended:* APC Back-UPS Pro 1500VA (`BR1500G-IN` / `BR1500MS`), CyberPower `CP1500PFCLCD`.
  * *Runtime:* ~5–10 minutes during intense gaming; ~30+ minutes on desktop.
* **Optimal Spec:** **2000VA – 2200VA / 1200W – 1400W**
  * *Recommended:* APC Smart-UPS `SMC2000I-IN`, CyberPower `OLS2000EC`.
  * *Advantage:* Zero stress on transient spikes, longer battery life, room for future upgrades.
* **Waveform:** Must be **Pure Sine Wave** (Active PFC compliant).

### Home Inverter (e.g. Genus MaxiLion Air 1500)
* **Capacity:** 1125 VA / **900 W Continuous** with 1280 Wh LiFePO4 battery.
* **Headroom:** Normal gaming (~627W) leaves **~273W safety cushion** for ceiling fans and room lights.
* **Critical Requirement:** **Set inverter toggle to "UPS Mode"**.
  * *UPS Mode:* Transfer time is **~10ms** (fast enough for ATX 3.0 power supply capacitor hold-up time).
  * *Normal / Eco Mode:* Transfer time is **40–50ms** (PC will reboot on power cut).

---

## 🚀 Quickstart & Usage

### 1. Launch the Desktop HUD
To launch the borderless on-screen HUD silently (zero console window):
* Double-click **`electro_hud.vbs`**

*(Or run via terminal: `python electro_hud.py`)*

#### HUD Controls & Features
* **📈 Rolling History Graph (60s):** Real-time animated wattage curve plotting your power draw over the last 60 seconds with live `Peak`, `Avg`, and `Min` statistics. Features a dashed red **900W Inverter Limit line** to instantly see your headroom.
* **Toggle Graph View:** Click the `📈` button in the header to fold or expand the history graph on demand.
* **Drag & Drop:** Click and hold anywhere to reposition the HUD anywhere on your monitor.
* **Compact / Pill Mode:** Double-click the header (or click `⎯`) to collapse the HUD into an ultra-compact status pill (`⚡ ELECTRO: 420W | GPU: 218W | CPU: 85W | Inv: 47%`). Double-click again to expand.
* **Monitor Toggle:** Click buttons on the monitor card to switch between **Display (45W)**, **+ USB-PD (135W)**, or **Off (0W)**.
* **Close:** Click `✕` in the top-right corner.

### 2. Log a Session to CSV
To record hardware metrics in the background during gaming:
```powershell
python measure_power.py
```
Outputs timestamped metrics every second to `power_session_log.csv`.

### 3. Analyze Telemetry & Compute Sizing
```powershell
python analyze_power.py
```
Parses internal logs and auto-detects any HWiNFO `.csv` logs in the workspace.

---

## ❓ Why `electro_hud.vbs` instead of `.bat`?

* When Windows runs a `.bat` file, the command prompt engine (`cmd.exe`) must instantiate a console handle, creating a brief black window flash before launching `pythonw`.
* In contrast, **`electro_hud.vbs`** invokes the Windows Script Host (`WScript.Shell.Run`) with window style `0` (hidden). This launches `pythonw` with **zero console creation and zero visual flicker**.
* `electro_hud.vbs` is the definitive, clean desktop launcher.

---

## 🤖 Context for Autonomous AI Agents

If you are an AI coding assistant (Antigravity, Cursor, Windsurf, Copilot, Codex, Claude) working with this codebase:

1. **Zero-Subprocess Rule:**
   * Never re-introduce `subprocess.run`, `subprocess.Popen`, or CLI calls to `nvidia-smi.exe` inside looping routines. Calling CLI binaries on Windows spawns console handles that steal window focus and cause screen flashing.
   * Always read GPU metrics using the in-memory C function calls via `ctypes.CDLL('nvml.dll')` already implemented in `GPUReader`.
2. **CPU Telemetry Architecture:**
   * CPU utilization is read via `ctypes.windll.kernel32.GetSystemTimes`.
   * For the AMD Ryzen 9 9950X3D, power curve scaling is:
     $$\text{Watts} = \min(32.0 + (\text{CPU\_util} / 100.0) \times 130.0, 162.0)$$
3. **Platform Circuitry Constant:**
   * Non-CPU, non-GPU platform load (10 ARGB fans, AIO pump, MSI X870E motherboard dual chipsets, 64GB DDR5 with PMIC, Samsung 990 Pro + 4 storage drives) is calibrated at **95.0 W DC**.
4. **Wall Power Equation:**
   $$\text{Wall AC} = \frac{\text{GPU\_watts} + \text{CPU\_watts} + 95.0}{0.90} + \text{Monitor\_watts}$$
5. **Path Resolution:**
   * All scripts use dynamic script directory resolution (`os.path.dirname(os.path.abspath(__file__))`) so they remain fully relocatable.
