<start> ::= <preamble> <stmt>+ <bye>{1}

<preamble> ::= <let_stmt_numeric>{2} | <let_stmt_string>{2}

<stmt> ::= (
    <if_stmt>? 
    <for_stmt>? 
    <print_numaric_stmt>{1}
    <print_string_stmt>*
    <next_statement>?
    <gosub_statement_with_return>?
    <data_read_restore>?
    <dimension_statement>?
    <on_statement>?
    <optional__stmt>?
)

<gosub_statement_with_return> ::= <return_statement> <gosub_statement>
<return_statement> ::= <line_number> " RETURN" "\n"
<gosub_statement> ::= "GOSUB " <line_number> "\n"

<on_statement> ::= "ON " <NUMERIC_VAR> " " <goto_or_gosub> <line_number>"\n"

<optional__stmt> ::= <randomize_stmt> | <rem_stmt> | <stop_statement> | <end_statement> | <troff_statement> | <tron_statement> | <resume_statement>

<randomize_stmt> ::= "RANDOMIZE" "\n"
<rem_stmt> ::= "REM " <string> "\n"
<stop_statement> ::= "STOP" "\n"
<end_statement> ::= "END" "\n"
<troff_statement> ::= "TROFF" "(" <string>? ")" "\n"
<tron_statement> ::= "TRON" "\n"
<resume_statement> ::= "RESUME" "\n"

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

<print_stmt> ::= <print_numaric_stmt> | <print_string_stmt>
<print_numaric_stmt> ::= "PRINT " <NUMERIC_VAR> "\n"
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

# -------------------- Constraints --------------------

# All variables used in IF conditions are previously defined using LET (numeric)
where all(var in *<let_stmt_numeric>.<NUMERIC_VAR> for var in *<if_stmt>[1].<NUMERIC_VAR>)

# Loop variables used in FOR loops are declared using LET (numeric).
where all(var in *<let_stmt_numeric>.<NUMERIC_VAR> for var in *<for_stmt>[1])

# Variables printed with numeric PRINT are declared using LET (numeric).
where all(var in *<let_stmt_numeric>.<NUMERIC_VAR> for var in *<print_numaric_stmt>.<NUMERIC_VAR>)

# Variables printed with string PRINT are declared using LET (string).
where all(var in *<let_stmt_string>.<STRING_VAR> for var in *<print_string_stmt>.<STRING_VAR>)

# Confirm- RETURN line number exists in GOSUB statement.
where all(line in *<gosub_statement_with_return>.<return_statement>.<line_number> for line in *<gosub_statement_with_return>.<gosub_statement>.<line_number>)


# Matching types in READ/DATA based on variable type.
# If READ has uppercase variables (e.g., A$), constants must be strings.
# If READ has lowercase variables (e.g., x), constants must be numeric.
where (
  (
    all(var.isupper() for var in *<data_read_restore>.<read_statement>.<variable>) and 
    all(const.startswith('"') for const in *<data_read_restore>.<data_statement>.<constant>)
  ) 
  or 
  (
    all(var.islower() for var in *<data_read_restore>.<read_statement>.<variable>) and 
    all(const.isdigit() for const in *<data_read_restore>.<data_statement>.<constant>)
  )
)

# If NEXT is used, ensure it matches the loop variable declared in FOR.
where (
  not *<next_statement> or
  (
    *<for_stmt> and
    all(n == f for n, f in zip(*<next_statement>.<NUMERIC_VAR>, *<for_stmt>.<NUMERIC_VAR>))
  )
)

# If ON statement is present, the variable used must be declared using numeric LET.
where all(var in *<let_stmt>.<NUMERIC_VAR> for var in *<on_statement>.<NUMERIC_VAR>)
