library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package vga_pkg is

    type vga_config_t is record
        h_visible_area  : integer;
        h_front_porch   : integer;
        h_sync_pulse    : integer;
        h_back_porch    : integer;
        h_whole_line    : integer;
        v_visible_area  : integer;
        v_front_porch   : integer;
        v_sync_pulse    : integer;
        v_back_porch    : integer;
        v_whole_frame   : integer;
    end record;

    -- clock frequency of 25.175 MHz for 640x480 @60Hz
    constant VGA_640x480 : vga_config_t := (
        h_visible_area  => 640,
        h_front_porch   => 16,
        h_sync_pulse    => 96,
        h_back_porch    => 48,
        h_whole_line    => 800,
        v_visible_area  => 480,
        v_front_porch   => 10,
        v_sync_pulse    => 2,
        v_back_porch    => 33,
        v_whole_frame   => 525
    );

    constant VGA_PULSE_ACTIVE : std_ulogic := '0';
    constant VGA_PULSE_INACTIVE : std_ulogic := '1';

    subtype pixel_x_t is unsigned (natural(ceil(log2(real(VGA_640x480.h_whole_line - 1)))) downto 0);
    subtype pixel_y_t is unsigned (natural(ceil(log2(real(VGA_640x480.v_whole_frame - 1)))) downto 0);
