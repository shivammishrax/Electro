# AGENTS.md - Electro Codebase Context & Engineering Rules

This document provides architectural constraints, hardware baselines, and design rules for AI agents modifying or extending **Electro**.

---

## 1. Core Architecture & Philosophy

* **Target Operating System:** Windows 10 / 11 (PowerShell / Command Prompt / WScript).
* **Language & Runtime:** Python 3.10+ (Standard library only: `ctypes`, `tkinter`, `csv`, `threading`, `time`, `os`).
* **Zero External Dependencies:** Do NOT add heavy third-party packages (`psutil`, `pynvml`, `PyQt`, etc.) unless explicitly instructed by the user. Standard Python + native Windows DLLs is an architectural principle.
* **Zero Console / Subprocess Rule (CRITICAL):**
  * Under NO circumstance should background loops spawn external processes (e.g. `nvidia-smi.exe`, `wmic`, `powershell.exe`) via `subprocess`.
  * External process execution on Windows instantiates `conhost.exe` and steals GUI focus, disrupting keyboard input and causing screen flickering.
  * GPU telemetry **must always** be queried in-memory via `nvml.dll` (`ctypes.CDLL('nvml.dll')`).
  * CPU telemetry **must always** be queried in-memory via Win32 `kernel32.dll` (`GetSystemTimes`).

---

## 2. Hardware Profile Reference

Electro is calibrated for the user's primary rig:
* **CPU:** AMD Ryzen 9 9950X3D (Zen 5, 16-Core / 32-Thread, 120W TDP, 162W PPT limit).
* **GPU:** NVIDIA GeForce RTX 5080 (Blackwell, 360W reference board limit).
* **Motherboard:** MSI MPG X870E EDGE TI WIFI (Dual Promontory 21 chipsets).
* **RAM:** 64GB DDR5 (2 × 32GB Kingston with onboard PMIC).
* **Storage:** Samsung 990 PRO 2TB NVMe + WD NVMe + HDDs.
* **Cooling:** AIO Liquid Cooler + Multi-fan chassis.
* **Monitor:** BenQ PD2706U (27" 4K UHD with 90W USB-C Power Delivery).

---

## 3. Power Calculation Formulas

1. **Internal DC Component Draw:**
   $$\text{DC}_{\text{total}} = \text{GPU\_Watts} + \text{CPU\_Watts} + \text{Platform\_Watts}$$
   * `Platform_Watts` is fixed at **75.0 W** (covers X870E chipset, DDR5 PMICs, NVMe drives, AIO pump, fans, and RGB).
2. **Wall AC Power Draw:**
   $$\text{Wall}_{\text{AC}} = \frac{\text{DC}_{\text{total}}}{0.90} + \text{Monitor\_Watts}$$
   * `0.90` represents 90% 80+ Gold / Platinum PSU efficiency.
   * `Monitor_Watts`: Default **45.0 W** (Normal) | **135.0 W** (+ USB-PD Laptop Charging) | **0.0 W** (Off).
3. **Inverter Capacity Load %:**
   $$\text{Inverter Load \%} = \left(\frac{\text{Wall}_{\text{AC}}}{\text{Inverter\_Capacity}}\right) \times 100$$
   * Default inverter capacity: **900.0 W** (calibrated for Genus MaxiLion Air 1500).

---

## 4. Launchers & File Roles

* `electro_hud.py`: Main desktop overlay GUI (Tkinter borderless topmost window).
* `measure_power.py`: Headless telemetry recorder (writes to `power_session_log.csv`).
* `analyze_power.py`: Statistical analyzer, percentile calculator, and UPS sizing engine.
* `electro_hud.vbs`: **Primary silent launcher** (uses `WScript.Shell.Run` with style `0` for zero console window flash).
* `assets/logo.png` & `assets/logo.svg`: Branding assets.
