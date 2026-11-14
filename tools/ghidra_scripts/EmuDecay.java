// Emulates the whole function 0x5752A (lift-off decay candidate) cycle by cycle with the SH-2 code and constants of
// the loaded ROM. RAM is kept between cycles (one emulator), so the internal target T (0xFFFF4198) evolves like on
// the car. Each cycle: set the inputs, run 0x5752A until it returns, log T and the output 0xFFFF3DA2.
// Inputs per scenario: request 0xFFFF40B0 (R0 for the first 40 cycles, then 0 = pedal released), speed 0xFFFF2C2C,
// RPM 0xFFFF289C, 0xFFFF2A1A (coolant temp x10 assumed), fuel cut flag 0xFFFF4341.
// Assumptions (not proven, stated in the output): timer 0xFFFF76B6 is decremented once per cycle by the timer task
// (done here before each run); flags not listed are 0; 0xFFFF2BD6 = 1 (skips the 0x8BFA filter block);
// 0xFFFF285E = 0x7FFF and +0x4C/+0x4E (0xFFFF4180/0xFFFF4182) = 0 so the request is not limited.
// Usage (headless postScript): EmuDecay.java <label> [<hexRomAddr>:<decimal16bitValue> ...]
// The optional patches are written into the emulator's copy of the ROM only (to compare stock vs modified).
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuDecay extends GhidraScript {

    private static final long START = 0x5752AL;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long REQUEST = 0xFFFF40B0L;
    private static final long LIMIT = 0xFFFF285EL;
    private static final long SPEED = 0xFFFF2C2CL;
    private static final long RPM = 0xFFFF289CL;
    private static final long ECT = 0xFFFF2A1AL;
    private static final long FUELCUT = 0xFFFF4341L;
    private static final long BASE = 0xFFFF4134L;     // GBR of 0x5752A
    private static final long T = BASE + 0x64;
    private static final long STEP = BASE + 0x60;
    private static final long OUT = 0xFFFF3DA2L;
    private static final long TIMER = 0xFFFF76B6L;

    private EmulatorHelper emu;

    private void W16(long a, int v) throws Exception {
        emu.writeMemory(toAddr(a), new byte[] { (byte) (v >> 8), (byte) v });
    }

    private void W8(long a, int v) throws Exception {
        emu.writeMemory(toAddr(a), new byte[] { (byte) v });
    }

    private int R16(long a) throws Exception {
        byte[] b = emu.readMemory(toAddr(a), 2);
        return (short) (((b[0] & 0xFF) << 8) | (b[1] & 0xFF));
    }

    private void Scenario(String label, String name, int r0, int speed, int rpm, int ect, int fuelCut, int cycles)
            throws Exception {
        emu = new EmulatorHelper(currentProgram);
        try {
            emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                public boolean unknownAddress(Address address, boolean write) { return false; }
            });
            emu.setBreakpoint(toAddr(RETURN));
            String[] args = getScriptArgs();
            for (int i = 1; i < args.length; i++) {
                String[] p = args[i].split(":");
                W16(Long.parseLong(p[0], 16), Integer.parseInt(p[1]));
            }
            W16(LIMIT, 0x7FFF);
            W16(BASE + 0x4C, 0);
            W16(BASE + 0x4E, 0);
            W16(BASE + 0x80, 16660);
            W8(0xFFFF2BD6L, 1);
            println(String.format("--- %s | %s: request %d then 0 at cycle 40, speed %d, rpm %d, ect %d, fuelcut %d",
                    label, name, r0, speed, rpm, ect, fuelCut));
            for (int c = 0; c < cycles; c++) {
                int t = R16(TIMER);
                if (t > 0) W16(TIMER, t - 1);
                W16(REQUEST, c < 40 ? r0 : 0);
                W16(SPEED, speed);
                W16(RPM, rpm);
                W16(ECT, ect);
                W8(FUELCUT, c < 40 ? 0 : fuelCut);
                emu.writeRegister("r15", 0xFFFFBF00L);
                emu.writeRegister("pr", RETURN);
                emu.writeRegister(emu.getPCRegister(), START);
                emu.run(monitor);
                long pc = emu.getExecutionAddress().getOffset();
                if (pc != RETURN) {
                    println(String.format("cycle %d: STOPPED AT 0x%X (%s)", c, pc, emu.getLastError()));
                    return;
                }
                if (c < 3 || (c >= 38 && c < 50) || c % 10 == 0) {
                    println(String.format("%s | %s | cycle %3d req %5d  T %5d  step %4d  out(3DA2) %5d  level66 %5d  level68 %5d",
                            label, name, c, c < 40 ? r0 : 0, R16(T), R16(STEP), R16(OUT), R16(BASE + 0x66),
                            R16(BASE + 0x68)));
                }
            }
        } finally {
            emu.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        Scenario(label, "moving 3000rpm warm", 4000, 60, 3000, 850, 0, 200);
        Scenario(label, "moving 3000rpm warm FUELCUT", 4000, 60, 3000, 850, 1, 60);
        Scenario(label, "stopped 3000rpm warm", 4000, 0, 3000, 850, 0, 200);
        Scenario(label, "moving 6000rpm warm", 8000, 60, 6000, 850, 0, 200);
        Scenario(label, "moving 3000rpm cold", 4000, 60, 3000, 0, 0, 200);
    }
}
