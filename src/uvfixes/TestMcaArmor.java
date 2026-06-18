import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 38 (uvfixes_mca_vanilla_render_when_geckolib_armor):
// HEAD-guards net.conczin.mca.MCAClient.useGeneticsRenderer(UUID)Z so it returns false when the
// player wears GeckoLib (GeoItem) armor -> MCA renders the player vanilla model+armor (Epic Paladins
// etc. fit again). Verifies: (a) exactly 1 target method, (b) 4 INSTANCEOF GeoItem inserted (one per
// armor slot), (c) 1 getPlayerByUUID call, (d) more instructions than before, (e) the patched class
// re-serializes under COMPUTE_FRAMES (catches the slot-1/2 stack-map-frame risk at the cont label).
public class TestMcaArmor {
    static final String ENTRY = "uvfixes_mca_vanilla_render_when_geckolib_armor";
    static final String NAME = "useGeneticsRenderer";
    static final String DESC = "(Ljava/util/UUID;)Z";
    static final String CLASS_PATH = ".uvrun/mcatest/net/conczin/mca/MCAClient.class";

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("_dev/uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(CLASS_PATH))).accept(in, 0);

        int beforeInsns = -1, targetsBefore = 0;
        for (MethodNode m : in.methods)
            if (m.name.equals(NAME) && m.desc.equals(DESC)) { targetsBefore++; beforeInsns = m.instructions.size(); }
        System.out.println("[1] target methods before=" + targetsBefore + " (insns=" + beforeInsns + ")");

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(ENTRY);
        if (entry == null) { System.out.println("FAIL: missing entry " + ENTRY); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        int targets = 0, afterInsns = -1, geo = 0, getPlayer = 0, ireturn = 0;
        for (MethodNode m : out.methods) {
            if (!(m.name.equals(NAME) && m.desc.equals(DESC))) continue;
            targets++; afterInsns = m.instructions.size();
            for (AbstractInsnNode n = m.instructions.getFirst(); n != null; n = n.getNext()) {
                if (n instanceof TypeInsnNode && n.getOpcode() == Opcodes.INSTANCEOF
                    && "software/bernie/geckolib/animatable/GeoItem".equals(((TypeInsnNode) n).desc)) geo++;
                if (n instanceof MethodInsnNode && "getPlayerByUUID".equals(((MethodInsnNode) n).name)) getPlayer++;
                if (n.getOpcode() == Opcodes.IRETURN) ireturn++;
            }
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

        System.out.println("targets=" + targets + " | insns " + beforeInsns + "->" + afterInsns
            + " | GeoItem-instanceof=" + geo + " | getPlayerByUUID-calls=" + getPlayer
            + " | IRETURN-total=" + ireturn + " | classWrites(COMPUTE_FRAMES)=" + writes);

        boolean pass = targets == 1 && geo == 4 && getPlayer == 1 && afterInsns > beforeInsns && writes;
        System.out.println(pass ? "\n==== McaArmor PASS ====" : "\n==== McaArmor FAIL ====");
    }
}
