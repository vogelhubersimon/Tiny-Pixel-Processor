#!/usr/bin/env python3

import threading
import queue
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, StringVar

from flash_lib import (
    BAUD_RATE,
    INSTR_MAP,
    MAX_LINES,
    POS_OPCODE,
    Programmer,
    bin_str,
    translate,
)
import serial
import serial.tools.list_ports
import os

# ---------------------------------------------------------------------------
# ── GUI ─────────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Palette
BG        = "#0d1117"
PANEL     = "#161b22"
ACCENT    = "#58a6ff"
ACCENT2   = "#58a6ff"
SUCCESS   = "#3fb950"
ERROR     = "#f85149"
WARNING   = "#d29922"
TEXT_DIM  = "#8b949e"
TEXT_MAIN = "#c9d1d9"
MONO      = "Courier New"

devMode = False

FH_Logo =   "FH R0\n"\
            "SET R1 #60\n"\
            "COMP R1 R0\n"\
            "ADDLT R0 RT\n"\
            "ADDLT R0 RX\n"

HSD_Logo =  "HSD R0\n"\
            "SET R1 #0\n"\
            "COMP R1 R0\n"\
            "SETEQ R0 #6\n"\

TT =        "TT R0\n"\
            "SET R1 #1\n"\
            "COMP R1 R0\n"\
            "ADDLT R0 RT\n"\
            "ADDLT R0 RX\n"\
            "ADDLT R0 RY\n"\
            "SUBGT R0 RT\n"\
            "ADDGT R0 RX\n"\
            "ADDGT R0 RY\n"\

DemoPrograms = [FH_Logo, HSD_Logo, TT]

def list_ports() -> list[str]:
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports] if ports else []


def run_flash(source_path: str, port: Optional[str],
              log_cb, done_cb) -> None:
    try:
        with open(source_path, "r") as f:
            lines = f.readlines()
    except OSError as exc:
        log_cb(f"ERROR opening file: {exc}", "error")
        done_cb(False); return

    programmer = Programmer(port=port if port else None)
    global devMode
    devMode = False
    
    try:
        programmer.init()
        log_cb(f"Port opened: {programmer._port} @ {BAUD_RATE} baud", "info")
    except Exception as exc:
        log_cb(f"ERROR initialising programmer: {exc}", "error")
        done_cb(False); return

    try:
        NOP_BITS = INSTR_MAP["NOP"].opcode << POS_OPCODE
        OUT_SLOT = MAX_LINES
        OUT_BITS = translate("OUT R0")
        regular = []
        OUT_OPCODE_MASK = 0b11111 << POS_OPCODE
        OUT_OPCODE      = INSTR_MAP["OUT"].opcode << POS_OPCODE

        for raw_line in lines:
            line = raw_line.rstrip("\n\r")
            if not line.strip(): continue
            if line == "##devMode##":
                devMode = True
                log_cb("INFO: Developer mode enabled — OUT instructions will be treated as regular instructions.", "info")
            try:
                instr_bits = translate(line)
            except ValueError as exc:
                log_cb(str(exc), "error")
                done_cb(False); return

            if ((instr_bits & OUT_OPCODE_MASK) == OUT_OPCODE) and not devMode:
                log_cb("INFO: source OUT ignored", "info")
                continue

            regular.append((line, instr_bits))

        if len(regular) >= OUT_SLOT:
            log_cb(
                f"ERROR: {len(regular)} instructions leave no room for OUT at slot {OUT_SLOT}",
                "error"
            )
            done_cb(False); return
        
        for slot in range(len(regular),OUT_SLOT):
            regular.append(("<NOP padding>", NOP_BITS))

        if not devMode:
            regular.append(("OUT R0", OUT_BITS))
        else:
            regular.append(("<NOP padding>", NOP_BITS))

        for slot, (src_line, instr_bits) in enumerate(regular):
            msg = f"[{slot:02d}]  {src_line:<24} →  {bin_str(instr_bits)}  0x{instr_bits:04x}"
            log_cb(msg, "instr")
            programmer.send(slot, instr_bits)

        log_cb("✓  Flash complete.", "success")
        done_cb(True)

    except Exception as exc:
        log_cb(f"ERROR: {exc}", "error")
        done_cb(False)
    finally:
        programmer.close()


class FlashApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Flash Pixel Processor")
        self.geometry("820x640")
        self.minsize(700, 520)
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self._busy = False
        self._log_queue: queue.Queue = queue.Queue()

        self._build_ui()
        self._refresh_ports()
        self._poll_log()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── Header bar ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=52)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(hdr, text="Flash Pixel Processor",
                             font=("Courier New", 15, "bold"),
                             text_color=TEXT_MAIN, padx=16, pady=10)
        title.grid(row=0, column=1, sticky="w")

        # ── File picker row ──────────────────────────────────────────────
        file_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        file_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 0))
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="SOURCE FILE",
                     font=("Courier New", 10, "bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=(14, 0), pady=(10, 0), sticky="w")

        self._file_var = StringVar(value="")
        self._file_entry = ctk.CTkEntry(
            file_frame, textvariable=self._file_var,
            font=(MONO, 12), fg_color="#0a0c11",
            border_color="#2a2d38", text_color=TEXT_MAIN,
            placeholder_text="No file selected …",
            placeholder_text_color=TEXT_DIM,
        )
        self._file_entry.grid(row=1, column=0, columnspan=2,
                              padx=14, pady=(4, 10), sticky="ew")

        self._browse_btn = ctk.CTkButton(
            file_frame, text="Browse …", width=96,
            font=("Courier New", 11), fg_color=ACCENT2,
            hover_color="#5b21b6", text_color="white",
            command=self._browse,
        )
        self._browse_btn.grid(row=1, column=2, padx=(0, 14), pady=(4, 10))

        self._demo_menu = ctk.CTkOptionMenu(
            file_frame, variable=StringVar(value="Demos"),
            values=["Demos", "Demo 1: FH Logo", "Demo 2: HSD Logo", "Demo 3: TinyTapeout Logo"],
            font=(MONO, 12), fg_color="#0a0c11",
            button_color=ACCENT2, button_hover_color="#5b21b6",
            dropdown_fg_color=PANEL, text_color=TEXT_MAIN,
            dropdown_text_color=TEXT_MAIN,
        )
        self._demo_menu.grid(row=1, column=3, padx=(0, 14), pady=(4, 10), sticky="w")

        self._demoLoadBtn = ctk.CTkButton(
            file_frame, text="Load Demo", width=96,
            font=("Courier New", 11), fg_color=ACCENT2,
            hover_color="#5b21b6", text_color="white",
            command=self._demoLoadBtn_callback,
        )
        self._demoLoadBtn.grid(row=1, column=4, padx=(0, 14), pady=(4, 10))

        # ── Port row ─────────────────────────────────────────────────────
        port_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        port_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 0))
        port_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(port_frame, text="SERIAL PORT",
                     font=("Courier New", 10, "bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=(14, 0), pady=(10, 0), sticky="w")

        self._port_var = StringVar(value="Auto-detect")
        self._port_menu = ctk.CTkOptionMenu(
            port_frame, variable=self._port_var,
            values=["Auto-detect"],
            font=(MONO, 12), fg_color="#0a0c11",
            button_color=ACCENT2, button_hover_color="#5b21b6",
            dropdown_fg_color=PANEL, text_color=TEXT_MAIN,
            dropdown_text_color=TEXT_MAIN,
        )
        self._port_menu.grid(row=1, column=0, padx=(14, 6), pady=(4, 10), sticky="w")

        self._refresh_btn = ctk.CTkButton(
            port_frame, text="Refresh", width=96,
            font=("Courier New", 11), fg_color="#1e2130",
            hover_color="#262a3a", text_color=ACCENT,
            border_width=1, border_color=ACCENT,
            command=self._refresh_ports,
        )
        self._refresh_btn.grid(row=1, column=1, padx=(0, 14), pady=(4, 10), sticky="w")

        self._speedInfoLabel = ctk.CTkLabel(port_frame, text="Set Time (Default: 5)", font=("Courier New", 10, "bold"), text_color=TEXT_DIM)
        self._speedInfoLabel.grid(row=0, column=2, padx=(0, 14), pady=(10, 0), sticky="w")

        self._speedTextInfo = ctk.CTkTextbox(port_frame, font=(MONO, 11), width=120, height=28,
            fg_color="#0a0c11", text_color=TEXT_DIM,
            border_width=1, border_color="#2a2d38",
            corner_radius=4, wrap="none", activate_scrollbars=False
        )
        self._speedTextInfo.grid(row=1, column=2, padx=(0, 14), pady=(4, 10), sticky="w")

        self._speedSenderBtn = ctk.CTkButton(
            port_frame, text="Set Time", width=96,
            font=("Courier New", 11), fg_color=ACCENT2,
            hover_color="#5b21b6", text_color="white",
            command=self._send_time,
        )
        self._speedSenderBtn.grid(row=1, column=3, padx=(0, 14), pady=(4, 10), sticky="w")

        # ── Console ───────────────────────────────────────────────────────
        console_outer = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        console_outer.grid(row=3, column=0, sticky="nsew", padx=16, pady=(10, 0))
        console_outer.grid_rowconfigure(1, weight=1)
        console_outer.grid_columnconfigure(0, weight=1)

        con_hdr = ctk.CTkFrame(console_outer, fg_color="#0d1018", corner_radius=0, height=28)
        con_hdr.grid(row=0, column=0, sticky="ew")
        con_hdr.grid_propagate(False)
        con_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(con_hdr, text="OUTPUT", font=("Courier New", 9, "bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=12, pady=5, sticky="w")

        self._clear_btn = ctk.CTkButton(
            con_hdr, text="Clear", width=52, height=20,
            font=("Courier New", 9), fg_color="transparent",
            hover_color="#1e2130", text_color=TEXT_DIM,
            command=self._clear_log,
        )
        self._clear_btn.grid(row=0, column=2, padx=8, pady=4)

        self._console = ctk.CTkTextbox(
            console_outer, font=(MONO, 11),
            fg_color="#080a0f", text_color=TEXT_MAIN,
            border_width=0, corner_radius=0,
            wrap="none", activate_scrollbars=True,
        )
        self._console.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Tag colours (we simulate tags via direct insertion with colour prefixes)
        self._console.configure(state="disabled")

        # ── Bottom bar ────────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=60)
        bottom.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bottom.grid_propagate(False)
        bottom.grid_columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(bottom, height=4,
                                             fg_color="#1a1d28",
                                             progress_color=ACCENT)
        self._progress.grid(row=0, column=0, columnspan=3, sticky="ew",
                            padx=16, pady=(8, 0))
        self._progress.set(0)

        self._flash_btn = ctk.CTkButton(
            bottom, text="FLASH",
            font=("Courier New", 13, "bold"),
            fg_color=ACCENT, hover_color="#00b8d4",
            text_color="#000000", height=34, width=130,
            command=self._start_flash,
        )
        self._flash_btn.grid(row=1, column=2, padx=16, pady=(6, 10))

        self._bot_status = ctk.CTkLabel(
            bottom, text="Ready — select a file and port to begin.",
            font=("Courier New", 10), text_color=TEXT_DIM,
        )
        self._bot_status.grid(row=1, column=0, padx=16, pady=(6, 10), sticky="w")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select assembly source",
            filetypes=[("Assembly files", "*.asm *.s *.txt"), ("Shader File", "*.shader"), ("All files", "*.*")],
        )
        if path:
            self._file_var.set(path)



    def _demoLoadBtn_callback(self):
        if self._busy:
            return
        demoProgram = self._demo_menu.get()
        match demoProgram:
            case "Demos":
                return
            case "Demo 1: FH Logo":
                f = open("demo1.txt", "w")
                f.write(DemoPrograms[0])
                source = f.name
                f.close()
                if not source:
                    self._log("Please select a Demo Program first.", "error")
                    return
                self._flash(source)
                return
            case "Demo 2: HSD Logo":
                f = open("demo2.txt", "w")
                f.write(DemoPrograms[1])
                source = f.name
                f.close()
                if not source:
                    self._log("Please select a Demo Program first.", "error")
                    return
                self._flash(source)
                return
            case "Demo 3: TinyTapeout Logo":
                f = open("demo3.txt", "w")
                f.write(DemoPrograms[2])
                source = f.name
                f.close()
                if not source:
                    self._log("Please select a Demo Program first.", "error")
                    return
                self._flash(source)
                return

    def _refresh_ports(self):
        ports = list_ports()
        options = ["Auto-detect"] + ports
        self._port_menu.configure(values=options)
        if self._port_var.get() not in options:
            self._port_var.set("Auto-detect")

    def _send_uart_frame(self, transmission_byte: int) -> None:
        """Send a single UART frame with the given byte."""
        try:
            port_sel = self._port_var.get()
            port = None if port_sel == "Auto-detect" else port_sel
            
            programmer = Programmer(port=port)
            programmer.init()
            programmer._write(bytes([transmission_byte]))
            programmer.close()
        except Exception:
            pass

    def _send_time(self):
        if self._busy:
            return
        
        value = self._speedTextInfo.get("1.0", "end").strip()
        
        try:
            speed_val = int(round(float(value)))
        except Exception:
            speed_val = value

        # Create 8-bit transmission:
        # Bits 7-6: 01 (command indicator = 0b01 = 1)
        # Bits 5-0: speed value (6 bits)
        transmission_byte = (0b01 << 6) | (speed_val & 0x3F)

        # Send via UART in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=self._send_uart_frame, args=(transmission_byte,), daemon=True)
        thread.start()

        return

    def _clear_log(self):
        self._console.configure(state="normal")
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")

    def _log(self, msg: str, tag: str = "info"):
        colours = {
            "info":    ACCENT,
            "instr":   TEXT_MAIN,
            "nop":     TEXT_DIM,
            "out":     WARNING,
            "success": SUCCESS,
            "error":   ERROR,
        }
        prefix = {
            "info":    "  ·  ",
            "instr":   "     ",
            "nop":     "     ",
            "out":     "  ►  ",
            "success": "  ✓  ",
            "error":   "  ✗  ",
        }
        color  = colours.get(tag, TEXT_MAIN)
        pre    = prefix.get(tag, "     ")
        line   = f"{pre}{msg}\n"
        self._console.configure(state="normal")
        self._console.insert("end", line)
        # Colour the last inserted line via tag_add (ctk wraps tk.Text)
        start = self._console.index("end - 1 lines linestart")
        end   = self._console.index("end - 1 lines lineend")
        tag_name = f"color_{tag}"
        self._console._textbox.tag_configure(tag_name, foreground=color)
        self._console._textbox.tag_add(tag_name, start, end)
        self._console.configure(state="disabled")
        self._console.see("end")

    def _poll_log(self):
        try:
            while True:
                msg, tag = self._log_queue.get_nowait()
                self._log(msg, tag)
        except queue.Empty:
            pass
        self.after(60, self._poll_log)

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._flash_btn.configure(state=state)
        self._browse_btn.configure(state=state)
        self._refresh_btn.configure(state=state)
        #self._timeButton.configure(state=state)
        if busy:
            self._progress.start()
        else:
            self._progress.stop()

    def _start_flash(self):
        if self._busy:
            return
        source = self._file_var.get().strip()
        if not source:
            self._log("Please select an assembly source file first.", "error")
            return
        self._flash(source)
    
    def _flash(self,source):
        port_sel = self._port_var.get()
        port = None if port_sel == "Auto-detect" else port_sel

        self._clear_log()
        self._log(f"Source : {source}", "info")
        self._log(f"Port   : {port_sel}", "info")
        self._log("─" * 66, "nop")
        self._set_busy(True)
        self._bot_status.configure(text="Flashing …", text_color=WARNING)

        def thread_log(msg, tag="info"):
            self._log_queue.put((msg, tag))

        def done(ok: bool):
            self._log_queue.put(("─" * 66, "nop"))
            if ok:
                self._log_queue.put(("Done — device programmed successfully.", "success"))
            else:
                self._log_queue.put(("Flash failed — see errors above.", "error"))
            # Schedule UI update on main thread
            self.after(0, self._flash_done, ok)

        threading.Thread(
            target=run_flash,
            args=(source, port, thread_log, done),
            daemon=True,
        ).start()

    def _flash_done(self, ok: bool):
        self._set_busy(False)
        if ok:
            self._bot_status.configure(text="Flash successful.", text_color=SUCCESS)
            self._progress.set(1)
        else:
            self._bot_status.configure(text="Flash failed.", text_color=ERROR)
            self._progress.set(0)


if __name__ == "__main__":
    app = FlashApp()
    app.mainloop()
