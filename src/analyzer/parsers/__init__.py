"""Document parsers for the analyzer."""

from .base import Parser
from .docx_parser import DOCXParser
from .xlsx_parser import XLSXParser
from .pdf_parser import PDFParser

__all__ = ["Parser", "DOCXParser", "XLSXParser", "PDFParser"]
