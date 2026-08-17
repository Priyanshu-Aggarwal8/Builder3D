"""
IFC Engine adapter providing backward compatibility using the pure-Python ifc_compiler.
"""

from app.services.ifc_compiler import (
    create_ifc4_project_from_model,
    parse_ifc_content,
    compile_bim_to_ifc4_step,
    parse_ifc4_step_to_bim,
    StepFile,
    StepEntity,
    StepParser,
    step_escape_string,
    step_unescape_string,
)

__all__ = [
    "create_ifc4_project_from_model",
    "parse_ifc_content",
    "compile_bim_to_ifc4_step",
    "parse_ifc4_step_to_bim",
    "StepFile",
    "StepEntity",
    "StepParser",
    "step_escape_string",
    "step_unescape_string",
]
