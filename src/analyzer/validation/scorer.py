"""Draft scoring logic."""

from ..config import get_config
from ..models import ScoreResponse
from ..store import SQLiteStore
from ..utils import normalize_text


def score_draft(
    company_id: str,
    doc_type: str,
    draft_text: str,
) -> ScoreResponse:
    """
    Score a draft document against the company playbook.
    
    Args:
        company_id: Company identifier
        doc_type: Document type
        draft_text: The draft document text
        
    Returns:
        ScoreResponse with scores and missing elements
    """
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    # Get playbook
    playbook = store.get_playbook(company_id, doc_type)
    
    if not playbook:
        # No playbook available, return neutral scores
        return ScoreResponse(
            company_id=company_id,
            doc_type=doc_type,
            scores={
                "structure_alignment_score": 0.5,
                "requirement_coverage_score": 0.5,
                "terminology_score": 0.5,
                "consistency_score": 0.5,
                "specificity_score": 0.5,
                "overall_quality_score": 0.5,
            },
            missing={"sections": [], "requirement_families": []},
        )
    
    draft_lower = draft_text.lower()
    draft_norm = normalize_text(draft_text)
    
    # Calculate structure alignment score
    required_sections = [s for s in playbook.typical_outline if s.required]
    found_sections = 0
    missing_sections = []
    
    for section in required_sections:
        section_norm = normalize_text(section.section_name)
        if section_norm in draft_norm:
            found_sections += 1
        else:
            missing_sections.append(section.section_name)
    
    structure_score = found_sections / len(required_sections) if required_sections else 1.0
    
    # Calculate requirement coverage score
    families = store.get_requirement_families_by_company(company_id)
    family_dict = {f.family_id: f for f in families}
    
    top_families = playbook.top_requirement_families[:10]
    found_families = 0
    missing_families = []
    
    for family_id in top_families:
        if family_id not in family_dict:
            continue
        
        family = family_dict[family_id]
        family_norm = normalize_text(family.canonical_text)
        keywords = family_norm.split()[:5]
        
        found = any(kw in draft_norm for kw in keywords if len(kw) > 3)
        if found:
            found_families += 1
        else:
            missing_families.append(family_id)
    
    requirement_score = found_families / len(top_families) if top_families else 1.0
    
    # Calculate specificity score
    vague_terms = ["tbd", "to be determined", "pending", "unclear", "maybe", "possibly"]
    vague_count = sum(draft_lower.count(term) for term in vague_terms)
    
    # Penalize based on vague term density
    word_count = len(draft_text.split())
    vague_ratio = vague_count / word_count if word_count > 0 else 0
    specificity_score = max(0.0, 1.0 - (vague_ratio * 100))  # Heavy penalty
    
    # Terminology score (simplified - check for glossary terms)
    # For MVP, just give neutral score
    terminology_score = 0.8
    
    # Consistency score (simplified - no contradictions detected)
    # For MVP, just give neutral score
    consistency_score = 0.9
    
    # Calculate overall score (weighted average)
    overall_score = (
        structure_score * 0.3 +
        requirement_score * 0.3 +
        terminology_score * 0.15 +
        consistency_score * 0.1 +
        specificity_score * 0.15
    )
    
    return ScoreResponse(
        company_id=company_id,
        doc_type=doc_type,
        scores={
            "structure_alignment_score": round(structure_score, 2),
            "requirement_coverage_score": round(requirement_score, 2),
            "terminology_score": round(terminology_score, 2),
            "consistency_score": round(consistency_score, 2),
            "specificity_score": round(specificity_score, 2),
            "overall_quality_score": round(overall_score, 2),
        },
        missing={
            "sections": missing_sections,
            "requirement_families": missing_families,
        },
    )
