"""Requirement clustering using similarity."""

from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from marianalyzer.models import Requirement
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def cluster_requirements(
    requirements: List[Requirement],
    embeddings: List[List[float]],
    threshold: float = 0.85,
) -> Dict[int, List[int]]:
    """Cluster requirements by similarity.

    Uses a simple threshold-based clustering:
    - Each requirement starts in its own cluster
    - Merge clusters if similarity > threshold
    - Continue until no more merges possible

    Args:
        requirements: List of requirements
        embeddings: Corresponding embedding vectors
        threshold: Similarity threshold for clustering (0.0-1.0)

    Returns:
        Dictionary mapping cluster_id -> list of requirement indices
    """
    if not requirements:
        return {}

    logger.info(f"Clustering {len(requirements)} requirements with threshold {threshold}")

    # Convert to numpy array
    embeddings_array = np.array(embeddings)

    # Compute pairwise cosine similarities
    similarities = cosine_similarity(embeddings_array)

    # Initialize: each requirement in its own cluster
    clusters = {i: [i] for i in range(len(requirements))}

    # Iteratively merge similar clusters
    changed = True
    iteration = 0

    while changed:
        changed = False
        iteration += 1

        cluster_ids = list(clusters.keys())

        for i in range(len(cluster_ids)):
            for j in range(i + 1, len(cluster_ids)):
                cluster_i = cluster_ids[i]
                cluster_j = cluster_ids[j]

                # Skip if either cluster no longer exists
                if cluster_i not in clusters or cluster_j not in clusters:
                    continue

                # Compute average similarity between clusters
                avg_sim = compute_cluster_similarity(
                    clusters[cluster_i],
                    clusters[cluster_j],
                    similarities,
                )

                # Merge if similarity exceeds threshold
                if avg_sim >= threshold:
                    clusters[cluster_i].extend(clusters[cluster_j])
                    del clusters[cluster_j]
                    changed = True

        logger.debug(f"Iteration {iteration}: {len(clusters)} clusters")

    # Re-index clusters with sequential IDs
    final_clusters = {}
    for new_id, (old_id, members) in enumerate(clusters.items()):
        final_clusters[new_id] = members

    logger.info(f"Clustering complete: {len(final_clusters)} clusters formed")

    return final_clusters


def compute_cluster_similarity(
    cluster1: List[int],
    cluster2: List[int],
    similarity_matrix: np.ndarray,
) -> float:
    """Compute average similarity between two clusters.

    Args:
        cluster1: Indices of requirements in cluster 1
        cluster2: Indices of requirements in cluster 2
        similarity_matrix: Pairwise similarity matrix

    Returns:
        Average similarity score
    """
    similarities = []

    for i in cluster1:
        for j in cluster2:
            similarities.append(similarity_matrix[i, j])

    return float(np.mean(similarities)) if similarities else 0.0


def get_cluster_centroid(
    cluster_members: List[int],
    embeddings: List[List[float]],
) -> List[float]:
    """Compute centroid (mean embedding) of a cluster.

    Args:
        cluster_members: Indices of cluster members
        embeddings: All embeddings

    Returns:
        Centroid embedding vector
    """
    cluster_embeddings = [embeddings[i] for i in cluster_members]
    centroid = np.mean(cluster_embeddings, axis=0)
    return centroid.tolist()


def select_most_representative(
    cluster_members: List[int],
    requirements: List[Requirement],
    embeddings: List[List[float]],
) -> int:
    """Select most representative requirement from cluster.

    Chooses the requirement closest to the cluster centroid.

    Args:
        cluster_members: Indices of cluster members
        requirements: All requirements
        embeddings: All embeddings

    Returns:
        Index of most representative requirement
    """
    # Compute centroid
    centroid = get_cluster_centroid(cluster_members, embeddings)

    # Find closest to centroid
    best_idx = cluster_members[0]
    best_sim = -1.0

    for idx in cluster_members:
        sim = float(cosine_similarity([embeddings[idx]], [centroid])[0][0])
        if sim > best_sim:
            best_sim = sim
            best_idx = idx

    return best_idx
