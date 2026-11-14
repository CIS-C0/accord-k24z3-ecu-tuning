// Emulates the tip-in ramp 0x56F6A call by call with the SH-2 code and constants of the loaded ROM (one emulator per
// scenario, RAM kept between calls). Its output 0xFFFF4178 (base 0xFFFF4134 + 0x44) caps the engine request in
// 0x56830 (request = min(gear limit, 4178)), so the delay it adds = calls until 4178 reaches the new demand.
// Each call: tick the up-counter 0xFFFF7852 (0xFFFF784C + 6; reset to 0 by 0x56F6A when the ramp ends; its real tick
// rate is NOT known: +1 every <tick> calls), set the inputs, run 0x56F6A until it returns, log.
// Inputs (meaning partly assumed, see KNOWLEDGE.md): demand 0xFFFF3CFA steps from <lo> to <hi> at call 20 (pedal
// stab); pedal 0xFFFF2ACE = demand / 2; RPM 0xFFFF289C; speed 0xFFFF2C2C = 50; gear 0xFFFF3F06 (0xFFFF2BD6 = 0);
// 0xFFFF3FBE = 2, 0xFFFF3F0A = 0, 0xFFFF3E2E = 0, 0xFFFF2B1C = 0, 0xFFFF784C = 10000 (time since start, assumed);
// 0xFFFF4162 (base + 0x2E, ramp start value, writer not known) = <lo>.
// Usage (headless postScript): EmuTipIn.java <label> [<hexRomAddr>:<decimal16bitValue> ...]
// The optional patches are written into the emulator's copy of the ROM only (to compare stock vs modified).
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuTipIn extends GhidraScript {

    private static final long START = 0x56F6AL;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long BASE = 0xFFFF4134L;
    private static final long OUT = BASE + 0x44;     // 0xFFFF4178
    private static final long RAMP = BASE + 0x38;    // 0xFFFF416C
    private static final long STEP = BASE + 0x14;    // 0xFFFF4148
    private static final long ACTIVE = BASE + 0x0E;  // 0xFFFF4142
    private static final long DEMAND = 0xFFFF3CFAL;
    private static final long COUNTER = 0xFFFF7852L;

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

    private int R8(long a) throws Exception {
        return emu.readMemory(toAddr(a), 1)[0];
    }

    private void Scenario(String label, String name, int lo, int hi, int rpm, int gear, int tick, int calls)
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
            W16(0xFFFF784CL, 10000);
            W16(0xFFFF2C2CL, 50);
            W8(0xFFFF3F06L, gear);
            W8(0xFFFF2BD6L, 0);
            W8(0xFFFF3FBEL, 2);
            W8(0xFFFF3F0AL, 0);
            W8(0xFFFF3E2EL, 0);
            W16(0xFFFF2B1CL, 0);
            W16(BASE + 0x2E, lo);
            println(String.format("--- %s | %s: demand %d -> %d at call 20, rpm %d, gear %d, counter tick every %d calls",
                    label, name, lo, hi, rpm, gear, tick));
            int reached = -1, firstActive = -1, lastOut = Integer.MIN_VALUE;
            for (int c = 0; c < calls; c++) {
                if (c % tick == 0) {
                    int t = R16(COUNTER); if (t < 32767) W16(COUNTER, t + 1);
                }
                int demand = c >= 20 ? hi : lo;
                W16(DEMAND, demand);
                W16(0xFFFF2ACEL, demand / 2);
                W16(0xFFFF289CL, rpm);
                emu.writeRegister("r15", 0xFFFFBF00L);
                emu.writeRegister("pr", RETURN);
                emu.writeRegister(emu.getPCRegister(), START);
                emu.run(monitor);
                long pc = emu.getExecutionAddress().getOffset();
                if (pc != RETURN) {
                    println(String.format("call %d: STOPPED AT 0x%X (%s)", c, pc, emu.getLastError()));
                    return;
                }
                int out = R16(OUT);
                if (R8(ACTIVE) != 0 && firstActive < 0) firstActive = c;
                if (c >= 20 && reached < 0 && out >= hi) reached = c;
                if (out != lastOut || (c >= 18 && c <= 24)) {
                    println(String.format("%s | %s | call %4d demand %5d  out(4178) %5d  ramp(416C) %5d  step(4148) %4d  active %d  counter %4d",
                            label, name, c, demand, out, R16(RAMP), R16(STEP), R8(ACTIVE), R16(COUNTER)));
                    lastOut = out;
                }
                if (reached >= 0 && c > reached + 3) break;
            }
            println(String.format("%s | %s | SUMMARY: ramp active from call %d, output reached the demand at call %d (%d calls after the step)",
                    label, name, firstActive, reached, reached < 0 ? -1 : reached - 20));
        } finally {
            emu.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        Scenario(label, "gear 2, 2500 rpm, tick 1", 3000, 12000, 2500, 2, 1, 400);
        Scenario(label, "gear 2, 2500 rpm, tick 3", 3000, 12000, 2500, 2, 3, 400);
        Scenario(label, "gear 2, 2500 rpm, tick 8", 3000, 12000, 2500, 2, 8, 600);
        Scenario(label, "gear 4, 2500 rpm, tick 3", 3000, 12000, 2500, 4, 3, 400);
        Scenario(label, "gear 1, 1500 rpm, tick 3", 3000, 12000, 1500, 1, 3, 400);
        Scenario(label, "gear 5, 4000 rpm, tick 3", 3000, 12000, 4000, 5, 3, 400);
        Scenario(label, "gear 2, small step +40, tick 3", 3000, 3040, 2500, 2, 3, 100);
    }
}
