// Decompile the function containing a given address in a raw SH-2 binary.
// Usage (headless postScript): DecompAt.java <hexAddress> [<hexAddress> ...]
// The function start is found by scanning backwards for the previous "rts" (0x000B) + delay slot,
// then skipping "nop" (0x0009) padding.
//@category Accord

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

public class DecompAt extends GhidraScript {

    private int readU16(Memory mem, Address a) throws Exception {
        return ((mem.getByte(a) & 0xFF) << 8) | (mem.getByte(a.add(1)) & 0xFF);
    }

    private Address findFunctionStart(Address target) throws Exception {
        Memory mem = currentProgram.getMemory();
        Address a = target.subtract(2);
        Address min = target.subtract(0x2000);
        while (a.compareTo(min) > 0) {
            if (readU16(mem, a) == 0x000B) {
                // rts found, skip its delay slot
                Address start = a.add(4);
                while (readU16(mem, start) == 0x0009) start = start.add(2);
                return start;
            }
            a = a.subtract(2);
        }
        return null;
    }

    // Define the literal pool words loaded by "mov.l @(disp,PC),Rn" (0xDndd) and "mov.w @(disp,PC),Rn" (0x9ndd)
    // as dword/word data, so the decompiler shows their values instead of _UNK_ globals.
    private void definePoolData(Function f) throws Exception {
        Memory mem = currentProgram.getMemory();
        for (Instruction ins : currentProgram.getListing().getInstructions(f.getBody(), true)) {
            long pc = ins.getAddress().getOffset();
            int op = readU16(mem, ins.getAddress());
            Address t;
            boolean isLong;
            if ((op & 0xF000) == 0xD000) {
                t = toAddr((pc & ~3L) + 4 + (op & 0xFF) * 4L);
                isLong = true;
            } else if ((op & 0xF000) == 0x9000) {
                t = toAddr(pc + 4 + (op & 0xFF) * 2L);
                isLong = false;
            } else {
                continue;
            }
            if (getInstructionContaining(t) != null || getDataContaining(t) != null) continue;
            try {
                if (isLong) createDWord(t); else createWord(t);
            } catch (Exception e) {
                println("could not define pool data at " + t + ": " + e.getMessage());
            }
        }
    }

    // Replace the DWORD_xxxx / WORD_xxxx names of the ROM pool words with their values (the ROM never changes).
    // A pointer shows as its address, so "*(short *)0xffff289c" reads as "the RAM word at 0xFFFF289C".
    private String substitutePoolValues(String c) throws Exception {
        Memory mem = currentProgram.getMemory();
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("\\b(DWORD|WORD)_([0-9a-fA-F]{8})\\b").matcher(c);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            Address a = toAddr(Long.parseLong(m.group(2), 16));
            String v;
            if (m.group(1).equals("DWORD")) {
                v = String.format("0x%x", ((long) readU16(mem, a) << 16) | readU16(mem, a.add(2)));
            } else {
                v = String.format("0x%x", readU16(mem, a));
            }
            m.appendReplacement(sb, v);
        }
        m.appendTail(sb);
        return sb.toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();

        // ROM is flash, mark it read-only so the decompiler shows literal pool values as constants
        for (ghidra.program.model.mem.MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (block.getStart().getOffset() < 0x100000) block.setWrite(false);
        }

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        for (String arg : args) {
            // "<start>@<target>" forces the function start, otherwise it is guessed
            Address start;
            Address target;
            if (arg.contains("@")) {
                start = toAddr(Long.parseLong(arg.split("@")[0].replace("0x", ""), 16));
                target = toAddr(Long.parseLong(arg.split("@")[1].replace("0x", ""), 16));
            } else {
                target = toAddr(Long.parseLong(arg.replace("0x", ""), 16));
                start = findFunctionStart(target);
            }
            println("=== target " + target + " -> function start guess " + start);
            if (start == null) continue;

            disassemble(start);
            Function f = getFunctionAt(start);
            if (f == null) f = createFunction(start, "FUN_" + start);
            if (f == null) {
                println("could not create function at " + start);
                continue;
            }
            println("function body: " + f.getBody());
            definePoolData(f);

            // listing of the whole function body
            StringBuilder listing = new StringBuilder();
            for (Instruction ins : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                listing.append(ins.getAddress()).append(": ").append(ins).append("\n");
            }
            println("--- listing ---\n" + listing);

            DecompileResults res = decomp.decompileFunction(f, 120, monitor);
            if (res.decompileCompleted()) {
                println("--- decompiled ---\n" + substitutePoolValues(res.getDecompiledFunction().getC()));
            } else {
                println("decompile failed: " + res.getErrorMessage());
            }
        }
        decomp.dispose();
    }
}
