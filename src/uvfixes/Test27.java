import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.CheckClassAdapter;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

// Offline test for PackFixes Fix 27 (createaeronauticscurios 2.0 typewriter-mixin neuter).
public class Test27 {
    static final String DIR = ".uvrun/aerocurios_test/in/com/titammods/aeronautics_curios_compat/mixin/";

    // (entry key in initializeCoreMod, class file, expected injectors removed, methods that MUST survive)
    static final Object[][] CASES = {
        {"uvfixes_aerocurios_typewriter_be", "MixinLinkedTypewriterBlockEntity.class", 6,
            new String[]{"saveAdditional", "loadAdditional", "isRunOnServer", "setClientCheck"}},
        {"uvfixes_aerocurios_typewriter_entries", "MixinLinkedTypewriterEntries.class", 0, new String[]{}},
        {"uvfixes_aerocurios_typewriter_interaction", "MixinLinkedTypewriterInteractionHandler.class", 1, new String[]{}},
    };

    static boolean isInjector(MethodNode m) {
        if (m.visibleAnnotations == null) return false;
        for (AnnotationNode a : m.visibleAnnotations) {
            if (a.desc.startsWith("Lcom/llamalad7/mixinextras/injector/")) return true;
            switch (a.desc) {
                case "Lorg/spongepowered/asm/mixin/injection/Inject;":
                case "Lorg/spongepowered/asm/mixin/injection/ModifyArg;":
                case "Lorg/spongepowered/asm/mixin/injection/ModifyArgs;":
                case "Lorg/spongepowered/asm/mixin/injection/ModifyConstant;":
                case "Lorg/spongepowered/asm/mixin/injection/ModifyVariable;":
                case "Lorg/spongepowered/asm/mixin/injection/Redirect;":
                    return true;
            }
        }
        return false;
    }

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() returned " + transformers.size() + " coremod entries: "
            + (transformers.size() > 0 ? "PASS" : "FAIL"));

        boolean allPass = true;
        for (Object[] c : CASES) {
            String key = (String) c[0];
            String file = (String) c[1];
            int expectRemoved = (Integer) c[2];
            String[] mustSurvive = (String[]) c[3];

            ClassNode in = new ClassNode();
            new ClassReader(Files.readAllBytes(Path.of(DIR + file))).accept(in, 0);
            int injectorsBefore = 0;
            for (MethodNode m : in.methods) if (isInjector(m)) injectorsBefore++;

            ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(key);
            if (entry == null) { System.out.println("  !! missing entry " + key); allPass = false; continue; }
            ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
            ClassNode out = (ClassNode) fn.call(entry, in);

            int injectorsAfter = 0;
            for (MethodNode m : out.methods) if (isInjector(m)) injectorsAfter++;
            int removed = injectorsBefore - injectorsAfter;

            boolean noInjectorsLeft = injectorsAfter == 0;
            boolean removedRight = removed == expectRemoved;
            boolean survived = true;
            Set<String> names = new HashSet<>();
            for (MethodNode m : out.methods) names.add(m.name);
            StringBuilder missing = new StringBuilder();
            for (String s : mustSurvive) if (!names.contains(s)) { survived = false; missing.append(s).append(" "); }

            // verify the transformed class still passes the verifier
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw);
            var sw = new java.io.StringWriter();
            CheckClassAdapter.verify(new ClassReader(cw.toByteArray()), false, new java.io.PrintWriter(sw));
            boolean verifies = sw.toString().isEmpty();

            boolean pass = noInjectorsLeft && removedRight && survived && verifies;
            allPass &= pass;
            System.out.println("[" + file + "] injectors " + injectorsBefore + "->" + injectorsAfter
                + " (removed " + removed + ", expect " + expectRemoved + ")"
                + " survivors_ok=" + survived + (missing.length() > 0 ? "(missing " + missing + ")" : "")
                + " verify=" + (verifies ? "CLEAN" : "PROBLEMS") + "  " + (pass ? "PASS" : "FAIL"));
            if (!verifies) System.out.println("    verify output:\n" + sw);
        }
        System.out.println(allPass ? "\n==== ALL PASS ====" : "\n==== FAIL ====");
    }
}
