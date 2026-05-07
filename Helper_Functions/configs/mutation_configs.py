## MUTATION ANALYSIS
# CONFIGS FOR PIT - to know where pit will find classes
sut_class_config_pit = {
    'CALC': {
        'pit': {
            'class_dir': "SUT/CALC",        # compiled class files for classpath
            'source_dir': "SUT/CALC"        # Java source files
        },
        'major': "SUT/CALC"                 # Major still needs source path
    },
    'basic': {
        'pit': {
            'class_dir': "SUT/basic/out",  # compiled classes
            'source_dir': "SUT/basic/indepth"  # source Java files
        },
        'major': "SUT/basic/indepth"
    },
    'rhino': {
        'pit': {
            'class_dir': 'SUT/rhino/rhino/build/classes/java/main',
            'source_dir': 'SUT/rhino/rhino/src/main/java'
        },
        'major': {
            'class_dir': 'SUT/rhino/rhino/build/classes/java/main',
            'source_dir': 'SUT/rhino/rhino/src/main/java'
        }
    },
    'nashorn': {
        "pit": {
            "class_dir": "SUT/nashorn/engine/classes",  # compiled .class files
            "source_dir": "SUT/nashorn/engine/classes"  # PIT needs the same path
        }
    },
    'karatejs': {
        "pit": {
            "class_dir": "SUT/karate-v2/karate-js/target/classes",  # compiled .class files
            "source_dir": "SUT/karate-v2/karate-js/target/classes"  # PIT needs the same path
        }
    },
    'graaljs':{
        "pit": {
            "class_dir": [
                "SUT/graalvm/graaljs/graal-js/mxbuild/jdk21/com.oracle.js.parser/bin",
                "SUT/graalvm/graaljs/graal-js/mxbuild/jdk21/com.oracle.truffle.js.parser/bin",
                "SUT/graalvm/graaljs/graal-js/mxbuild/jdk21/com.oracle.truffle.js/bin",
            ],

            "source_dir": "SUT/graalvm/graal-js/src"
        }
    }

}

