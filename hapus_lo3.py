import tkinter as tk
from tkinter import ttk, messagebox
import win32com.client
import pythoncom
import threading
import time
import winreg
from datetime import datetime, timedelta

class SAPLOManagerPro:
    def __init__(self, root):
        self.root = root
        self.root.title("SAP MiniPod")
        # Ukuran sangat mini & ramping (iPod Style)
        self.root.geometry("280x550") 
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)
        
        # Bypass SAP Scripting Security Warning
        self.disable_sap_warnings()

        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        self.lo_list = []
        self.start_time = None

        self.setup_ui()
        self.update_clock()

    def disable_sap_warnings(self):
        try:
            paths = [
                r"Software\SAP\SAPGUI Front\SAP Frontend Server\Security",
                r"Software\Wow6432Node\SAP\SAPGUI Front\SAP Frontend Server\Security"
            ]
            for path in paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "SecurityLevel", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(key, "WarnOnAttach", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(key, "WarnOnConnection", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                except: continue
        except: pass

    def setup_ui(self):
        # Mini Header
        header = tk.Frame(self.root, bg="#121212", pady=10)
        header.pack(fill="x")
        
        self.lbl_clock = tk.Label(header, text="00:00:00", font=("Helvetica", 18, "bold"), fg="#007aff", bg="#121212")
        self.lbl_clock.pack()

        # Slim Container
        container = tk.Frame(self.root, bg="#121212", padx=15)
        container.pack(fill="both", expand=True)

        # LO Input Area - Compact
        tk.Label(container, text="LO QUEUE", font=("Helvetica", 8, "bold"), fg="#8e8e93", bg="#121212").pack(anchor="w")
        self.txt_lo_list = tk.Text(container, height=4, font=("Consolas", 9), bg="#1c1c1e", fg="#ffffff", bd=0, insertbackground="white")
        self.txt_lo_list.pack(fill="x", pady=(2, 10))

        # Reason Area - Compact
        tk.Label(container, text="REASON", font=("Helvetica", 8, "bold"), fg="#8e8e93", bg="#121212").pack(anchor="w")
        self.ent_reason = tk.Entry(container, font=("Helvetica", 9), bg="#1c1c1e", fg="#ffffff", bd=0)
        self.ent_reason.insert(0, "Lo outstanding Jan-Mar 26")
        self.ent_reason.pack(fill="x", pady=(2, 10), ipady=3)

        # Schedule Area - iPod Button Style
        sched_frame = tk.Frame(container, bg="#1c1c1e", padx=5, pady=5)
        sched_frame.pack(fill="x")
        
        self.ent_time = tk.Entry(sched_frame, width=5, font=("Helvetica", 10, "bold"), bg="#121212", fg="#007aff", bd=0, justify="center")
        self.ent_time.insert(0, datetime.now().strftime("%H:%M"))
        self.ent_time.pack(side="left", padx=5)
        
        btn_sched = tk.Button(sched_frame, text="SET SCHEDULE", font=("Helvetica", 7, "bold"), bg="#007aff", fg="white", relief="flat", command=self.set_schedule)
        btn_sched.pack(side="right", padx=5)

        # Activity Display - The "iPod Screen"
        screen_frame = tk.Frame(container, bg="#000000", pady=10, highlightthickness=1, highlightbackground="#333")
        screen_frame.pack(fill="x", pady=15)
        
        self.lbl_active_lo = tk.Label(screen_frame, text="STANDBY", font=("Helvetica", 14, "bold"), fg="#34c759", bg="#000000")
        self.lbl_active_lo.pack()
        
        self.lbl_detail = tk.Label(screen_frame, text="Ready to process", font=("Helvetica", 7), fg="#8e8e93", bg="#000000")
        self.lbl_detail.pack()

        self.lbl_eta = tk.Label(screen_frame, text="ETA: --:--", font=("Helvetica", 7, "bold"), fg="#ff9500", bg="#000000")
        self.lbl_eta.pack(pady=2)

        # Slim Progress Bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("mini.Horizontal.TProgressbar", thickness=2, troughcolor="#1c1c1e", background="#007aff", borderwidth=0)
        self.pb = ttk.Progressbar(container, style="mini.Horizontal.TProgressbar", variable=tk.DoubleVar(), maximum=100)
        self.pb.pack(fill="x", pady=5)

        # Controls - Bottom Fixed
        ctrl_frame = tk.Frame(self.root, bg="#121212", pady=15)
        ctrl_frame.pack(side="bottom", fill="x")

        self.btn_run = tk.Button(ctrl_frame, text="RUN SYSTEM", bg="#007aff", fg="white", font=("Helvetica", 9, "bold"), relief="flat", height=2, command=self.start_process)
        self.btn_run.pack(fill="x", padx=15, pady=2)

        row2 = tk.Frame(ctrl_frame, bg="#121212")
        row2.pack(fill="x", padx=15)

        self.btn_pause = tk.Button(row2, text="PAUSE", bg="#2c2c2e", fg="white", font=("Helvetica", 8), relief="flat", width=10, command=self.toggle_pause)
        self.btn_pause.pack(side="left", pady=2)

        self.btn_end = tk.Button(row2, text="STOP", bg="#ff3b30", fg="white", font=("Helvetica", 8), relief="flat", width=10, command=self.stop_process)
        self.btn_end.pack(side="right", pady=2)

    def update_clock(self):
        self.lbl_clock.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def set_schedule(self):
        target = self.ent_time.get()
        self.lbl_detail.config(text=f"Timer: {target}", fg="#007aff")
        threading.Thread(target=self.wait_for_time, args=(target,), daemon=True).start()

    def wait_for_time(self, target_time):
        while True:
            if datetime.now().strftime("%H:%M") == target_time:
                self.root.after(0, self.start_process)
                break
            time.sleep(20)

    def toggle_pause(self):
        if self.is_running:
            self.is_paused = not self.is_paused
            self.btn_pause.config(text="RESUME" if self.is_paused else "PAUSE", bg="#ff9500" if self.is_paused else "#2c2c2e")

    def stop_process(self):
        if self.is_running:
            self.stop_requested = True
            self.lbl_detail.config(text="Interrupting...", fg="#ff3b30")

    def start_process(self):
        if self.is_running: return
        raw_lo = self.txt_lo_list.get("1.0", tk.END).strip()
        if not raw_lo:
            messagebox.showwarning("Admin", "List LO kosong!")
            return
        self.lo_list = [line.strip() for line in raw_lo.split("\n") if line.strip()]
        self.reason = self.ent_reason.get()
        self.is_running, self.is_paused, self.stop_requested = True, False, False
        threading.Thread(target=self.sap_worker, daemon=True).start()

    def sap_worker(self):
        try:
            pythoncom.CoInitialize()
            sap_gui_auto = win32com.client.GetObject("SAPGUI")
            application = sap_gui_auto.GetScriptingEngine
            connection = application.Children(0)
            session = connection.Children(0)
            total = len(self.lo_list)

            for index, lo in enumerate(self.lo_list):
                if self.stop_requested: break
                while self.is_paused: time.sleep(1)

                # Update Small Screen
                self.lbl_active_lo.config(text=lo, fg="#007aff")
                self.lbl_detail.config(text=f"Deleting {index+1}/{total}", fg="#8e8e93")
                
                # ETA Calculation
                remaining = total - index
                eta_time = (datetime.now() + timedelta(seconds=remaining * 6)).strftime("%H:%M")
                self.lbl_eta.config(text=f"ETA: {eta_time}")

                # --- ALGORITMA SAP (TIDAK BERUBAH) ---
                session.findById("wnd[0]").maximize()
                session.findById("wnd[0]/tbar[0]/okcd").text = "/nvl02n"
                session.findById("wnd[0]").sendVKey(0)
                session.findById("wnd[0]/usr/ctxtLIKP-VBELN").text = lo
                session.findById("wnd[0]").sendVKey(0)
                
                session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/ssubSUBSCREEN_BODY:SAPMV50A:1102/tblSAPMV50ATC_LIPS_OVER").getAbsoluteRow(0).selected = True
                session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/ssubSUBSCREEN_BODY:SAPMV50A:1102/subSUBSCREEN_ICONBAR:SAPMV50A:1708/btnBT_POLO_T").press()
                
                try:
                    session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()
                    session.findById("wnd[1]/tbar[0]/btn[0]").press()
                except: pass

                session.findById("wnd[0]/mbar/menu[2]/menu[1]/menu[9]").select()
                tree = session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_HEAD/tabpT\\09/ssubSUBSCREEN_BODY:SAPMV50A:2120/subTEXTEDIT:SAPLV70T:2100/cntlSPLITTER_CONTAINER/shellcont/shellcont/shell/shellcont[0]/shell")
                tree.selectItem("Z004", "Column1")
                tree.doubleClickItem("Z004", "Column1")
                
                editor = session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_HEAD/tabpT\\09/ssubSUBSCREEN_BODY:SAPMV50A:2120/subTEXTEDIT:SAPLV70T:2100/cntlSPLITTER_CONTAINER/shellcont/shellcont/shell/shellcont[1]/shell")
                editor.text = self.reason
                session.findById("wnd[0]/tbar[0]/btn[11]").press()
                
                self.pb['value'] = ((index + 1) / total) * 100
                time.sleep(1)

            self.lbl_active_lo.config(text="DONE", fg="#34c759")
            self.lbl_detail.config(text="All tasks finished.")
            messagebox.showinfo("Success", "Process Completed.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            pythoncom.CoUninitialize()

if __name__ == "__main__":
    root = tk.Tk()
    app = SAPLOManagerPro(root)
    root.mainloop()