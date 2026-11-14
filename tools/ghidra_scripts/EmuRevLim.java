// Emulates the rev limiter function FUN_00058898 (whole function, called like the fuel cut manager 0x580DE does)
// with the SH-2 code and tables of the loaded ROM, cycle after cycle in one emulator (RAM state kept), and finds
// the RPM where the fuel cut flag 0xFFFF4382 (= OR of list 0x15BB8: 4E40, 4389, 438A, 438B, 59FD) turns on going
// up 1 rpm per cycle, then where it turns off going down 1 rpm per cycle.
// Usage (headless postScript): EmuRevLim.java <label> [<hexRomAddr>:<decimal 16-bit value> ...]
// The optional patches are written into the emulator memory only (the program / ROM file is not changed).
//@category Accord

import java.util.ArrayList;
import java.util.List;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuRevLim extends GhidraScript {

    private static final long FUNC = 0x58898L;
    private static final long RET = 0x8000L;          // fake return address (breakpoint)
    private static final long STACK = 0xFFFFBF00L;
    private static final long RPM = 0xFFFF289CL;
    private static final long SPEED = 0xFFFF2C2CL;
    private static final long ECT = 0xFFFF2A1AL;
    private static final long VTEC = 0xFFFF3D0DL;
    private static final long CUT = 0xFFFF4382L;      // GBR 0x433C + 0x46
    private static final long F4E40 = 0xFFFF4E40L;
    private static final long F438A = 0xFFFF438AL;
    private static final long CUTPT = 0xFFFF438CL;    // +0x50 cut point
    private static final long RESPT = 0xFFFF438EL;    // +0x52 resume point
    private static final long PERIOD = 0xFFFF76C8L;   // period timer of the cut/resume point ramps (reload 0xB21C)
    private static final long[] LIST = { 0xFFFF4E40L, 0xFFFF4389L, 0xFFFF438AL, 0xFFFF438BL, 0xFFFF59FDL };

    private String flags() throws Exception {
        StringBuilder sb = new StringBuilder();
        for (long a : LIST) sb.append(String.format(" %X=%d", a & 0xFFFF, r8(a)));
        return sb.toString().trim();
    }

    private EmulatorHelper emu;

    private void w8(long a, int v) throws Exception { emu.writeMemory(toAddr(a), new byte[] { (byte) v }); }
    private void w16(long a, int v) throws Exception { emu.writeMemory(toAddr(a), new byte[] { (byte) (v >> 8), (byte) v }); }
    private int r8(long a) throws Exception { return emu.readMemoryByte(toAddr(a)) & 0xFF; }
    private int r16(long a) throws Exception {
        byte[] b = emu.readMemory(toAddr(a), 2);
        return (short) (((b[0] & 0xFF) << 8) | (b[1] & 0xFF));
    }

    private void call() throws Exception {
        w16(PERIOD, 0);    // decremented by the timer service, not by this function: 1 call = 1 expired period
        emu.writeRegister("r15", STACK);
        emu.writeRegister("pr", RET);
        emu.writeRegister(emu.getPCRegister(), FUNC);
        emu.run(monitor);
        Address pc = emu.getExecutionAddress();
        if (pc.getOffset() != RET) throw new Exception("stopped at " + pc + " (" + emu.getLastError() + ")");
    }

    // rpm held at 'hold' for 'settle' cycles, then from 'start' +1 rpm per cycle until the cut flag sets, then -1 per
    // cycle until it clears. Returns "cut at X, resume at Y" with the internal cut/resume points. Start close to the
    // limit: when stopped, 600 cycles above 3500 rpm start the stopped protection (cut point steps down).
    private String thresholds(String name, int speed, int vtec, int hold, int start, int settle) throws Exception {
        w16(SPEED, speed);
        w8(VTEC, vtec);
        w16(RPM, hold);
        for (int i = 0; i < settle; i++) call();
        int rpm = start;
        if (r8(CUT) != 0) return name + ": cut flag already set at " + start + " (" + flags() + ", cut point "
                + r16(CUTPT) + ", resume point " + r16(RESPT) + ")";
        int on = -1, off = -1;
        for (int i = 0; i < 2000 && on < 0; i++) {
            rpm++;
            w16(RPM, rpm);
            call();
            if (r8(CUT) != 0) on = rpm;
        }
        String who = flags();
        int cp = r16(CUTPT), rp = r16(RESPT);
        for (int i = 0; i < 2000 && on >= 0 && off < 0; i++) {
            rpm--;
            w16(RPM, rpm);
            call();
            if (r8(CUT) == 0) off = rpm;
        }
        return String.format("%s: cut ON at %d rpm (%s), cut OFF at %d rpm | internal cut point %d, resume point %d",
                name, on, who, off, cp, rp);
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String label = args.length > 0 ? args[0] : currentProgram.getName();
        disassemble(toAddr(FUNC));
        // patches as <hexAddr>:<decimal> (the .bat launcher splits arguments on '=')
        List<long[]> patches = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            String[] kv = args[i].split(":");
            patches.add(new long[] { Long.parseLong(kv[0].replace("0x", ""), 16), Integer.parseInt(kv[1]) });
        }
        newEmu(patches);
        try {
            StringBuilder sb = new StringBuilder();
            for (long[] p : patches) sb.append(String.format("0x%X=%d (read back %d) ", p[0], p[1], r16(p[0])));
            println("=== " + label + " | patches: " + (patches.isEmpty() ? "none" : sb.toString().trim()));
            println(String.format("%s | tables (moving): cut 0x15BF6=%d (no VTEC) 0x15BFE=%d (VTEC) 0x15C2A=%d (2nd); "
                    + "resume 0x15C06=%d (no VTEC) 0x15C0E=%d (VTEC) 0x15C32=%d (2nd)", label,
                    r16(0x15BF6), r16(0x15BFE), r16(0x15C2A), r16(0x15C06), r16(0x15C0E), r16(0x15C32)));
        } finally {
            emu.dispose();
        }
        Object[][] cases = { { "moving 80 km/h, VTEC on ", 80, 1, 7200 }, { "moving 80 km/h, VTEC off", 80, 0, 7000 },
                             { "stopped 0 km/h, VTEC off", 0, 0, 3950 } };
        for (Object[] c : cases) {       // fresh RAM state for each case
            newEmu(patches);
            try {
                println(label + " | " + thresholds((String) c[0], (Integer) c[1], (Integer) c[2], 3000, (Integer) c[3], 40));
            } finally {
                emu.dispose();
            }
        }
    }

    private void newEmu(List<long[]> patches) throws Exception {
        emu = new EmulatorHelper(currentProgram);
        emu.setMemoryFaultHandler(new MemoryFaultHandler() {
            public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
            public boolean unknownAddress(Address address, boolean write) { return false; }
        });
        emu.setBreakpoint(toAddr(RET));
        for (long[] p : patches) w16(p[0], (int) p[1]);
        w16(ECT, 850);
    }
}
