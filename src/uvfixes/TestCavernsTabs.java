import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 33 (uvfixes_caverns_creativetab_config_guard):
// wraps each (ItemDisplayParameters,Output)V creative-tab generator in CCCreativeTabs in
// try{...}catch(Throwable){return} so a client-config-not-loaded throw on a dedicated server
// can't abort PlayerList.placeNewPlayer ("Invalid player data" kick + accessory wipe).
// Verifies: (a) exactly 2 target methods, (b) each gained one Throwable try-catch block,
// (c) each still ends in RETURN, (d) the patched class re-serializes under COMPUTE_FRAMES.
public class TestCavernsTabs {
    static final String ENTRY = "uvfixes_caverns_creativetab_config_guard";
    static final String DESC = "(Lnet/minecraft/world/item/CreativeModeTab$ItemDisplayParameters;Lnet/minecraft/world/item/CreativeModeTab$Output;)V";
    static final String CLASS_PATH = ".uvrun/cctabs/com/teamabnormals/caverns_and_chasms/core/other/CCCreativeTabs.class";

    static boolean isReal(AbstractInsnNode n) {
        return !(n instanceof LabelNode || n instanceof LineNumberNode || n instanceof FrameNode);
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

        int targets = 0, tcBefore = 0;
        for (MethodNode m : in.methods) {
            if (m.desc.equals(DESC)) {
                targets++;
                tcBefore += (m.tryCatchBlocks == null ? 0 : m.tryCatchBlocks.size());
            }
        }

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(ENTRY);
        if (entry == null) { System.out.println("FAIL: missing entry " + ENTRY); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        int tcAfter = 0, endReturn = 0, throwableHandlers = 0;
        for (MethodNode m : out.methods) {
            if (!m.desc.equals(DESC)) continue;
            int tc = (m.tryCatchBlocks == null ? 0 : m.tryCatchBlocks.size());
            tcAfter += tc;
            for (Object o : m.tryCatchBlocks) {
                TryCatchBlockNode t = (TryCatchBlockNode) o;
                if ("java/lang/Throwable".equals(t.type)) throwableHandlers++;
            }
            AbstractInsnNode last = m.instructions.getLast();
            while (last != null && !isReal(last)) last = last.getPrevious();
            if (last != null && last.getOpcode() == Opcodes.RETURN) endReturn++;
        }

        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("targets=" + targets + " | tryCatch " + tcBefore + "->" + tcAfter
            + " (added " + (tcAfter - tcBefore) + ", Throwable-handlers=" + throwableHandlers + ")"
            + " | DESC-methods-ending-RETURN=" + endReturn + " | classWrites=" + writes);

        boolean pass = targets == 2
            && (tcAfter - tcBefore) == 2
            && throwableHandlers == 2
            && endReturn == 2
            && writes;
        System.out.println(pass ? "\n==== CavernsTabs PASS ====" : "\n==== CavernsTabs FAIL ====");
    }
}
