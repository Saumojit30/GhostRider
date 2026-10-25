"""Step Synthesizer and Canonical Sorter for Ghost Data Still Exists.

Enforces strict phase ordering, operation priority, secondary tie-breaking,
consecutive step numbering, and valid JSON array formatting.
"""

import json
from typing import Dict, List

from code.config import OPERATION_ORDER, PHASE_ORDER
from code.core.policy import RawStep


class StepSynthesizer:
    """Canonical sorter and serializer for audit step sequences."""

    @staticmethod
    def canonical_sort_key(step: RawStep):
        phase_rank = PHASE_ORDER.get(step.phase, 99)
        op_rank = OPERATION_ORDER.get(step.operation, 99)
        return (phase_rank, op_rank, step.system_id, step.resource_id)

    @classmethod
    def synthesize(cls, raw_steps: List[RawStep]) -> str:
        """Sorts, renumbers, and serializes steps to a valid JSON string.
        
        Returns:
            JSON array string with consecutive step_no starting at 1.
        """
        if not raw_steps:
            return "[]"

        # 1. Deduplicate by (phase, system_id, resource_id, operation)
        seen = set()
        unique_steps: List[RawStep] = []
        for s in raw_steps:
            sig = (s.phase, s.system_id, s.resource_id, s.operation)
            if sig not in seen:
                seen.add(sig)
                unique_steps.append(s)

        # 2. Canonical sorting
        sorted_steps = sorted(unique_steps, key=cls.canonical_sort_key)

        # 3. Format serialized dicts with consecutive step_no
        output_dicts: List[Dict] = []
        for idx, s in enumerate(sorted_steps, start=1):
            output_dicts.append({
                "step_no": idx,
                "phase": s.phase,
                "system_id": s.system_id,
                "resource_id": s.resource_id,
                "operation": s.operation,
                "state": s.state,
                "evidence_id": s.evidence_id,
            })

        return json.dumps(output_dicts, separators=(",", ":"))
