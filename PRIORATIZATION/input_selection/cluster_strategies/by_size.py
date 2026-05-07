

def cluster_by_size(clusters):
    """
    Return cluster labels sorted by ascending cluster size.
    """
    return sorted(clusters.keys(), key=lambda label: len(clusters[label]))
