import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import java.nio.file.Files;
import java.nio.file.Path;

public class ParseCheck {
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        if (engine == null) { System.out.println("NO ENGINE"); System.exit(2); }
        String src = Files.readString(Path.of(args[0]));
        engine.eval(src); // declares initializeCoreMod, runs no transformer code
        Object result = ((javax.script.Invocable) engine).invokeFunction("initializeCoreMod");
        java.util.Map<?, ?> map = (java.util.Map<?, ?>) result;
        System.out.println("PARSE OK, transformers: " + map.keySet());
    }
}
