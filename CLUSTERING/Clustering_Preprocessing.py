from CLUSTERING.Clustering_Algo_Operations import clustering
from CLUSTERING.Clustering_Process import clustering_process
from COVERAGE_REPORTS.Coverage_Profile import cluster_region_map_with_profile
from Gini_Impurity_Analysis import calculate_and_save_gini_impurities
from Helper_Functions.HelperFunctions import load_vectors_from_files

"""
SELECTION of K:Number of Clusters
Guided By: Number of Unique Coverage Profiles

"""



def automate_clustering_process(subject_program, pca=1.0, runs=20, decimal_places=3, process_type="mutation",
                                profile_limit=None,EMBEDDING_MODEL_ORIGINAL="SFR"):
    """
    Automates the clustering process based on the subject program and process type.

        :param EMBEDDING_MODEL_ORIGINAL:
        :param profile_limit: How many profiles do we want to use for testing purposes.
    """

    base_vector_directory = f"../EMBEDDINGS/VECTORS_COLLECTION/{subject_program.upper()}"
    base_results_directory = f"../RESULTS/{subject_program.upper()}"

    vector_directories = {
        EMBEDDING_MODEL_ORIGINAL: f"{base_vector_directory}/{EMBEDDING_MODEL_ORIGINAL}_vectors",
        f"fine_tuned_{EMBEDDING_MODEL_ORIGINAL}": f"{base_vector_directory}/{EMBEDDING_MODEL_ORIGINAL}_refined_vectors"
    }
    # save_cluster_result_path =f"{base_results_directory}/Report_with_contrastive_{EMBEDDING_MODEL_ORIGINAL}"
    save_cluster_result_path = f"{base_results_directory}/JULY/FAN/graphcodeBERT" #codet5_small #qwen3 #graphcodeBERT #uniXcoder

    # Clustering algorithms: we are testing with
    # AffinityPropagation has been added inside for now
    # HDBSCAN + OPTICS: were giving 1-3 clusters only [ self-cluster number determined]
    # False: we have to provide K, True: Self-determined K
    clustering_algorithms = [
        ("KMeans", False),
        ("Agglomerative", False),
        # ("GMM", False),
        ("Birch", False),
        ("SpectralClustering", False),
        ("AffinityPropagation", True),  # self-determining
        # ("HDBSCAN", True),  # self-determining
        # ("MeanShift", True),  # self-determining
        # ("OPTICS", True),  # self-determining # not considering
    ]

    print(f"Vector directories: {vector_directories}")

    # Functionality for a clustering process
    clustering_process(vector_directories=vector_directories,
                       clustering_algorithms=clustering_algorithms,
                       base_results_directory=base_results_directory,
                       save_cluster_result_path = save_cluster_result_path,
                       pca=pca,
                       runs=runs,
                       decimal_places=decimal_places,
                       process_type=process_type,
                       subject_program=subject_program,
                       profile_limit=profile_limit)
