// Find the code that loads given 32-bit constants (table descriptors, ROM tables, RAM addresses) in a raw SH-2 binary.
// Usage (headless postScript): FindRefs.java [-decomp] [-writes] <hexValue> [<hexValue> ...]
// -writes: only list the loads followed by a store through the loaded register (who WRITES a RAM variable).
// For each value: finds the literal pool words equal to it, then the "mov.l @(disp,PC),Rn" instructions (0xDndd)
// that load those words. With -decomp, the function around each loading instruction is decompiled
// (start found like DecompAt: previous "rts" + delay slot, nop padding skipped).
//@category Accord

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class FindRefs extends GhidraScript {

    private static final long ROM_START = 0x8000;
    private static final long ROM_END = 0x100000;

    private int readU16(Memory mem, long a) throws Exception {
        Address ad = toAddr(a);
        return ((mem.getByte(ad) & 0xFF) << 8) | (mem.getByte(ad.add(1)) & 0xFF);
    }

    private long readU32(Memory mem, long a) throws Exception {
        return ((long) readU16(mem, a) << 16) | readU16(mem, a + 2);
    }

    private Long findFunctionStart(Memory mem, long target) throws Exception {
        long a = target - 2;
        long min = Math.max(ROM_START, target - 0x2000);
        while (a > min) {
            if (readU16(mem, a) == 0x000B) {
                long start = a + 4;
                while (readU16(mem, start) == 0x0009) start += 2;
                return start;
            }
            a -= 2;
        }
        return null;
    }

    private boolean doWrites = false;

    // Follows the register loaded at pc for up to 40 instructions (stops at rts/branch or when the register is
    // overwritten) and returns the stores through it: "mov.x rM,@rN" and "mov.x rM,@(disp,rN)".
    private String findStores(long pc, int reg) throws Exception {
        String rn = "r" + reg;
        StringBuilder sb = new StringBuilder();
        Address a = toAddr(pc + 2);
        for (int n = 0; n < 40; n++) {
            Instruction ins = getInstructionAt(a);
            if (ins == null) {
                disassemble(a);
                ins = getInstructionAt(a);
                if (ins == null) break;
            }
            String s = ins.toString().toLowerCase();
            if (s.matches("mov\\.[bwl] r\\d+,@" + rn) || s.matches("mov\\.[bwl] r\\d+,@\\(0x[0-9a-f]+," + rn + "\\)")) {
                sb.append(String.format("\n        STORE 0x%s: %s", ins.getAddress(), ins));
            }
            boolean overwritten = false;
            for (Object o : ins.getResultObjects()) {
                if (o instanceof Register && ((Register) o).getName().equalsIgnoreCase(rn)) overwritten = true;
            }
            String m = ins.getMnemonicString().toLowerCase();
            if (overwritten || m.startsWith("rts") || m.startsWith("bra") || m.startsWith("jmp")) break;
            a = ins.getFallThrough();
            if (a == null) break;
        }
        return sb.toString();
    }

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        boolean doDecomp = false;
        List<Long> values = new ArrayList<>();
        for (String arg : getScriptArgs()) {
            if (arg.equals("-decomp")) doDecomp = true;
            else if (arg.equals("-writes")) doWrites = true;
            else values.add(Long.parseLong(arg.replace("0x", ""), 16));
        }

        for (ghidra.program.model.mem.MemoryBlock block : mem.getBlocks()) {
            if (block.getStart().getOffset() < ROM_END) block.setWrite(false);
        }

        Set<Long> functionStarts = new LinkedHashSet<>();
        for (long value : values) {
            println(String.format("=== value 0x%X", value));
            for (long pool = ROM_START; pool <= ROM_END - 4; pool += 4) {
                if (readU32(mem, pool) != value) continue;
                println(String.format("  pool word at 0x%X", pool));
                // mov.l @(disp,PC),Rn: target = (pc & ~3) + 4 + disp*4, disp 0..255, pc = instruction address
                for (long pc = Math.max(ROM_START, pool - 4 - 255 * 4); pc < pool; pc += 2) {
                    int op = readU16(mem, pc);
                    if ((op & 0xF000) != 0xD000) continue;
                    long t = (pc & ~3L) + 4 + (op & 0xFF) * 4L;
                    if (t != pool) continue;
                    int reg = (op >> 8) & 0xF;
                    Long start = findFunctionStart(mem, pc);
                    String stores = doWrites ? findStores(pc, reg) : "";
                    if (doWrites && stores.isEmpty()) continue;
                    println(String.format("    mov.l at 0x%X -> r%d, function start guess %s%s", pc, reg,
                            start == null ? "?" : String.format("0x%X", start), stores));
                    if (start != null) functionStarts.add(start);
                }
            }
        }

        if (!doDecomp) return;
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        for (long s : functionStarts) {
            Address start = toAddr(s);
            println(String.format("=== decompile 0x%X", s));
            disassemble(start);
            Function f = getFunctionAt(start);
            if (f == null) f = createFunction(start, "FUN_" + start);
            if (f == null) {
                println("could not create function at " + start);
                continue;
            }
            println("function body: " + f.getBody());
            DecompileResults res = decomp.decompileFunction(f, 120, monitor);
            if (res.decompileCompleted()) println(res.getDecompiledFunction().getC());
            else println("decompile failed: " + res.getErrorMessage());
        }
        decomp.dispose();
    }
}
