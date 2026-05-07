from fuzzingbook.Grammars import crange


def get_basic_grammar_fuzzingbook():
    basic_ebnf_grammar = {

        "<start>": [
            "<preamble>?<statementSeq><NEWLINE><print_numeric_stmt> ",
            "<preamble>?<NEWLINE><print_numeric_stmt><statementSeq>"
        ],

        "<preamble>": [
            "<let_statement><NEWLINE>",
            "<let_statement><NEWLINE><preamble>"
        ],

        "<statementSeq>": [
            "<statement>",
            "<statement><statementSeq>"
        ],

        # ======================================================
        # STATEMENTS
        # ======================================================
        "<statement>": [
            "<let_statement> <NEWLINE>",
            "<data_read_restore> <NEWLINE>",
            "<gosub_statement_with_return> <NEWLINE>",
            "<if_statement> <NEWLINE>",
            "<for_print_block> <NEWLINE>",
            "<optional_stmt> <NEWLINE>",
            "<print_statement> <NEWLINE>",
            "<on_statement> <NEWLINE>",
            "<dimension_statement> <NEWLINE>",
        ],

        # ======================================================
        # VARIABLE AND ASSIGNMENT
        # ======================================================
        "<let_statement>": [
            "<LET> <NUMERIC_VAR>=<numeric_assignment>",
            "<LET> <STRING_VAR>=<string_assignment>"
        ],

        "<numeric_assignment>": [
            "<numeric_exp>",
            "<numeric_function_call>",
            "<function_name_no_args>"
        ],

        "<string_assignment>": [
            "<string_exp>",
            "<string_function_call>"
        ],

        # ======================================================
        # DATA / READ / RESTORE GROUP
        # ======================================================
        "<data_read_restore>": [
            "<data_statement>",
            "<data_statement> <read_statement>",
            "<data_statement> <restore_statement>",
            "<data_statement> <read_statement> <restore_statement>"
        ],

        "<data_statement>": ["DATA <constant_list>"],
        "<read_statement>": ["READ <variable_list>"],
        "<restore_statement>": ["RESTORE"],

        # ======================================================
        # CONTROL FLOW: GOTO / GOSUB / RETURN
        # ======================================================
        "<goto_statement>": ["GOTO <line_number>"],
        "<gosub_statement>": ["GOSUB <line_number>"],
        "<return_statement>": ["<line_number> RETURN"],

        "<gosub_statement_with_return>": [
            "<gosub_statement> <NEWLINE> <return_statement>",
            "<goto_statement> <NEWLINE> <return_statement>"
        ],

        # ======================================================
        # CONDITIONALS
        # ======================================================
        "<if_statement>": [
            "IF <var_number_cmp> THEN <simple_stat> <NEWLINE>"
        ],

        "<var_number_cmp>": [
            "<NUMERIC_VAR> <comparison_operator> <NUMERIC_VAR>",
            "<NUMERIC_VAR> <comparison_operator> <number>",
            "<number> <comparison_operator> <NUMERIC_VAR>"
        ],

        "<comparison_operator>": ["=", ">", "<", ">=", "<="],

        "<simple_stat>": [
            "<let_statement>",
            "<goto_statement>",
            "<print_statement>",
            "<end_statement>"
        ],

        # ======================================================
        # LOOP BLOCK (FOR–PRINT–NEXT)
        # ======================================================
        "<for_print_block>": [
            "<for_statement> <print_numeric_stmt> <print_string_stmt_seq> <next_statement>",
            "<print_numeric_stmt> <print_string_stmt_seq> <next_statement>",
            "<for_statement> <print_numeric_stmt> <print_string_stmt_seq>"
        ],

        "<print_string_stmt_seq>": [
            "",
            "<print_string_stmt>",
            "<print_string_stmt> <print_string_stmt>"
        ],
        "<print_numeric_stmt>": [
            "PRINT <NUMERIC_VAR> <NEWLINE>",
            "PRINT <number> <NEWLINE>",
            "PRINT <NUMERIC_VAR> + <NUMERIC_VAR> <NEWLINE>"
        ],
        "<for_statement>": [
            "FOR <NUMERIC_VAR> = <numeric_exp> TO <numeric_exp>",
            "FOR <NUMERIC_VAR> = <numeric_exp> TO <numeric_exp> STEP <numeric_exp>"
        ],

        "<next_statement>": ["NEXT <NUMERIC_VAR>"],

        # ======================================================
        # PRINT STATEMENTS
        # ======================================================
        "<print_statement>": ["PRINT <printable_list>"],

        "<printable_list>": [
            "<printable>",
            "<printable> <separator> <printable_list>"
        ],

        "<printable>": [
            "<exp>",
            "<string>",
            "<variable>",
            "<numeric_function_call>",
            "<string_function_call>"
        ],

        "<separator>": [",", ";"],


        "<print_string_stmt>": [
            "PRINT <STRING_VAR> <NEWLINE>",
            'PRINT "<character>*" <NEWLINE>'
        ],

        # ======================================================
        # OPTIONAL STATEMENTS
        # ======================================================
        "<optional_stmt>": [
            "<randomize_statement>",
            "<rem_statement>",
            "<end_statement>",
            "<tron_statement>",
            "<troff_statement>",
            "<resume_statement>"
        ],

        "<randomize_statement>": ["RANDOMIZE"],
        "<end_statement>": ["END"],
        "<resume_statement>": ["RESUME"],
        "<tron_statement>": ["TRON ( <string>)?"],
        "<troff_statement>": ["TROFF"],

        "<rem_statement>": ["REM <comment>"],
        "<comment>": ['"<character>*"', "<STRING_VAR>", "<NUMERIC_VAR>"],

        # ======================================================
        # ON STATEMENT
        # ======================================================
        "<on_statement>": [
            "ON <NUMERIC_VAR> GOTO <line_number>",
            "ON <NUMERIC_VAR> GOSUB <line_number>"
        ],

        # ======================================================
        # DIMENSION (ARRAY DECLARATIONS)
        # ======================================================
        "<dimension_statement>": ["DIM <array_declaration_list>"],
        "<array_declaration_list>": ["<array_declaration>(, <array_declaration>)*"],
        "<array_declaration>": ["<NUMERIC_VAR>(<dimension_list>)"],
        "<dimension_list>": ["<digit>(, <digit>)*"],

        # ======================================================
        # EXPRESSIONS
        # ======================================================
        "<exp>": ["<numeric_exp>", "<string_exp>"],

        "<numeric_exp>": ["<term>", "<term> <add_op> <term>"],
        "<term>": ["<factor>", "<factor> <mul_op> <factor>"],
        "<factor>": ["<number>", "<NUMERIC_VAR>", "( <numeric_exp> )", "<numeric_function_call>"],

        "<add_op>": ["+", "-"],
        "<mul_op>": ["*", "/"],

        # ======================================================
        # FUNCTION CALLS
        # ======================================================
        "<numeric_function_call>": [
            "<function_name_with_single_numeric_exp>(<numeric_exp>)",
            "<function_name_with_two_exp>(<numeric_exp>, <numeric_exp>)"
        ],

        "<string_function_call>": [
            "<function_name_with_single_string_exp>(<string_exp>)",
            "<string_fn_with_numeric_arg>(<numeric_exp>)",
            "<function_name_with_string_and_exp>(<STRING_VAR>, <numeric_exp>)",
            "<function_name_with_string_and_two_exp>(<STRING_VAR>, <numeric_exp>, <numeric_exp>)"
        ],

        "<function_name_with_single_numeric_exp>": [
            "RND", "INT", "SIN", "COS", "TAN", "ATN", "SQR", "ABS", "LOG", "SGN"
        ],

        "<function_name_with_single_string_exp>": ["VAL", "LEN"],
        "<string_fn_with_numeric_arg>": ["STR$", "CHR$", "SPC$", "TAB$"],
        "<function_name_with_two_exp>": ["MAX", "MIN"],
        "<function_name_with_string_and_exp>": ["LEFT$", "RIGHT$"],
        "<function_name_with_string_and_two_exp>": ["MID$"],
        "<function_name_no_args>": ["FRE"],

        # ======================================================
        # STRINGS, VARIABLES & CONSTANTS
        # ======================================================
        "<string_exp>": ["<string>", "<STRING_VAR>"],
        "<string>": ['"<character>+"'],

        "<variable_list>": ["<variable>(, <variable>)*"],
        "<variable>": ["<NUMERIC_VAR>", "<STRING_VAR>"],

        "<constant_list>": ["<constant>(, <constant>)*"],
        "<constant>": ["<number>", "<string>"],

        # ======================================================
        # TOKENS AND CHARACTER SETS
        # ======================================================
        "<NUMERIC_VAR>": ["<LETTER>", "<LETTER><LETTER_OR_DIGIT>"],
        "<STRING_VAR>": ["<LETTER>$", "<LETTER><LETTER_OR_DIGIT>$"],
        "<LETTER>": crange('A', 'Z') + crange('a', 'z'),
        "<LETTER_OR_DIGIT>": crange('A', 'Z') + crange('a', 'z') + crange('0', '9'),
        "<digit>": crange('0', '9'),

        "<number>": [
            "<digit>+",
            "<digit>+.<digit>+",
            "<digit>+<E>?<digit>+",
            "<digit>+.<digit>+<E>?<digit>+"
        ],

        "<E>": ["E"],
        "<line_number>": [str(i) for i in range(10, 200, 10)],
        "<character>": crange('A', 'Z') + crange('a', 'z') + [" ", "!", "?", ".", ",", "*"],
        "<LET>": ["LET", "let", "Let"],
        "<NEWLINE>": ["\n"]
    }

    return basic_ebnf_grammar
