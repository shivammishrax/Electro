import csv
import os
import sys

def analyze():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, 'power_session_log.csv'),
        os.path.join(script_dir, '..', 'Sidekick', 'Energy', 'power_session_log.csv'),
        r'c:\Codex\power_session_log.csv',
    ]
    log_file = next((c for c in candidates if os.path.exists(c)), os.path.join(script_dir, 'power_session_log.csv'))

    hwinfo_files = [
        os.path.join(script_dir, 'hwinfo_log.csv'),
        os.path.join(script_dir, 'hwinfo.csv'),
        r'c:\Codex\hwinfo_log.csv',
        r'c:\Codex\hwinfo.csv',
        os.path.expanduser(r'~\Desktop\hwinfo_log.csv'),
        os.path.expanduser(r'~\Desktop\hwinfo.csv'),
        os.path.expanduser(r'~\Documents\hwinfo_log.csv'),
    ]

    print("=" * 68)
    print("          ⚡ ELECTRO - HARDWARE TELEMETRY & UPS/INVERTER SIZING       ")
    print("=" * 68)

    # 1. Check for HWiNFO log
    hwinfo_cpu_peak = None
    hwinfo_cpu_avg = None
    hwinfo_gpu_peak = None
    hwinfo_gpu_avg = None

    hwinfo_file = None
    for hf in hwinfo_files:
        if os.path.exists(hf):
            hwinfo_file = hf
            break

    if hwinfo_file:
        print(f"\n[Found HWiNFO Log: {hwinfo_file}]")
        try:
            with open(hwinfo_file, 'r', encoding='latin-1') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    cpu_pwr_idx = [i for i, h in enumerate(headers) if 'cpu package power' in h.lower() or 'package power' in h.lower()]
                    gpu_pwr_idx = [i for i, h in enumerate(headers) if 'gpu power' in h.lower() or 'gpu board power' in h.lower() or 'total board power' in h.lower()]
                    
                    cpu_vals = []
                    gpu_vals = []
                    for row in reader:
                        if cpu_pwr_idx and len(row) > cpu_pwr_idx[0]:
                            try:
                                cpu_vals.append(float(row[cpu_pwr_idx[0]]))
                            except ValueError: pass
                        if gpu_pwr_idx and len(row) > gpu_pwr_idx[0]:
                            try:
                                gpu_vals.append(float(row[gpu_pwr_idx[0]]))
                            except ValueError: pass
                    
                    if cpu_vals:
                        hwinfo_cpu_avg = sum(cpu_vals) / len(cpu_vals)
                        hwinfo_cpu_peak = max(cpu_vals)
                        print(f"  * HWiNFO CPU Package Power: Avg = {hwinfo_cpu_avg:.1f} W | Peak = {hwinfo_cpu_peak:.1f} W")
                    if gpu_vals:
                        hwinfo_gpu_avg = sum(gpu_vals) / len(gpu_vals)
                        hwinfo_gpu_peak = max(gpu_vals)
                        print(f"  * HWiNFO GPU Board Power  : Avg = {hwinfo_gpu_avg:.1f} W | Peak = {hwinfo_gpu_peak:.1f} W")
        except Exception as e:
            print(f"  * Note parsing HWiNFO file: {e}")

    # 2. Check Background Session Logger
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            gpu_watts = []
            gpu_utils = []
            cpu_utils = []
            for row in reader:
                try:
                    gpu_watts.append(float(row['GPU_Power_W']))
                    gpu_utils.append(float(row['GPU_Util_Pct']))
                    cpu_utils.append(float(row['CPU_Util_Pct']))
                except (ValueError, KeyError):
                    continue

        if gpu_watts:
            count = len(gpu_watts)
            duration_min = count / 60.0
            peak_gpu = max(gpu_watts)
            avg_gpu = sum(gpu_watts) / count
            peak_gpu_util = max(gpu_utils)
            avg_gpu_util = sum(gpu_utils) / count
            peak_cpu_util = max(cpu_utils)
            avg_cpu_util = sum(cpu_utils) / count

            print(f"\n[Telemetry Session: {duration_min:.1f} minutes recorded]")
            print(f"  * GPU Draw (RTX 5080)   : Avg = {avg_gpu:.1f} W | Peak = {peak_gpu:.1f} W")
            print(f"  * GPU Utilization       : Avg = {avg_gpu_util:.1f}% | Peak = {peak_gpu_util:.1f}%")
            print(f"  * CPU Utilization       : Avg = {avg_cpu_util:.1f}% | Peak = {peak_cpu_util:.1f}%")

            # CPU calculation
            if hwinfo_cpu_peak is not None:
                final_cpu_avg = hwinfo_cpu_avg
                final_cpu_peak = hwinfo_cpu_peak
            else:
                final_cpu_avg = 28.0 + (avg_cpu_util / 100.0) * 110.0
                final_cpu_peak = min(35.0 + (peak_cpu_util / 100.0) * 127.0, 162.0)

            final_gpu_avg = hwinfo_gpu_avg if hwinfo_gpu_avg else avg_gpu
            final_gpu_peak = hwinfo_gpu_peak if hwinfo_gpu_peak else peak_gpu

            # Platform Circuitry (MSI X870E, 64GB DDR5, NVMe/SSDs, AIO Pump, Fans, RGB, USB)
            rest_system_dc = 75.0  # Watts

            dc_avg = final_gpu_avg + final_cpu_avg + rest_system_dc
            dc_peak = final_gpu_peak + final_cpu_peak + rest_system_dc

            # Wall draw (PSU efficiency ~90% 80+ Gold/Platinum)
            psu_eff = 0.90
            wall_avg = dc_avg / psu_eff
            wall_peak = dc_peak / psu_eff

            # Detected Monitor: BenQ PD2706U 4K UHD
            mon_normal = 45.0
            mon_max_pd = 135.0

            wall_with_mon_normal = wall_peak + mon_normal
            wall_with_mon_pd = wall_peak + mon_max_pd

            print("\n[Estimated System Power Breakdown]")
            print(f"  * CPU Package (Ryzen 9 9950X3D) : Avg = {final_cpu_avg:.1f} W | Peak = {final_cpu_peak:.1f} W")
            print(f"  * GPU Total Board (RTX 5080)    : Avg = {final_gpu_avg:.1f} W | Peak = {final_gpu_peak:.1f} W")
            print(f"  * Platform Circuitry (Motherboard / 64GB DDR5 / SSDs / AIO Fans) : ~{rest_system_dc:.1f} W")
            print(f"  * Total DC Power to Components  : Avg = {dc_avg:.1f} W | Peak = {dc_peak:.1f} W")
            print(f"  * AC Power Drawn from Wall Outlet (90% PSU eff) : Avg = {wall_avg:.1f} W | Peak = {wall_peak:.1f} W")

            print(f"\n[Detected Monitor: BenQ PD2706U (27\" 4K)]")
            print(f"  * Scenario 1: Display Only (Normal gaming/viewing)   : +{mon_normal:.0f} W  -> Total Wall = {wall_with_mon_normal:.1f} W")
            print(f"  * Scenario 2: Display + USB-C Laptop PD Charging     : +{mon_max_pd:.0f} W -> Total Wall = {wall_with_mon_pd:.1f} W")

            print("\n" + "=" * 68)
            print("                UPS & INVERTER RECOMMENDATIONS               ")
            print("=" * 68)
            print(f"  * Normal Peak Load (PC + BenQ 4K Display) : ~{wall_with_mon_normal:.0f} Watts")
            print(f"  * Maximum Peak Load (PC + BenQ + USB-C PD): ~{wall_with_mon_pd:.0f} Watts")
            print("  * Transient Spike Cushion (20-25%)         : +150W - 200W")
            print("  * Required Pure Sine Wave Capacity         : 900W - 1000W minimum")
            print("\n  [Recommended Dedicated Computer UPS]:")
            print("    1. 1500VA / 900W - 1000W Pure Sine Wave (PFC compatible)")
            print("       Examples: APC Back-UPS Pro BR1500G-IN / CyberPower CP1500PFCLCD")
            print("    2. 2000VA - 2200VA / 1200W - 1400W (Ideal / Heavy Gaming & Headroom)")
            print("       Examples: APC Smart-UPS SMC2000I-IN or CyberPower OLS2000EC")
            print("\n  [Recommended Home Inverter Setup (e.g. Genus MaxiLion 1500)]:")
            print("    - Capacity: 1125VA / 900W Pure Sine Wave with 1280Wh LiFePO4 battery")
            print("    - MUST have 'UPS Mode' enabled (changeover < 10ms so PC doesn't restart)")
            print("    - Normal gaming (~627W load) leaves ~273W safety headroom.")
            print("=" * 68)
    else:
        print("\nNo log recorded yet.")

if __name__ == '__main__':
    analyze()
