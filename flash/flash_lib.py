#!/usr/bin/env python3
# Inlcudes
import time
from pathlib import Path
from typing import Optional

import serial
import platform
from dataclasses import dataclass
import serial.tools.list_ports

# Constants
CMD_PROGRAM   = 0x80
CMD_SET       = 0x40
MAX_LINES     = 19
MAX_IMM_VAL   = 63
MAX_REG_SRC   = 7
MAX_REG_DST   = 3
REG_X = 4; REG_Y = 5; REG_T = 6; REG_R = 7
POS_OPCODE = 11; POS_REG_1 = 8; POS_REG_2 = 5; POS_IMM = 2; POS_COND = 0
COND_EQ = 0b00; COND_GT = 0b01; COND_LT = 0b10; COND_ALWAYS = 0b11
BAUD_RATE = 9600
devMode = False

# Data structure for instruction entries
@dataclass(frozen=True)
class InstrEntry:
    name: str; opcode: int; itype: int

# Instruction table mapping instruction names to their opcodes and types
INSTR_TABLE = [
    InstrEntry("NOP",  0b00000, 0),
    InstrEntry("SET",  0b00001, 1),
    InstrEntry("MOV",  0b00010, 3), 
    InstrEntry("ADD",  0b00011, 4),
    InstrEntry("SUB",  0b00100, 4), 
    InstrEntry("SL",   0b00101, 2),
    InstrEntry("SR",   0b00110, 2), 
    InstrEntry("AND",  0b00111, 4),
    InstrEntry("NAND", 0b01000, 4), 
    InstrEntry("OR",   0b01001, 4),
    InstrEntry("NOR",  0b01010, 4), 
    InstrEntry("XOR",  0b01011, 4),
    InstrEntry("SIN",  0b01101, 4),
    InstrEntry("RAMP", 0b01111, 4),
    InstrEntry("SAW",  0b10000, 4),
    InstrEntry("COMP", 0b10001, 5),
    InstrEntry("OUT",  0b01100, 6),
    InstrEntry("FH", 0b10010, 7),
    InstrEntry("HSD", 0b10011, 7),
    InstrEntry("TT", 0b10100, 7), 
    InstrEntry("Credits", 0b10101, 7),
    InstrEntry("FlagP", 0b10110, 7),
    InstrEntry("ESE", 0b10111, 7),
]
INSTR_MAP = {e.name: e for e in INSTR_TABLE}

# Helper functions for serial communication and instruction parsing
def get_serial_ports() -> str:
    ports = serial.tools.list_ports.comports()

    for p in ports:
        if platform.system() == "Windows":
            if "USB" in p.description:
                return p.device
        elif platform.system() == "Linux":
            if "USB" in p.description:
                return p.device
        else:
            raise RuntimeError(f"No serial ports found. Try: check your system's device manager")

def bin_str(value: int) -> str:
    bits = f"{value:016b}"
    return bits[:5] + " " + bits[5:8] + " " + bits[8:14] + " " + bits[14:]

def convert_str_to_int(s: str) -> Optional[int]:
    aliases = {'X': REG_X, 'Y': REG_Y, 'T': REG_T, 'R': REG_R}
    if s and s[0] in aliases:
        return aliases[s[0]]
    
    try:
        return int(s, 10)
    except (ValueError, TypeError):
        return None
    
def read_src_reg(token, line_no):
    if token is None or token[0].upper() != 'R':
        raise ValueError(f"invalid source register at line {line_no}")
    
    val = convert_str_to_int(token[1:])
    if val is None: raise ValueError(f"invalid source register {token} at line {line_no}")
    if val > MAX_REG_SRC: raise ValueError(f"invalid source register R{val} at line {line_no}")
    return val


def read_dst_reg(token, line_no):
    if token is None or token[0].upper() != 'R':
        raise ValueError(f"invalid destination register {token} at line {line_no}")
    
    val = convert_str_to_int(token[1:])
    if val is None: raise ValueError(f"invalid destination register {token} at line {line_no}")
    if not devMode:
        if val > MAX_REG_DST: raise ValueError(f"invalid destination register R{val} at line {line_no}")
    else:
        if val > MAX_REG_SRC: raise ValueError(f"invalid destination register R{val} at line {line_no}")
    return val

