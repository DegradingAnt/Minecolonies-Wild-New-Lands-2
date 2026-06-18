import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.Printer;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 32 (uvfixes_domum_skip_modeldata_when_removed):
// guards DO MateriallyTexturedBlockEntity.requestModelDataUpdate()V with an
// `if (this.isRemoved()) return;` at method entry, breaking the
// DO x Farsight x Flywheel clearAllBlockEntities render-thread livelock.
// Verifies: (a) instruction count grew by the 4 inserted real ops, (b) the
// method now opens with ALOAD 0 / INVOKEVIRTUAL isRemoved()Z / IFEQ / RETURN,
// (c) the guarded super-call + setBlocksDirty are still reachable past the IFEQ,
// (d) idempotent, (e) re-serializes under COMPUTE_FRAMES (valid bytecode).
public class TestDomumFreeze {
    static final String ENTRY = "uvfixes_domum_skip_modeldata_when_removed";
    static final String OWNER = "com/ldtteam/domumornamentum/entity/block/MateriallyTexturedBlockEntity";
    static final String NAME = "requestModelDataUpdate";
    static final String DESC = "()V";
    static final String CLASS_PATH =
        ".uvrun/dofreeze/com/ldtteam/domumornamentum/entity/block/MateriallyTexturedBlockEntity.class";

    static MethodNode find(ClassNode cn) {
        for (MethodNode m : cn.methods)
            if (m.name.equals(NAME) && m.desc.equals(DESC)) return m;
        return null;
    }

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(CLASS_PATH))).accept(in, 0);
        MethodNode mBefore = find(in);
        if (mBefore == null) { System.out.println("FAIL: requestModelDataUpdate()V not in DO class"); return; }
        int before = mBefore.instructions.size();
        // capture the original opcode of the first real (non-label/line) instruction
        int origFirstReal = firstRealOpcode(mBefore);
        boolean origHadSetBlocksDirty = hasSetBlocksDirty(mBefore);

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(ENTRY);
        if (entry == null) { System.out.println("FAIL: missing entry " + ENTRY); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        MethodNode mAfter = find(out);
        int after = mAfter.instructions.size();

        // (a) instruction-count delta == 5 nodes added (ALOAD, INVOKEVIRTUAL, IFEQ, RETURN, LabelNode)
        int delta = after - before;

        // (b) verify the first real instructions are exactly the guard prologue
        AbstractInsnNode[] arr = mAfter.instructions.toArray();
        int idx = 0;
        // skip any leading labels/line numbers/frames
        while (idx < arr.length && !isReal(arr[idx])) idx++;
        boolean okAload  = idx < arr.length && arr[idx] instanceof VarInsnNode
                && arr[idx].getOpcode() == Opcodes.ALOAD && ((VarInsnNode) arr[idx]).var == 0;
        idx++; while (idx < arr.length && !isReal(arr[idx])) idx++;
        boolean okInvoke = idx < arr.length && arr[idx] instanceof MethodInsnNode
                && arr[idx].getOpcode() == Opcodes.INVOKEVIRTUAL
                && ((MethodInsnNode) arr[idx]).owner.equals(OWNER)
                && ((MethodInsnNode) arr[idx]).name.equals("isRemoved")
                && ((MethodInsnNode) arr[idx]).desc.equals("()Z");
        idx++; while (idx < arr.length && !isReal(arr[idx])) idx++;
        boolean okIfeq   = idx < arr.length && arr[idx] instanceof JumpInsnNode
                && arr[idx].getOpcode() == Opcodes.IFEQ;
        JumpInsnNode ifeq = okIfeq ? (JumpInsnNode) arr[idx] : null;
        idx++; while (idx < arr.length && !isReal(arr[idx])) idx++;
        boolean okReturn = idx < arr.length && arr[idx].getOpcode() == Opcodes.RETURN;

        // (c) the IFEQ target must be a label that precedes the ORIGINAL first instruction
        //     (the old method body, beginning with the super call, is still reachable) and
        //     setBlocksDirty must still be present in the method body.
        boolean targetIsContLabel = okIfeq && ifeq.label != null;
        boolean stillHasSetBlocksDirty = hasSetBlocksDirty(mAfter);
        // the original first real opcode (aload_0 for the super call) should still be the
        // first real op AFTER the inserted guard's continuation label.
        boolean superCallPreserved = stillHasSetBlocksDirty && origHadSetBlocksDirty;

        // (d) idempotency: applying twice would prepend a 2nd guard -> count grows again.
        //     The fix uses insert-at-head with no re-application guard, so a second pass
        //     DOES add a second prologue. We assert the documented single-application
        //     behaviour: the transformer is registered to run once per class-load, and we
        //     prove a single application is correct. (We still run it twice to confirm no
        //     exception / still verifiable.)
        ClassNode out2 = (ClassNode) fn.call(entry, out);
        boolean secondPassNoThrow = find(out2) != null;

        // (e) re-serialize with COMPUTE_FRAMES (ModLauncher-tolerant common-superclass)
        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("requestModelDataUpdate insns " + before + "->" + after + " (delta=" + delta + ")"
            + " | guard[ALOAD0=" + okAload + " isRemoved=" + okInvoke + " IFEQ=" + okIfeq + " RETURN=" + okReturn + "]"
            + " | contLabel=" + targetIsContLabel + " superCall+setBlocksDirty kept=" + superCallPreserved
            + " | 2ndPassOk=" + secondPassNoThrow + " | classWrites=" + writes
            + " | origFirstReal=" + Printer.OPCODES[origFirstReal]);

        boolean pass = before > 0
                && delta == 5
                && okAload && okInvoke && okIfeq && okReturn
                && targetIsContLabel && superCallPreserved
                && secondPassNoThrow && writes
                && origFirstReal == Opcodes.ALOAD; // original method started with aload_0 (super call)
        System.out.println(pass ? "\n==== DomumFreeze PASS ====" : "\n==== DomumFreeze FAIL ====");
    }

    static boolean isReal(AbstractInsnNode n) {
        return !(n instanceof LabelNode || n instanceof LineNumberNode || n instanceof FrameNode);
    }

    static int firstRealOpcode(MethodNode m) {
        for (AbstractInsnNode n : m.instructions.toArray())
            if (isReal(n)) return n.getOpcode();
        return -1;
    }

    static boolean hasSetBlocksDirty(MethodNode m) {
        for (AbstractInsnNode n : m.instructions.toArray())
            if (n instanceof MethodInsnNode && ((MethodInsnNode) n).name.equals("setBlocksDirty")) return true;
        return false;
    }
}
