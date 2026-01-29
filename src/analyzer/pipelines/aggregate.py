"""Playbook aggregation pipeline."""

import hashlib
from collections import Counter, defaultdict
from datetime import datetime

from rich.console import Console

from ..config import get_config
from ..models import Playbook, PlaybookSection, RequirementFamily
from ..store import SQLiteStore
from ..utils import generate_embedding

console = Console()


def cluster_requirements(requirements: list, threshold: float = 0.8) -> list[RequirementFamily]:
    """
    Cluster similar requirements into families.
    
    Uses normalized text similarity for clustering.
    """
    # Group by normalized text
    norm_groups = defaultdict(list)
    for req in requirements:
        norm_groups[req.req_norm].append(req)
    
    # Create families from groups
    families = []
    for norm_text, members in norm_groups.items():
        if len(members) < 2:
            # Skip singleton groups
            continue
        
        # Use the first requirement as canonical
        canonical = members[0]
        
        family_id = hashlib.md5(norm_text.encode()).hexdigest()[:16]
        
        # Generate embedding for family
        embedding = generate_embedding(canonical.req_text)
        
        family = RequirementFamily(
            family_id=family_id,
            company_id=canonical.company_id,
            title=canonical.topic or "General",
            canonical_text=canonical.req_text,
            member_count=len(members),
            embedding=embedding,
            created_at=datetime.utcnow(),
        )
        families.append((family, members))
    
    return families


def build_playbook(company_id: str, doc_type: str = "general") -> None:
    """
    Build company playbook from documents.
    
    Args:
        company_id: Company identifier
        doc_type: Document type (e.g., "offer_deck", "rfp")
    """
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    console.print(f"Building playbook for {company_id}")
    
    # Get all documents
    documents = store.get_documents_by_company(company_id)
    total_docs = len(documents)
    
    if total_docs == 0:
        console.print("[yellow]No documents found[/yellow]")
        return
    
    # Analyze headings to build typical outline
    headings = store.get_headings_by_company(company_id)
    
    # Count heading frequencies by normalized text
    heading_counter = Counter()
    heading_examples = defaultdict(list)
    
    for heading in headings:
        heading_counter[heading.heading_norm] += 1
        heading_examples[heading.heading_norm].append(heading.heading_text)
    
    # Build typical outline
    typical_outline = []
    for heading_norm, count in heading_counter.most_common():
        frequency = count / total_docs
        
        # Only include headings that appear in a significant portion of docs
        if frequency >= config.min_section_frequency:
            section = PlaybookSection(
                section_name=heading_examples[heading_norm][0],  # Use first example
                frequency=frequency,
                required=frequency >= config.required_section_threshold,
                typical_subsections=[],
            )
            typical_outline.append(section)
    
    console.print(f"Found {len(typical_outline)} typical sections")
    
    # Cluster requirements into families
    requirements = store.get_requirements_by_company(company_id)
    
    console.print(f"Clustering {len(requirements)} requirements")
    
    families_with_members = cluster_requirements(requirements)
    
    # Store families
    for family, members in families_with_members:
        store.insert_requirement_family(family)
        for member in members:
            store.add_requirement_to_family(family.family_id, member.req_id)
    
    console.print(f"Created {len(families_with_members)} requirement families")
    
    # Get top families by member count
    families = store.get_requirement_families_by_company(company_id)
    families.sort(key=lambda f: f.member_count, reverse=True)
    top_family_ids = [f.family_id for f in families[:20]]  # Top 20
    
    # Build playbook
    playbook = Playbook(
        company_id=company_id,
        doc_type=doc_type,
        typical_outline=typical_outline,
        top_requirement_families=top_family_ids,
        glossary_terms=[],  # TODO: Extract glossary terms
        updated_at=datetime.utcnow(),
    )
    
    store.insert_playbook(playbook)
    
    console.print("[green]Playbook building complete[/green]")
