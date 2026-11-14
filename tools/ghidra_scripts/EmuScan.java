// Runs each given interrupt handler once (fresh emulator, rte frame) and reports which instructions change the
// watched RAM words. Watched words are preset to 5 so that both up and down counting shows.
// Hardware registers read as 0; a handler that waits on hardware stops at the step limit (reported).
// Usage (headless postScript): EmuScan.java <watch1_watch2_...> <hexStart> [<hexStart> ...]
// ("_" separator: PowerShell splits a comma list into separate arguments)
//@category Accord

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuScan extends GhidraScript {

    private static final long RETURN = 0x8402L;      // never executed (checksum area): used as the return address
    private static final long STACK = 0xFFFFBF00L;
    private static final int STEP_LIMIT = 60000;

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
        String[] ws = args[0].split("_");
        long[] watch = new long[ws.length];
        for (int i = 0; i < ws.length; i++) watch[i] = Long.parseLong(ws[i], 16);
        for (int s = 1; s < args.length; s++) {
            long start = Long.parseLong(args[s], 16);
            disassemble(toAddr(start));
            emu = new EmulatorHelper(currentProgram);
            try {
                emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                    public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                    public boolean unknownAddress(Address address, boolean write) { return false; }
                });
                emu.writeMemory(toAddr(0xFFFFBEA6L), new byte[] { 1 });
                int[] last = new int[watch.length];
                for (int w = 0; w < watch.length; w++) { W16(watch[w], 5); last[w] = 5; }
                W32(STACK - 8, RETURN);
                W32(STACK - 4, 0x000000F0L);
                emu.writeRegister("r15", STACK - 8);
                emu.writeRegister(emu.getPCRegister(), start);
                int steps = 0;
                String result = "returned";
                StringBuilder changes = new StringBuilder();
                while (true) {
                    long pc = emu.getExecutionAddress().getOffset();
                    if (pc == RETURN) break;
                    if (steps >= STEP_LIMIT) { result = String.format("step limit at 0x%X", pc); break; }
                    if (!emu.step(monitor)) { result = String.format("stopped at 0x%X", pc); break; }
                    steps++;
                    for (int w = 0; w < watch.length; w++) {
                        int v = R16(watch[w]);
                        if (v != last[w]) {
                            changes.append(String.format(" [%X: %d->%d at PC 0x%X]", watch[w] & 0xFFFF, last[w], v, pc));
                            last[w] = v;
                        }
                    }
                }
                println(String.format("handler 0x%X: %s after %d instructions;%s", start, result, steps,
                        changes.length() == 0 ? " no change" : changes.toString()));
            } finally {
                emu.dispose();
            }
        }
    }
}
