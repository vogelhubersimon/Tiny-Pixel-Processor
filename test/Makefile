# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

SRC_DIR = $(PWD)/../src
WAVES = 0 # do not dump waveforms, github action will fail

ifneq ($(GATES),yes)

# RTL simulation:
SIM = ghdl
TOPLEVEL_LANG = vhdl
SIM_BUILD = sim_build/rtl
VHDL_SOURCES += $(SRC_DIR)/tt_um_pixel_processor.vhdl
TOPLEVEL = tt_um_pixel_processor
EXTRA_ARGS += --std=08

else

# Gate level simulation:
export GL_TEST_MODE = 1
SIM = icarus
TOPLEVEL_LANG = verilog
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

endif

# List test modules to run, separated by commas and without the .py suffix:
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
