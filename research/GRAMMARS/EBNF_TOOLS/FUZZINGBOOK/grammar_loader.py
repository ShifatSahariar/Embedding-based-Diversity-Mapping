from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.BASIC.basic_grammar import get_basic_grammar_fuzzingbook
from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.CALC.calc_grammar import get_calc_grammar
from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.KARATEJS.karatejs_grammar import get_karatejs_grammar

from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.RHINO.rhino_grammar import get_rhino_grammar


# this is the version of EBNF grammar of SUBJECT PROGRAMS


def get_gram(grammar_type='CALC'):
    """
       Example:
           calc_grammar = get_gram('CALC') # Returns the calculator grammar
       """

    # Add more grammars here for other subject programs
    # Return the appropriate grammar based on the type passed as an argument
    if grammar_type == 'calc':
        return get_calc_grammar()
    elif grammar_type == 'basic':
        return get_basic_grammar_fuzzingbook()
    elif grammar_type == 'rhino':
        return get_rhino_grammar()
    elif grammar_type == 'karatejs':
        return get_karatejs_grammar()
    else:
        raise ValueError(f"Unsupported grammar type: {grammar_type}")
