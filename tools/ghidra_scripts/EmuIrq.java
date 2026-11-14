// Emulates the ATU CMI7D interrupt handler 0x2C438 (vector 151, every 3.3 ms) many times in a row with RAM kept, one
// instruction at a time, and reports which instructions change the watched RAM words (who writes them, how often).
// The handler returns with rte, so a fake exception frame (PC = RETURN, SR) is pushed before each call.
// Hardware registers read as 0 (no peripheral model): code that waits on a hardware flag stops at the step limit,
// which is reported with its PC.
// Inputs set before each call: mode 0xFFFFBEA6 = 1, RPM 0xFFFF289C, speed 0xFFFF2C2C, coolant 0xFFFF2A1A, pedal
// (sensor code may overwrite them from the zero A/D registers).
// Usage (headless postScript): EmuIrq.java <calls> <hexStart> <hexAddr> [<hexAddr> ...]
// <hexStart> = 2C438 (the handler, rte frame) or a normal function such as 4BFFC (returns with rts to PR).
//@category Accord

import java.util.LinkedHashMap;
import java.util.Map;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuIrq extends GhidraScript {

    private static final long HANDLER = 0x2C438L;
    private long START;
    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long STACK = 0xFFFFBF00L;
    private static final int STEP_LIMIT = 400000;

    private EmulatorHelper emu;

    private void W16(long a, int v) throws Exception {
        emu.writeMemory(toAddr(a), new byte[] { (byte) (v >> 8), (byte) v });
    }

    private void W32(long a, long v) throws Exception {
        emu.writeMemory(toAddr(a), new byte[] { (byte) (v >> 24), (byte) (v >> 16), (byte) (v >> 8), (byte) v });
    }

    private int R16(long a) throws Exception {
        byte[] b = emu.readMemory(toAddr(a), 2);
        return (short) (((b[0] & 0xFF) << 8) | (b[1] & 0xFF));
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int calls = Integer.parseInt(args[0]);
        START = Long.parseLong(args[1].replace("0x", ""), 16);
        long[] watch = new long[args.length - 2];
        for (int i = 2; i < args.length; i++) watch[i - 2] = Long.parseLong(args[i].replace("0x", ""), 16);
        disassemble(toAddr(START));
        emu = new EmulatorHelper(currentProgram);
        try {
            emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                public boolean unknownAddress(Address address, boolean write) { return false; }
            });
            int[] last = new int[watch.length];
            @SuppressWarnings("unchecked")
            Map<String, Integer>[] writers = new Map[watch.length];
            for (int w = 0; w < watch.length; w++) writers[w] = new LinkedHashMap<>();
            int printed = 0;
            long totalSteps = 0;
            for (int c = 0; c < calls; c++) {
                emu.writeMemory(toAddr(0xFFFFBEA6L), new byte[] { 1 });
                W16(0xFFFF289CL, 2500);
                W16(0xFFFF2C2CL, 50);
                W16(0xFFFF2A1AL, 850);
                // pedal 0xFFFF2ACE is NOT forced: 0x3DB70 checks it against its own copy 0xFFFF2C56 and calls the
                // fatal reset 0x2A454 (code 0xD8) on a mismatch
                for (int w = 0; w < watch.length; w++) last[w] = R16(watch[w]);
                if (START == HANDLER) {
                    W32(STACK - 8, RETURN);
                    W32(STACK - 4, 0x000000F0L);
                    emu.writeRegister("r15", STACK - 8);
                } else {
                    emu.writeRegister("r15", STACK);
                    emu.writeRegister("pr", RETURN);
                }
                emu.writeRegister(emu.getPCRegister(), START);
                int steps = 0;
                long pc = START;
                java.util.ArrayDeque<String> trail = new java.util.ArrayDeque<>();
                while (true) {
                    pc = emu.getExecutionAddress().getOffset();
                    if (pc == RETURN) break;
                    if (steps >= STEP_LIMIT || monitor.isCancelled()) {
                        println(String.format("call %d: step limit at PC 0x%X, PR 0x%X, last calls %s", c, pc,
                                emu.readRegister("pr").longValue(), String.join(" ", trail)));
                        break;
                    }
                    if (!emu.step(monitor)) {
                        println(String.format("call %d: STOPPED AT 0x%X (%s)", c, pc, emu.getLastError()));
                        break;
                    }
                    steps++;
                    long npc = emu.getExecutionAddress().getOffset();
                    if (npc < pc || npc > pc + 4) {
                        // branch or call taken: keep the last 12 jumps (from>to) for the stop report
                        trail.addLast(String.format("%X>%X", pc, npc));
                        if (trail.size() > 400) trail.removeFirst();
                    }
                    for (int w = 0; w < watch.length; w++) {
                        int v = R16(watch[w]);
                        if (v != last[w]) {
                            String key = String.format("0x%05X", pc);
                            writers[w].merge(key, 1, Integer::sum);
                            if (printed < 60) {
                                println(String.format("call %4d step %6d: PC 0x%05X  %08X  %d -> %d", c, steps, pc,
                                        watch[w], last[w], v));
                                printed++;
                            }
                            last[w] = v;
                        }
                    }
                }
                totalSteps += steps;
                if (pc != RETURN) return;
                if (c < 3 || c % 50 == 0) println(String.format("call %d: %d instructions", c, steps));
            }
            println(String.format("SUMMARY: %d calls, %d instructions", calls, totalSteps));
            for (int w = 0; w < watch.length; w++) {
                println(String.format("SUMMARY %08X: final %d, changed by %s", watch[w], R16(watch[w]), writers[w]));
            }
        } finally {
            emu.dispose();
        }
    }
}
