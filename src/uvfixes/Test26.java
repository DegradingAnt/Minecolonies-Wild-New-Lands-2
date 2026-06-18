import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.CheckClassAdapter;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class Test26 {
    static final String OWNER = "io/gitlab/jfronny/libjf/unsafe/asm/patch/targeting/InterfaceImplTargetPatch";
    static final String TARGET_CLASS =
        ".uvrun/libjf_dump/unsafe_jij/io/gitlab/jfronny/libjf/unsafe/asm/patch/targeting/InterfaceImplTargetPatch.class";

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");

        ClassNode node = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(TARGET_CLASS))).accept(node, 0);
        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get("uvfixes_libjf_interfaceimpl_deadlock");
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, node);

        // ---- structural checks ----
        MethodNode helper = find(out, "uvScanByName", "(Ljava/lang/String;)V");
        System.out.println("[1] uvScanByName method present: " + (helper != null ? "PASS" : "FAIL"));

        MethodNode scan = find(out, "scanInterfaces", "(Lorg/objectweb/asm/tree/ClassNode;)V");
        boolean loadClassGone = !contains(scan, in -> in instanceof MethodInsnNode mi
            && mi.owner.equals("java/lang/ClassLoader") && mi.name.equals("loadClass"));
        boolean scanCallsHelper = contains(scan, in -> in instanceof MethodInsnNode mi
            && mi.owner.equals(OWNER) && mi.name.equals("uvScanByName"));
        System.out.println("[2] scanInterfaces: loadClass removed=" + loadClassGone + " calls uvScanByName=" + scanCallsHelper
            + "  " + ((loadClassGone && scanCallsHelper) ? "PASS" : "FAIL"));

        MethodNode upper = find(out, "getUpper", "(Ljava/lang/String;)Ljava/util/Set;");
        boolean forNameGone = !contains(upper, in -> in instanceof MethodInsnNode mi
            && mi.owner.equals("java/lang/Class") && mi.name.equals("forName"));
        boolean scanClassGone = !contains(upper, in -> in instanceof MethodInsnNode mi
            && mi.owner.equals(OWNER) && mi.name.equals("scanInterfaces") && mi.desc.equals("(Ljava/lang/Class;)V"));
        boolean upperCallsHelper = contains(upper, in -> in instanceof MethodInsnNode mi
            && mi.owner.equals(OWNER) && mi.name.equals("uvScanByName"));
        System.out.println("[3] getUpper: forName removed=" + forNameGone + " scanInterfaces(Class) removed=" + scanClassGone
            + " calls uvScanByName=" + upperCallsHelper + "  "
            + ((forNameGone && scanClassGone && upperCallsHelper) ? "PASS" : "FAIL"));

        // ---- structural verification with frames recomputed (as ModLauncher does) ----
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
            protected String getCommonSuperClass(String a, String b) {
                try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
            }
        };
        out.accept(cw);
        var sw = new java.io.StringWriter();
        CheckClassAdapter.verify(new ClassReader(cw.toByteArray()), false, new java.io.PrintWriter(sw));
        System.out.println("[4] full-class verify: " + (sw.toString().isEmpty() ? "CLEAN PASS" : "PROBLEMS:\n" + sw));

        // ---- runtime: copy uvScanByName into a standalone probe, retarget refs, run it ----
        runtimeProbe(helper);
    }

    static void runtimeProbe(MethodNode helperOrig) throws Exception {
        final String PROBE = "UvProbe";
        // retarget INTERFACES field, recursive call, and the LDC class-constant from OWNER -> PROBE
        for (AbstractInsnNode in : helperOrig.instructions.toArray()) {
            if (in instanceof FieldInsnNode fi && fi.owner.equals(OWNER) && fi.name.equals("INTERFACES")) fi.owner = PROBE;
            if (in instanceof MethodInsnNode mi && mi.owner.equals(OWNER) && mi.name.equals("uvScanByName")) mi.owner = PROBE;
            if (in instanceof LdcInsnNode ld && ld.cst instanceof Type t && t.getInternalName().equals(OWNER))
                ld.cst = Type.getObjectType(PROBE);
        }
        ClassNode probe = new ClassNode();
        probe.version = Opcodes.V17;
        probe.access = Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER;
        probe.name = PROBE;
        probe.superName = "java/lang/Object";
        probe.fields.add(new FieldNode(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "INTERFACES", "Ljava/util/Map;", null, null));
        probe.methods.add(helperOrig);

        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
            protected String getCommonSuperClass(String a, String b) {
                try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
            }
        };
        probe.accept(cw);
        byte[] bytes = cw.toByteArray();

        ClassLoader cl = new ClassLoader(Test26.class.getClassLoader()) {
            Class<?> def(String n, byte[] b) { return defineClass(n, b, 0, b.length); }
        };
        Class<?> probeClass = (Class<?>) cl.getClass().getDeclaredMethod("def", String.class, byte[].class)
            .invoke(cl, PROBE, bytes);

        Map<String, Object> map = new HashMap<>();
        probeClass.getField("INTERFACES").set(null, map);
        var mh = probeClass.getDeclaredMethod("uvScanByName", String.class);
        mh.setAccessible(true);

        String seed = "org/objectweb/asm/tree/MethodNode";
        long t0 = System.nanoTime();
        mh.invoke(null, seed);
        long ms = (System.nanoTime() - t0) / 1_000_000;

        boolean terminated = true; // invoke returned => no infinite loop / deadlock
        boolean hasSeed = map.containsKey(seed);
        Object seedSupers = map.get(seed);
        boolean walkedUp = map.size() > 1;                       // recursion populated ancestors
        boolean foundAbstract = map.containsKey("org/objectweb/asm/tree/AbstractInsnNode"); // not a super of MethodNode, but reachable? no
        boolean foundObjectOrNode = map.containsKey("java/lang/Object") || map.containsKey("org/objectweb/asm/tree/AbstractInsnNode");
        System.out.println("[5] runtime uvScanByName: returned in " + ms + "ms (no deadlock/hang)  " + (terminated ? "PASS" : "FAIL"));
        System.out.println("    INTERFACES entries=" + map.size() + "  seed present=" + hasSeed
            + "  seedDirectSupers=" + seedSupers);
        System.out.println("[6] transitive walk populated ancestors (size>1): " + (walkedUp ? "PASS" : "FAIL")
            + "  reachedJavaLangObject=" + map.containsKey("java/lang/Object"));
        // sanity: MethodNode's superclass should be present as a key after recursion
        Object ms2 = null;
        if (seedSupers instanceof Set<?> set && !set.isEmpty()) {
            String sup = (String) set.iterator().next();
            ms2 = map.get(sup);
        }
        System.out.println("    one ancestor entry sample: " + ms2);
    }

    // helpers
    interface P { boolean t(AbstractInsnNode in); }
    static boolean contains(MethodNode m, P p) {
        if (m == null) return false;
        for (AbstractInsnNode in : m.instructions.toArray()) if (p.t(in)) return true;
        return false;
    }
    static MethodNode find(ClassNode c, String n, String d) {
        for (MethodNode m : c.methods) if (m.name.equals(n) && m.desc.equals(d)) return m;
        return null;
    }
}
