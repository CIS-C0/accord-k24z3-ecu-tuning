// Emulates the dashpot function 0x502F4 call by call with the SH-2 code and constants of the loaded ROM. RAM is kept
// between calls (one emulator per scenario), so the term 0xFFFF3CF8 and the flags evolve like on the car.
// Each call: set the inputs, tick the timers 0xFFFF7668 / 0xFFFF766A (their real tick rate is NOT known: one tick
// every <tick> calls), run 0x502F4 until it returns, log the term 3CF8 and the timers.
// Inputs (meaning partly assumed, see KNOWLEDGE.md): trigger variable 0xFFFF3CBA (copy of 0xFFFF3E08, probably
// engine speed) falls from <hi> to <lo> by <drop> per call; 0xFFFF3158 = -<drop> (speed change, negative when
// dropping); coolant 0xFFFF2A1A (x10 assumed); 0xFFFF784C = 1000 (>= 500 enables); 0xFFFF3DD8 = 1, 0xFFFF3DDE = 0
// (-> arm threshold 0xFFFF3DE4 = clamp(3DDE, 1000, 32767) = 1000); 0xFFFF3DDA (rate threshold) = 0; flags
// 0xFFFF3CB0/3CB2/3CB3/3403 = 0.
// Usage (headless postScript): EmuDashpot.java <label>
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuDashpot extends GhidraScript {

    private static final long START = 0x502F4L;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long BASE = 0xFFFF3CB0L;    // GBR of 0x502F4
    private static final long TERM = BASE + 0x48;    // 0xFFFF3CF8
    private static final long TRIG = BASE + 0x0A;    // 0xFFFF3CBA
    private static final long LOCK = 0xFFFF7668L;
    private static final long DUR = 0xFFFF766AL;
    private static final long RATE = 0xFFFF3158L;
    private static final long ECT = 0xFFFF2A1AL;

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

    private void Scenario(String label, String name, int hi, int lo, int drop, int ect, int tick, int calls)
            throws Exception {
        emu = new EmulatorHelper(currentProgram);
        try {
            emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                public boolean unknownAddress(Address address, boolean write) { return false; }
            });
            emu.setBreakpoint(toAddr(RETURN));
            W16(0xFFFF784CL, 1000);
            W8(0xFFFF3DD8L, 1);
            W16(BASE + 0x12E, 0);
            W16(BASE + 0x12A, 0);
            println(String.format("--- %s | %s: trigger %d -> %d by %d/call from call 20, ect %d, timer tick every %d calls",
                    label, name, hi, lo, drop, ect, tick));
            int trig = hi;
            int last = -1;
            int firstOn = -1, lastOn = -1, peak = 0;
            for (int c = 0; c < calls; c++) {
                if (c % tick == 0) {
                    int t = R16(LOCK); if (t > 0) W16(LOCK, t - 1);
                    t = R16(DUR); if (t > 0) W16(DUR, t - 1);
                }
                int rate = 0;
                if (c >= 20 && trig > lo) { trig = Math.max(lo, trig - drop); rate = -drop; }
                W16(TRIG, trig);
                W16(RATE, rate);
                W16(ECT, ect);
                emu.writeRegister("r15", 0xFFFFBF00L);
                emu.writeRegister("pr", RETURN);
                emu.writeRegister(emu.getPCRegister(), START);
                emu.run(monitor);
                long pc = emu.getExecutionAddress().getOffset();
                if (pc != RETURN) {
                    println(String.format("call %d: STOPPED AT 0x%X (%s)", c, pc, emu.getLastError()));
                    return;
                }
                int term = R16(TERM);
                if (term > 0) { if (firstOn < 0) firstOn = c; lastOn = c; peak = Math.max(peak, term); }
                if (term != last || c % 50 == 0) {
                    println(String.format("%s | %s | call %4d trig %5d rate %5d  term(3CF8) %5d  lock %4d  dur %4d  thr(3DE4) %5d  flag %d",
                            label, name, c, trig, rate, term, R16(LOCK), R16(DUR), R16(BASE + 0x134),
                            emu.readMemory(toAddr(0xFFFF3DE0L), 1)[0]));
                    last = term;
                }
            }
            println(String.format("%s | %s | SUMMARY: term > 0 from call %d to %d (%d calls), peak %d",
                    label, name, firstOn, lastOn, firstOn < 0 ? 0 : lastOn - firstOn + 1, peak));
        } finally {
            emu.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        Scenario(label, "warm fast drop, tick 1", 3000, 800, 100, 850, 1, 600);
        Scenario(label, "warm fast drop, tick 3", 3000, 800, 100, 850, 3, 600);
        Scenario(label, "warm fast drop, tick 8", 3000, 800, 100, 850, 8, 600);
        Scenario(label, "warm slow drop, tick 3", 3000, 800, 10, 850, 3, 800);
        Scenario(label, "cold fast drop, tick 3", 3000, 800, 100, 0, 3, 600);
    }
}
