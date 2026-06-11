import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer

import sys
import os
from pathlib import Path

# flash_lib.py liegt in diesem Ordner
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'flash'))
from flash_lib import translate, INSTR_MAP, MAX_LINES, POS_OPCODE

PROGRAMFOLDER = Path(__file__).resolve().parent / "TestPrograms"

BAUD = 9600
BIT_TIME_NS = int(1e9 / BAUD)

OUT_DIR = Path(__file__).resolve().parent / "cocoPPM"
OUT_DIR.mkdir(exist_ok=True)
OUT_FILE = OUT_DIR / "CocoTB.ppm"

IN_DIR = Path(__file__).resolve().parent / "vunitPPM"

PYTHON_SIM_FILENAME = Path(__file__).resolve().parent / "output_image_sim.ppm"

WIDTH = 640
HEIGHT = 480

H_BACK_PORCH = 48
V_BACK_PORCH = 33
CAPTURE_START_OFFSET = 8

# sends one uart byte to cpu
async def send_uart_byte(dut, value):
    # idle
    dut.ui_in.value = 1
    await Timer(BIT_TIME_NS, unit="ns")

    # start bit
    dut.ui_in.value = 0
    await Timer(BIT_TIME_NS, unit="ns")

    # data bits
    for i in range(8):
        dut.ui_in.value = (value >> i) & 1
        await Timer(BIT_TIME_NS, unit="ns")

    # stop bit
    dut.ui_in.value = 1
    await Timer(BIT_TIME_NS, unit="ns")


# sends uart instruction via uart
async def send_uart_instr(dut, addr, instr):
    await send_uart_byte(dut, 0x80 | (addr & 0x1F))
    await send_uart_byte(dut, (instr >> 8) & 0xFF)
    await send_uart_byte(dut, instr & 0xFF)

# sends complete program via uart
async def send_sim_program(dut, program):
    for addr, instr in enumerate(program[:NUM_INSTR]):
        await send_uart_instr(dut, addr, instr)

# creates a ppm file with the name "filename"
async def CreatePPMFile(dut, filename):
    # Sync to end of vsync pulse
    await wait_vsync_rising(dut)
    dut._log.info("vsync rising detected")

    # Skip vertical back porch
    for _ in range(V_BACK_PORCH - 1):
        await wait_hsync_rising(dut)

    dut._log.info("Active frame should start now")

    with open(filename, "wb") as f:
        f.write(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode())

        for _ in range(HEIGHT):
            await wait_hsync_rising(dut)

            for _ in range(H_BACK_PORCH - 1):
                await wait_pixel_tick(dut)

            for _ in range(WIDTH):
                await wait_pixel_tick(dut)

                pix = pixel6(dut)
                r, g, b = pixel6_to_rgb888(pix)
                f.write(bytes([r, g, b]))
    dut._log.info(f"PPM file written: {filename}")

# checks if both files are exactly the same
def CheckPPMFiles(filename1, filename2):
    with open(filename1, "rb") as Coco:
        file1 = Coco.read()
    with open(filename2, "rb") as VUnit:
        file2 = VUnit.read()

    assert file1 == file2, f"PPM files not equal: {filename1} != {filename2}"





# returns current hsync value
def hsync(dut) -> int:
    return (int(dut.uo_out.value) >> 7) & 1

# returns current vsync value
def vsync(dut) -> int:
    return (int(dut.uo_out.value) >> 3) & 1

# Internal map of outputs in vhdl
# uo_out(0) <= sVGAColor(5);
# uo_out(1) <= sVGAColor(3);
# uo_out(2) <= sVGAColor(1);
# uo_out(3) <= sVSync;
# uo_out(4) <= sVGAColor(4);
# uo_out(5) <= sVGAColor(2);
# uo_out(6) <= sVGAColor(0);
# uo_out(7) <= sHSync;

# returns the current 6 bit pixel color value
def pixel6(dut) -> int:
    v = int(dut.uo_out.value)
    return (
        ((v >> 0) & 1) << 5 |
        ((v >> 4) & 1) << 4 |
        ((v >> 1) & 1) << 3 |
        ((v >> 5) & 1) << 2 |
        ((v >> 2) & 1) << 1 |
        ((v >> 6) & 1)
    )

# Converts 6-bit RGB (2 bits per channel) to RGB888
def pixel6_to_rgb888(pixel_color: int) -> tuple[int, int, int]:
    red   = ((pixel_color >> 4) & 0b11) * 85
    green = ((pixel_color >> 2) & 0b11) * 85
    blue  = (pixel_color & 0b11) * 85
    return red, green, blue

# wait for 2 CLK cycles
async def wait_pixel_tick(dut):
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

# waits until rising edge of hsync
async def wait_hsync_rising(dut):
    prev = hsync(dut)
    while True:
        await RisingEdge(dut.clk)
        cur = hsync(dut)
        if prev == 0 and cur == 1:
            return
        prev = cur

# waits until rising edge of vsync
async def wait_vsync_rising(dut):
    prev = vsync(dut)
    while True:
        await RisingEdge(dut.clk)
        cur = vsync(dut)
        if prev == 0 and cur == 1:
            return
        prev = cur

def ReadInputFile(dut, sourcePath) -> list[tuple[str, int]]:
    
    
    with open(sourcePath, "r") as f:
        lines = f.readlines()

    NOP_BITS = INSTR_MAP["NOP"].opcode << POS_OPCODE
    OUT_SLOT = MAX_LINES
    OUT_BITS = translate("OUT R0")

    OUT_OPCODE_MASK = 0b11111 << POS_OPCODE
    OUT_OPCODE = INSTR_MAP["OUT"].opcode << POS_OPCODE

    regular = []


    for raw_line in lines:
        line = raw_line.rstrip("\n\r")

        if not line.strip():
            continue


        try:
            instr_bits = translate(line)
        except ValueError as exc:
            raise AssertionError(str(exc))

        if ((instr_bits & OUT_OPCODE_MASK) == OUT_OPCODE):
            dut._log.info("source OUT ignored")
            continue

        regular.append((line, instr_bits))

    if len(regular) >= OUT_SLOT:
        raise AssertionError(
            f"{len(regular)} instructions leave no room for OUT at slot {OUT_SLOT}"
        )

    while len(regular) < OUT_SLOT:
        regular.append(("<NOP padding>", NOP_BITS))

    regular.append(("OUT R0", OUT_BITS))
    
    return regular

async def ResetDUT(dut):
    # Reset
    dut.ui_in.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    programs = sorted(PROGRAMFOLDER.glob("*.txt"))
    assert programs, f"No test programs found in {PROGRAMFOLDER}"

    for filePath in programs:
        dut._log.info(f"Loading program: {filePath.name}")

        await ResetDUT(dut)
        dut._log.info(
            f"after reset: hsync={hsync(dut)} vsync={vsync(dut)} pixel={pixel6(dut)}"
        )

        regular = ReadInputFile(dut, filePath)

        # send instruction via uart
        for slot, (src_line, instr_bits) in enumerate(regular):
            dut._log.info(
                f"[{slot:02d}] {src_line:<25} -> 0x{instr_bits:04x}"
            )
            await send_uart_instr(dut, slot, instr_bits)

        out_file = OUT_DIR / f"{filePath.stem}.ppm"
        await CreatePPMFile(dut, out_file)

        vunit_file = IN_DIR / f"{filePath.stem}.ppm"
        assert vunit_file.exists(), f"VUnit PPM file missing: {vunit_file}"

        CheckPPMFiles(out_file, vunit_file)

        dut._log.info(f"PPM compare OK: {out_file.name}")