# package is most important when we are indicating any class
subject_program_config = {
    # CALC has no package, so we did not use any package with main class
    'calc': {
        'subject_program_name': 'calc',
        'classes_root': 'SUT/CALC',
        'source_classes_directory':'SUT/CALC',
        'package_prefix': None,
        'main_class': 'CalcParser',
        'dependencies': ['SUT/CALC/antlr-3.2.jar'],
        'class_files': [
            "SUT/CALC/CalcLexer.class",
            "SUT/CALC/CalcParser.class"
        ],
        'exit_command': 'exit'
    },
    'rhino': {
        'subject_program_name': 'rhino',
        'classes_root': 'SUT/rhino/rhino/build/classes/java/main',  # core runtime
        'source_classes_directory': 'SUT/rhino/rhino/build/classes/java/main',
        'package_prefix': 'org.mozilla.javascript',
        'main_class': 'org.mozilla.javascript.tools.shell.Main',
        'dependencies': [
            'SUT/rhino/rhino-engine/build/classes/java/main',
            'SUT/rhino/rhino-tools/build/classes/java/main',
            'SUT/rhino/rhino/build/resources/main'
        ],
        'class_files': [ "SUT/rhino/rhino/build/classes/java/main/org/mozilla/javascript/Parser.class",],
        'exit_command': 'quit();'
    },
    'karatejs': {
        'subject_program_name': 'karatejs',
        'classes_root': 'SUT/karate-v2/karate-js/target/classes',  # core runtime
        'source_classes_directory': 'SUT/karate-v2/karate-js/target/classes',
        'package_prefix': 'io.karatelabs.js',
        'main_class': 'io.karatelabs.js.JsLauncher',
        'input_execution_mode': 'file_arg',
        'dependencies': [
            'SUT/karate-v2/karate-js/target/karate-js-2.0.0.RC1.jar',
            'SUT/karate-v2/karate-js/target/dependency/*'
        ],
        'class_files': [
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/Engine.class',
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/Parser.class',
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/Interpreter.class',
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/JsString.class',
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/JsNumber.class',
            'SUT/karate-v2/karate-js/target/classes/io/karatelabs/js/JsObject.class',
        ],
        'exit_command': ''
    },

    'nashorn': {
        'subject_program_name': 'nashorn',

        # PIT and JaCoCo look for bytecode to mutate/inspect
        'classes_root': 'SUT/nashorn/engine/classes',
        # Same as classes_root
        'source_classes_directory': 'SUT/nashorn/engine/classes',
        'package_prefix': 'org.openjdk.nashorn',
        # MAIN CLASS (the runner)
        # ---------------------------------------------------------
        # No package → direct top-level class
        'main_class': 'NashornRunner',
        # DEPENDENCIES
        # ---------------------------------------------------------
        # These are appended to classpath for running + coverage + PIT
        'dependencies': [
            # Runner directory (contains NashornRunner.class)
            'SUT/nashorn/runner',
            # Nashorn engine JAR
            'SUT/nashorn/engine/nashorn.jar',
            # ASM JARs required by Nashorn engine
            'SUT/nashorn/engine/asm-7.3.1.jar',
            'SUT/nashorn/engine/asm-tree-7.3.1.jar',
            'SUT/nashorn/engine/asm-util-7.3.1.jar',
            'SUT/nashorn/engine/asm-analysis-7.3.1.jar',
            'SUT/nashorn/engine/asm-commons-7.3.1.jar'
        ],

        # ---------------------------------------------------------
        # CLASSES TO MUTATE (PIT representative selection)
        # ---------------------------------------------------------
        # You don't need to list all classes — just key ones for analysis.
        'class_files': [
            'SUT/nashorn/engine/classes/org/openjdk/nashorn/internal/parser/Parser.class'
        ],

        # ---------------------------------------------------------
        # EXIT COMMAND
        # ---------------------------------------------------------
        # NashornRunner is batch-only → no exit command
        'exit_command': None
    },

    'graaljs': {
        'subject_program_name': 'graaljs',

        # Where the CLASS FILES live (used for PIT and mutant injection)
        'classes_root': 'SUT/graalvm/GRAAL_JS_RUNTIME',
        # Where your JARs live
        'source_classes_directory': 'SUT/graalvm/GRAAL_JS_RUNTIME',
        # Main class for running JS files
        'main_class': 'com.oracle.truffle.js.shell.JSLauncher',
        # No package prefix needed
        'package_prefix': None,
        # The JARs required to *run* the interpreter
        'dependencies': [
            'SUT/graalvm/GRAAL_JS_RUNTIME'  # Python code will expand to all jars
        ],
        # JVM flags we must always add
        'jvm_flags': [
            '-Dpolyglotimpl.AttachLibraryFailureAction=ignore',
            '-Dpolyglot.engine.WarnInterpreterOnly=false',
            '-Dpolyglot.log.file=/dev/null'
        ],

        # No exit command needed — JSLauncher just runs file and exits
        'exit_command': None,
    },

    'basic': {
        'subject_program_name': 'basic',
        'classes_root': 'SUT/basic/out/',
        'source_classes_directory':'SUT/basic/out/',
        'package_prefix':'basic',
        'main_class': 'basic.BASIC',
        'class_files': [
            # Have to cover all the classes related with Parsing [ expression, statement ]
            "SUT/basic/out/basic/Program.class",
            "SUT/basic/out/basic/BASIC.class",
            "SUT/basic/out/basic/BooleanExpression.class",
            "SUT/basic/out/basic/CommandInterpreter.class",
            "SUT/basic/out/basic/ConsoleWindow.class",
            "SUT/basic/out/basic/ConstantExpression.class",
            "SUT/basic/out/basic/DATAStatement.class",
            "SUT/basic/out/basic/DIMStatement.class",
            "SUT/basic/out/basic/ENDStatement.class",
            "SUT/basic/out/basic/Expression.class",
            "SUT/basic/out/basic/FORStatement.class",
            "SUT/basic/out/basic/FunctionExpression.class",
            "SUT/basic/out/basic/GOSUBStatement.class",
            "SUT/basic/out/basic/GOTOStatement.class",
            "SUT/basic/out/basic/IFStatement.class",
            "SUT/basic/out/basic/INPUTStatement.class",
            "SUT/basic/out/basic/LETStatement.class",
            "SUT/basic/out/basic/NEXTStatement.class",
            "SUT/basic/out/basic/LexicalTokenizer.class",
            "SUT/basic/out/basic/ONStatement.class",
            "SUT/basic/out/basic/ParseExpression.class",
            "SUT/basic/out/basic/ParseStatement.class",
            "SUT/basic/out/basic/PRINTStatement.class",
            "SUT/basic/out/basic/RANDOMIZEStatement.class",
            "SUT/basic/out/basic/READStatement.class",
            "SUT/basic/out/basic/REMStatement.class",
            "SUT/basic/out/basic/RESTOREStatement.class",
            "SUT/basic/out/basic/RETURNStatement.class",
            "SUT/basic/out/basic/Statement.class",
            "SUT/basic/out/basic/STOPStatement.class",
            "SUT/basic/out/basic/StringExpression.class",
            "SUT/basic/out/basic/TROFFStatement.class",
            "SUT/basic/out/basic/TRONStatement.class",
            "SUT/basic/out/basic/Variable.class"

        ],
        'dependencies': [],
        'exit_command': 'bye'
    }
}
