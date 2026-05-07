"""Unit tests for Kafka task handler modules.

Tests handler registration (HANDLERS dicts), handler dispatch, and
individual handler logic with mocked DB, Redis, and Kafka.

Test files MUST NOT import from main.py or worker.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Dispatcher registration tests
# ---------------------------------------------------------------------------

class TestHandlerRegistration:
    """Verify that each tasks module exports a HANDLERS dict with the expected keys."""

    def test_submission_handlers_registered(self):
        """Test that submission.py exports HANDLERS with required event types."""
        from tasks.submission import HANDLERS

        assert "GRADE_SUBMISSION_ATTEMPT" in HANDLERS
        assert "REFRESH_DASHBOARD" in HANDLERS
        assert callable(HANDLERS["GRADE_SUBMISSION_ATTEMPT"])
        assert callable(HANDLERS["REFRESH_DASHBOARD"])

    def test_exam_handlers_registered(self):
        """Test that exam.py exports HANDLERS with required event types."""
        from tasks.exam import HANDLERS

        assert "UPDATE_EXAM_STATUS" in HANDLERS
        assert "SEND_QUEUED_EMAILS" in HANDLERS
        assert "FORCE_SUBMIT_EXAM" in HANDLERS
        assert callable(HANDLERS["UPDATE_EXAM_STATUS"])
        assert callable(HANDLERS["SEND_QUEUED_EMAILS"])
        assert callable(HANDLERS["FORCE_SUBMIT_EXAM"])

    def test_question_handlers_registered(self):
        """Test that question.py exports HANDLERS with required event types."""
        from tasks.question import HANDLERS

        assert "DETECT_ANSWER" in HANDLERS
        assert "PARSE_AND_CREATE" in HANDLERS
        assert "PRELOAD_QUESTIONS" in HANDLERS
        assert "UPSERT_STUDENT_ANSWER" in HANDLERS
        assert callable(HANDLERS["DETECT_ANSWER"])
        assert callable(HANDLERS["PARSE_AND_CREATE"])
        assert callable(HANDLERS["PRELOAD_QUESTIONS"])
        assert callable(HANDLERS["UPSERT_STUDENT_ANSWER"])

    def test_email_handlers_registered(self):
        """Test that email.py exports HANDLERS with required event types."""
        from tasks.email import HANDLERS

        assert "SEND_EMAIL" in HANDLERS
        assert callable(HANDLERS["SEND_EMAIL"])

    def test_billing_handlers_registered(self):
        """Test that billing.py exports HANDLERS with required event types."""
        from tasks.billing import HANDLERS

        assert "INITIATE_BILLING" in HANDLERS
        assert callable(HANDLERS["INITIATE_BILLING"])

    def test_all_handlers_are_coroutines(self):
        """Test that all registered handlers are async coroutine functions."""
        import asyncio
        from tasks.submission import HANDLERS as sub_handlers
        from tasks.exam import HANDLERS as exam_handlers
        from tasks.question import HANDLERS as q_handlers
        from tasks.email import HANDLERS as email_handlers
        from tasks.billing import HANDLERS as billing_handlers

        all_handlers = {
            **sub_handlers,
            **exam_handlers,
            **q_handlers,
            **email_handlers,
            **billing_handlers,
        }

        for event_type, handler in all_handlers.items():
            assert asyncio.iscoroutinefunction(handler), (
                f"Handler for '{event_type}' is not a coroutine function"
            )

    def test_no_duplicate_event_types_across_modules(self):
        """Test that no event type is registered in more than one module."""
        from tasks.submission import HANDLERS as sub_handlers
        from tasks.exam import HANDLERS as exam_handlers
        from tasks.question import HANDLERS as q_handlers
        from tasks.email import HANDLERS as email_handlers
        from tasks.billing import HANDLERS as billing_handlers

        all_keys = (
            list(sub_handlers.keys())
            + list(exam_handlers.keys())
            + list(q_handlers.keys())
            + list(email_handlers.keys())
            + list(billing_handlers.keys())
        )

        assert len(all_keys) == len(set(all_keys)), (
            f"Duplicate event types found: {[k for k in all_keys if all_keys.count(k) > 1]}"
        )


# ---------------------------------------------------------------------------
# handle_grade_submission_attempt tests
# ---------------------------------------------------------------------------

class TestHandleGradeSubmissionAttempt:
    """Tests for tasks.submission.handle_grade_submission_attempt."""

    @pytest.mark.asyncio
    async def test_missing_attempt_id_returns_early(self):
        """Test that handler returns early when attempt_id is missing."""
        from tasks.submission import handle_grade_submission_attempt

        # Should not raise, just log and return
        await handle_grade_submission_attempt({"exam_id": "exam-1"})

    @pytest.mark.asyncio
    async def test_missing_exam_id_returns_early(self):
        """Test that handler returns early when exam_id is missing."""
        from tasks.submission import handle_grade_submission_attempt

        await handle_grade_submission_attempt({"attempt_id": "attempt-1"})

    @pytest.mark.asyncio
    async def test_already_graded_skips_regrading(self):
        """Test that handler skips re-grading when attempt is already graded."""
        from tasks.submission import handle_grade_submission_attempt

        # Mock with_db to simulate already-graded attempt
        async def mock_with_db(fn, *args, **kwargs):
            # Simulate idempotency check returning True (already graded)
            return True

        with patch("tasks.submission.with_db", side_effect=mock_with_db):
            # Should not raise or call grading service
            await handle_grade_submission_attempt({
                "attempt_id": "550e8400-e29b-41d4-a716-446655440000",
                "exam_id": "550e8400-e29b-41d4-a716-446655440001",
            })


# ---------------------------------------------------------------------------
# handle_refresh_dashboard tests
# ---------------------------------------------------------------------------

class TestHandleRefreshDashboard:
    """Tests for tasks.submission.handle_refresh_dashboard."""

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_early(self):
        """Test that handler returns early when user_id is missing."""
        from tasks.submission import handle_refresh_dashboard

        await handle_refresh_dashboard({})

    @pytest.mark.asyncio
    async def test_invalid_user_id_returns_early(self):
        """Test that handler returns early for invalid UUID."""
        from tasks.submission import handle_refresh_dashboard

        await handle_refresh_dashboard({"user_id": "not-a-uuid"})


# ---------------------------------------------------------------------------
# handle_update_exam_status tests
# ---------------------------------------------------------------------------

class TestHandleUpdateExamStatus:
    """Tests for tasks.exam.handle_update_exam_status."""

    @pytest.mark.asyncio
    async def test_handler_calls_update_statuses(self):
        """Test that handler invokes _update_exam_statuses."""
        from tasks.exam import handle_update_exam_status

        with patch("tasks.exam._update_exam_statuses", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {"activated": 0, "completed": 0, "skipped": 0}
            await handle_update_exam_status({})

        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_reraises_on_failure(self):
        """Test that handler re-raises exceptions from _update_exam_statuses."""
        from tasks.exam import handle_update_exam_status

        with patch("tasks.exam._update_exam_statuses", new_callable=AsyncMock) as mock_update:
            mock_update.side_effect = RuntimeError("DB error")

            with pytest.raises(RuntimeError, match="DB error"):
                await handle_update_exam_status({})


# ---------------------------------------------------------------------------
# handle_send_queued_emails tests
# ---------------------------------------------------------------------------

class TestHandleSendQueuedEmails:
    """Tests for tasks.exam.handle_send_queued_emails."""

    @pytest.mark.asyncio
    async def test_handler_does_not_raise(self):
        """Test that handle_send_queued_emails completes without error (stub)."""
        from tasks.exam import handle_send_queued_emails

        # Should not raise
        await handle_send_queued_emails({})


# ---------------------------------------------------------------------------
# handle_force_submit_exam tests
# ---------------------------------------------------------------------------

class TestHandleForceSubmitExam:
    """Tests for tasks.exam.handle_force_submit_exam."""

    @pytest.mark.asyncio
    async def test_missing_exam_id_returns_early(self):
        """Test that handler returns early when exam_id is missing."""
        from tasks.exam import handle_force_submit_exam

        await handle_force_submit_exam({"tenant_id": "tenant-1"})

    @pytest.mark.asyncio
    async def test_invalid_exam_id_returns_early(self):
        """Test that handler returns early for invalid UUID."""
        from tasks.exam import handle_force_submit_exam

        await handle_force_submit_exam({"exam_id": "not-a-uuid"})


# ---------------------------------------------------------------------------
# handle_preload_questions tests
# ---------------------------------------------------------------------------

class TestHandlePreloadQuestions:
    """Tests for tasks.question.handle_preload_questions."""

    @pytest.mark.asyncio
    async def test_missing_exam_id_returns_early(self):
        """Test that handler returns early when exam_id is missing."""
        from tasks.question import handle_preload_questions

        await handle_preload_questions({"duration_seconds": 3600})

    @pytest.mark.asyncio
    async def test_no_redis_returns_early(self):
        """Test that handler returns early when Redis is not configured."""
        from tasks.question import handle_preload_questions

        with patch("tasks.question.get_redis_client", return_value=None):
            await handle_preload_questions({
                "exam_id": "550e8400-e29b-41d4-a716-446655440000",
                "duration_seconds": 3600,
            })


# ---------------------------------------------------------------------------
# handle_upsert_student_answer tests
# ---------------------------------------------------------------------------

class TestHandleUpsertStudentAnswer:
    """Tests for tasks.question.handle_upsert_student_answer."""

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_early(self):
        """Test that handler returns early when required fields are missing."""
        from tasks.question import handle_upsert_student_answer

        # Missing question_id
        await handle_upsert_student_answer({
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "exam_id": "550e8400-e29b-41d4-a716-446655440001",
            "answer": {"selected": "A"},
        })

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_early(self):
        """Test that handler returns early for invalid UUIDs."""
        from tasks.question import handle_upsert_student_answer

        await handle_upsert_student_answer({
            "student_id": "not-a-uuid",
            "exam_id": "550e8400-e29b-41d4-a716-446655440001",
            "question_id": "550e8400-e29b-41d4-a716-446655440002",
            "answer": {"selected": "A"},
        })


# ---------------------------------------------------------------------------
# handle_send_email tests
# ---------------------------------------------------------------------------

class TestHandleSendEmail:
    """Tests for tasks.email.handle_send_email."""

    @pytest.mark.asyncio
    async def test_missing_to_returns_early(self):
        """Test that handler returns early when 'to' is missing."""
        from tasks.email import handle_send_email

        await handle_send_email({"subject": "Test"})

    @pytest.mark.asyncio
    async def test_sends_raw_html_email(self):
        """Test that handler sends raw HTML email via brevo."""
        from tasks.email import handle_send_email

        with patch("tasks.email.brevo") as mock_brevo:
            mock_brevo.send_email = AsyncMock()
            await handle_send_email({
                "to": "test@example.com",
                "subject": "Test Subject",
                "body": "<p>Hello</p>",
            })

        mock_brevo.send_email.assert_called_once_with(
            "Test Subject", "test@example.com", "<p>Hello</p>"
        )

    @pytest.mark.asyncio
    async def test_sends_verify_email_template(self):
        """Test that handler sends verification email via template."""
        from tasks.email import handle_send_email

        with patch("tasks.email.brevo") as mock_brevo:
            mock_brevo.send_verification_email = AsyncMock()
            await handle_send_email({
                "to": "test@example.com",
                "subject": "Verify Email",
                "template": "verify_email",
                "template_vars": {
                    "verify_url": "https://example.com/verify",
                    "full_name": "Test User",
                },
            })

        mock_brevo.send_verification_email.assert_called_once()


# ---------------------------------------------------------------------------
# handle_initiate_billing tests
# ---------------------------------------------------------------------------

class TestHandleInitiateBilling:
    """Tests for tasks.billing.handle_initiate_billing."""

    @pytest.mark.asyncio
    async def test_missing_invoice_id_returns_early(self):
        """Test that handler returns early when invoice_id is missing."""
        from tasks.billing import handle_initiate_billing

        await handle_initiate_billing({"tenant_id": "tenant-1"})

    @pytest.mark.asyncio
    async def test_invalid_invoice_id_returns_early(self):
        """Test that handler returns early for invalid UUID."""
        from tasks.billing import handle_initiate_billing

        await handle_initiate_billing({"invoice_id": "not-a-uuid"})
