#!/usr/bin/env python3

import sys
from typing import Optional

from flash_lib import (
    BAUD_RATE,
    INSTR_MAP,
    MAX_LINES,
    POS_OPCODE,
    Programmer,
    bin_str,
    translate,
)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Usage: flash.py <program> [--port COMx]
    args = sys.argv[1:]
    port: Optional[str] = None

    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 >= len(args):
            print("error: --port requires a value (e.g. --port COM3)", file=sys.stderr)
            return 1
        port = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if len(args) != 1:
        print("usage: python flash.py <program> [--port COM3]", file=sys.stderr)
        print("  <program>   path to the assembly source file", file=sys.stderr)
        print("  --port      serial port to use (auto-detected if omitted)", file=sys.stderr)
        return 1

    source_path = args[0]

    try:
        with open(source_path, "r") as f:
            lines = f.readlines()
    except OSError as exc:
        print(f"error opening file: {exc}", file=sys.stderr)
        return 1

    programmer = Programmer(port=port)
    try:
        programmer.init()
    except Exception as exc:
        print(f"error initialising programmer: {exc}", file=sys.stderr)
        return 1

    try:
        NOP_BITS = INSTR_MAP["NOP"].opcode << POS_OPCODE
        OUT_SLOT = MAX_LINES  # OUT must always live at slot 19

        # First pass: translate every line, separate OUT from the rest
        regular: list[tuple[str, int]] = []  # (source_line, instr_bits) for slots 0..18
        out_bits: int | None = None

        OUT_OPCODE_MASK = 0b11111 << POS_OPCODE
        OUT_OPCODE      = INSTR_MAP["OUT"].opcode << POS_OPCODE
        out_line_src    = ""   # original source text of the OUT line

        for line in lines:
            line = line.rstrip("\n\r")
            if not line.strip():
                continue  # skip blank lines

            try:
                instr_bits = translate(line)  # slot assigned after OUT separation
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1

            if (instr_bits & OUT_OPCODE_MASK) == OUT_OPCODE:
                if out_bits is not None:
                    print("error: more than one OUT instruction", file=sys.stderr)
                    return 1
                out_bits     = instr_bits
                out_line_src = line
            else:
                regular.append((line, instr_bits))

        if len(regular) >= OUT_SLOT:
            print(
                f"error: {len(regular)} instructions leave no room for OUT at slot {OUT_SLOT}",
                file=sys.stderr,
            )
            return 1

        # Second pass: print + send in final slot order
        for slot, (src_line, instr_bits) in enumerate(regular):
            print(f"line {slot}: {src_line} -> {bin_str(instr_bits)} 0x{instr_bits:04x}")
            programmer.send(slot, instr_bits)

        for slot in range(len(regular), OUT_SLOT):
            print(f"line {slot}: <NOP padding> -> {bin_str(NOP_BITS)} 0x{NOP_BITS:04x}")
            programmer.send(slot, NOP_BITS)

        if out_bits is not None:
            print(f"line {OUT_SLOT}: {out_line_src} -> {bin_str(out_bits)} 0x{out_bits:04x}")
            programmer.send(OUT_SLOT, out_bits)
        else:
            print(f"line {OUT_SLOT}: <NOP padding (no OUT)> -> {bin_str(NOP_BITS)} 0x{NOP_BITS:04x}")
            programmer.send(OUT_SLOT, NOP_BITS)


    finally:
        programmer.close()

    return 0

# class App(customtkinter.CTk):
#     def __init__(self):
#         super().__init__()

#         self.title("my app")
#         self.geometry("400x150")
#         self.grid_columnconfigure((0, 1), weight=1)

#         self.button = customtkinter.CTkButton(self, text="my button", command=self.button_callback)
#         self.button.grid(row=0, column=0, padx=20, pady=20, sticky="ew", columnspan=2)
#         self.checkbox_1 = customtkinter.CTkCheckBox(self, text="checkbox 1")
#         self.checkbox_1.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
#         self.checkbox_2 = customtkinter.CTkCheckBox(self, text="checkbox 2")
#         self.checkbox_2.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="w")
        
#     def button_callback(self):
#         print("button pressed")

# def main():
#     app = App()
#     app.mainloop()



if __name__ == "__main__":
    sys.exit(main())
