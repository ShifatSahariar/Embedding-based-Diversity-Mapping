import hdbscan
import numpy as np
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans, AgglomerativeClustering, AffinityPropagation, SpectralClustering, MeanShift, OPTICS, \
    Birch
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture



def clustering(vectors, num_clusters, save_plot_path, identifiers, algo="AffinityPropagation", pca_variance=1.0):
    """
    :param pca_variance: variance to retain in PCA (e.g., 1.0 for 100%, 0.9 for 90%).
    :param identifiers: Identifiers corresponding to each vector.
    :param save_plot_path: Path to save the cluster visualization.
    :param num_clusters: The number of clusters (used by algorithms like KMeans, Agg, GMM).
    :param vectors: Vectors profiles of the inputs
    Returns:
        A dictionary mapping file identifiers to cluster labels, and the number of clusters.
    """


    X = np.array(vectors)

    random_seed = 42
    # to avoid 'UnboundLocalError'
    labels = None
    if len(X) == 0 or X.ndim != 2:
        raise ValueError(f"Invalid vectors.{X.shape}")

    # Apply PCA based on the specified variance
    if pca_variance < 1.0:
        pca = PCA()
        pca.fit(X)
        explained_variance_ratio = pca.explained_variance_ratio_
        cumulative_variance = np.cumsum(explained_variance_ratio)
        num_components = np.argmax(cumulative_variance >= pca_variance) + 1

        # Ensure that num_components does not exceed min(n_samples, n_features)
        num_components = min(num_components, min(X.shape))

        # Apply PCA with the determined number of components
        pca = PCA(n_components=num_components)
        X = pca.fit_transform(X)
    else:
        pass
    #     # If pca_variance is 1.0, apply PCA but keep only as many components as min(n_samples, n_features)
    #     num_components = min(X.shape)
    #     pca = PCA(n_components=num_components)
    #     X = pca.fit_transform(X)

    # Perform clustering based on the chosen algorithm
    if algo == "AffinityPropagation":
        # determines the number of clusters
        clustering_algo = AffinityPropagation(random_state=random_seed)
        labels = clustering_algo.fit_predict(X)
        num_clusters = len(np.unique(labels))
    elif algo == "KMeans":
        clustering_algo = KMeans(n_clusters=num_clusters, init='k-means++', n_init=20, random_state=random_seed)
        labels = clustering_algo.fit_predict(X)
    elif algo == "Agglomerative":
        clustering_algo = AgglomerativeClustering(n_clusters=num_clusters)
        labels = clustering_algo.fit_predict(X)
    elif algo == "GMM":
        clustering_algo = GaussianMixture(n_components=num_clusters, random_state=random_seed)
        labels = clustering_algo.fit_predict(X)
    elif algo == "MeanShift":
        # determines the number of clusters
        clustering_algo = MeanShift()
        labels = clustering_algo.fit_predict(X)
        num_clusters = len(np.unique(labels))
    elif algo == "Birch":
        clustering_algo = Birch(n_clusters=num_clusters)
        labels = clustering_algo.fit_predict(X)
    elif algo == "SpectralClustering":
        clustering_algo = SpectralClustering(n_clusters=num_clusters, affinity='nearest_neighbors',
                                             random_state=random_seed)
        labels = clustering_algo.fit_predict(X)
    elif algo == "HDBSCAN":
        # determines the number of clusters
        clustering_algo = hdbscan.HDBSCAN()
        labels = clustering_algo.fit_predict(X)
        num_clusters = len(np.unique(labels))

    elif algo == "OPTICS":
        # determines clusters automatically
        clustering_algo = OPTICS(min_samples=5, xi=0.05, min_cluster_size=0.1)
        labels = clustering_algo.fit_predict(X)
        num_clusters = len(np.unique(labels))
    else:
        raise ValueError(f"Unsupported clustering algorithm: {algo}")

    if labels is None:
        raise ValueError(f"Clustering labels were not assigned for algorithm: {algo}")

    if save_plot_path is not None:
        # Visualization of clustering
        pca_2d = PCA(n_components=2)
        reduced_vectors_2d = pca_2d.fit_transform(X)
        plt.figure(figsize=(10, 7))
        plt.scatter(reduced_vectors_2d[:, 0], reduced_vectors_2d[:, 1], c=labels, cmap='viridis', marker='o', alpha=0.7)
        plt.title(f'{algo} Clustering\nNumber of clusters: {num_clusters}')
        plt.xlabel('PCA Component 1')
        plt.ylabel('PCA Component 2')
        plt.colorbar(label='Cluster Label')
        plt.savefig(save_plot_path)
        plt.close()

    filename_to_cluster = dict(zip(identifiers, labels))
    return filename_to_cluster, num_clusters


