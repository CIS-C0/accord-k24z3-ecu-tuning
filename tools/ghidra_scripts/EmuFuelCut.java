// Emulates the fuel cut manager 0x580DE call by call (one emulator per scenario, RAM kept between calls) to measure
// the decel fuel cut entry delay: number of timer ticks from "lift-off" (conditions met) to the fuel cut flag
// 0xFFFF4341 (base 0xFFFF433E + 3). The delay timer is 0xFFFF76C0 (0xFFFF76BC + 4), loaded in 0x58652-0x58720.
// Assumptions (stated in the output): one call = one timer tick; all words 0xFFFF76BC..0xFFFF76CE are down-counters
// decremented by 1 per tick (done here before each call); RAM not listed is 0.
// Phase 1 (<pre> calls, "pedal on"): 0xFFFF3D0C = 1, MAP 0xFFFF29D8 = 9000. Phase 2 ("lift-off"): 0xFFFF3D0C = 0,
// MAP = 1900. Inputs: RPM 0xFFFF289C, speed 0xFFFF2C2C, gear 0xFFFF3F06 (= previous gear 0xFFFF3FD9),
// 0xFFFF784C = 10000 (time since start).
// Usage (headless postScript): EmuFuelCut.java <label> [<hexRomAddr>:<decimal16bitValue> ...]
// The optional patches are written into the emulator's copy of the ROM only (to compare stock vs modified).
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuFuelCut extends GhidraScript {

    private static final long START = 0x580DEL;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long BASE = 0xFFFF433EL;
    private static final long TIMERS = 0xFFFF76BCL;

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

    private void Scenario(String label, String name, int rpm, int speed, int gear, int pre, int calls) throws Exception {
        Scenario(label, name, rpm, speed, gear, pre, calls, -1, -1, false);
    }

    // Calls mmStart..mmEnd-1: previous gear 0xFFFF3FD9 = gear - 1 (gear change seen, 0xFFFF76BE loaded from 0xB13E).
    // sticky: 0xFFFF76BE is not decremented (its decrementer was not found in the ROM: both cases are shown).
    private void Scenario(String label, String name, int rpm, int speed, int gear, int pre, int calls, int mmStart,
            int mmEnd, boolean sticky) throws Exception {
        if (mmStart >= 0) name += sticky ? " [76BE not decremented]" : " [76BE decremented]";
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
            W8(0xFFFF3F06L, gear);
            W8(0xFFFF3FD9L, gear);
            println(String.format("--- %s | %s: rpm %d, speed %d, gear %d, lift-off at call %d", label, name, rpm, speed,
                    gear, pre));
            int cut = -1;
            String lastState = "";
            for (int c = 0; c < calls; c++) {
                for (long t = TIMERS; t <= TIMERS + 0x12; t += 2) {
                    int v = R16(t);
                    if (v > 0 && !(sticky && t == TIMERS + 2)) W16(t, v - 1);
                }
                if (mmStart >= 0) W8(0xFFFF3FD9L, c >= mmStart && c < mmEnd ? gear - 1 : gear);
                boolean lifted = c >= pre;
                W8(0xFFFF3D0CL, lifted ? 0 : 1);
                W16(0xFFFF29D8L, lifted ? 1900 : 9000);
                W16(0xFFFF289CL, rpm);
                W16(0xFFFF2C2CL, speed);
                emu.writeRegister("r15", 0xFFFFBF00L);
                emu.writeRegister("pr", RETURN);
                emu.writeRegister(emu.getPCRegister(), START);
                emu.run(monitor);
                long pc = emu.getExecutionAddress().getOffset();
                if (pc != RETURN) {
                    println(String.format("call %d: STOPPED AT 0x%X (%s)", c, pc, emu.getLastError()));
                    return;
                }
                String state = String.format("B0 %d B2 %d FC(4341) %d B1F %d B20 %d delay(76C0) %d hold(76C2) %d 76BE %d",
                        R8(BASE), R8(BASE + 2), R8(BASE + 3), R8(BASE + 0x1F), R8(BASE + 0x20), R16(TIMERS + 4),
                        R16(TIMERS + 6), R16(TIMERS + 2));
                String key = state.replaceAll("delay\\(76C0\\) -?\\d+ hold\\(76C2\\) -?\\d+", "");
                if (c == pre - 1 || c == pre || !key.equals(lastState)) {
                    println(String.format("%s | %s | call %4d %s", label, name, c, state));
                    lastState = key;
                }
                if (lifted && cut < 0 && R8(BASE + 3) != 0) cut = c;
                if (cut >= 0 && c > cut + 2) break;
            }
            println(String.format("%s | %s | SUMMARY: fuel cut %s", label, name,
                    cut < 0 ? "NEVER" : (cut - pre) + " ticks after lift-off"));
        } finally {
            emu.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        Scenario(label, "moving gear 2 3000rpm", 3000, 50, 2, 50, 300);
        Scenario(label, "moving gear 3 3000rpm", 3000, 60, 3, 50, 300);
        Scenario(label, "moving gear 4 3000rpm", 3000, 80, 4, 50, 300);
        Scenario(label, "moving gear 2 4500rpm", 4500, 70, 2, 50, 300);
        Scenario(label, "stopped 3000rpm", 3000, 0, 0, 400, 700);
        for (boolean sticky : new boolean[] { false, true }) {
            Scenario(label, "gear 3 3000rpm, shift 2->3 ends 5 calls before lift-off", 3000, 60, 3, 150, 400, 140,
                    145, sticky);
            Scenario(label, "gear 3 3000rpm, shift 2->3 ends 100 calls before lift-off", 3000, 60, 3, 150, 400, 40,
                    50, sticky);
            Scenario(label, "gear 3 4500rpm, shift 2->3 ends 100 calls before lift-off", 4500, 90, 3, 150, 400, 40,
                    50, sticky);
        }
    }
}
