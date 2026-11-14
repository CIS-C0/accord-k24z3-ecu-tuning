// Find the code that loads on-chip I/O register addresses (0xFFFFxxxx) with "mov.w @(disp,PC),Rn" (0x9ndd, the
// 16-bit pool word is sign-extended, so 0xF464 -> 0xFFFFF464) or "mov.l @(disp,PC),Rn" (0xDndd), and print the
// 12 instructions that follow each load, so register writes and their values can be read.
// Usage (headless postScript): FindIoRefs.java <hexLow> <hexHigh>   (e.g. FFFFF400 FFFFF4FF)
//@category Accord

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

public class FindIoRefs extends GhidraScript {

    private int readU16(Memory mem, long a) throws Exception {
        Address ad = toAddr(a);
        return ((mem.getByte(ad) & 0xFF) << 8) | (mem.getByte(ad.add(1)) & 0xFF);
    }

    @Override
    public void run() throws Exception {
        long lo = Long.parseLong(getScriptArgs()[0].replace("0x", ""), 16);
        long hi = Long.parseLong(getScriptArgs()[1].replace("0x", ""), 16);
        Memory mem = currentProgram.getMemory();
        long end = 0x8000 + mem.getBlocks()[0].getSize();
        for (long pc = 0x8000; pc < end - 2; pc += 2) {
            int op = readU16(mem, pc);
            long value;
            if ((op & 0xF000) == 0x9000) {
                long t = pc + 4 + (op & 0xFF) * 2L;
                if (t + 2 > end) continue;
                value = (short) readU16(mem, t) & 0xFFFFFFFFL;
            } else if ((op & 0xF000) == 0xD000) {
                long t = (pc & ~3L) + 4 + (op & 0xFF) * 4L;
                if (t + 4 > end) continue;
                value = ((long) readU16(mem, t) << 16) | readU16(mem, t + 2);
            } else {
                continue;
            }
            if (value < lo || value > hi) continue;
            StringBuilder sb = new StringBuilder(String.format("=== 0x%X loads 0x%08X into r%d", pc, value, (op >> 8) & 0xF));
            Address a = toAddr(pc);
            disassemble(a);
            Instruction ins = getInstructionAt(a);
            for (int n = 0; n < 13 && ins != null; n++) {
                sb.append(String.format("\n    %s: %s", ins.getAddress(), ins));
                Address next = ins.getFallThrough();
                if (next == null) break;
                if (getInstructionAt(next) == null) disassemble(next);
                ins = getInstructionAt(next);
            }
            println(sb.toString());
        }
    }
}
