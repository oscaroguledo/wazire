from __future__ import annotations

from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json


async def bulk_update_student_answers(session: AsyncSession, mappings: List[Dict[str, Any]], batch_size: int = 500) -> None:
    """Bulk-update `student_answers.answer` JSON by merging a `graded` key into existing JSON.

    This builds a single UPDATE statement per batch using VALUES(...) and a FROM join
    so that many rows are updated in one database hit.

    Each mapping must contain: student_id (UUID str), exam_id (UUID str), question_id (UUID str), graded (serializable dict)
    """
    if not mappings:
        return

    # Prepare batches
    for i in range(0, len(mappings), batch_size):
        batch = mappings[i : i + batch_size]

        # Build VALUES list and parameter dict
        values_sql = []
        params: Dict[str, Any] = {}
        for idx, m in enumerate(batch):
            sid_key = f"s_{idx}"
            eid_key = f"e_{idx}"
            qid_key = f"q_{idx}"
            gkey = f"g_{idx}"
            values_sql.append(f"(:{sid_key}::uuid, :{eid_key}::uuid, :{qid_key}::uuid, :{gkey}::jsonb)")
            params[sid_key] = str(m["student_id"])
            params[eid_key] = str(m["exam_id"])
            params[qid_key] = str(m["question_id"])
            params[gkey] = json.dumps(m["graded"])

        values_clause = ",\n".join(values_sql)

        # SQL: update student_answers set answer = answer || v.graded
        sql = f"""
        WITH v(student_id, exam_id, question_id, graded) AS (
            VALUES
            {values_clause}
        )
        UPDATE academic.student_answers sa
        SET answer = sa.answer || v.graded
        FROM v
        WHERE sa.student_id = v.student_id
          AND sa.exam_id = v.exam_id
          AND sa.question_id = v.question_id
        ;
        """

        await session.execute(text(sql), params)
        # Commit after each batch to free resources; caller may manage transactions instead
        await session.commit()
