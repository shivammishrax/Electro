import ctypes
import os
import time
from datetime import datetime

# ----------------- Native Windows CPU Times -----------------
class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', ctypes.c_uint32), ('dwHighDateTime', ctypes.c_uint32)]

def to_int(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

def get_cpu_times():
    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    return to_int(idle), to_int(kernel), to_int(user)

# ----------------- Native NVML C-Bindings -----------------
class nvmlUtilization_t(ctypes.Structure):
    _fields_ = [('gpu', ctypes.c_uint), ('memory', ctypes.c_uint)]

class nvmlMemory_t(ctypes.Structure):
    _fields_ = [('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong), ('used', ctypes.c_ulonglong)]

class GPUReader:
    def __init__(self):
        self.available = False
        try:
            self.nvml = ctypes.CDLL('nvml.dll')
            if self.nvml.nvmlInit() == 0:
                self.dev = ctypes.c_void_p()
                if self.nvml.nvmlDeviceGetHandleByIndex(0, ctypes.byref(self.dev)) == 0:
                    self.available = True
        except Exception:
            self.available = False

    def read_metrics(self):
        if not self.available:
            return 0.0, 0.0, 0.0, 0.0
        try:
            pwr = ctypes.c_uint()
            temp = ctypes.c_uint()
            util = nvmlUtilization_t()
            mem = nvmlMemory_t()

            self.nvml.nvmlDeviceGetPowerUsage(self.dev, ctypes.byref(pwr))
            self.nvml.nvmlDeviceGetTemperature(self.dev, 0, ctypes.byref(temp))
            self.nvml.nvmlDeviceGetUtilizationRates(self.dev, ctypes.byref(util))
            self.nvml.nvmlDeviceGetMemoryInfo(self.dev, ctypes.byref(mem))

            return pwr.value / 1000.0, float(util.gpu), float(temp.value), float(mem.used / (1024 ** 2))
        except Exception:
            return 0.0, 0.0, 0.0, 0.0

    def shutdown(self):
        if self.available:
            try:
                self.nvml.nvmlShutdown()
            except Exception:
                pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, 'power_session_log.csv')
    write_header = not os.path.exists(log_file) or os.path.getsize(log_file) == 0

    gpu_reader = GPUReader()

    with open(log_file, 'a', encoding='utf-8') as f:
        if write_header:
            f.write("Timestamp,GPU_Power_W,GPU_Util_Pct,GPU_Temp_C,GPU_Mem_MB,CPU_Util_Pct\n")
            f.flush()

        prev_idle, prev_kernel, prev_user = get_cpu_times()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Started background power monitoring. Logging to {log_file}...")

        try:
            while True:
                time.sleep(1.0)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                curr_idle, curr_kernel, curr_user = get_cpu_times()
                idle_diff = curr_idle - prev_idle
                kernel_diff = curr_kernel - prev_kernel
                user_diff = curr_user - prev_user
                total_diff = kernel_diff + user_diff

                cpu_pct = 100.0 * (total_diff - idle_diff) / total_diff if total_diff > 0 else 0.0
                prev_idle, prev_kernel, prev_user = curr_idle, curr_kernel, curr_user

                gw, gu, gt, gm = gpu_reader.read_metrics()

                line = f"{now},{gw:.2f},{gu:.1f},{gt:.1f},{gm:.0f},{cpu_pct:.1f}\n"
                f.write(line)
                f.flush()
        finally:
            gpu_reader.shutdown()

if __name__ == '__main__':
    main()
