"""
================================================================================
PostgreSQL Knowledge Base Client (agents/shared/kb_client.py)
================================================================================
Dedicated read-only interface to Ganesh's Supabase PostgreSQL Knowledge Base.
Access is strictly read-only (enforced at Postgres role level: kb_readonly).

Views exposed:
- kb.v_person_state         -> Aggregated stats per person (assignments, concepts, QA, feedback)
- kb.v_assignments_current  -> Current assignment statuses (given, in_progress, delivered, late)
- kb.v_assignments          -> Full historical lifecycle of assignments
- kb.v_concepts             -> Concept observations by understanding state (confused, partial, demonstrated)
- kb.v_qa                   -> Q&A exchanges by answer quality (incorrect, partial, correct)
- kb.v_feedback             -> Verbatim feedback history from mentor with sentiment
- kb.v_decisions            -> Architectural decisions with owner, rationale, and date
- kb.v_digests              -> Session summaries and per-person delta JSONB
- kb.v_patterns             -> Longitudinal behavioral/technical capability patterns
================================================================================
"""

import os
import sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False


class KnowledgeBaseClient:
    """
    Client for querying Ganesh's structured Knowledge Base in Supabase PostgreSQL.
    """

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv(
            "KB_DSN",
            "postgresql://kb_readonly.eyjxacmjtutztnfegttg:read123@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres"
        )

    def _query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Executes a parameterized read-only query and returns a list of dictionaries."""
        if not PSYCOPG_AVAILABLE:
            raise RuntimeError("psycopg is not installed. Run: pip install 'psycopg[binary]'")
        if not self.dsn:
            raise RuntimeError("KB_DSN is not configured in .env or environment.")

        try:
            print(f"  [KB Client] Live query to Supabase: {sql[:70]}...")
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    if not cur.description:
                        return []
                    cols = [d.name for d in cur.description]
                    rows = cur.fetchall()
                    print(f"  [KB Client] Fetched {len(rows)} verified records from Supabase.")
                    return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            print(f"[KBClient Error] Query failed: {e}", file=sys.stderr)
            return []

    # ── Canonical Person List ──────────────────────────────────────────────────

    def get_all_persons(self) -> List[str]:
        """Returns the list of canonical names in the KB."""
        rows = self._query("SELECT canonical_name FROM kb.person ORDER BY canonical_name;")
        return [r["canonical_name"] for r in rows if r.get("canonical_name")]

    # ── 1. Person State (Rollup) ──────────────────────────────────────────────

    def get_person_state(self, person: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns rolled-up current state per person:
        - assignments_open, assignments_delivered, assignments_late
        - concepts_demonstrated, concepts_partial, concepts_confused
        - qa_correct, qa_partial, qa_incorrect
        - feedback_received
        """
        if person:
            return self._query("SELECT * FROM kb.v_person_state WHERE person = %s;", (person,))
        return self._query("SELECT * FROM kb.v_person_state ORDER BY person;")

    # ── 2. Current Assignments ────────────────────────────────────────────────

    def get_current_assignments(
        self,
        person: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns active/current state of assignments (one row per assignment).
        Filters: person (e.g. 'Ganesh Krishna'), status ('given', 'in_progress', 'delivered', etc.)
        """
        sql = "SELECT person, task_description, status, due_date, delivered_date, was_late, as_of_session, evidence_lines FROM kb.v_assignments_current"
        conditions = []
        params = []

        if person:
            conditions.append("person = %s")
            params.append(person)
        if status:
            conditions.append("status = %s")
            params.append(status)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY due_date NULLS LAST, person;"

        return self._query(sql, tuple(params) if params else None)

    # ── 3. Concept Gaps & Knowledge Tracking ─────────────────────────────────

    def get_concept_gaps(
        self,
        person: Optional[str] = None,
        states: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns concept observations.
        By default retrieves 'confused' and 'partial' states representing learning gaps.
        """
        active_states = states or ["confused", "partial"]
        placeholders = ", ".join(["%s"] * len(active_states))

        if person:
            sql = f"""
                SELECT person, concept, understanding_state, observation, session_date, evidence_lines
                FROM kb.v_concepts
                WHERE person = %s AND understanding_state IN ({placeholders})
                ORDER BY session_date DESC, person;
            """
            params = (person, *active_states)
        else:
            sql = f"""
                SELECT person, concept, understanding_state, observation, session_date, evidence_lines
                FROM kb.v_concepts
                WHERE understanding_state IN ({placeholders})
                ORDER BY session_date DESC, person;
            """
            params = tuple(active_states)

        return self._query(sql, params)

    # ── 4. Q&A Quality & Exam Performance ────────────────────────────────────

    def get_qa_history(
        self,
        person: Optional[str] = None,
        qualities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns Q&A exchanges.
        By default retrieves 'incorrect', 'partial', 'unanswered' answers.
        """
        active_qualities = qualities or ["incorrect", "partial", "unanswered"]
        placeholders = ", ".join(["%s"] * len(active_qualities))

        if person:
            sql = f"""
                SELECT answered_by, question_text, answer_summary, answer_quality, topic, session_date, evidence_lines
                FROM kb.v_qa
                WHERE answered_by = %s AND answer_quality IN ({placeholders})
                ORDER BY session_date DESC;
            """
            params = (person, *active_qualities)
        else:
            sql = f"""
                SELECT answered_by, question_text, answer_summary, answer_quality, topic, session_date, evidence_lines
                FROM kb.v_qa
                WHERE answer_quality IN ({placeholders})
                ORDER BY session_date DESC, answered_by;
            """
            params = tuple(active_qualities)

        return self._query(sql, params)

    # ── 5. Feedback History ───────────────────────────────────────────────────

    def get_feedback_history(
        self,
        person: Optional[str] = None,
        from_person: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns verbatim feedback given to a trainee, along with sentiment and date.
        """
        conditions = []
        params = []
        sql = "SELECT to_person, from_person, topic, verbatim_feedback, sentiment, session_date, evidence_lines FROM kb.v_feedback"

        if person:
            conditions.append("to_person = %s")
            params.append(person)
        if from_person:
            conditions.append("from_person = %s")
            params.append(from_person)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY session_date DESC;"

        return self._query(sql, tuple(params) if params else None)

    # ── 6. Decisions Register ────────────────────────────────────────────────

    def get_decisions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        owner: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns architectural/technical decisions made during meetings.
        """
        conditions = []
        params = []
        sql = "SELECT decision_text, rationale, owner, scope, session_date, evidence_lines FROM kb.v_decisions"

        if owner:
            conditions.append("owner = %s")
            params.append(owner)
        if start_date and end_date:
            conditions.append("session_date BETWEEN %s AND %s")
            params.extend([start_date, end_date])
        elif start_date:
            conditions.append("session_date >= %s")
            params.append(start_date)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY session_date DESC;"

        return self._query(sql, tuple(params) if params else None)

    # ── 7. Session Digest & Deltas ───────────────────────────────────────────

    def get_session_digest(self, session_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns session summary, per-person deltas (JSONB), and unresolved items.
        """
        if session_date:
            return self._query(
                "SELECT session_date, summary, per_person_delta, key_topics, unresolved_items, evidence_lines FROM kb.v_digests WHERE session_date = %s;",
                (session_date,)
            )
        return self._query(
            "SELECT session_date, summary, per_person_delta, key_topics, unresolved_items FROM kb.v_digests ORDER BY session_date DESC;"
        )

    # ── 8. Longitudinal Behavioral Patterns ──────────────────────────────────

    def get_patterns(self, person: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns corpus-wide technical and behavioural patterns.
        """
        if person:
            return self._query(
                "SELECT person, pattern_type, observation, technical_capability, session_date, evidence_lines FROM kb.v_patterns WHERE person = %s;",
                (person,)
            )
        return self._query(
            "SELECT person, pattern_type, observation, technical_capability, session_date FROM kb.v_patterns ORDER BY person;"
        )


# Global singleton instance
kb_client = KnowledgeBaseClient()
