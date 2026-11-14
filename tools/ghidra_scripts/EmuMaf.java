// Emulates the MAF airflow function 0x5381C with the SH-2 code and constants of the loaded ROM (one emulator, RAM kept
// between calls). 0x5381C: lookup(0xA75C, MAF A/D 0xFFFF2948) -> 0xFFFF3F88 (instant, GBR 0xFFFF3E30 + 0x158),
// 6-sample history 0xFFFF3F72.. ; when 0xFFFF29C4 == 0: sum / 6 (0x9128C) clamped (0x8B1C) -> 0xFFFF3E4A (+0x1A).
// Sweep: every A/D 0..1023, the function is called 7 times with the same A/D (history full), then
// "SWEEP,<label>,<ad>,<instant 3F88>,<average 3E4A>" is printed. Step test: A/D 300 for 10 calls then 700 for 10 calls,
// the average is printed on every call. Flags: 0xFFFF29C4 = 0, 0xFFFF2C0B = 0, RPM 0xFFFF289C = 2500 (other outputs of
// the function, not used here).
// Usage (headless postScript): EmuMaf.java <label>
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuMaf extends GhidraScript {

    private static final long START = 0x5381CL;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long AD = 0xFFFF2948L;
    private static final long INSTANT = 0xFFFF3F88L;
    private static final long AVERAGE = 0xFFFF3E4AL;

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

    private boolean Call(int ad) throws Exception {
        W16(AD, ad);
        emu.writeRegister("r15", 0xFFFFBF00L);
        emu.writeRegister("pr", RETURN);
        emu.writeRegister(emu.getPCRegister(), START);
        emu.run(monitor);
        long pc = emu.getExecutionAddress().getOffset();
        if (pc != RETURN) {
            println(String.format("A/D %d: STOPPED AT 0x%X (%s)", ad, pc, emu.getLastError()));
            return false;
        }
        return true;
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        emu = new EmulatorHelper(currentProgram);
        try {
            emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                public boolean unknownAddress(Address address, boolean write) { return false; }
            });
            emu.setBreakpoint(toAddr(RETURN));
            W8(0xFFFF29C4L, 0);
            W8(0xFFFF2C0BL, 0);
            W16(0xFFFF289CL, 2500);
            for (int ad = 0; ad <= 1023; ad++) {
                for (int c = 0; c < 7; c++) {
                    if (!Call(ad)) return;
                }
                println(String.format("SWEEP,%s,%d,%d,%d", label, ad, R16(INSTANT), R16(AVERAGE)));
            }
            for (int c = 0; c < 20; c++) {
                int ad = c < 10 ? 300 : 700;
                if (!Call(ad)) return;
                println(String.format("STEP,%s,%d,%d,%d,%d", label, c, ad, R16(INSTANT), R16(AVERAGE)));
            }
            println(label + " DONE");
        } finally {
            emu.dispose();
        }
    }
}
