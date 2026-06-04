from fuzzingbook.Grammars import extend_grammar
from fuzzingbook.ProbabilisticGrammarFuzzer import set_prob


def set_probabilities_calc(calc_probabilistic_grammar):
    grammar = calc_probabilistic_grammar
    set_prob(grammar, "<stat>", "<sumExp> <NEWLINE>", 0.3)
    set_prob(grammar, "<stat>", "<avgExp> <NEWLINE>", 0.3)
    set_prob(grammar, "<stat>", "<letExp> <NEWLINE>", 0.2)
    set_prob(grammar, "<stat>", "<printExp> <NEWLINE>", 0.2)
    set_prob(grammar, "<stat-1>", "<stat>", 0.8)
    set_prob(grammar, "<stat-1>", "<stat><stat-1>", 0.2)

def set_probabilities_basic(basic_probabilistic_grammar):
    grammar = basic_probabilistic_grammar

    # Make programs moderate length: prefer single-statement expansion 60% vs recursion 40%
    set_prob(grammar, "<statementSeq>", "<statement>", 0.6)
    set_prob(grammar, "<statementSeq>", "<statement><statementSeq>", 0.4)

    # <statement> diversity — 100% total
    # increased LET and FOR and PRINT to favor observable, useful constructs
    set_prob(grammar, "<statement>", "<let_statement> <NEWLINE>", 0.20)
    set_prob(grammar, "<statement>", "<data_read_restore> <NEWLINE>", 0.06)
    set_prob(grammar, "<statement>", "<gosub_statement_with_return> <NEWLINE>", 0.03)
    set_prob(grammar, "<statement>", "<if_statement> <NEWLINE>", 0.12)
    set_prob(grammar, "<statement>", "<for_print_block> <NEWLINE>", 0.20)
    set_prob(grammar, "<statement>", "<optional_stmt> <NEWLINE>", 0.05)
    set_prob(grammar, "<statement>", "<print_statement> <NEWLINE>", 0.18)
    set_prob(grammar, "<statement>", "<on_statement> <NEWLINE>", 0.06)
    set_prob(grammar, "<statement>", "<dimension_statement> <NEWLINE>", 0.10)

    # <optional_stmt> — 100% total (keep REM common, but bound others; reduce some noisy options)
    set_prob(grammar, "<optional_stmt>", "<randomize_statement>", 0.10)
    set_prob(grammar, "<optional_stmt>", "<rem_statement>", 0.30)
    set_prob(grammar, "<optional_stmt>", "<end_statement>", 0.10)
    set_prob(grammar, "<optional_stmt>", "<tron_statement>", 0.15)
    set_prob(grammar, "<optional_stmt>", "<troff_statement>", 0.10)
    set_prob(grammar, "<optional_stmt>", "<resume_statement>", 0.25)

    # <printable> — ensure numeric / expression bias (100% total)
    # favor numeric/expressions a bit more to create more numeric output and richer numeric expressions
    set_prob(grammar, "<printable>", "<exp>", 0.35)
    set_prob(grammar, "<printable>", "<string>", 0.12)
    set_prob(grammar, "<printable>", "<variable>", 0.18)
    set_prob(grammar, "<printable>", "<numeric_function_call>", 0.25)
    set_prob(grammar, "<printable>", "<string_function_call>", 0.10)

    # <for_print_block> — 100% total
    # keep the canonical FOR..PRINT..NEXT form common, but give a bit more chance to short for/print combos
    # <for_print_block> — 100% total
    set_prob(grammar, "<for_print_block>",
             "<for_statement> <print_numeric_stmt> <print_string_stmt_seq> <next_statement>", 0.57)
    set_prob(grammar, "<for_print_block>",
             "<print_numeric_stmt> <print_string_stmt_seq> <next_statement>", 0.14)
    set_prob(grammar, "<for_print_block>",
             "<for_statement> <print_numeric_stmt> <print_string_stmt_seq>", 0.29)

    # <if_statement> remains deterministic
    set_prob(grammar, "<if_statement>", "IF <var_number_cmp> THEN <simple_stat> <NEWLINE>", 1.0)

    # <var_number_cmp> — keep balanced comparisons between variables and constants
    set_prob(grammar, "<var_number_cmp>", "<NUMERIC_VAR> <comparison_operator> <NUMERIC_VAR>", 0.40)
    set_prob(grammar, "<var_number_cmp>", "<NUMERIC_VAR> <comparison_operator> <number>", 0.35)
    set_prob(grammar, "<var_number_cmp>", "<number> <comparison_operator> <NUMERIC_VAR>", 0.25)

    # <numeric_function_call> — favor single-arg functions slightly (100% total)
    set_prob(grammar, "<numeric_function_call>", "<function_name_with_single_numeric_exp>(<numeric_exp>)", 0.60)
    set_prob(grammar, "<numeric_function_call>", "<function_name_with_two_exp>(<numeric_exp>, <numeric_exp>)", 0.40)

    # <string_function_call> — bias toward simpler string ops
    set_prob(grammar, "<string_function_call>", "<function_name_with_single_string_exp>(<string_exp>)", 0.40)
    set_prob(grammar, "<string_function_call>", "<string_fn_with_numeric_arg>(<numeric_exp>)", 0.20)
    set_prob(grammar, "<string_function_call>", "<function_name_with_string_and_exp>(<STRING_VAR>, <numeric_exp>)", 0.20)
    set_prob(grammar, "<string_function_call>", "<function_name_with_string_and_two_exp>(<STRING_VAR>, <numeric_exp>, <numeric_exp>)", 0.20)

    # <exp> and <numeric_exp> — 100% totals
    set_prob(grammar, "<exp>", "<numeric_exp>", 0.65)
    set_prob(grammar, "<exp>", "<string_exp>", 0.35)

    set_prob(grammar, "<numeric_exp>", "<term>", 0.6)
    set_prob(grammar, "<numeric_exp>", "<term> <add_op> <term>", 0.4)

    # <simple_stat> — favor LET and PRINT in simple statements (100% total)
    set_prob(grammar, "<simple_stat>", "<let_statement>", 0.42)
    set_prob(grammar, "<simple_stat>", "<goto_statement>", 0.18)
    set_prob(grammar, "<simple_stat>", "<print_statement>", 0.27)

    set_prob(grammar, "<simple_stat>", "<end_statement>", 0.13)

    return grammar


