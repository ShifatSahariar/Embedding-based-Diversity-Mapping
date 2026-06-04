<start> ::= <define_var>{1} <stat>{2} "exit\n"
<stat> ::= <letExp> | <printExp> <NEWLINE>| <sumExp> <NEWLINE>| <avgExp> <NEWLINE>
<define_var> ::= <LET> <VAR> " = "<DIGIT> <NEWLINE>
<letExp> ::= <LET> <VAR> " = "<exp> <NEWLINE>
<exp> ::= <multExp> (" + " <multExp>)* | <multExp> (" - " <multExp>)*
<multExp> ::= <atom> | <atom> " * " <atom> | <atom> " / " <atom>
<atom> ::= <DIGIT> | <VAR> | <TRIG> "( " <exp> " )" | "( " <exp> " )"
<sumExp> ::= <SUM> <listExp> 
<listExp> ::= <exp> | <exp> " , " <listExp>
<avgExp> ::= <AVG> "(" <avgCalc>" )"
<avgCalc> ::= <exp> | <exp> "," <avgCalc>
<printExp> ::= <PRINT> <exp> | <PRINT> <avgExp> | <PRINT> <sumExp>
<LET> ::= "let " | "LET " | "Let "
<PRINT> ::= "print " | "PRINT " | "Print "
<TRIG> ::= "sin" | "cos" | "tan"
<SUM> ::= "sum " | "SUM " | "Sum "
<AVG> ::= "avg " | "AVG " | "Avg "
<VAR> ::= r'[A-Z]{1}'

<DIGIT> ::= r'[1-9]{2}'
<NEWLINE> ::= "\n"

# --------- CONSTRAINTS ---------

where all(var in *<define_var>.<VAR> for var in *<atom>.<VAR>)

