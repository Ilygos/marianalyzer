"""Draft validation logic."""

from ..config import get_config
from ..models import Evidence, EvidenceExample, ValidationIssue, ValidationResponse
from ..store import SQLiteStore
from ..utils import normalize_text


def validate_draft(
    company_id: str,
    doc_type: str,
    draft_text: str,
) -> ValidationResponse:
    """
    Validate a draft document against the company playbook.
    
    Args:
        company_id: Company identifier
        doc_type: Document type
        draft_text: The draft document text
        
    Returns:
        ValidationResponse with issues found
    """
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    issues: list[ValidationIssue] = []
    
    # Get playbook
    playbook = store.get_playbook(company_id, doc_type)
    
    if not playbook:
        # No playbook available
        return ValidationResponse(
            company_id=company_id,
            doc_type=doc_type,
            issues=[],
        )
    
    draft_lower = draft_text.lower()
    draft_norm = normalize_text(draft_text)
    
    # Check for missing required sections
    for section in playbook.typical_outline:
        if section.required:
            section_norm = normalize_text(section.section_name)
            
            # Simple check: is section name present in draft?
            if section_norm not in draft_norm:
                issue = ValidationIssue(
                    severity="high",
                    type="missing_section",
                    message=f"Missing required section: {section.section_name}",
                    recommended_fix=f"Add section '{section.section_name}' to your document",
                    evidence=[],
                )
                issues.append(issue)
    
    # Check for missing requirement families
    families = store.get_requirement_families_by_company(company_id)
    family_dict = {f.family_id: f for f in families}
    
    for family_id in playbook.top_requirement_families[:10]:  # Check top 10
        if family_id not in family_dict:
            continue
        
        family = family_dict[family_id]
        family_norm = normalize_text(family.canonical_text)
        
        # Check if any keywords from the requirement are in the draft
        keywords = family_norm.split()[:5]  # First 5 words
        found = any(kw in draft_norm for kw in keywords if len(kw) > 3)
        
        if not found:
            # Get example chunks for evidence
            chunks = store.get_chunks_by_company(company_id)
            examples = []
            
            for chunk in chunks[:3]:  # Up to 3 examples
                if family_norm in normalize_text(chunk.text):
                    example = EvidenceExample(
                        path=store.get_document(chunk.doc_id).path,
                        locator=chunk.locator.model_dump(),
                        chunk_id=chunk.chunk_id,
                    )
                    examples.append(example)
            
            evidence = Evidence(
                family_id=family_id,
                canonical_text=family.canonical_text,
                examples=examples,
            )
            
            issue = ValidationIssue(
                severity="medium",
                type="missing_requirement",
                message=f"Missing common requirement: {family.title}",
                recommended_fix=f"Consider addressing: {family.canonical_text}",
                evidence=[evidence],
            )
            issues.append(issue)
    
    # Check for vague terms (specificity check)
    vague_terms = ["tbd", "to be determined", "pending", "unclear", "maybe", "possibly"]
    vague_count = sum(draft_lower.count(term) for term in vague_terms)
    
    if vague_count > 3:
        issue = ValidationIssue(
            severity="medium",
            type="specificity",
            message=f"Document contains {vague_count} vague terms (TBD, pending, etc.)",
            recommended_fix="Replace vague terms with specific values or commitments",
            evidence=[],
        )
        issues.append(issue)
    
    return ValidationResponse(
        company_id=company_id,
        doc_type=doc_type,
        issues=issues,
    )
