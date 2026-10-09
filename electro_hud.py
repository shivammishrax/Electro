import collections
import ctypes
import os
import threading
import time
import tkinter as tk

# =====================================================================
#  ELECTRO ⚡ - Real-Time PC Hardware Power & UPS / Inverter HUD
#  Zero-Subprocess • Native C-Level NVML & Win32 API • 0% CPU Overhead
#  Real-Time 60-Second Rolling History Tracking Graph
# =====================================================================

# ----------------- Native Windows CPU Times -----------------
class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', ctypes.c_uint32), ('dwHighDateTime', ctypes.c_uint32)]

def to_int(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

def get_cpu_times():
    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    return to_int(idle), to_int(kernel), to_int(user)

# ----------------- Native NVML C-Bindings (Zero Console / Zero Subprocess) -----------------
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

            gpu_w = pwr.value / 1000.0
            gpu_u = float(util.gpu)
            gpu_t = float(temp.value)
            gpu_m = float(mem.used / (1024 ** 2))
            return gpu_w, gpu_u, gpu_t, gpu_m
        except Exception:
            return 0.0, 0.0, 0.0, 0.0

    def shutdown(self):
        if self.available:
            try:
                self.nvml.nvmlShutdown()
            except Exception:
                pass

# ----------------- UI Overlay Widget -----------------
class ElectroHUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Electro - Power HUD")
        
        # Borderless, always-on-top, semi-transparent
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.93)
        self.root.configure(bg="#0b0f19")

        # Telemetry State
        self.gpu_reader = GPUReader()
        self.gpu_watts = 0.0
        self.gpu_util = 0.0
        self.gpu_temp = 0.0
        self.gpu_vram = 0.0
        self.cpu_util = 0.0
        self.cpu_watts = 35.0
        self.platform_watts = 75.0
        self.monitor_watts = 45.0  # BenQ PD2706U 45W
        self.inverter_capacity = 900.0 # MaxiLion 1500 (900W)

        # 60-Second Rolling History Buffer
        self.history = collections.deque(maxlen=60)
        self.show_graph = True

        self.is_compact = False
        self.is_running = True
        
        # Position top-right
        screen_w = self.root.winfo_screenwidth()
        self.win_x = screen_w - 350
        self.win_y = 35
        self.normal_h = 475
        self.root.geometry(f"320x{self.normal_h}+{self.win_x}+{self.win_y}")

        # Drag variables
        self._drag_start_x = 0
        self._drag_start_y = 0

        self.setup_ui()

        # Telemetry thread (native C calls only, zero subprocess)
        self.worker_thread = threading.Thread(target=self.telemetry_loop, daemon=True)
        self.worker_thread.start()

        self.update_gui()

    def setup_ui(self):
        self.root.bind("<ButtonPress-1>", self.on_drag_start)
        self.root.bind("<B1-Motion>", self.on_drag_motion)

        self.container = tk.Frame(self.root, bg="#0b0f19", highlightbackground="#1f293d", highlightthickness=1)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Header Frame
        self.header_frame = tk.Frame(self.container, bg="#121826", height=28)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.bind("<ButtonPress-1>", self.on_drag_start)
        self.header_frame.bind("<B1-Motion>", self.on_drag_motion)

        self.lbl_brand = tk.Label(
            self.header_frame, text="⚡ ELECTRO", font=("Segoe UI", 9, "bold"),
            fg="#00f2fe", bg="#121826"
        )
        self.lbl_brand.pack(side=tk.LEFT, padx=(8, 2), pady=4)

        self.lbl_subtitle = tk.Label(
            self.header_frame, text="HUD", font=("Segoe UI", 7, "bold"),
            fg="#6e7681", bg="#121826"
        )
        self.lbl_subtitle.pack(side=tk.LEFT, pady=4)

        btn_close = tk.Label(
            self.header_frame, text="✕", font=("Segoe UI", 9, "bold"),
            fg="#8b949e", bg="#121826", cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT, padx=6)
        btn_close.bind("<Button-1>", lambda e: self.close_app())
        btn_close.bind("<Enter>", lambda e: btn_close.config(fg="#ff7b72"))
        btn_close.bind("<Leave>", lambda e: btn_close.config(fg="#8b949e"))

        self.btn_toggle_mode = tk.Label(
            self.header_frame, text="⎯", font=("Segoe UI", 9, "bold"),
            fg="#8b949e", bg="#121826", cursor="hand2"
        )
        self.btn_toggle_mode.pack(side=tk.RIGHT, padx=6)
        self.btn_toggle_mode.bind("<Button-1>", lambda e: self.toggle_view_mode())

        # Toggle Graph Button in Header
        self.btn_toggle_graph = tk.Label(
            self.header_frame, text="📈", font=("Segoe UI", 8),
            fg="#00f2fe", bg="#121826", cursor="hand2"
        )
        self.btn_toggle_graph.pack(side=tk.RIGHT, padx=4)
        self.btn_toggle_graph.bind("<Button-1>", lambda e: self.toggle_graph_view())

        # Expanded View
        self.expanded_frame = tk.Frame(self.container, bg="#0b0f19", padx=10, pady=6)
        self.expanded_frame.pack(fill=tk.BOTH, expand=True)

        # Hero Metric (Total Wall Power)
        hero_box = tk.Frame(self.expanded_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, pady=6)
        hero_box.pack(fill=tk.X, pady=(0, 6))

        tk.Label(hero_box, text="TOTAL ESTIMATED WALL DRAW", font=("Segoe UI", 7, "bold"), fg="#8b949e", bg="#101624").pack()

        self.lbl_total_watts = tk.Label(hero_box, text="--- W", font=("Segoe UI", 24, "bold"), fg="#00f5a0", bg="#101624")
        self.lbl_total_watts.pack()

        # Inverter Load Bar
        self.inverter_frame = tk.Frame(hero_box, bg="#101624", padx=10)
        self.inverter_frame.pack(fill=tk.X, pady=(2, 4))

        self.lbl_inverter_status = tk.Label(
            self.inverter_frame, text="Inverter Load: --% of 900W", font=("Segoe UI", 7), fg="#8b949e", bg="#101624"
        )
        self.lbl_inverter_status.pack(anchor="w")

        self.inverter_canvas = tk.Canvas(self.inverter_frame, height=6, bg="#1c2438", highlightthickness=0)
        self.inverter_canvas.pack(fill=tk.X, pady=(2, 0))

        # ----------------- History Graph Card -----------------
        self.graph_card = tk.Frame(self.expanded_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, padx=6, pady=4)
        self.graph_card.pack(fill=tk.X, pady=(0, 6))

        graph_hdr = tk.Frame(self.graph_card, bg="#101624")
        graph_hdr.pack(fill=tk.X, pady=(0, 2))

        tk.Label(graph_hdr, text="📈 ROLLING HISTORY (60s)", font=("Segoe UI", 7, "bold"), fg="#00f2fe", bg="#101624").pack(side=tk.LEFT)
        self.lbl_graph_stats = tk.Label(graph_hdr, text="Peak: --W | Avg: --W", font=("Segoe UI", 6), fg="#8b949e", bg="#101624")
        self.lbl_graph_stats.pack(side=tk.RIGHT)

        self.graph_canvas = tk.Canvas(self.graph_card, height=72, bg="#0b0f19", highlightthickness=0)
        self.graph_canvas.pack(fill=tk.X, pady=(2, 2))

        # Metrics Grid (GPU & CPU)
        grid_frame = tk.Frame(self.expanded_frame, bg="#0b0f19")
        grid_frame.pack(fill=tk.X, pady=(0, 5))

        # GPU Card
        gpu_card = tk.Frame(grid_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, padx=6, pady=3)
        gpu_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        tk.Label(gpu_card, text="🎮 RTX 5080", font=("Segoe UI", 7, "bold"), fg="#00f2fe", bg="#101624").pack(anchor="w")
        self.lbl_gpu_power = tk.Label(gpu_card, text="-- W", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#101624")
        self.lbl_gpu_power.pack(anchor="w")
        self.lbl_gpu_stats = tk.Label(gpu_card, text="Util: --% | --°C", font=("Segoe UI", 6), fg="#8b949e", bg="#101624")
        self.lbl_gpu_stats.pack(anchor="w")

        # CPU Card
        cpu_card = tk.Frame(grid_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, padx=6, pady=3)
        cpu_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        tk.Label(cpu_card, text="🧠 Ryzen 9 9950X3D", font=("Segoe UI", 7, "bold"), fg="#ff7b72", bg="#101624").pack(anchor="w")
        self.lbl_cpu_power = tk.Label(cpu_card, text="-- W", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#101624")
        self.lbl_cpu_power.pack(anchor="w")
        self.lbl_cpu_stats = tk.Label(cpu_card, text="Util: --%", font=("Segoe UI", 6), fg="#8b949e", bg="#101624")
        self.lbl_cpu_stats.pack(anchor="w")

        # Platform Circuitry Card (Motherboard, RAM, SSDs, Cooling)
        platform_box = tk.Frame(self.expanded_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, padx=6, pady=2)
        platform_box.pack(fill=tk.X, pady=(0, 5))
        
        lbl_plat_title = tk.Label(platform_box, text="⚙️ Platform Circuitry: ~75 W", font=("Segoe UI", 7, "bold"), fg="#e3b341", bg="#101624")
        lbl_plat_title.pack(anchor="w")
        lbl_plat_detail = tk.Label(
            platform_box, text="64GB DDR5 (~12W) • X870E Board (~25W) • SSDs (~12W) • AIO/Fans (~26W)",
            font=("Segoe UI", 6), fg="#8b949e", bg="#101624"
        )
        lbl_plat_detail.pack(anchor="w")

        # Monitor Card (BenQ PD2706U)
        mon_card = tk.Frame(self.expanded_frame, bg="#101624", highlightbackground="#1f293d", highlightthickness=1, padx=6, pady=3)
        mon_card.pack(fill=tk.X, pady=(0, 4))

        tk.Label(mon_card, text="🖥️ BenQ PD2706U 4K Monitor", font=("Segoe UI", 7, "bold"), fg="#d2a8ff", bg="#101624").pack(anchor="w")

        mon_btn_frame = tk.Frame(mon_card, bg="#101624")
        mon_btn_frame.pack(fill=tk.X, pady=(2, 0))

        self.btn_mon_normal = tk.Label(
            mon_btn_frame, text="Display: 45W", font=("Segoe UI", 7, "bold"),
            bg="#238636", fg="#ffffff", padx=4, pady=1, cursor="hand2"
        )
        self.btn_mon_normal.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_mon_normal.bind("<Button-1>", lambda e: self.set_monitor_mode("normal"))

        self.btn_mon_pd = tk.Label(
            mon_btn_frame, text="+ USB-PD: 135W", font=("Segoe UI", 7),
            bg="#1f293d", fg="#8b949e", padx=4, pady=1, cursor="hand2"
        )
        self.btn_mon_pd.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_mon_pd.bind("<Button-1>", lambda e: self.set_monitor_mode("pd"))

        self.btn_mon_off = tk.Label(
            mon_btn_frame, text="Off: 0W", font=("Segoe UI", 7),
            bg="#1f293d", fg="#8b949e", padx=4, pady=1, cursor="hand2"
        )
        self.btn_mon_off.pack(side=tk.LEFT)
        self.btn_mon_off.bind("<Button-1>", lambda e: self.set_monitor_mode("off"))

        # Footer Tip
        self.lbl_footer = tk.Label(
            self.expanded_frame, text="Double-click header for Pill mode • Click 📈 to toggle Graph", font=("Segoe UI", 6), fg="#484f58", bg="#0b0f19"
        )
        self.lbl_footer.pack(side=tk.BOTTOM)

        # Compact Pill View (hidden initially)
        self.compact_label = tk.Label(
            self.container, text="⚡ ELECTRO: --- W | GPU: --W | CPU: --W",
            font=("Segoe UI", 8, "bold"), fg="#00f5a0", bg="#0b0f19", padx=8, pady=4
        )
        self.compact_label.bind("<ButtonPress-1>", self.on_drag_start)
        self.compact_label.bind("<B1-Motion>", self.on_drag_motion)
        self.compact_label.bind("<Double-Button-1>", lambda e: self.toggle_view_mode())
        self.header_frame.bind("<Double-Button-1>", lambda e: self.toggle_view_mode())

    def set_monitor_mode(self, mode):
        if mode == "normal":
            self.monitor_watts = 45.0
            self.btn_mon_normal.config(bg="#238636", fg="#ffffff", font=("Segoe UI", 7, "bold"))
            self.btn_mon_pd.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
            self.btn_mon_off.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
        elif mode == "pd":
            self.monitor_watts = 135.0
            self.btn_mon_normal.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
            self.btn_mon_pd.config(bg="#1f6feb", fg="#ffffff", font=("Segoe UI", 7, "bold"))
            self.btn_mon_off.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
        elif mode == "off":
            self.monitor_watts = 0.0
            self.btn_mon_normal.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
            self.btn_mon_pd.config(bg="#1f293d", fg="#8b949e", font=("Segoe UI", 7))
            self.btn_mon_off.config(bg="#30363d", fg="#ffffff", font=("Segoe UI", 7, "bold"))

    def toggle_graph_view(self):
        self.show_graph = not self.show_graph
        if self.show_graph:
            self.graph_card.pack(fill=tk.X, pady=(0, 6), before=self.expanded_frame.winfo_children()[1])
            self.btn_toggle_graph.config(fg="#00f2fe")
            self.normal_h = 475
        else:
            self.graph_card.pack_forget()
            self.btn_toggle_graph.config(fg="#6e7681")
            self.normal_h = 375
        
        if not self.is_compact:
            self.root.geometry(f"320x{self.normal_h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def toggle_view_mode(self):
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.expanded_frame.pack_forget()
            self.header_frame.pack_forget()
            self.compact_label.pack(fill=tk.BOTH, expand=True)
            self.btn_toggle_mode.config(text="⤢")
            self.root.geometry(f"290x30+{self.root.winfo_x()}+{self.root.winfo_y()}")
        else:
            self.compact_label.pack_forget()
            self.header_frame.pack(fill=tk.X)
            self.expanded_frame.pack(fill=tk.BOTH, expand=True)
            self.btn_toggle_mode.config(text="⎯")
            self.root.geometry(f"320x{self.normal_h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def on_drag_motion(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def telemetry_loop(self):
        prev_idle, prev_kernel, prev_user = get_cpu_times()
        while self.is_running:
            time.sleep(1.0)
            
            # CPU calculation (Win32 API)
            curr_idle, curr_kernel, curr_user = get_cpu_times()
            idle_diff = curr_idle - prev_idle
            kernel_diff = curr_kernel - prev_kernel
            user_diff = curr_user - prev_user
            total_diff = kernel_diff + user_diff
            
            cpu_p = 100.0 * (total_diff - idle_diff) / total_diff if total_diff > 0 else 0.0
            prev_idle, prev_kernel, prev_user = curr_idle, curr_kernel, curr_user
            self.cpu_util = cpu_p
            self.cpu_watts = min(32.0 + (cpu_p / 100.0) * 130.0, 162.0)

            # GPU Metrics (Native C API via nvml.dll - ZERO console windows!)
            gw, gu, gt, gm = self.gpu_reader.read_metrics()
            self.gpu_watts = gw
            self.gpu_util = gu
            self.gpu_temp = gt
            self.gpu_vram = gm

    def draw_history_graph(self):
        if not self.show_graph or len(self.history) < 2:
            return

        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        if w < 20 or h < 20:
            return

        # Adaptive Y max scale (minimum 700W, or higher up to 1000W+)
        hist_max = max(self.history)
        y_max = max(700.0, hist_max * 1.15)
        if hist_max > 700.0:
            y_max = max(y_max, 960.0)

        # Draw grid reference lines
        for ref_w, col, dash in [(300, "#192236", None), (600, "#1f2a42", None), (900, "#ff7b72", (2, 2))]:
            if ref_w <= y_max:
                y = h - (ref_w / y_max) * h
                if dash:
                    self.graph_canvas.create_line(0, y, w, y, fill=col, dash=dash, width=1)
                    self.graph_canvas.create_text(w - 4, y - 5, text="900W Limit", fill="#ff7b72", font=("Segoe UI", 6), anchor="e")
                else:
                    self.graph_canvas.create_line(0, y, w, y, fill=col, width=1)
                    self.graph_canvas.create_text(4, y - 4, text=f"{ref_w}W", fill="#6e7681", font=("Segoe UI", 5), anchor="w")

        # Map points
        n = len(self.history)
        points = []
        area_pts = [0, h]
        for i, val in enumerate(self.history):
            x = (i / 59.0) * w if n > 1 else 0
            y = h - (val / y_max) * h
            y = max(3.0, min(float(h - 3), y))
            points.extend([x, y])
            area_pts.extend([x, y])

        area_pts.extend([points[-2], h])

        # Fill subtle gradient-like polygon under curve
        self.graph_canvas.create_polygon(area_pts, fill="#0c2338", outline="")

        # Draw smooth curve
        line_color = "#00f5a0" if hist_max < 450 else ("00f2fe" if hist_max < 700 else "#ff7b72")
        self.graph_canvas.create_line(points, fill=line_color, width=2, smooth=True)

        # Draw pulsing head dot at current point
        lx, ly = points[-2], points[-1]
        self.graph_canvas.create_oval(lx - 3, ly - 3, lx + 3, ly + 3, fill="#00f2fe", outline="#ffffff", width=1)

    def update_gui(self):
        if not self.is_running:
            return

        dc_total = self.gpu_watts + self.cpu_watts + self.platform_watts
        wall_pc = dc_total / 0.90
        total_wall = wall_pc + self.monitor_watts
        inverter_pct = (total_wall / self.inverter_capacity) * 100.0

        # Append to 60s history buffer
        self.history.append(total_wall)

        # Update History Stats
        if self.history:
            h_peak = max(self.history)
            h_avg = sum(self.history) / len(self.history)
            h_min = min(self.history)
            self.lbl_graph_stats.config(
                text=f"Peak: {h_peak:.0f}W | Avg: {h_avg:.0f}W | Min: {h_min:.0f}W"
            )

        if inverter_pct < 50:
            wall_color = "#00f5a0" # Emerald
            inv_bar_color = "#00f5a0"
        elif inverter_pct < 75:
            wall_color = "#00f2fe" # Electric Cyan
            inv_bar_color = "#00f2fe"
        elif inverter_pct < 90:
            wall_color = "#e3b341" # Yellow Warning
            inv_bar_color = "#e3b341"
        else:
            wall_color = "#ff7b72" # Red Overload
            inv_bar_color = "#ff7b72"

        self.lbl_total_watts.config(text=f"{total_wall:.0f} W", fg=wall_color)
        self.lbl_inverter_status.config(
            text=f"Inverter Load: {inverter_pct:.0f}% of 900W ({total_wall:.0f}W)",
            fg=wall_color
        )
        
        self.inverter_canvas.delete("all")
        canvas_w = self.inverter_canvas.winfo_width()
        if canvas_w > 10:
            bar_w = int(canvas_w * min(inverter_pct / 100.0, 1.0))
            self.inverter_canvas.create_rectangle(0, 0, bar_w, 6, fill=inv_bar_color, width=0)

        self.lbl_gpu_power.config(text=f"{self.gpu_watts:.1f} W")
        self.lbl_gpu_stats.config(text=f"Util: {self.gpu_util:.0f}% | {self.gpu_temp:.0f}°C | {self.gpu_vram/1024:.1f}GB")

        self.lbl_cpu_power.config(text=f"~{self.cpu_watts:.0f} W")
        self.lbl_cpu_stats.config(text=f"Util: {self.cpu_util:.0f}% (16-Core)")

        self.compact_label.config(
            text=f"⚡ ELECTRO: {total_wall:.0f}W  |  GPU: {self.gpu_watts:.0f}W ({self.gpu_temp:.0f}°C)  |  CPU: {self.cpu_watts:.0f}W  |  Inv: {inverter_pct:.0f}%",
            fg=wall_color
        )

        # Draw History Graph
        self.draw_history_graph()

        self.root.after(1000, self.update_gui)

    def close_app(self):
        self.is_running = False
        self.gpu_reader.shutdown()
        self.root.destroy()

if __name__ == '__main__':
    app = ElectroHUD()
    app.root.mainloop()
