import tkinter as tk
from tkinter import filedialog
import threading
import datetime
import os
import cv2
from PIL import Image, ImageTk

# --- MODERNE ANTHRAZIT FARBPALETTE ---
BG_MAIN = "#18181b"
BG_PANEL = "#27272a"
BG_ELEMENT = "#3f3f46"
FG_DIM = "#a1a1aa"
FG_BRIGHT = "#f4f4f5"
ACCENT = "#3b82f6"

FONT_SM = ("Consolas", 9)
FONT_MD = ("Consolas", 10)
FONT_LG = ("Consolas", 12, "bold")
FONT_XL = ("Consolas", 14, "bold")

app_state = {
    "video_path": None,
    "original_frame": None,
    "preview_img": None,
    "output_dir": os.path.abspath("./exports")
}

# --- CUSTOM PROGRESS BAR ---
class CleanProgressBar(tk.Canvas):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, height=6, bg=BG_PANEL, highlightthickness=0, *args, **kwargs)
        self.progress = 0.0
        self.bind("<Configure>", self.draw)

    def set_progress(self, value):
        self.progress = max(0.0, min(1.0, value))
        self.draw()

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        self.create_rectangle(0, 0, w, h, fill=BG_ELEMENT, width=0)
        if self.progress > 0:
            self.create_rectangle(0, 0, w * self.progress, h, fill=ACCENT, width=0)

