from fuzzingbook.Grammars import crange


def get_calc_grammar():
    calc_ebnf_grammar = {
        "<start>": ["<prog>"],
        "<prog>": ["<stat>+"],
        "<stat>": ["<exp> <NEWLINE>",
                   "<letExp> <NEWLINE>",
                   "<printExp> <NEWLINE>",
                   "<sumExp> <NEWLINE>",
                   "<avgExp> <NEWLINE>"],
        "<letExp>": ["<LET> <VAR> = <exp>"],
        "<exp>": ["<multExp>( + <multExp>)*", "<multExp>( - <multExp>)*"],

        "<multExp>": ["<atom>", "<atom> * <atom>", "<atom> / <atom>"],
        "<atom>": ["<BD>", "<VAR>", "<TRIG> (<exp>)", "(<exp>)"],
        "<sumExp>": ["<SUM> (<listExp>)"],
        "<listExp>": ["<exp>(,<listExp>)?"],
        "<avgExp>": ["<AVG> (<avgCalc>)"],
        "<avgCalc>": ["<exp>(,<avgCalc>)?"],

        "<printExp>": ["<PRINT> <exp>", "<PRINT> <avgExp>", "<PRINT> <sumExp>"],

        "<LET>": ["let", "LET", "Let"],
        "<PRINT>": ["print", "PRINT", "Print"],
        "<TRIG>": ["sin", "cos", "tan"],
        "<SUM>": ["sum", "SUM", "Sum"],
        "<AVG>": ["avg", "AVG", "Avg"],

        "<VAR>": ["<CAPITAL_LETTER><VAR_NEXT>"],
        "<VAR_NEXT>": ["<CAPITAL_LETTER>", "<SMALL_LETTER>", "<DIGIT>"],
        "<CAPITAL_LETTER>": crange('A', 'Z'),
        "<SMALL_LETTER>": crange('a', 'z'),
        "<DIGIT>": crange('0', '9'),
        "<BD>": ["<DIGIT>", "<DIGIT><DIGIT>"],
        "<NEWLINE>": ["\n"]

    }
    return calc_ebnf_grammar