end package;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package Global is
    -- global types, constants, and function declarations go here

    -------------------------------------- General Constants --------------------------------------
    constant cClkFrequency : natural := 5035E4; -- 50,35 MHz

    ------------------------------------------- Opcodes -------------------------------------------
    subtype aOpcode is std_ulogic_vector(4 downto 0);
    constant cOpNop     : aOpcode := "00000"; -- No Operation
    constant cOpSet     : aOpcode := "00001"; -- Set Register to Immediate
    constant cOpMov     : aOpcode := "00010"; -- Move Register to Register
    constant cOpAdd     : aOpcode := "00011"; -- Add two registers
    constant cOpSub     : aOpcode := "00100"; -- Subtract two registers
    constant cOpSl      : aOpcode := "00101"; -- Shift Left
    constant cOpSr      : aOpcode := "00110"; -- Shift Right
    constant cOpAnd     : aOpcode := "00111"; -- Bitwise AND
    constant cOpNand    : aOpcode := "01000"; -- Bitwise NAND
    constant cOpOr      : aOpcode := "01001"; -- Bitwise OR
    constant cOpNor     : aOpcode := "01010"; -- Bitwise NOR
    constant cOpXor     : aOpcode := "01011"; -- Bitwise XOR
    constant cOpOut     : aOpcode := "01100"; -- Output Register to ODR
    constant cOpSin     : aOpcode := "01101"; -- Sine of Time Register to Output Data Register
    constant cOpRand    : aOpcode := "01110"; -- Output random number to RD
    constant cOpRamp    : aOpcode := "01111"; -- Value from Ramp LUT
    constant cOpSaw     : aOpcode := "10000"; -- Value from Sawtooth LUT
    constant cOpComp    : aOpcode := "10001"; -- Compare two registers and set condition flags

    ----------------------------------------- Registers -------------------------------------------
    subtype aInstrRegIdx is std_ulogic_vector(2 downto 0); -- 3 bits to index 8 registers 
    constant cReg0      : aInstrRegIdx := "000";
    constant cReg1      : aInstrRegIdx := "001";
    constant cReg2      : aInstrRegIdx := "010";
    constant cReg3      : aInstrRegIdx := "011";
    constant cReg4      : aInstrRegIdx := "100";
    constant cReg5      : aInstrRegIdx := "101";
    constant cReg6      : aInstrRegIdx := "110";
    constant cReg7      : aInstrRegIdx := "111";

    ---------- Constants for special registers ----------
    constant cRegX      : aInstrRegIdx := "100"; -- Dekapixel X coordinate
    constant cRegY      : aInstrRegIdx := "101"; -- Dekapixel Y coordinate
    constant cRegT      : aInstrRegIdx := "110"; -- Time Register
    constant cRegR      : aInstrRegIdx := "111"; -- Random Number Register
    

    ------------------- Register File -------------------
    subtype aRegister is std_ulogic_vector(5 downto 0); -- 6-bit registers
    type aRegisterFile is array(7 downto 0) of aRegister; -- 8 registers total (including special registers)
    subtype aRegFileIdx is integer range 0 to 7; -- index for register file

    ----------- Indexes for special registers -----------
    constant cIdxRegX   : natural := 4; -- Dekapixel X coordinate
    constant cIdxRegY   : natural := 5; -- Dekapixel Y coordinate
    constant cIdxRegT   : natural := 6; -- Time Register
    constant cIdxRegR   : natural := 7; -- Random Number Register

    -------------------------------------------- Alu  ---------------------------------------------
    subtype ALU_Word is std_ulogic_vector(5 downto 0);

    ----------------------------------------- Conditions ------------------------------------------
    subtype aCond is std_ulogic_vector(1 downto 0);
    constant cAlways    : aCond := "11";
    constant cEqual     : aCond := "00";
    constant cGreater   : aCond := "01";
    constant cLess      : aCond := "10";

    ------------------------------------- Instruction Memory --------------------------------------
    subtype aInstrAddr is std_ulogic_vector(4 downto 0);
    subtype aInstruction is std_ulogic_vector(15 downto 0);
    constant cNumInstr  : integer := 20;    
    type aInstruction_mem is array (cNumInstr - 1 downto 0) of aInstruction;
    
    --------- Instruction Memory initial state ----------
    constant cInstrMemInitState : aInstruction_mem := (
        0 => (cOpMov & cReg0 & cRegR & ("000") & cAlways),
        --1 => (cOpRamp & cReg1 & cRegY & ("000") & cAlways),
        --2 => (cOpComp & cReg0 & cReg1 & ("000") & cAlways),
        --3 => (cOpSin & cReg0 & cReg0 & ("000") & cLess),
        --4 => (cOpSin & cReg1 & cReg1 & ("000") & cLess),
        --3 => (cOpXor & cReg0 & cReg1 & ("000") & cGreater),
        19 => (cOpOut & cReg0 & "000000" & cAlways),
        others => (others => '0') 
    );
    
    ------------------------------------------ Immediate ------------------------------------------
    subtype aImmediate is std_ulogic_vector(5 downto 0);

    ----------------------------------------- Output Data -----------------------------------------
    subtype aPixelColor is std_ulogic_vector(5 downto 0); 

    ---------------------------------------- Time Refister ----------------------------------------
    constant cFrameCount: natural := 5;

    ----------------------------------------- Programming -----------------------------------------
    constant cBaudRate  : natural := 9600;
    constant cBaudPeriod: time := (1 sec) / cBaudRate;
    constant cDataBits  : natural := 8;
    constant cDataBytes : natural := 3;
    subtype aUartData is std_ulogic_vector(cDataBits - 1 downto 0);
    subtype aSPIData is std_ulogic_vector(cDataBits - 1 downto 0);

    --------------------------------------------- LUT ---------------------------------------------
    -- Matlab:
    -- 0     6    12    18    24    30    35    40    45    49    53    56    59    61    62    63
    type aSineLUT is array(0 to 15) of std_ulogic_vector(5 downto 0);
    constant cSineLUT : aSineLUT := (
         0 => std_ulogic_vector(to_unsigned(0, 6)),
         1 => std_ulogic_vector(to_unsigned(6, 6)),
         2 => std_ulogic_vector(to_unsigned(12, 6)),
         3 => std_ulogic_vector(to_unsigned(18, 6)),
         4 => std_ulogic_vector(to_unsigned(24, 6)),
         5 => std_ulogic_vector(to_unsigned(30, 6)),
         6 => std_ulogic_vector(to_unsigned(35, 6)),
         7 => std_ulogic_vector(to_unsigned(40, 6)),
         8 => std_ulogic_vector(to_unsigned(45, 6)),
         9 => std_ulogic_vector(to_unsigned(49, 6)),
        10 => std_ulogic_vector(to_unsigned(53, 6)),
        11 => std_ulogic_vector(to_unsigned(56, 6)),
        12 => std_ulogic_vector(to_unsigned(59, 6)),
        13 => std_ulogic_vector(to_unsigned(61, 6)),
        14 => std_ulogic_vector(to_unsigned(62, 6)),
        15 => std_ulogic_vector(to_unsigned(63, 6))
    );
    
    type aRampLUT is array(0 to 15) of std_ulogic_vector(5 downto 0);
    constant cRampLUT : aRampLUT := (
         0 => std_ulogic_vector(to_unsigned(0, 6)),
         1 => std_ulogic_vector(to_unsigned(4, 6)),
         2 => std_ulogic_vector(to_unsigned(8, 6)),
         3 => std_ulogic_vector(to_unsigned(12, 6)),
         4 => std_ulogic_vector(to_unsigned(16, 6)),
         5 => std_ulogic_vector(to_unsigned(20, 6)),
         6 => std_ulogic_vector(to_unsigned(24, 6)),
         7 => std_ulogic_vector(to_unsigned(28, 6)),
         8 => std_ulogic_vector(to_unsigned(32, 6)),
         9 => std_ulogic_vector(to_unsigned(36, 6)),
        10 => std_ulogic_vector(to_unsigned(40, 6)),
        11 => std_ulogic_vector(to_unsigned(44, 6)),
        12 => std_ulogic_vector(to_unsigned(48, 6)),
        13 => std_ulogic_vector(to_unsigned(52, 6)),
        14 => std_ulogic_vector(to_unsigned(56, 6)),
        15 => std_ulogic_vector(to_unsigned(60, 6))
    );

    ------------------------------------------ Rand Func ------------------------------------------
    function lfsrand(reg : in std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
end Global;


Package body Global is

    function lfsrand(reg : in std_ulogic_vector(5 downto 0)) 
    return std_ulogic_vector is
    begin
        return reg(0) & (reg(5) xor reg(0)) & reg(4 downto 1);
    end function;

end Global;
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

use work.Global.all;

entity UartRx is
    generic (
        gClkFrequency : natural := cClkFrequency;
        gBaudrate : natural := cBaudRate;
        gDataBits : natural := cDataBits
    );
    port (
        iClk : in std_ulogic;
        inRstAsync : in std_ulogic;
        iRx : in std_ulogic;
        oData : out aUartData;
        oValid : out std_ulogic
    );
end entity UartRx;

architecture Rtl of UartRx is

    type aState is (Idle, Start, Data, Stop);

    constant cClocksPerBaud : natural := gClkFrequency / gBaudrate;
    constant cBaudStrobeBits : natural := natural(ceil(log2(real(cClocksPerBaud))));

    type aRegSet is record
        State : aState;
        DataBitCount : natural range 0 to gDataBits - 1;
        BaudStrobe : std_ulogic;
        BaudStrobeCounter : unsigned(cBaudStrobeBits - 1 downto 0);
        Data : aUartData;
        Valid : std_ulogic;
    end record;

    constant cInitValR : aRegSet := (
        State => Idle,
        DataBitCount => 0,
        BaudStrobe => '0',
        BaudStrobeCounter => to_unsigned(0, cBaudStrobeBits),
        Data => (others => '0'),
        Valid => '0'
    );

    signal R, NxR : aRegSet;

begin

    process (iClk, inRstAsync)
    begin
        if inRstAsync = not('1') then
            R <= cInitValR;
        elsif rising_edge(iClk) then
            R <= NxR;
        end if;
    end process;

    process (all)
    begin

        NxR <= R;
        NxR.Valid <= '0';

        -- Strobe generator
        NxR.BaudStrobeCounter <= R.BaudStrobeCounter + 1;
        NxR.BaudStrobe <= '0';
        if R.BaudStrobeCounter = cClocksPerBaud - 1 then
            NxR.BaudStrobeCounter <= to_unsigned(0, cBaudStrobeBits);
            NxR.BaudStrobe <= '1';
        end if;

        -- state machine for uart recieve sequence
        case R.State is
            when Idle =>
                if iRx = '0' then
                    NxR.BaudStrobeCounter <= to_unsigned(cClocksPerBaud / 2, cBaudStrobeBits);
                    NxR.State <= Start;
                    NxR.BaudStrobe <= '0';
                end if;

            when Start =>
                if R.BaudStrobe = '1' then
                    NxR.State <= Data;
                    NxR.DataBitCount <= 0;
                end if;

            when Data =>
                if R.BaudStrobe = '1' then
                    NxR.Data(R.DataBitCount) <= iRx;
                    if R.DataBitCount = gDataBits - 1 then
                        NxR.State <= Stop;
                    else
                        NxR.DataBitCount <= R.DataBitCount + 1;
                    end if;
                end if;

            when Stop =>
                if R.BaudStrobe = '1' then
                    if iRx = '1' then -- stop bit
                        NxR.Valid <= '1';
                    end if;
                    NxR.State <= Idle;
                end if;

            when others => null;

        end case;

    end process;

    oData <= R.Data;
    oValid <= R.Valid;

end architecture;
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

use work.Global.all;

entity UartInterpreter is
    generic (
        gClkFrequency : natural := cClkFrequency;
        gDataBits : natural := cDataBits;
        gDataBytes : natural := cDataBytes
    );
    port (
        iClk : in std_ulogic;
        inRstAsync : in std_ulogic;
        iData : in aUartData;
        iValid : in std_ulogic;
        oWE : out std_ulogic;
        oAddr : out aInstrAddr;
        oInstr : out aInstruction;
        oRun : out std_ulogic
    );
end entity UartInterpreter;

architecture Rtl of UartInterpreter is

    type aState is (Command, InstructionHigh, InstructionLow, Output);
    type aByte is (CommandByte, InstructionHighByte, InstructionLowByte);
    type aInputData is array(aByte range <>) of std_ulogic_vector;

    type aRegSet is record
        State : aState;
        Data : aInputData(CommandByte to InstructionLowByte)(gDataBits - 1 downto 0);
        WE : std_ulogic;
        Instr : aInstruction;
        Addr : aInstrAddr;
        Run : std_ulogic;
    end record;

    constant cInitValR : aRegSet := (
        State => Command,
        Data => (others => (others => '0')),
        WE => '0',
        Addr => (others => '0'),
        Instr => (others => '0'),
        Run => '1'
    );

    signal R, NxR : aRegSet;

begin

    process (iClk, inRstAsync)
    begin
        if inRstAsync = not('1') then
            R <= cInitValR;
        elsif rising_edge(iClk) then
            R <= NxR;
        end if;
    end process;

    process (all)
    begin

        -- default assignments
        NxR <= R;
        NxR.WE <= '0';

        -- state machine for command iterpreting sequence
        case R.State is
            when Command =>
                if iValid = '1' then
                    NxR.Data(CommandByte) <= iData;
                    if (iData(gDataBits - 1) = '1') then -- Instruction
                        NxR.State <= InstructionHigh;
                    else
                        NxR.State <= Output; -- received a Command
                    end if;
                end if;

            when InstructionHigh =>
                if iValid = '1' then
                    NxR.Data(InstructionHighByte) <= iData;
                    NxR.State <= InstructionLow;
                end if;

            when InstructionLow =>
                if iValid = '1' then
                    NxR.Data(InstructionLowByte) <= iData;
                    NxR.State <= Output;
                end if;

            when Output =>
                if (R.Data(CommandByte)(gDataBits - 1) = '1') then -- Instruction
                    NxR.WE <= '1';
                    NxR.Addr <= R.Data(CommandByte)(4 downto 0);
                    NxR.Instr <= R.Data(InstructionHighByte) & R.Data(InstructionLowByte);
                else -- Command
                    NxR.Run <= not(R.Data(CommandByte)(0));
                end if;
                NxR.State <= Command;

            when others => null;

        end case;

    end process;

    oWE <= R.WE;
    oAddr <= R.Addr;
    oInstr <= R.Instr;
    oRun <= R.Run;

end architecture;
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.Global.all;
use work.vga_pkg.all;

entity PixelCPU is
    port (
        iClk : in std_ulogic;
        inRstAsync : in std_ulogic;

        -- Uart Inputs
        iRx : in std_ulogic;

        -- VGA Outputs
        oHsync : out std_ulogic;
        oVsync : out std_ulogic;
        oVideoOn : out std_ulogic;
        oPixelColor : out aPixelColor
    );
end entity PixelCPU;

architecture rtl of PixelCPU is

    -- UART Signals
    signal sUart_WritePulse, sUart_CpuStart : std_ulogic;
    signal sUart_AdressSelect : aInstrAddr;
    signal sUart_Instr : aInstruction;

    -- UartRx to UartInterpreter
    signal sUart_Data : aUartData;
    signal sUart_Valid : std_ulogic;

    signal sInstrMem : aInstruction_mem;
    signal sVGA_Strobe : std_ulogic;
    signal sVGA_HSync : std_ulogic;
    signal sVGA_VSync : std_ulogic;
    signal sVGA_VideoOn : std_ulogic;
    signal sVGA_PixelX : pixel_x_t;
    signal sVGA_PixelY : pixel_y_t;

    -- Programm Counter:
    signal sCPU_Pc : integer range 0 to cNumInstr - 1;
    signal sCPU_YCounter : unsigned(3 downto 0); -- for mod counting in dekapixel logic
    signal sCPU_Run : std_ulogic;
    signal sCPU_SavedInstr : aInstruction;
    signal sCPU_RegFile : aRegisterFile;
    signal sTIME_Counter : unsigned(5 downto 0); -- for counting frames
    signal sCPU_Cond : aCond;
    signal sCPU_ODR : aPixelColor;
    signal sInstr_Rd : aRegFileIdx; 
    signal sInstr_Rs : aRegFileIdx;
    signal sInstr_Imm : aImmediate;
    signal sInstr_Cond : aCond;
    signal sInstr_Opcode : aOpcode;

begin
    -- due to timing related issues caused by the FSMD creating huge fanouts
    -- the instruction memory is implemented inside a process
    instr_mem : process (iClk, inRstAsync) is
    begin
        if inRstAsync = not('1') then
            sInstrMem <= cInstrMemInitState;
        elsif rising_edge(iClk) then
            if sUart_WritePulse = '1'and (unsigned(sUart_AdressSelect)) < cNumInstr - 1 then
                sInstrMem(to_integer(unsigned(sUart_AdressSelect))) <= sUart_Instr;
            end if;
        end if;
    end process instr_mem;

    -- for the same reason the pc logic lives inside this process
    program_counter : process (iClk, inRstAsync) is
    begin
        if inRstAsync = not('1') then
            sCPU_Pc <= 0;
        elsif rising_edge(iClk) then
            if sCPU_RUN = '1' then
                if sCPU_Pc = cNumInstr - 1 then
                    sCPU_Pc <= 0;
                else
                    sCPU_Pc <= sCPU_Pc + 1;
                end if;
            else
                sCPU_Pc <= 0;
            end if;
        end if;
    end process program_counter;

    -- same goes for the VGA signal generation logic
    vga : process (iClk, inRstAsync) is
    begin
        if inRstAsync = not('1') then
            sVGA_Strobe <= '0';
            sVGA_HSync <= VGA_PULSE_INACTIVE;
            sVGA_VSync <= VGA_PULSE_INACTIVE;
            sVGA_VideoOn <= '0';
            sVGA_PixelX <= (others => '0');
            sVGA_PixelY <= (others => '0');
        elsif rising_edge(iClk) then

            -- =================================================================
            -- VGA Signal Generation Logic
            -- ---------------------------
            -- VGA_Strobe 
            --      is a singal that halfs the clock frequency for the VGA 
            --      signal generation, because the VGA timing  requirements are 
            --      half the frequency of the system clock
            -- VGA_PixelX, VGA_PixelY
            --      are counters that count the current pixel position, and are
            --      used for generating the sync pulses and the video on signal
            -- HSYNC, VSYNC
            --      are generated based on the current pixel position and the
            --      VGA timing requirements.
            -- VideoOn
            --      is used for blanking the screen outside of the visible area
            -- =================================================================
            sVGA_Strobe <= not sVGA_Strobe;

            sVGA_HSync <= VGA_PULSE_INACTIVE;
            sVGA_VSync <= VGA_PULSE_INACTIVE;

            if sVGA_Strobe = '1' then
                -- Counter logic
                
                if sVGA_PixelX = VGA_640x480.h_whole_line - 1 then
                    sVGA_PixelX <= (others => '0');

                    if sVGA_PixelY = VGA_640x480.v_whole_frame - 1 then
                        sVGA_PixelY <= (others => '0');
                    else
                        sVGA_PixelY <= sVGA_PixelY + 1;
                    end if;
                else
                    sVGA_PixelX <= sVGA_PixelX + 1;
                end if;
            end if;

            -- =================================================================
            -- SYNC Pulse Generation Logic
            -- =================================================================
            if sVGA_PixelX >= VGA_640x480.h_visible_area + VGA_640x480.h_front_porch and
                sVGA_PixelX < VGA_640x480.h_whole_line - VGA_640x480.h_back_porch then
                sVGA_HSync <= VGA_PULSE_ACTIVE;
            end if;

            if sVGA_PixelY >= VGA_640x480.v_visible_area + VGA_640x480.v_front_porch and
                sVGA_PixelY < VGA_640x480.v_whole_frame - VGA_640x480.v_back_porch then
                sVGA_VSync <= VGA_PULSE_ACTIVE;
            end if;

            -- =================================================================
            -- VIDEO ON LOGIC
            -- --------------
            -- Checks if the current pixel position is within the visible area.
            -- =================================================================
            if sVGA_PixelX < VGA_640x480.h_visible_area
                and sVGA_PixelY < VGA_640x480.v_visible_area then
                sVGA_VideoOn <= '1';
            else
                sVGA_VideoOn <= '0';
            end if;

        end if;
    end process vga;

    reg : process (iClk, inRstAsync) is
    begin
        if inRstAsync = not('1') then
            sCPU_YCounter <= (others => '0');
            sCPU_Run <= '0';
            sCPU_SavedInstr <= (others => '0');
            sCPU_RegFile <= (others => (others => '0'));
            sCPU_Cond <= cAlways;
            sTIME_Counter <= (others => '0');
            sCPU_ODR <= (others => '0');
            sInstr_Rd <= 0;
            sInstr_Rs <= 0;
            sInstr_Imm <= (others => '0');
            sInstr_Cond <= cAlways;
            sInstr_Opcode <= (others => '0');
        elsif rising_edge(iClk) then

            sCPU_YCounter <= sCPU_YCounter;
            sCPU_Run <= sCPU_Run;
            sCPU_SavedInstr <= sCPU_SavedInstr;
            sCPU_RegFile <= sCPU_RegFile;
            sCPU_Cond <= sCPU_Cond;
            sTIME_Counter <= sTIME_Counter;
            sCPU_ODR <= sCPU_ODR;
            sInstr_Rd <= sInstr_Rd;
            sInstr_Rs <= sInstr_Rs;
            sInstr_Imm <= sInstr_Imm;
            sInstr_Cond <= sInstr_Cond;
            sInstr_Opcode <= sInstr_Opcode;

            if sVGA_PixelX >= (VGA_640x480.h_whole_line - 11)
                or sVGA_PixelX < VGA_640x480.h_visible_area then
                sCPU_Run <= '1';
            else
                sCPU_Run <= '0';
            end if;

            -- =================================================================
            -- Instruction Execution Logic (hell yeah - the ALU)
            -- ---------------------------
            -- Here the instructions are excecuted in one clock cycle based on 
            -- the opcode. 
            -- =================================================================
            if (sInstr_Cond = cAlways or sCPU_Cond = sInstr_Cond) then
                case sInstr_Opcode is
                    when cOpSet =>
                        sCPU_RegFile(sInstr_Rd) <= sInstr_Imm;
                    when cOpMov =>
                        sCPU_RegFile(sInstr_Rd) <= sCPU_RegFile(sInstr_Rs);
                    when cOpAdd =>
                        sCPU_RegFile(sInstr_Rd) <= std_ulogic_vector(unsigned(sCPU_RegFile(sInstr_Rd)) + unsigned(sCPU_RegFile(sInstr_Rs)));
                    when cOpSub =>
                        sCPU_RegFile(sInstr_Rd) <= std_ulogic_vector(unsigned(sCPU_RegFile(sInstr_Rd)) - unsigned(sCPU_RegFile(sInstr_Rs)));
                    when cOpSl =>
                        sCPU_RegFile(sInstr_Rd) <= std_ulogic_vector(shift_left(unsigned(sCPU_RegFile(sInstr_Rd)), to_integer(unsigned(sInstr_Imm))));
                    when cOpSr =>
                        sCPU_RegFile(sInstr_Rd) <= std_ulogic_vector(shift_right(unsigned(sCPU_RegFile(sInstr_Rd)), to_integer(unsigned(sInstr_Imm))));
                    when cOpAnd =>
                        sCPU_RegFile(sInstr_Rd) <= sCPU_RegFile(sInstr_Rd) and sCPU_RegFile(sInstr_Rs);
                    when cOpNand =>
                        sCPU_RegFile(sInstr_Rd) <= not (sCPU_RegFile(sInstr_Rd) and sCPU_RegFile(sInstr_Rs));
                    when cOpOr =>
                        sCPU_RegFile(sInstr_Rd) <= sCPU_RegFile(sInstr_Rd) or sCPU_RegFile(sInstr_Rs);
                    when cOpNor =>
                        sCPU_RegFile(sInstr_Rd) <= not (sCPU_RegFile(sInstr_Rd) or sCPU_RegFile(sInstr_Rs));
                    when cOpXor =>
                        sCPU_RegFile(sInstr_Rd) <= sCPU_RegFile(sInstr_Rd) xor sCPU_RegFile(sInstr_Rs);
                    when cOpOut =>
                        sCPU_ODR <= sCPU_RegFile(sInstr_Rd);
                    when cOpSin =>
                        if sCPU_RegFile(sInstr_Rs)(4) = '0' then
                            sCPU_RegFile(sInstr_Rd) <= cSineLUT(to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        else
                            sCPU_RegFile(sInstr_Rd) <= cSineLUT(15 - to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        end if;
                    when cOpRamp =>
                        if unsigned(sCPU_RegFile(sInstr_Rs)) < to_unsigned(16, 6) then
                            sCPU_RegFile(sInstr_Rd) <= cRampLUT(to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        elsif unsigned(sCPU_RegFile(sInstr_Rs)) < to_unsigned(32, 6) then
                            sCPU_RegFile(sInstr_Rd) <= cRampLUT(15 - to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        elsif unsigned(sCPU_RegFile(sInstr_Rs)) < to_unsigned(48, 6) then
                            sCPU_RegFile(sInstr_Rd) <= cRampLUT(to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        else
                            sCPU_RegFile(sInstr_Rd) <= cRampLUT(15 - to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                        end if;
                    when cOpSaw =>
                        sCPU_RegFile(sInstr_Rd) <= cRampLUT(to_integer(unsigned(sCPU_RegFile(sInstr_Rs)(3 downto 0))));
                    when cOpComp =>
                        if unsigned(sCPU_RegFile(sInstr_Rd)) = unsigned(sCPU_RegFile(sInstr_Rs)) then
                            sCPU_Cond <= cEqual; -- equal
                        elsif unsigned(sCPU_RegFile(sInstr_Rd)) < unsigned(sCPU_RegFile(sInstr_Rs)) then
                            sCPU_Cond <= cLess; -- less
                        elsif unsigned(sCPU_RegFile(sInstr_Rd)) > unsigned(sCPU_RegFile(sInstr_Rs)) then
                            sCPU_Cond <= cGreater; -- greater
                        else
                            sCPU_Cond <= cAlways; -- always
                        end if;
                    when others => null; -- nop gets implicitly handled
                end case;
            end if;

            -- =================================================================
            -- RUN_CPU Logic
            -- --------------
            -- In here the instructions are excecuted based on the current
            -- count of the program countes The PC counts up each strobe when
            -- the cpu is running, and resets when it reaches the number of 
            -- instructions for a pixel (cNumInstr) or when the cpu is not running. 
            -- 
            -- Also the registers that are used for the dekapixel logic 
            -- (RegFile(4) and RegFile(5)) are generated.
            -- =================================================================
            if sCPU_RUN = '1' then

                -- Increment every 10 pixels
                if sCPU_Pc = cNumInstr - 1 then
                    sCPU_RegFile(cIdxRegX) <= std_ulogic_vector(unsigned(sCPU_RegFile(cIdxRegX)) + 1);
                end if;

            else -- CPU is not running, reset PC and DekapixelX counter
                sCPU_RegFile(cIdxRegX) <= (others => '0');

                -- =============================================================
                -- Y Coordinate mod counting logic (regfile(5) and Y_Counter)
                -- --------------
                -- To get the current dekapixel y coordinate, we need to count 
                -- how many times we reached the end of a dekapixel line. For 
                -- that we use a counter that counts from 0 to 9, and when it
                -- reaches 9, we reset it and increment the dekapixel y coordinate
                -- =============================================================
                if sVGA_PixelX = VGA_640x480.h_whole_line - 20
                    and sVGA_PixelY < VGA_640x480.v_visible_area
                    and sVGA_Strobe = '1' then
                    -- increment Y counter
    

                    -- when Y counter reaches 10, reset it and increment Dekapixel Y counter
                    if sCPU_YCounter = to_unsigned(9, 4) then
                        sCPU_YCounter <= (others => '0');
                        sCPU_RegFile(cIdxRegY) <= std_ulogic_vector(unsigned(sCPU_RegFile(cIdxRegY)) + 1);

                        if sCPU_RegFile(cIdxRegY) = std_ulogic_vector(to_unsigned(47, 6)) then
                            sCPU_RegFile(cIdxRegY) <= (others => '0');
                        end if;
                    else
                        sCPU_YCounter <= sCPU_YCounter + 1;
                    end if;
                end if;
            end if;

            -- =================================================================
            -- Time Register Logic
            -- -------------------
            -- Here the TIME_Counter is compared to the compare registes
            -- when the counter reaches the compare value, it resets and
            -- increments the time register (RegFile(6) == REGT). 
            -- REGT is allowed to overflow.
            -- =================================================================
            if sVGA_PixelX = 0 and sVGA_PixelY = VGA_640x480.v_whole_frame - 1 then
                if sTIME_Counter = to_unsigned(cFrameCount, 6) then
                    sTIME_Counter <= (others => '0');
                    sCPU_RegFile(cIdxRegT) <= std_ulogic_vector(unsigned(sCPU_RegFile(cIdxRegT)) + 1);
                else
                    sTIME_Counter <= sTIME_Counter + 1;
                end if;
            end if;

            -- =================================================================
            -- Rand Register Logic
            -- -------------------
            -- 
            -- =================================================================

            if sCPU_Pc = cNumInstr - 1 then
                if sVGA_PixelX > VGA_640x480.h_visible_area then
                    sCPU_RegFile(cIdxRegR) <= lfsrand(std_ulogic_vector(unsigned(sCPU_RegFile(cIdxRegY)) + 1));
                else
                    sCPU_RegFile(cIdxRegR) <= lfsrand(sCPU_RegFile(cIdxRegR));
                end if;
            end if;

            sCPU_SavedInstr <= sInstrMem(sCPU_Pc);

            sInstr_Rd <= to_integer(unsigned(sCPU_SavedInstr(10 downto 8)));
            sInstr_Rs <= to_integer(unsigned(sCPU_SavedInstr(7 downto 5)));
            sInstr_Imm <= sCPU_SavedInstr(7 downto 2);
            sInstr_Cond <= sCPU_SavedInstr(1 downto 0);
            sInstr_Opcode <= sCPU_SavedInstr(15 downto 11);
        end if;
    end process reg;

    oVideoOn <= sVGA_VideoOn;
    oPixelColor <= sCPU_ODR;
    oVSync <= sVGA_VSync;
    oHSync <= sVGA_HSync;

    UartRx : entity work.UartRx(rtl)
        port map(
            iClk => iClk,
            inRstAsync => inRstAsync,
            iRx => iRx,
            oData => sUart_Data,
            oValid => sUart_Valid
        );

    UartInterpreter_inst : entity work.UartInterpreter(Rtl)
        port map(
            iClk => iClk,
            inRstAsync => inRstAsync,
            iData => sUart_Data,
            iValid => sUart_Valid,
            oWE => sUart_WritePulse,
            oAddr => sUart_AdressSelect,
            oInstr => sUart_Instr,
            oRun => sUart_CpuStart
        );

end architecture rtl;
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

library work;
use work.Global.all;

entity TinyPixelProcessor is
    port (
        iClk        : in std_ulogic;
        inRstAsync  : in std_ulogic;
        iRx         : in std_ulogic;

        oHSync      : out std_ulogic;
        oVSync      : out std_ulogic;
        oVideoOn    : out std_ulogic;
        oPixelColor : out aPixelColor
    );
end entity TinyPixelProcessor;

architecture Rtl of TinyPixelProcessor is
    signal nRstSynced: std_ulogic;
    signal nRstMayMeta : std_ulogic;
    
    signal RxSyncMayMeta : std_ulogic;
    signal RxSync : std_ulogic;

begin
    
    PixelProcessor : entity work.PixelCPU(rtl)
    port map(
        iClk => iClk,
        inRstAsync => nRstSynced,
        iRx => RxSync,
        oHSync => oHSync,
        oVSync => oVSync,
        oVideoOn => oVideoOn,
        oPixelColor => oPixelColor
    );

    process(iClk, inRstAsync) is
    begin
        if inRstAsync = not('1') then
            nRstSynced <= '0';
            nRstMayMeta <= '0';
        elsif falling_edge(iClk) then
            nRstSynced <= nRstMayMeta;
            nRstMayMeta <= '1';
        end if;
    end process;

    process (iClk, nRstSynced) is
    begin
        if nRstSynced = not('1') then
            RxSyncMayMeta <= '1';
            RxSync <= '1';
        elsif falling_edge(iClk) then
            RxSyncMayMeta <= iRx;
            RxSync <= RxSyncMayMeta;
        end if;
    end process;
    
    
end architecture;
-- this file contains the standard chip interface provided by tinytapout
-- CHANGE NOTHING!

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tt_um_pixel_processor is
    port (
        ui_in  : in  std_ulogic_vector(7 downto 0); -- Dedicated inputs
        uo_out : out std_ulogic_vector(7 downto 0); -- Dedicated outputs
        
        uio_in : in  std_ulogic_vector(7 downto 0); -- IOs: Input path
        uio_out: out std_ulogic_vector(7 downto 0); -- IOs: Output path
        uio_oe : out std_ulogic_vector(7 downto 0); -- IOs: Enable path (active high: 0=input, 1=output)
        
        ena    : in  std_ulogic; -- always 1 when the design is powered, so you can ignore it
        clk    : in  std_ulogic; -- clock
        rst_n  : in  std_ulogic -- reset_n - low to reset
    );
end entity tt_um_pixel_processor;

architecture rtl of tt_um_pixel_processor is
    signal sVGAColor : std_ulogic_vector(5 downto 0);
    signal sVSync : std_ulogic;
    signal sHSync : std_ulogic;
begin

PROCESSOR: entity work.TinyPixelProcessor(rtl)
port map(
        iClk        => clk,
        inRstAsync  => rst_n,
        -- SPI Inputs
        iRx         => ui_in(0),
        -- VGA Outputs
        oHsync      => sHSync,
        oVsync      => sVSync,
        oPixelColor => sVGAColor
    );

uo_out(0) <= sVGAColor(5);
uo_out(1) <= sVGAColor(3);
uo_out(2) <= sVGAColor(1);
uo_out(3) <= sVSync;
uo_out(4) <= sVGAColor(4);
uo_out(5) <= sVGAColor(2);
uo_out(6) <= sVGAColor(0);
uo_out(7) <= sHSync;

uio_out <= (others => '0');
uio_oe  <= (others => '0');
end architecture rtl;