def read_imm_val(token, line_no):
    if token is None or token[0] != '#':
        raise ValueError(f"invalid immediate value {token} at line {line_no}")
    
    val = int(token[1:])
    if val > MAX_IMM_VAL: raise ValueError(f"invalid immediate value {val} at line {line_no}")
    return val

def check_conditional(instr):
    if len(instr) >= 2:
        suffix = instr[-2:]
        if suffix == "EQ": return instr[:-2], COND_EQ
        if suffix == "LT": return instr[:-2], COND_LT
        if suffix == "GT": return instr[:-2], COND_GT
    return instr, COND_ALWAYS

def op(idx, operands):
    if idx < len(operands):
        return operands[idx]
    else:
        return None

def translate(line: str, line_no: int = -1) -> int:
    instr_bits = 0

    if line == "##devMode##":
        global devMode
        devMode = True
        return 0

    tokens = line.split()

    if not tokens:
        tokens = ["NOP"]  # Default to NOP for empty lines
    
    if tokens[0].startswith("//"):
        tokens = ["NOP"]  # Treat comment lines as NOPs

    if any(t.startswith("//") for t in tokens[1:]):
        # If there's an inline comment, ignore tokens after the comment
        comment_index = next(i for i, t in enumerate(tokens) if t.startswith("//"))
        tokens = tokens[:comment_index]

    mnemonic_raw = tokens[0]
    operands = tokens[1:]
    mnemonic, cond = check_conditional(mnemonic_raw)

    entry = INSTR_MAP.get(mnemonic)
    if entry is None:
        raise ValueError(f"invalid instruction {mnemonic} at line {line_no}")
    instr_bits |= entry.opcode << POS_OPCODE

    t = entry.itype
    
    if t == 0: pass
    elif t == 1:
        instr_bits |= read_dst_reg(op(0,operands), line_no) << POS_REG_1
        instr_bits |= read_imm_val(op(1,operands), line_no) << POS_IMM
    elif t == 2:
        instr_bits |= read_dst_reg(op(0,operands), line_no) << POS_REG_1
        instr_bits |= read_imm_val(op(1,operands), line_no) << POS_IMM
    elif t == 3:
        instr_bits |= read_dst_reg(op(0,operands), line_no) << POS_REG_1
        instr_bits |= read_src_reg(op(1,operands), line_no) << POS_REG_2
    elif t == 4:
        instr_bits |= read_dst_reg(op(0,operands), line_no) << POS_REG_1
        instr_bits |= read_src_reg(op(1,operands), line_no) << POS_REG_2
    elif t == 5:
        instr_bits |= read_src_reg(op(0,operands), line_no) << POS_REG_1
        instr_bits |= read_src_reg(op(1,operands), line_no) << POS_REG_2
    elif t == 6:
        instr_bits |= read_src_reg(op(0,operands), line_no) << POS_REG_2
    elif t == 7:
        instr_bits |= read_dst_reg(op(0,operands), line_no) << POS_REG_1
    else:
        raise ValueError(f"unknown instruction type {t} at line {line_no}")
    
    instr_bits |= cond << POS_COND
    return instr_bits

class Programmer:
    def __init__(self, port=None, baud=BAUD_RATE):
        self._ser = None; self._port = port; self._baud = baud

    def init(self):
        if self._port is None:
            self._port = get_serial_ports()
        self._ser = serial.Serial(
            port=self._port, baudrate=self._baud,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE, timeout=1.0,
            xonxoff=False, rtscts=False, dsrdtr=False,
        )
        self._ser.dtr = False
        time.sleep(0.1)

    def send(self, line_counter, instr_bits):
        if line_counter > MAX_LINES:
            raise RuntimeError(f"limit of lines at line {line_counter} reached, terminating...")
        high = (instr_bits >> 8) & 0xFF
        low  =  instr_bits       & 0xFF
        self._write(bytes([CMD_PROGRAM | line_counter, high, low]))

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()

    def _write(self, data):
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("serial port not open")
        self._ser.write(data)

    def __enter__(self): self.init(); return self
    def __exit__(self, *_): self.close()