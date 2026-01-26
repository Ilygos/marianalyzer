"""Requirement family building and aggregation."""

from collections import defaultdict
from typing import Dict, List

from tqdm import tqdm

from marianalyzer.aggregation.clusterer import cluster_requirements, select_most_representative
from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.llm.embedder import embed_batch
from marianalyzer.models import Requirement, RequirementFamily, RequirementFamilyMember
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def build_families(db: Database, config: Config) -> Dict[str, int]:
    """Build requirement families from extracted requirements.

    Args:
        db: Database instance
        config: Configuration

    Returns:
        Statistics dictionary
    """
    logger.info("Building requirement families")

    # Load all requirements
    requirements = db.get_all_requirements()

    if not requirements:
        logger.warning("No requirements found in database")
        return {"families_created": 0, "requirements_clustered": 0}

    # Generate embeddings for normalized requirements
    logger.info(f"Generating embeddings for {len(requirements)} requirements")
    req_texts = [req.req_norm for req in requirements]

    embeddings = embed_batch(
        texts=req_texts,
        model=config.embed_model,
        ollama_host=config.ollama_host,
        batch_size=10,
        show_progress=True,
    )

    # Cluster requirements
    logger.info("Clustering requirements")
    clusters = cluster_requirements(
        requirements=requirements,
        embeddings=embeddings,
        threshold=config.clustering_threshold,
    )

    # Filter out singleton clusters if min_cluster_size > 1
    if config.min_cluster_size > 1:
        clusters = {
            cluster_id: members
            for cluster_id, members in clusters.items()
            if len(members) >= config.min_cluster_size
        }
        logger.info(f"After filtering: {len(clusters)} clusters with size >= {config.min_cluster_size}")

    # Build families from clusters
    stats = {
        "families_created": 0,
        "requirements_clustered": 0,
    }

    for cluster_id, member_indices in tqdm(clusters.items(), desc="Creating families"):
        # Get requirements in this cluster
        cluster_reqs = [requirements[i] for i in member_indices]

        # Select most representative requirement for canonical text
        representative_idx = select_most_representative(
            cluster_members=member_indices,
            requirements=requirements,
            embeddings=embeddings,
        )
        canonical_text = requirements[representative_idx].req_text

        # Count unique documents
        doc_ids = set()
        for req in cluster_reqs:
            # Get chunk to find doc_id
            chunk = db.get_all_chunks()  # TODO: Optimize this lookup
            for c in chunk:
                if c.id == req.chunk_id:
                    doc_ids.add(c.doc_id)
                    break

        doc_count = len(doc_ids)

        # Create family
        family = RequirementFamily(
            canonical_text=canonical_text,
            member_count=len(member_indices),
            doc_count=doc_count,
        )

        # Insert family
        family_id = db.insert_family(family)
        stats["families_created"] += 1

        # Create family members
        members = []
        for req_idx in member_indices:
            req = requirements[req_idx]

            # Compute similarity to centroid
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            from marianalyzer.aggregation.clusterer import get_cluster_centroid

            centroid = get_cluster_centroid(member_indices, embeddings)
            similarity = float(cosine_similarity([embeddings[req_idx]], [centroid])[0][0])

            member = RequirementFamilyMember(
                family_id=family_id,
                requirement_id=req.id,
                similarity_score=similarity,
            )
            members.append(member)
            stats["requirements_clustered"] += 1

        # Insert family members
        db.insert_family_members(members)

        logger.debug(
            f"Created family {family_id}: {len(member_indices)} members, "
            f"{doc_count} documents, canonical: {canonical_text[:60]}..."
        )

    logger.info(
        f"Family building complete: {stats['families_created']} families, "
        f"{stats['requirements_clustered']} requirements clustered"
    )

    return stats
