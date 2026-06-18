import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.CheckClassAdapter;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 29 (ec_an_plugin ECPluginItems server-safe @SubscribeEvent stub).
public class Test29 {
    static boolean hasSub(MethodNode m) {
        if (m.visibleAnnotations == null) return false;
        for (AnnotationNode a : m.visibleAnnotations)
            if (a.desc.equals("Lnet/neoforged/bus/api/SubscribeEvent;")) return true;
        return false;
    }
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(".uvrun/ecan_test/ECPluginItems.class"))).accept(in, 0);
        int before = in.methods.size();
        boolean hadSubBefore = false;
        for (MethodNode m : in.methods) if (hasSub(m)) hadSubBefore = true;

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get("uvfixes_ecan_server");
        if (entry == null) { System.out.println("FAIL: missing entry uvfixes_ecan_server"); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        MethodNode added = null;
        for (MethodNode m : out.methods) if (m.name.equals("uvfixes$serverSafeNoop")) added = m;
        boolean methodAdded = added != null;
        boolean isStatic   = methodAdded && (added.access & Opcodes.ACC_STATIC) != 0;
        boolean descOk     = methodAdded && added.desc.equals("(Lnet/neoforged/fml/event/lifecycle/FMLCommonSetupEvent;)V");
        boolean annoOk     = methodAdded && hasSub(added);
        // idempotency: applying twice must not add a 2nd stub
        ClassNode out2 = (ClassNode) fn.call(entry, out);
        int stubs = 0; for (MethodNode m : out2.methods) if (m.name.equals("uvfixes$serverSafeNoop")) stubs++;
        boolean idempotent = stubs == 1;

        // bytecode validity (tolerant common-superclass like ModLauncher)
        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("methods " + before + "->" + out.methods.size()
            + " | hadSubEvent_before=" + hadSubBefore
            + " | added=" + methodAdded + " static=" + isStatic + " desc_ok=" + descOk
            + " @SubscribeEvent=" + annoOk + " idempotent=" + idempotent + " classWrites=" + writes);
        boolean pass = methodAdded && isStatic && descOk && annoOk && idempotent && writes;
        System.out.println(pass ? "\n==== Fix29 PASS ====" : "\n==== Fix29 FAIL ====");
    }
}