# --- CUSTOM PILL SLIDER ---
class PillSlider(tk.Canvas):
    def __init__(self, parent, min_val, max_val, default_val, command=None, *args, **kwargs):
        super().__init__(parent, height=24, bg=BG_PANEL, highlightthickness=0, *args, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.val = default_val
        self.command = command
        
        self.bind("<Configure>", self.draw)
        self.bind("<Button-1>", self.click)
        self.bind("<B1-Motion>", self.drag)
        
    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: w = 200 
        
        self.create_line(15, h//2, w-15, h//2, fill=BG_ELEMENT, width=12, capstyle="round")
        
        percent = (self.val - self.min_val) / (self.max_val - self.min_val)
        x = 15 + percent * (w - 30)
        
        self.create_line(x-12, h//2, x+12, h//2, fill="#71717a", width=12, capstyle="round")
        
    def update_val_from_x(self, x):
        w = self.winfo_width()
        percent = (x - 15) / (w - 30)
        percent = max(0.0, min(1.0, percent))
        self.val = int(self.min_val + percent * (self.max_val - self.min_val))
        self.draw()
        if self.command:
            self.command(self.val)
            
    def click(self, event): self.update_val_from_x(event.x)
    def drag(self, event): self.update_val_from_x(event.x)
    def get(self): return self.val


def select_output_dir(root, lbl_output):
    folder_path = filedialog.askdirectory(parent=root, title="Export-Ordner auswählen")
    if folder_path:
        app_state["output_dir"] = folder_path
        display_path = folder_path if len(folder_path) < 35 else "..." + folder_path[-32:]
        lbl_output.config(text=f"{display_path}")

def load_video(canvas, lbl_stats):
    file_path = filedialog.askopenfilename(
        title="Motorrad-Video auswählen", filetypes=[("Video Files", "*.mp4 *.mov")]
    )
    if not file_path: return
    app_state["video_path"] = file_path
    
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened(): raise Exception("Konnte Video nicht lesen.")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 60) 
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            lbl_stats.config(text=f"{int(width)}x{int(height)} @ {round(fps, 1)} FPS")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            app_state["original_frame"] = Image.fromarray(frame_rgb)
            redraw_canvas_image(canvas)
            
    except Exception as e:
        with open("apexflow_error.txt", "a") as f:
            f.write(f"\n--- FEHLER BEIM VIDEO LADEN {datetime.datetime.now()} ---\n{e}\n")

def redraw_canvas_image(canvas, event=None):
    if app_state["original_frame"]:
        c_width = canvas.winfo_width()
        c_height = canvas.winfo_height()
        if c_width < 10 or c_height < 10: return
        
        img = app_state["original_frame"].copy()
        img.thumbnail((c_width, c_height), Image.Resampling.LANCZOS)
        app_state["preview_img"] = ImageTk.PhotoImage(img)
        
        canvas.delete("all")
        canvas.create_image(c_width//2, c_height//2, image=app_state["preview_img"], anchor="center")
    else:
        c_width = canvas.winfo_width()
        c_height = canvas.winfo_height()
        canvas.delete("all")
        if c_width > 10:
            for i in range(0, max(c_width, c_height), 40):
                canvas.create_line(i, 0, i, c_height, fill=BG_MAIN)
                canvas.create_line(0, i, c_width, i, fill=BG_MAIN)
            canvas.create_text(c_width//2, c_height//2, text="Awaiting Footage", fill=FG_DIM, font=FONT_LG)

# --- RENDER LOGIK ---
def run_render_test(root, button, var_sens, var_pad, var_min, progress_bar):
    if not app_state["video_path"]: return
    button.config(state="disabled", text="ANALYZING...", bg="#52525b")
    progress_bar.set_progress(0.0) 
    
    sensitivity_val = var_sens.get()
    padding_val = var_pad.get()
    min_length_val = var_min.get()
    
    def update_progress(percent):
        root.after(0, lambda: progress_bar.set_progress(percent))
    
    def task():
        try:
            from apexflow.analyzer import scan_for_highlights
            from apexflow.trimmer import extract_clips
            
            highlights = scan_for_highlights(
                app_state["video_path"], 
                sensitivity=sensitivity_val, 
                padding=padding_val,
                min_length=min_length_val,
                progress_callback=update_progress 
            )
            
            if highlights:
                root.after(0, lambda: button.config(text="TRIMMING..."))
                root.after(0, lambda: progress_bar.set_progress(1.0))
                extract_clips(app_state["video_path"], highlights, output_dir=app_state["output_dir"])
            
            with open("apexflow_log.txt", "a") as f:
                f.write(f"\n--- Analyse beendet für {app_state['video_path']} ---\n")
                
        except Exception as e:
            with open("apexflow_error.txt", "a") as f:
                f.write(f"\n--- FEHLER BEI RENDER PROZESS ---\n{e}\n")
        finally:
            root.after(0, lambda: progress_bar.set_progress(0.0))
            root.after(0, lambda: button.config(state="normal", text="RENDER ➔", bg=FG_BRIGHT))

    threading.Thread(target=task, daemon=True).start()

def start_gui():
    root = tk.Tk()
    root.geometry("1280x800")
    root.title("APEXFLOW v2.0")
    root.configure(bg=BG_MAIN)
    
    # --- HEADER ---
    top_frame = tk.Frame(root, bg=BG_MAIN, pady=15, padx=20)
    top_frame.pack(fill="x")
    tk.Label(top_frame, text="APEXFLOW v2.0", bg=BG_MAIN, fg=FG_BRIGHT, font=FONT_MD).pack(side="left")
    tk.Label(top_frame, text="● READY", bg=BG_MAIN, fg="#52525b", font=FONT_MD).pack(side="right")
    
    # --- VIDEO BEREICH ---
    video_frame = tk.Frame(root, bg=BG_PANEL)
    video_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    preview_canvas = tk.Canvas(video_frame, bg=BG_PANEL, highlightthickness=0)
    preview_canvas.pack(fill="both", expand=True)
    preview_canvas.bind("<Configure>", lambda e: redraw_canvas_image(preview_canvas, e))
    
    # --- DASHBOARD ---
    bottom_deck = tk.Frame(root, bg=BG_PANEL, height=180)
    bottom_deck.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
    bottom_deck.pack_propagate(False) 
    
    bottom_deck.grid_columnconfigure(0, weight=1)
    bottom_deck.grid_columnconfigure(1, weight=2)
    bottom_deck.grid_columnconfigure(2, weight=1)
    
    # 1. SOURCE
    col1 = tk.Frame(bottom_deck, bg=BG_PANEL, padx=20, pady=20)
    col1.grid(row=0, column=0, sticky="nsew")
    tk.Label(col1, text="1. SOURCE", bg=BG_PANEL, fg=FG_DIM, font=FONT_SM, anchor="w").pack(fill="x", pady=(0,10))
    btn_select = tk.Button(col1, text="Select Footage", bg=BG_ELEMENT, fg=FG_BRIGHT, relief="flat", borderwidth=0, font=FONT_MD, activebackground="#52525b", activeforeground=FG_BRIGHT, command=lambda: load_video(preview_canvas, lbl_stats))
    btn_select.pack(fill="x", ipady=12)
    lbl_stats = tk.Label(col1, text="No video loaded", bg=BG_PANEL, fg=FG_DIM, font=("Consolas", 8), anchor="w")
    lbl_stats.pack(fill="x", pady=(10, 0))

    # 2. AI PARAMETER
    col2 = tk.Frame(bottom_deck, bg=BG_PANEL, padx=20, pady=20)
    col2.grid(row=0, column=1, sticky="nsew")
    tk.Label(col2, text="2. AI ENGINE SETTINGS", bg=BG_PANEL, fg=FG_DIM, font=FONT_SM, anchor="w").pack(fill="x", pady=(0,10))
    sliders_frame = tk.Frame(col2, bg=BG_PANEL)
    sliders_frame.pack(fill="x")
    
    def create_deck_slider(parent, label, min_val, max_val, default_val):
        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BG_PANEL, fg=FG_DIM, font=FONT_SM, width=15, anchor="w").pack(side="left")
        val_lbl = tk.Label(row, text=str(default_val), bg=BG_PANEL, fg=FG_BRIGHT, font=("Consolas", 9, "bold"), width=4)
        val_lbl.pack(side="right")
        slider = PillSlider(row, min_val, max_val, default_val, command=lambda v: val_lbl.config(text=str(v)))
        slider.pack(side="left", fill="x", expand=True, padx=10)
        return slider

    var_sens = create_deck_slider(sliders_frame, "SENSITIVITY", 10, 150, 40)
    var_pad = create_deck_slider(sliders_frame, "PADDING (SEC)", 1, 10, 5)
    var_min = create_deck_slider(sliders_frame, "MIN LENGTH", 1, 10, 3)

    # 3. OUTPUT & RENDER
    col3 = tk.Frame(bottom_deck, bg=BG_PANEL, padx=20, pady=20)
    col3.grid(row=0, column=2, sticky="nsew")
    tk.Label(col3, text="3. OUTPUT", bg=BG_PANEL, fg=FG_DIM, font=FONT_SM, anchor="w").pack(fill="x", pady=(0,5))
    
    out_row = tk.Frame(col3, bg=BG_PANEL)
    out_row.pack(fill="x", pady=(0, 10))
    lbl_out = tk.Label(out_row, text="./exports", bg=BG_PANEL, fg=FG_BRIGHT, font=("Consolas", 9, "underline"), cursor="hand2", anchor="w")
    lbl_out.pack(side="left", fill="x", expand=True)
    lbl_out.bind("<Button-1>", lambda e: select_output_dir(root, lbl_out))
    
    progress_bar = CleanProgressBar(col3)
    progress_bar.pack(fill="x", pady=(0, 5))
    
    render_btn = tk.Button(col3, text="RENDER ➔", bg=FG_BRIGHT, fg="black", 
                           activebackground="#d4d4d8", activeforeground="black",
                           relief="flat", borderwidth=0, font=FONT_XL)
    render_btn.config(command=lambda: run_render_test(root, render_btn, var_sens, var_pad, var_min, progress_bar))
    render_btn.pack(fill="x", ipady=12)

    root.mainloop()

if __name__ == "__main__":
    start_gui()