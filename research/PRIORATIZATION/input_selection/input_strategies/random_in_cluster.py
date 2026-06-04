import random

def select_random_in_cluster(cluster_inputs, _):
    return random.sample(cluster_inputs, len(cluster_inputs))
