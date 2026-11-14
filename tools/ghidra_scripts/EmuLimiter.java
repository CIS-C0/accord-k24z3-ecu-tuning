// Emulates the speed limiter block of FUN_000580de (ROM 0x587B6-0x587EC) with the SH-2 code and constants of the
// loaded ROM, for several RPM / speed inputs, and prints the fuel cut flag it writes (GBR+0x45 = 0xFFFF4383).
// Registers (verified in the function listing): GBR = [0x581E4] = 0xFFFF433E (flags), r8 = [0x581E8] = 0xFFFF2C2C
// (speed), r9 = [0x58438] = 0xFFFF289C (RPM), r13 = [0x588C8] = 0xFFFF76BC (timers: +0x10 delay, +0x12 hold).
// Usage (headless postScript): EmuLimiter.java <label>
//@category Accord

import java.math.BigInteger;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.pcode.memstate.MemoryFaultHandler;

public class EmuLimiter extends GhidraScript {

    private static final long FLAGS = 0xFFFF433EL;
    private static final long SPEED = 0xFFFF2C2CL;
    private static final long RPM = 0xFFFF289CL;
    private static final long TIMERS = 0xFFFF76BCL;
    private static final long START = 0x587B6L;
    private static final long STOP = 0x587EEL;   // right after mov.b r0,@(0x45,gbr)

    private int ReadU16(Address a) throws Exception {
        return ((currentProgram.getMemory().getByte(a) & 0xFF) << 8) | (currentProgram.getMemory().getByte(a.add(1)) & 0xFF);
    }

    private String RunCase(int rpm, int speed, int delay, int hold) throws Exception {
        EmulatorHelper emu = new EmulatorHelper(currentProgram);
        try {
            emu.setMemoryFaultHandler(new MemoryFaultHandler() {
                public boolean uninitializedRead(Address address, int size, byte[] buf, int bufOffset) { return false; }
                public boolean unknownAddress(Address address, boolean write) { return false; }
            });
            emu.writeRegister("gbr", FLAGS);
            emu.writeRegister("r8", SPEED);
            emu.writeRegister("r9", RPM);
            emu.writeRegister("r13", TIMERS);
            emu.writeRegister("r15", 0xFFFF8000L);
            emu.writeMemory(toAddr(SPEED), new byte[] { (byte) (speed >> 8), (byte) speed });
            emu.writeMemory(toAddr(RPM), new byte[] { (byte) (rpm >> 8), (byte) rpm });
            emu.writeMemory(toAddr(TIMERS + 0x10), new byte[] { (byte) (delay >> 8), (byte) delay, (byte) (hold >> 8), (byte) hold });
            emu.writeMemory(toAddr(FLAGS + 0x45), new byte[] { (byte) 0xAA });   // sentinel: must be overwritten
            emu.writeRegister(emu.getPCRegister(), START);
            emu.setBreakpoint(toAddr(STOP));
            boolean ok = emu.run(monitor);
            Address pc = emu.getExecutionAddress();
            if (pc.getOffset() != STOP) return "STOPPED AT " + pc + " (" + emu.getLastError() + ")";
            byte flag = emu.readMemoryByte(toAddr(FLAGS + 0x45));
            byte[] t = emu.readMemory(toAddr(TIMERS + 0x10), 4);
            int newDelay = ((t[0] & 0xFF) << 8) | (t[1] & 0xFF);
            int newHold = ((t[2] & 0xFF) << 8) | (t[3] & 0xFF);
            return String.format("flag=%d delay=%d hold=%d", flag & 0xFF, newDelay, newHold);
        } finally {
            emu.dispose();
        }
    }

    @Override
    public void run() throws Exception {
        String label = getScriptArgs().length > 0 ? getScriptArgs()[0] : currentProgram.getName();
        disassemble(toAddr(START));
        println("=== " + label + " | ROM 0xB2C0 rpm limit=" + ReadU16(toAddr(0xB2C0)) + " | 0xB2C2 speed limit=" + ReadU16(toAddr(0xB2C2))
            + " | 0xB2C4 delay=" + ReadU16(toAddr(0xB2C4)) + " | 0xB2C6 hold=" + ReadU16(toAddr(0xB2C6)));

        int[] speeds = { 150, 199, 200, 201, 220, 239, 240, 241, 250 };
        for (int s : speeds) {
            println(String.format("%s | rpm 4000 speed %3d timers expired      -> %s", label, s, RunCase(4000, s, 0, 0)));
        }
        println(String.format("%s | rpm 4000 speed 250 delay running (50) -> %s", label, RunCase(4000, 250, 50, 0)));
        println(String.format("%s | rpm 3000 speed 250 timers expired      -> %s", label, RunCase(3000, 250, 0, 0)));
        println(String.format("%s | rpm 4000 speed 180 hold running (30)   -> %s", label, RunCase(4000, 180, 0, 30)));
    }
}
