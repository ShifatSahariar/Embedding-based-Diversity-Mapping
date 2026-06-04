import os
import shutil

from EMBEDDINGS.VECTOR_MODELS.CodeBERT_Embedding import export_codebert_vectors
from EMBEDDINGS.VECTOR_MODELS.GraphCodeBERT_Embedding import export_graphcodebert_vectors
from EMBEDDINGS.VECTOR_MODELS.OpenAI_Embedding import export_openai_embeddings

from EMBEDDINGS.VECTORS_COLLECTION.codet_5_plus_embeddings import export_codet5_small_vectors

from EMBEDDINGS.VECTOR_MODELS.codestral_Embedding import export_codestral_vectors
print("[DEBUG-CR] Starting import of qwen3_Embedding")
from EMBEDDINGS.VECTOR_MODELS.qwen3_Embedding import export_qwen3_vectors
print("[DEBUG-CR] Starting import of sfrembed_embedding")
from EMBEDDINGS.VECTOR_MODELS.sfrembed_embedding import export_sfrembed_vectors
from EMBEDDINGS.VECTOR_MODELS.uni_x_coder_Embedding import export_uniXcoder_vectors


from Helper_Functions.HelperFunctions import clear_directory

# constant values for vector our_trained_models types
CODE2VEC = 'code2vec'
CODEBERT = 'codeBERT'
OPENAI = 'openai'
GRAPH_CODEBERT = 'graphcodeBERT'

# constant values for subject programs
CALC = 'CALC'
BASIC = 'basic'


def get_directories(vector_model_type, subject_program):
    """
    Returns the input and output directories based on the subject program and vector our_trained_models type.

    Args:
        vector_model_type (str): The type of vector our_trained_models (e.g., 'code2vec', 'codeBERT').
        subject_program (str): The name of the subject program (e.g., 'CALC', 'basic').

    Returns:
        tuple: A tuple containing input directory and output directory paths.

    """
    # Directory: From where will read the JAVA methods
    input_dir = f"GENERATED_INPUTS/{subject_program.upper()}"
    # Output directory pattern based on vector our_trained_models and subject program
    if vector_model_type == "CODE2VEC":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/code2vec_vectors"
    elif vector_model_type == "CODEBERT":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/codeBERT_vectors"
        # output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/codeBERT_vectors_gen_file"
    elif vector_model_type == "OPENAI":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/openai_vectors"
    elif vector_model_type == "GRAPH_CODEBERT":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/graphcodeBERT_vectors"
    elif vector_model_type == "SFR":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/SFR_vectors"
    elif vector_model_type == "UNIXCODER":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/uniXcoder_vectors"
    elif vector_model_type == "CODET5_PLUS":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/codeT5_plus_vectors"
    elif vector_model_type == "CODE_STRAL":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/codestral_vectors"
    elif vector_model_type == "QWEN3":
        output_dir = f"EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}/qwen3_vectors"
    else:
        raise ValueError(f"Unsupported vector our_trained_models type: {vector_model_type}")

    # input directory exists or not
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    return input_dir, output_dir


def generate_embeddings(vector_model_type, subject_program):
    """
    Generates vector embeddings based on the vector our_trained_models type and subject program.

    Usage:
        vector_model_type = CODE2VEC
        subject_program = CALC
        generate_embeddings(vector_model_type, subject_program)

        # input_dir = 'PATH/CALC/INPUTS_AS_JAVA_METHOD'
        # output_dir = 'PATH/CALC/code2vec_vectors'
        :param vector_model_type: The type of embedding our_trained_models to use (e.g., 'code2vec', 'codeBERT').
        :param subject_program: Subject program for which the embeddings are generated (e.g., 'CALC', 'basic').
    """
    # Avoiding CASE-SENSITIVE NAME
    vector_model_type = vector_model_type.upper()
    subject_program = subject_program.upper()

    # Getting the input and output directories based on our_trained_models type and subject program
    input_dir, output_dir = get_directories(vector_model_type, subject_program)
    print(f"Directory for inputs{input_dir}")
    clear_directory(output_dir)

    # if vector_model_type == "CODE2VEC":
    #     print(f"Generating code2vec vectors for {subject_program}...")
    #     export_vectors_code2vec(output_vector_for_subject_directory=output_dir,
    #                             converted_input_to_java_files_directory=input_dir)
    if vector_model_type == "CODEBERT":
        print(f"Generating CodeBERT vectors for {subject_program}...")
        export_codebert_vectors(input_dir, output_dir)
    elif vector_model_type == "SFR":
        print(f"Generating SFR vectors for {subject_program}...")
        export_sfrembed_vectors(input_dir, output_dir)
    elif vector_model_type == "OPENAI":
        print(f"Generating OpenAI vectors for {subject_program}...")
        export_openai_embeddings(input_dir, output_dir)
    elif vector_model_type == "GRAPH_CODEBERT":
        print(f"Generating GraphCodeBERT vectors for {subject_program}...")
        export_graphcodebert_vectors(input_dir, output_dir)
    elif vector_model_type == "UNIXCODER":
        print(f"Generating UniXcoder vectors for {subject_program}...")
        export_uniXcoder_vectors(input_dir, output_dir)
    elif vector_model_type == "CODET5_PLUS":
        print(f"Generating CODET5_PLUS vectors for {subject_program}...")
        export_codet5_small_vectors(input_dir, output_dir)
    elif vector_model_type == "CODE_STRAL":
        print(f"Generating CODESTRAL vectors for {subject_program}...")
        export_codestral_vectors(input_dir, output_dir)
    elif vector_model_type == "QWEN3":
        print(f"Generating QWEN3 vectors for {subject_program}...")
        export_qwen3_vectors(input_dir, output_dir)
    # elif vector_model_type == "VOYAGE_CODE_3":
    #     print(f"Generating VOYAGE_CODE_3 vectors for {subject_program}...")
    #     export_voyage_vectors(input_dir, output_dir)

    else:
        raise ValueError(f"Unsupported vector our_trained_models type: {vector_model_type}")


