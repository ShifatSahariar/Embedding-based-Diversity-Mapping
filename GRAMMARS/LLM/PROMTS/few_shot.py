# --- FEW-SHOT EXAMPLES (per compiler) ---
import json


def build_assistant_fewshot(compiler_name: str) -> str:
    examples = {
        "basic": [
            {
                "id": 1,
                "constructs": ["arithmetic", "print"],
                "program": "LET A = 5\nLET B = 10\nPRINT A+B\nBYE"
            },
            {
                "id": 2,
                "constructs": ["loop", "print"],
                "program": "FOR I = 1 TO 3\nPRINT I\nNEXT I\nBYE"
            }
        ],

        "CALC": [
            {
                "id": 1,
                "constructs": ["sum", "print"],
                "program": "let A = 5\nlet B = 10\nsum A,B\nprint A+B\nexit"
            },
            {
                "id": 2,
                "constructs": ["average", "print"],
                "program": "let X = 3\nlet Y = 9\navg(X,Y)\nprint Y-X\nexit"
            }
        ],

        "rhino": [
            {
                "id": 1,
                "constructs": ["variable", "arithmetic"],
                "program": (
                    "var x = 5;\n"
                    "var y = 10;\n"
                    "var sum = x + y;"
                )
            },
            {
                "id": 2,
                "constructs": ["function", "return"],
                "program": (
                    "function multiply(a, b) {\n"
                    "    return a * b;\n"
                    "}"
                )
            },
            {
                "id": 3,
                "constructs": ["loop", "condition"],
                "program": (
                    "for (var i = 0; i < 3; i++) {\n"
                    "    if (i == 2) {\n"
                    "        break;\n"
                    "    }\n"
                    "}"
                )
            },
            {
                "id": 4,
                "constructs": ["try", "catch", "throw"],
                "program": (
                    "try {\n"
                    "    throw new Error('Something went wrong');\n"
                    "} catch (e) {\n"
                    "    var msg = e.message;\n"
                    "}"
                )
            },
            {
                "id": 5,
                "constructs": ["print"],
                "program": (
                    "print('Hello, Rhino!');"
                )
            }
        ]

    }

    # Return consistent JSON structure
    return json.dumps({
        "compiler": compiler_name,
        "tests": examples.get(compiler_name.lower(), [])
    }, ensure_ascii=False)
