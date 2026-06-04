package io.karatelabs.js;

import java.nio.file.Files;
import java.nio.file.Paths;

public class JsLauncher {

    public static void main(String[] args) throws Exception {

        if (args.length == 0) {
            System.err.println("Usage: java JsRunner <script.js>");
            System.exit(1);
        }

        String path = args[0];
        String script = new String(Files.readAllBytes(Paths.get(path)));

        Engine engine = new Engine();

        try {
            Object result = engine.eval(script);
            System.out.println(result == null ? "" : result.toString());
        } catch (Exception e) {
            System.err.println("JS ERROR: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