def get_subject_program_mutation_config(subject_program):
    """
    Returns the mutation configuration for the given subject program.
    subject_program (str): The name of the subject program (e.g., 'CALC', 'basic').

    """
    mutation_config_map = {
        'CALC': {
            "target_classes": ["CalcLexer","CalcParser"],  # CalcLexer,CalcParser,
            "dependencies": ["SUT/CALC/antlr-3.2.jar"],
            'source_classes_directory': 'SUT/CALC',
            'package_prefix': None  # no package

        },
        'basic': {
            "target_classes": [
                "Program",  # Core execution logic, manages variables/statements
                # Control flow & logic
                "Statement",
                "IFStatement",
                "FORStatement",
                "NEXTStatement",
                "GOTOStatement",
                "GOSUBStatement",
                "RETURNStatement",
                "LETStatement",
                "DATAStatement",
                "READStatement",
                "DIMStatement",
                "ONStatement",
                "PRINTStatement",
                # # Expression and function evaluation
                "Expression",  # Generic expression tree
                "FunctionExpression",
                #
                # # Input/output (can keep or remove based on importance)
                # Following classes are big but either not covered (always not killed or killed with a certain pattern)
                # this is we found primarily redundant since all tools cover same mutants
                # "BASIC",  # Entry point and program driver
                # "CommandInterpreter",  # Executes commands entered by user
                #"LexicalTokenizer",
                #"ParseStatement",
                #"ParseExpression",
                # "RedBlackTree",
                # "KeyboardBuffer",
                # "ConsoleWindow",
                # "INPUTStatement" # we did not include input in our grammar since we are not taking any inputs
            ],
            "dependencies": [],
            'source_classes_directory': 'SUT/basic/out',
            'package_prefix': 'basic'  # Java package name
        },
        'rhino': {
            "target_classes": [
                # --- Functions & Calls ---
                #"ast.FunctionNode",
                # "ast.FunctionCall",

                # --- Variable declarations & assignments ---
               # "ast.VariableDeclaration",
               # "ast.VariableInitializer",
               # "ast.ExpressionStatement",
               # "ast.UpdateExpression",  # ++, --

                # --- Control flow structures ---
                "ast.IfStatement",
                "ast.ForLoop",
                "ast.WhileLoop",
                "ast.SwitchStatement",

                # --- Parser & context ---
                "Context",
                "Parser",
                "ScriptRuntime",
                "Interpreter",
                "Node",
                "optimizer.BodyCodegen",
                "regexp.NativeRegExp"

            ],
            "dependencies": [
                "SUT/rhino/rhino-engine/build/classes/java/main",
                "SUT/rhino/rhino-tools/build/classes/java/main",
                "SUT/rhino/rhino/build/resources/main"
            ],
            'source_classes_directory': 'SUT/rhino/rhino/build/classes/java/main',
            'package_prefix': 'org.mozilla.javascript'
        },
        'nashorn': {
            "target_classes": [
                # Correct parser path under internal
                "org.openjdk.nashorn.internal.parser.Parser",
                "org.openjdk.nashorn.internal.ir.LexicalContext",

                # Codegen components
                "org.openjdk.nashorn.internal.codegen.Compiler",
                "org.openjdk.nashorn.internal.codegen.CodeGenerator",

                # Runtime core
                "org.openjdk.nashorn.internal.runtime.Context",
                # "org.openjdk.nashorn.internal.runtime.ScriptObject",


                # Native objects
                "org.openjdk.nashorn.internal.objects.Global",

            ],

            "dependencies": [
                "SUT/nashorn/engine/nashorn.jar",
                "SUT/nashorn/engine/asm-7.3.1.jar",
                "SUT/nashorn/engine/asm-tree-7.3.1.jar",
                "SUT/nashorn/engine/asm-util-7.3.1.jar",
                "SUT/nashorn/engine/asm-analysis-7.3.1.jar",
                "SUT/nashorn/engine/asm-commons-7.3.1.jar",
            ],

            "source_classes_directory": "SUT/nashorn/engine/classes",

            "package_prefix": "org.openjdk.nashorn.internal"
        },
        'karatejs': {
            "target_classes": [
                # Correct parser path under internal
                "io.karatelabs.js.CoreContext",
                "io.karatelabs.js.Interpreter",
                "io.karatelabs.js.JsParser",
                "io.karatelabs.js.JsProperty",
                "io.karatelabs.js.Parser",
                "io.karatelabs.js.Terms",
                "io.karatelabs.js.Engine",
            ],

            "dependencies": [
                "SUT/karate-v2/karate-js/target/test-classes",
                "SUT/karate-v2/karate-js/target/dependency",
                "SUT/karate-v2/karate-js/target/karate-js-2.0.0.RC1.jar",
            ],
            "target_tests": "io.karatelabs.js.*Test,io.karatelabs.gherkin.*Test,io.karatelabs.common.*Test",

            "source_classes_directory": "SUT/karate-v2/karate-js/target/classes",

            "package_prefix": "io.karatelabs.js"
        },
        'graaljs': {
            "target_classes": [
                # === Core Parser / AST front-end ===
                "com.oracle.js.parser.Parser",  # core JS parser
                "com.oracle.js.parser.Lexer",  # JS lexer
                # "com.oracle.js.parser.AbstractParser",  # shared parser logic
                # "com.oracle.js.parser.ParserStrings",  # string intern table
                #
                # # === ECMAScript Frontend (Node factory, AST nodes) ===
                "com.oracle.truffle.js.parser.GraalJSParserHelper",  # central factory
                # "com.oracle.truffle.js.parser.JSParser",  # interface parser
                # "com.oracle.truffle.js.parser.date.DateParser",  # date parsing
                #
                # # === Execution Runtime ===
                "com.oracle.truffle.js.runtime.JSContext",  # VM context
                # "com.oracle.truffle.js.runtime.ParserOptions",  # parser settings
                # "com.oracle.truffle.js.runtime.JSParserOptions",  # truffle-side parser config
                #
                # # === Interpreter State / Execution Engine ===
                # "com.oracle.truffle.js.runtime.JSRealm",  # execution realm
                # "com.oracle.truffle.js.nodes.ScriptNode",  # top-level script node
                "com.oracle.truffle.js.nodes.function.FunctionRootNode",  # function execution
                "com.oracle.truffle.js.nodes.access.PropertyGetNode",  # core property access
                "com.oracle.truffle.js.nodes.access.PropertySetNode",  # property set logic
                #
                # # === Builtins (core behavior of JS) ===
                # "com.oracle.truffle.js.builtins.helper.ReplaceStringParser",
                # "com.oracle.truffle.js.builtins.json.TruffleJSONParser",
                # "com.oracle.truffle.js.builtins.helper.FloatParser",
                #
                # # === Temporal (ECMAScript Temporal API) — optional, but interesting ===
                # "com.oracle.truffle.js.runtime.util.TemporalParser",
            ],

            "dependencies": ["SUT/graalvm/GRAAL_JS_RUNTIME"],
            # # Location of compiled classes (we created this earlier)
            # "source_classes_directory": "SUT/graalvm/graaljs/graal-js/mxbuild/jdk21/",
            #
            # # Bytecode root for PIT
            # "class_dir": "SUT/graalvm/GRAAL_JS_RUNTIME"
        }

    }

    return mutation_config_map.get(subject_program, None)
