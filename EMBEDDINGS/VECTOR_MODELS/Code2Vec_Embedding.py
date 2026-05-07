import re
import subprocess
import shutil
import os

from Helper_Functions.HelperFunctions import clear_directory


def copy_to_input_java(input_file_path, code2vec_input_path):
    shutil.copy(input_file_path, code2vec_input_path)


def run_code2vec(input_data_path, code2vec_path, output_vector_directory):
    """
    Runs the code2vec our_trained_models to generate code vectors for the input Java file.

    This function executes the code2vec our_trained_models on a specified Java file to generate code vectors.
    It then saves the vector part of the output to a text file in the specified output directory.

    Args:
        input_data_path (str): Path to the input Java file that will be processed by code2vec.
        code2vec_path (str): Path to the directory where the code2vec our_trained_models and scripts are located.
        output_vector_directory (str): Directory where the output vector file will be saved.

    Returns:
        str: The path to the generated output vector file.

    Example:
        run_code2vec('path/to/input/Example.java', 'path/to/code2vec/', 'path/to/output_vectors/')

        This will generate a vector file 'Example_vector.txt' in the 'path/to/output_vectors/' directory
        based on the input 'Example.java' processed by the code2vec our_trained_models.
    """
    # Define the command to run code2vec prediction
    command = [
        'python3', 'code2vec.py',
        '--load', 'models/java14_model/saved_model_iter8.release',
        '--predict', '--export_code_vectors'
    ]
    # Start the code2vec process
    process = subprocess.Popen(command,
                               cwd=code2vec_path,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)

    # Send the input result followed by 'Enter'
    process.stdin.write('\n')
    process.stdin.flush()
    # Read the output
    output, errors = process.communicate()
    # Check for errors
    if errors:
        print(f"Error: {errors}")
        # The name of the output file is derived from the name of the input file
    # ONLY vector part is saving
    code_vector_section = extract_code_vector(output)
    base_name = os.path.basename(input_data_path)
    output_file_name = base_name.replace(".java", "_vector.txt")
    output_vector_path = os.path.join(output_vector_directory, output_file_name)

    # Run the code2vec prediction command and redirect stdout to the output vector file
    with open(output_vector_path, 'w') as output_file:
        output_file.write(code_vector_section)

    # Return the path to the output vector file
    return output_vector_path


def export_vectors_code2vec(output_vector_for_subject_directory, converted_input_to_java_files_directory):
    """
     Exports code vectors for a collection of Java files using the code2vec our_trained_models.

     Example:
         export_vectors('/path/to/code2vec/our_trained_models', '/path/to/output/vectors', '/path/to/converted/java/files')

         This will take all `.java` files from the 'converted/java/files' directory, copy them to 'Input.java' inside the
         code2vec our_trained_models folder, generate vectors,
         and save the vector output for each Java file in the 'output/vectors' directory.


         :param converted_input_to_java_files_directory: directory containing the Java files for which vectors are to be generated.
         :param code2vec_model_path: Directory where the code2vec our_trained_models
         :param output_vector_for_subject_directory: directory where the output vector files will be saved.
     """
    code2vec_model_path = 'EMBEDDINGS/VECTOR_MODELS/code2vec'
    # Get a list of all Java files in the input directory
    java_files = [f for f in os.listdir(converted_input_to_java_files_directory) if f.endswith('.java')]

    # Path to the Input.java file used by code2vec
    # we will use Input.java file to replace our java code inside this file
    # cause code2vec will use this file as input to generate vectors
    copy_to_input_dot_java_path = os.path.join(code2vec_model_path, 'Input.java')

    # Loop over all Java files
    for java_file in java_files:
        # Full path to the Java file
        java_file_path = os.path.join(converted_input_to_java_files_directory, java_file)

        # Copy the Java file content to Input.java
        copy_to_input_java(java_file_path, copy_to_input_dot_java_path)

        # Run code2vec on the Input.java file and save the output vector
        output_code_vector_path = run_code2vec(java_file_path, code2vec_model_path, output_vector_for_subject_directory)
        print(f"Output VECTORS_COLLECTION saved to: {output_code_vector_path}")
    # Once the generation of vectors is done:-
    # We have to filter and keep only the vector parts from each generated vector file
    # Because each vector file also contains other details rather than only the vectors
    extract_code_vector(output_vector_directory_for_subject_program=output_vector_for_subject_directory)


def extract_code_vector(output_vector_directory_for_subject_program):
    """
    :param output_vector_directory_for_subject_program:
    Extracts the code vector section from the output of the code2vec process.

    Looking for a section in the output string
    that starts with 'Code vector':
    and ends at 'Modify the file.'
    It then extracts the content between these two markers,
    which represents the code vector
    generated by the code2vec our_trained_models

    Returns:
        str: The extracted code vector section,
        or a message
        indicating that the code vector was not found.

    Example:
        Given the following `output` string:
        '''
        Code vector: [0.12, 0.85, 0.34]
        Modify the file:
        '''
        The function will return:
        '[0.12, 0.85, 0.34]'
    """
    # Pattern to match the start of the code vector section and end at the modified prompt
    pattern = re.compile(r'Code vector:(.*?)Modify the file:', re.DOTALL)

    # Search for the code vector section
    match = pattern.search(output_vector_directory_for_subject_program)
    if match:
        # Extract and return the code vector part, stripping leading/trailing whitespace
        return match.group(1).strip()
    else:
        # If there is no match, return an indication of not found
        return "Code vector section not found."


# Assuming 'output' is the string containing the entire output of process.communicate()
# >>>>>>>>>>>> RUN Code2Vec <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# #Once the Conversion is done , now the next tasks are:
# - Take each java file and copy into "Input.java" file in the code2vec directory
# - run the command to have the vector
# - save the vector into the code2vec_vectors directory
# """
#
# output_vector_directory = 'VECTORS_COLLECTION/CALC/code2vec_vectors'
# converted_input_to_java_files_directory = "../COVERAGE_REPORTS/CONVERTED_JAVA_METHODS/CALC/INPUTS_AS_JAVA_METHOD"
#
# # Before re-generate, we may clear the old vectors
# clear_directory(output_vector_directory)
# # Export the vector embedding for the subject programs generated inputs
# export_vectors_code2vec(output_vector_for_subject_directory=output_vector_directory,
#                         converted_input_to_java_files_directory=converted_input_to_java_files_directory)
# # # We have to filter and keep only the vector parts from each generated vector file
# # # Because each vector file also contains other details rather than only the vectors
# # code_vector_section = extract_code_vector(output_vector_directory_for_subject_program=output_vector_directory)
# # print(code_vector_section)
