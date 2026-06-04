# -------------------- BASIC --------------------

<start> ::= <preamble> <stmt>+ <print_numeric_stmt>{1}<bye>{1}

<preamble> ::= <let_stmt_numeric>{2} | <let_stmt_string>{2}


<stmt> ::= (
    <if_stmt> |
    <for_stmt> |
    <print_string_stmt> |
    <next_statement> |
    <gosub_statement_with_return> |
    <data_read_restore> |
    <dimension_statement> |
    <on_statement> |
    <optional__stmt>
)

<gosub_statement_with_return> ::= <gosub_statement> <return_statement> 
<gosub_statement> ::= "GOSUB " <line_number> "\n"
<return_statement> ::= <line_number> " RETURN" "\n"

<on_statement> ::= "ON " <NUMERIC_VAR> " " <goto_or_gosub> <line_number>"\n"

<stop_statement> ::= "STOP" "\n"
<end_statement> ::= "END" "\n"
<let_stmt_numeric> ::= <LET> <NUMERIC_VAR> " = " <numeric_assignment>
<let_stmt_string> ::= <LET> <STRING_VAR> " = " <string_assignment> 

<numeric_assignment> ::= <number> "\n" | <numeric_function_call> "\n"

<numeric_function_call> ::= (
    <function_name_with_single_numeric_exp> "(" <numeric_exp> ")"
    | <function_name_with_two_exp> "(" <numeric_exp> ", " <numeric_exp> ")" 
    | "FRE"
    | <function_name_with_single_string_exp> "(" <string> ")"
)

<function_name_with_single_string_exp> ::= "LEN" | "VAL"
<function_name_with_single_numeric_exp> ::= "RND" | "INT" | "SIN" | "COS" | "TAN" | "ATN" | "SQR" | "ABS" | "LOG" | "SGN"
<function_name_with_two_exp> ::= "MAX" | "MIN"

<string_assignment> ::= <string> "\n" | <string_function_call> "\n"

<string_function_call> ::= (
    <function_name_with_single_num_exp> "(" <numeric_exp> ")"
    | <function_name_with_string_and_an_exp> "(" <string> ", " <digit> ")"
    | "MID$" "(" <string> ", " <digit> "," <digit> ")"
)

<function_name_with_single_num_exp> ::= "STR$" | "CHR$" | "SPC$" | "TAB$"
<function_name_with_string_and_an_exp> ::= "LEFT$" | "RIGHT$"

<print_stmt> ::= <print_numeric_stmt> | <print_string_stmt>
<print_numeric_stmt> ::= "PRINT " <NUMERIC_VAR> "\n"
<print_string_stmt> ::= "PRINT " <STRING_VAR> "\n"

<if_stmt> ::= "IF " <var_number_cmp> " THEN " <simple_stat> "\n"

<for_stmt> ::= "FOR " <NUMERIC_VAR> " = " <factor> " TO " <factor>{2} (" STEP " <number>)? "\n"
<next_statement> ::= "NEXT " <NUMERIC_VAR> "\n"

<simple_stat> ::= <let_stmt_numeric> | <goto_statement> | <print_stmt> | <stop_statement> | <end_statement>
<goto_statement> ::= "GOTO " <line_number> "\n"

<data_statement> ::= "DATA " <constant> "\n"
<read_statement> ::= "READ " <variable> "\n"
<restore_statement> ::= "RESTORE" "\n"
<data_read_restore> ::= <data_statement> <read_statement>? <restore_statement>?

<dimension_statement> ::= "DIM " <array_declaration_list> "\n"
<array_declaration_list> ::= <ARRAY_VAR> "(" <dimension_list> ")"
<dimension_list> ::= <digit> | <digit> "," <digit>

<optional__stmt> ::= (
    <randomize_stmt> |
    <rem_stmt> |
    <stop_statement> |
    <end_statement> |
    <tron_statement> |
    <troff_statement> |
    <resume_statement>
)
<randomize_stmt> ::= "RANDOMIZE" "\n"
<rem_stmt> ::= "REM " <string> "\n"
<tron_statement> ::= "TRON" "\n"
<troff_statement> ::= "TROFF" "(" <string>? ")" "\n"
<resume_statement> ::= "RESUME" "\n"

<LET> ::= "LET " | "let " | "Let "

# -------------------- Helper- Terminals --------------------

<var_number_cmp> ::= <NUMERIC_VAR> <comparison_operator> <number>
<numeric_exp> ::= <term> | <term> <add_op> <term>
<term> ::= <factor> | <factor> <mul_op> <factor>
<factor> ::= <digit>{1}

<add_op> ::= "+" | " - "
<mul_op> ::= "*" | " / "

<digit> ::= r'[1-9]'
<STRING_VAR> ::= r'[A-Z]{1}\$'
<NUMERIC_VAR> ::= r'[a-z]{1}'
<ARRAY_VAR> ::= r'[A-Za-z]{2}'
<line_number> ::= r'\d{1}'
<variable> ::= <NUMERIC_VAR> | <STRING_VAR>
<goto_or_gosub> ::= "GOTO " | "GOSUB "
<constant> ::= <number> | <string>
<string> ::= r'"[A-Za-z0-9 ]{5}"'
<number> ::= r'\d{1,2}'
<comparison_operator> ::= " = " | " < " | " > "
<bye> ::= "bye" "\n"