"""

RHINO CORPUS ::::::
if (...) → 69%
if (...) else (...) → 31%
for  ≈ 55%
while ≈ 43%
do-while ≈ 1%
for-in ≈ <1% (implied)

throw new Error(...)  ≈ 30%
throw TypeError(...)  ≈ 20%
throw string          ≈ 10%
throw identifier      ≈ 10%
others split small %

~18% function declarations
~82% statements


"""


def set_probabilities_rhino(grammar):

        # -------------------------------
        # STATEMENT MIX (Total 1.00)
        # -------------------------------
        set_prob(grammar, "<statement>", "<variableStatement>", 0.15)
        set_prob(grammar, "<statement>", "<arrayDeclaration>", 0.08)
        set_prob(grammar, "<statement>", "<objectDeclaration>", 0.07)
        set_prob(grammar, "<statement>", "<expressionStatement>", 0.20)
        set_prob(grammar, "<statement>", "<ifStatement>", 0.10)
        set_prob(grammar, "<statement>", "<iterationStatement>", 0.12)
        set_prob(grammar, "<statement>", "<switchStatement>", 0.05)
        set_prob(grammar, "<statement>", "<tryStatement>", 0.08)
        set_prob(grammar, "<statement>", "<printStatement>", 0.08)
        set_prob(grammar, "<statement>", "<functionDeclaration>", 0.07)

        # -------------------------------
        # IF / ELSE Distribution
        # -------------------------------
        set_prob(grammar, "<ifStatement>",
                 "if ( <expression> ) { <simpleStatementList> }", 0.6)
        set_prob(grammar, "<ifStatement>",
                 "if ( <expression> ) { <simpleStatementList> } else { <simpleStatementList> }", 0.4)

        # -------------------------------
        # LOOP Distribution
        # -------------------------------
        set_prob(grammar, "<iterationStatement>",
                 "while ( <expression> ) { <simpleStatementList> }", 0.45)
        set_prob(grammar, "<iterationStatement>",
                 "for ( var <identifier> = <numericLiteral> ; <expression> ; <identifier> ++ ) { <simpleStatementList> }", 0.55)



        # -------------------------------
        # EXPRESSION Distribution
        # -------------------------------
        set_prob(grammar, "<expression>", "<numericLiteral>", 0.15)
        set_prob(grammar, "<expression>", "<identifier>", 0.25)
        set_prob(grammar, "<expression>", "<identifier> + <identifier>", 0.10)
        set_prob(grammar, "<expression>", "<identifier> - <identifier>", 0.10)
        set_prob(grammar, "<expression>", "<identifier> * <identifier>", 0.10)
        set_prob(grammar, "<expression>", "<identifier> / <identifier>", 0.08)
        set_prob(grammar, "<expression>", "<identifier> . <property>", 0.05)
        set_prob(grammar, "<expression>", "<identifier> [ <expression> ]", 0.05)
        set_prob(grammar, "<expression>", "<identifier> ( <argumentList> )", 0.05)
        set_prob(grammar, "<expression>", "<identifier> . <property> ( <argumentList> )", 0.07)

        # -------------------------------
        # PRINT Distribution
        # -------------------------------
        # set_prob(grammar, "<printStatement>", "print(<identifier>) ;", 0.5)
        # set_prob(grammar, "<printStatement>", "print(<numericLiteral>) ;", 0.25)
        # set_prob(grammar, "<printStatement>", "print(<stringLiteral>) ;", 0.25)

        # -------------------------------
        # FUNCTION Declaration / Return
        # -------------------------------
        set_prob(grammar, "<functionDeclaration>",
                 "function <identifier> ( <formalParameterList> ) { <functionBody> }", 1.0)
        set_prob(grammar, "<functionBody>",
                 "<simpleStatementList>\nreturn <expression> ;", 0.7)
        set_prob(grammar, "<functionBody>",
                 "<simpleStatementList>\nreturn ;", 0.3)




def get_probabilistic_grammar(subject_program, bnf_grammar):
    """
    Returns a probabilistic grammar after setting probabilities based on the subject program.

    Args:
        subject_program (str): The name of the subject program (e.g., 'CALC', 'sql').

    Returns:
        dict: The probabilistic grammar with the probabilities set.
        :param bnf_grammar:
    """
    extended_grammar = extend_grammar(bnf_grammar)

    if subject_program == 'calc':
        set_probabilities_calc(extended_grammar)
    elif subject_program == 'basic':
        set_probabilities_basic(extended_grammar)
    elif subject_program == 'rhino':
        set_probabilities_rhino(extended_grammar)
    elif subject_program == 'karatejs':
        set_probabilities_rhino(extended_grammar)
    else:
        raise ValueError(f"Unsupported subject program: {subject_program}")

    return extended_grammar
