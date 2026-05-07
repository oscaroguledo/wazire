"""
Preservation Property Tests — Property 2
=========================================
These tests encode the BASELINE (currently-working) behavior.
On UNFIXED code, every test in this file MUST PASS.
Passing = the baseline is confirmed and must be preserved after fixes.

DO NOT modify source files to make these tests pass.
Run with: cd backend && python -m pytest tests/test_preservation_properties.py -v

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.14, 3.15, 3.22, 3.23, 3.24, 3.36, 3.40
"""
import sys
import os
import ast
import yaml
import pytest

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)


def _backend_path(*parts: str) -> str:
    return os.path.join(BACKEND_DIR, *parts)


def _parse_file(*parts: str) -> ast.Module:
    path = _backend_path(*parts)
    with open(path) as f:
        return ast.parse(f.read())


def _get_to_dict_keys(class_name: str, *file_parts: str) -> set:
    """Extract the keys returned by a class's to_dict() method via AST analysis."""
    tree = _parse_file(*file_parts)

    target_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            target_class = node
            break

    assert target_class is not None, (
        f"Class '{class_name}' not found in {os.path.join(*file_parts)}"
    )

    to_dict_func = None
    for node in ast.walk(target_class):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "to_dict":
            to_dict_func = node
            break

    assert to_dict_func is not None, (
        f"to_dict() method not found in class '{class_name}'"
    )

    # Find all dict literal keys in the return statement
    keys = set()
    for node in ast.walk(to_dict_func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


# ---------------------------------------------------------------------------
# Property 2a — Auth Response Shape Preservation
# Validates: Requirements 3.3, 3.4
# ---------------------------------------------------------------------------

def test_login_handler_returns_auth_read():
    """
    Property 2a: POST /api/v1/auth/login handler returns AuthRead with user and tokens.
    Preservation: login endpoint continues to return AuthRead(user=..., **tokens) after fixes.
    MUST PASS on unfixed code — confirms baseline behavior.
    """
    tree = _parse_file("routes", "account", "users.py")

    login_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "login":
            login_func = node
            break

    assert login_func is not None, (
        "login handler not found in routes/account/users.py — "
        "POST /api/v1/auth/login endpoint is missing"
    )

    # Verify AuthRead is used in the return statement
    uses_auth_read = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "AuthRead")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "AuthRead")
        )
        for node in ast.walk(login_func)
    )
    assert uses_auth_read, (
        "PRESERVATION VIOLATION: login handler does not use AuthRead in its response. "
        "POST /api/v1/auth/login must return AuthRead(user=..., **tokens) to preserve "
        "the auth response contract."
    )

    # Verify AuthRead is called with 'user' keyword argument
    auth_read_has_user_kwarg = False
    for node in ast.walk(login_func):
        if isinstance(node, ast.Call):
            func = node.func
            is_auth_read = (
                (isinstance(func, ast.Name) and func.id == "AuthRead")
                or (isinstance(func, ast.Attribute) and func.attr == "AuthRead")
            )
            if is_auth_read:
                for kw in node.keywords:
                    if kw.arg == "user":
                        auth_read_has_user_kwarg = True
                        break

    assert auth_read_has_user_kwarg, (
        "PRESERVATION VIOLATION: AuthRead in login handler is missing 'user=' keyword argument. "
        "The response shape AuthRead(user=user.to_dict(), **tokens) must be preserved."
    )


def test_auth_read_schema_has_user_and_token_fields():
    """
    Property 2a: AuthRead schema has 'user', 'access_token', 'refresh_token', 'token_type' fields.
    Preservation: AuthRead schema contract is preserved after any refactor.
    MUST PASS on unfixed code — confirms baseline schema shape.
    """
    tree = _parse_file("schemas", "account", "auth.py")

    auth_read_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AuthRead":
            auth_read_class = node
            break

    assert auth_read_class is not None, (
        "AuthRead class not found in schemas/account/auth.py"
    )

    # Collect annotated field names
    field_names = set()
    for node in ast.walk(auth_read_class):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            field_names.add(node.target.id)

    required_fields = {"access_token", "refresh_token", "token_type", "user"}
    missing = required_fields - field_names
    assert not missing, (
        f"PRESERVATION VIOLATION: AuthRead schema is missing fields: {missing}. "
        "The auth response shape (user + tokens) must be preserved."
    )


def test_me_handler_exists_with_correct_signature():
    """
    Property 2a: GET /api/v1/auth/me handler exists and returns current user profile.
    Preservation: me endpoint continues to return current_user data after fixes.
    MUST PASS on unfixed code — confirms baseline behavior.
    """
    tree = _parse_file("routes", "account", "users.py")

    me_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "me":
            me_func = node
            break

    assert me_func is not None, (
        "me handler not found in routes/account/users.py — "
        "GET /api/v1/auth/me endpoint is missing"
    )

    # Verify it has a current_user parameter (auth dependency)
    param_names = [arg.arg for arg in me_func.args.args]
    assert "current_user" in param_names, (
        "PRESERVATION VIOLATION: me handler is missing 'current_user' parameter. "
        "GET /api/v1/auth/me must authenticate the user via dependency injection."
    )

    # Verify it returns a Response with data=current_user
    has_response_with_data = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "Response")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "Response")
        )
        for node in ast.walk(me_func)
    )
    assert has_response_with_data, (
        "PRESERVATION VIOLATION: me handler does not return a Response object. "
        "GET /api/v1/auth/me must return the current user profile."
    )


def test_refresh_token_handler_returns_access_token_and_token_type():
    """
    Property 2a: POST /api/v1/auth/refresh handler returns access_token and token_type.
    Preservation: refresh endpoint continues to return token data after fixes.
    MUST PASS on unfixed code — confirms baseline behavior.
    """
    tree = _parse_file("routes", "account", "users.py")

    refresh_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "refresh_token":
            refresh_func = node
            break

    assert refresh_func is not None, (
        "refresh_token handler not found in routes/account/users.py — "
        "POST /api/v1/auth/refresh endpoint is missing"
    )

    # Verify the response dict contains 'access_token' and 'token_type' keys
    token_keys_returned = set()
    for node in ast.walk(refresh_func):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    token_keys_returned.add(key.value)

    required_keys = {"access_token", "token_type"}
    missing = required_keys - token_keys_returned
    assert not missing, (
        f"PRESERVATION VIOLATION: refresh_token handler response is missing keys: {missing}. "
        "POST /api/v1/auth/refresh must return access_token and token_type."
    )


# ---------------------------------------------------------------------------
# Property 2b — Kafka Handler Registration Preservation
# Validates: Requirements 3.22, 3.23
# ---------------------------------------------------------------------------

EXPECTED_KAFKA_HANDLERS = {
    "GRADE_SUBMISSION_ATTEMPT": ("tasks/submission.py", "handle_grade_submission_attempt"),
    "REFRESH_DASHBOARD": ("tasks/submission.py", "handle_refresh_dashboard"),
    "DETECT_ANSWER": ("tasks/question.py", "handle_detect_answer"),
    "PARSE_AND_CREATE": ("tasks/question.py", "handle_parse_and_create"),
    "SEND_EMAIL": ("tasks/email.py", "handle_send_email"),
    "UPDATE_EXAM_STATUS": ("tasks/exam.py", "handle_update_exam_status"),
    "SEND_QUEUED_EMAILS": ("tasks/exam.py", "handle_send_queued_emails"),
}


def test_kafka_consumer_load_handlers_registers_all_seven():
    """
    Property 2b: All 7 Kafka event handlers are registered across task modules.
    Preservation: all existing Kafka handlers continue to be registered after dispatcher refactor.
    MUST PASS — confirms baseline handler registration via dispatcher pattern.
    """
    # After the dispatcher refactor, handlers are registered in task module HANDLERS dicts,
    # not hardcoded in _load_handlers. Check each task module for its HANDLERS dict.
    registered_events: set = set()

    for module_path, (file_path, _) in EXPECTED_KAFKA_HANDLERS.items():
        # file_path is like "tasks/submission.py" — parse it
        tree = _parse_file(*file_path.split("/"))
        # Look for HANDLERS = { ... } or HANDLERS: dict = { ... } at module level
        for node in ast.walk(tree):
            # Handle both `HANDLERS = {...}` (Assign) and `HANDLERS: dict = {...}` (AnnAssign)
            value_node = None
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "HANDLERS":
                        value_node = node.value
                        break
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "HANDLERS":
                    value_node = node.value

            if value_node is not None and isinstance(value_node, ast.Dict):
                for key in value_node.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        registered_events.add(key.value)

    expected_events = set(EXPECTED_KAFKA_HANDLERS.keys())
    missing = expected_events - registered_events
    assert not missing, (
        f"PRESERVATION VIOLATION: HANDLERS dicts in task modules are missing: {missing}. "
        "All 7 Kafka event handlers must remain registered to preserve worker functionality."
    )


def test_kafka_consumer_uses_manual_offset_commit():
    """
    Property 2b: KafkaConsumerService uses manual offset commit (enable_auto_commit=False).
    Preservation: manual commit pattern is preserved after any consumer refactor.
    MUST PASS on unfixed code — confirms baseline consumer configuration.
    """
    tree = _parse_file("core", "utils", "kafka", "consumer.py")

    # Find enable_auto_commit=False in the consumer builder
    has_manual_commit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword):
            if node.arg == "enable_auto_commit":
                if isinstance(node.value, ast.Constant) and node.value.value is False:
                    has_manual_commit = True
                    break

    assert has_manual_commit, (
        "PRESERVATION VIOLATION: KafkaConsumerService does not use manual offset commit. "
        "enable_auto_commit=False must be preserved to ensure at-least-once delivery semantics."
    )


def test_kafka_consumer_has_dead_letter_logging():
    """
    Property 2b: KafkaConsumerService logs failed handler events (dead-letter logging).
    Preservation: dead-letter logging pattern is preserved after any consumer refactor.
    MUST PASS — confirms baseline error handling.
    """
    tree = _parse_file("core", "utils", "kafka", "consumer.py")

    # Find the _handle_message method and verify it has error/exception logging
    handle_message_func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_handle_message":
            handle_message_func = node
            break

    assert handle_message_func is not None, (
        "_handle_message method not found in core/utils/kafka/consumer.py"
    )

    # Verify there's a logger.error or logger.exception call in _handle_message
    # (dead-letter forwarding may be delegated to _forward_to_dead_letter)
    has_error_logging = False
    for node in ast.walk(handle_message_func):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("exception", "error"):
                has_error_logging = True
                break

    assert has_error_logging, (
        "PRESERVATION VIOLATION: _handle_message does not have dead-letter logging. "
        "logger.error() or logger.exception() must be called on handler failures to preserve observability."
    )


@pytest.mark.parametrize("event_type,handler_info", list(EXPECTED_KAFKA_HANDLERS.items()))
def test_kafka_handler_function_exists_as_async_def(event_type, handler_info):
    """
    Property 2b: Each Kafka handler function exists as an async def in its module.
    Preservation: all handler functions remain async and callable after refactor.
    MUST PASS on unfixed code — confirms baseline handler implementations exist.
    """
    module_path, handler_name = handler_info
    tree = _parse_file(*module_path.split("/"))

    handler_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == handler_name:
            handler_func = node
            break

    assert handler_func is not None, (
        f"PRESERVATION VIOLATION: {handler_name} not found as async def in {module_path}. "
        f"The Kafka handler for '{event_type}' must remain an async function."
    )


# ---------------------------------------------------------------------------
# Property 2c — Non-Buggy Model to_dict() Field Preservation
# Validates: Requirements 3.36
# ---------------------------------------------------------------------------

def test_user_to_dict_preserves_expected_fields():
    """
    Property 2c: User.to_dict() includes all expected fields.
    Preservation: User model to_dict() output is unchanged after new columns are added.
    MUST PASS on unfixed code — confirms baseline User serialization.
    """
    actual_keys = _get_to_dict_keys("User", "models", "account", "users.py")
    expected_fields = {
        "id", "first_name", "middle_name", "last_name", "email", "role",
        "is_active", "is_locked", "tenant_id", "institution_id",
        "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: User.to_dict() is missing fields: {missing}. "
        "These fields must remain in the User serialization output."
    )


def test_tenant_to_dict_preserves_expected_fields():
    """
    Property 2c: Tenant.to_dict() includes all expected fields.
    Preservation: Tenant model to_dict() output is unchanged after new columns are added.
    MUST PASS on unfixed code — confirms baseline Tenant serialization.
    """
    actual_keys = _get_to_dict_keys("Tenant", "models", "account", "tenant.py")
    expected_fields = {
        "id", "name", "domain", "logo_url", "is_active", "is_deleted",
        "deleted_at", "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: Tenant.to_dict() is missing fields: {missing}. "
        "These fields must remain in the Tenant serialization output."
    )


def test_course_to_dict_preserves_expected_fields():
    """
    Property 2c: Course.to_dict() includes all expected fields.
    Preservation: Course model to_dict() output is unchanged after any refactor.
    MUST PASS on unfixed code — confirms baseline Course serialization.
    """
    actual_keys = _get_to_dict_keys("Course", "models", "academic", "course.py")
    expected_fields = {
        "id", "name", "description", "course_code", "tenant_id", "semester_id",
        "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: Course.to_dict() is missing fields: {missing}. "
        "These fields must remain in the Course serialization output."
    )


def test_exam_to_dict_preserves_expected_fields():
    """
    Property 2c: Exam.to_dict() includes all expected fields.
    Preservation: Exam model to_dict() output is unchanged after new columns are added.
    MUST PASS on unfixed code — confirms baseline Exam serialization.
    """
    actual_keys = _get_to_dict_keys("Exam", "models", "academic", "exam.py")
    expected_fields = {
        "id", "title", "description", "start_time", "duration_hours", "duration_minutes",
        "total_marks", "passing_marks", "status", "max_attempts", "tenant_id", "semester_id",
        "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: Exam.to_dict() is missing fields: {missing}. "
        "These fields must remain in the Exam serialization output."
    )


def test_submission_to_dict_preserves_expected_fields():
    """
    Property 2c: Submission.to_dict() includes all expected fields.
    Preservation: Submission model to_dict() output is unchanged after new columns are added.
    MUST PASS on unfixed code — confirms baseline Submission serialization.
    """
    actual_keys = _get_to_dict_keys("Submission", "models", "academic", "submission.py")
    expected_fields = {
        "id", "student_id", "exam_id", "tenant_id", "semester_id",
        "latest_score", "attempts", "status", "graded_at",
        "created_at", "updated_at",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: Submission.to_dict() is missing fields: {missing}. "
        "These fields must remain in the Submission serialization output."
    )


def test_submission_attempt_to_dict_preserves_expected_fields():
    """
    Property 2c: SubmissionAttempt.to_dict() includes all expected fields.
    Preservation: SubmissionAttempt model to_dict() output is unchanged after new columns are added.
    MUST PASS on unfixed code — confirms baseline SubmissionAttempt serialization.
    """
    actual_keys = _get_to_dict_keys("SubmissionAttempt", "models", "academic", "submission.py")
    expected_fields = {"id", "submission_id", "score", "created_at"}
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: SubmissionAttempt.to_dict() is missing fields: {missing}. "
        "These fields must remain in the SubmissionAttempt serialization output."
    )


def test_lecturer_dashboard_to_dict_preserves_expected_fields():
    """
    Property 2c: LecturerDashboard.to_dict() includes all expected fields.
    Preservation: LecturerDashboard model to_dict() output is unchanged after any refactor.
    MUST PASS on unfixed code — confirms baseline LecturerDashboard serialization.
    """
    actual_keys = _get_to_dict_keys("LecturerDashboard", "models", "analytics", "dashboard.py")
    expected_fields = {
        "id", "lecturer_id", "tenant_id", "total_courses", "active_courses",
        "total_students", "total_exams", "pending_submissions", "graded_submissions",
        "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: LecturerDashboard.to_dict() is missing fields: {missing}. "
        "These fields must remain in the LecturerDashboard serialization output."
    )


def test_admin_dashboard_to_dict_preserves_expected_fields():
    """
    Property 2c: AdminDashboard.to_dict() includes all expected fields.
    Preservation: AdminDashboard model to_dict() output is unchanged after any refactor.
    MUST PASS on unfixed code — confirms baseline AdminDashboard serialization.
    """
    actual_keys = _get_to_dict_keys("AdminDashboard", "models", "analytics", "dashboard.py")
    expected_fields = {
        "id", "tenant_id", "total_users", "total_students", "total_lecturers",
        "total_courses", "total_exams", "total_submissions",
        "pending_submissions", "graded_submissions",
        "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: AdminDashboard.to_dict() is missing fields: {missing}. "
        "These fields must remain in the AdminDashboard serialization output."
    )


def test_student_dashboard_to_dict_preserves_expected_fields():
    """
    Property 2c: StudentDashboard.to_dict() includes all expected fields.
    Preservation: StudentDashboard model to_dict() output is unchanged after any refactor.
    MUST PASS on unfixed code — confirms baseline StudentDashboard serialization.
    """
    actual_keys = _get_to_dict_keys("StudentDashboard", "models", "analytics", "dashboard.py")
    expected_fields = {
        "id", "student_id", "tenant_id", "total_courses", "active_courses",
        "completed_courses", "total_exams", "upcoming_exams", "missed_exams",
        "total_submissions", "graded_submissions", "pending_submissions",
        "average_score", "created_at", "updated_at", "created_by", "updated_by",
    }
    missing = expected_fields - actual_keys
    assert not missing, (
        f"PRESERVATION VIOLATION: StudentDashboard.to_dict() is missing fields: {missing}. "
        "These fields must remain in the StudentDashboard serialization output."
    )


# ---------------------------------------------------------------------------
# Property 2d — Docker Non-Buggy Services Preservation
# Validates: Requirement 3.14
# ---------------------------------------------------------------------------

def test_docker_postgres_service_is_intact():
    """
    Property 2d: docker-compose.yml postgres service has image, healthcheck, and volumes.
    Preservation: postgres service definition is unchanged after docker-compose.yml is fixed.
    MUST PASS on unfixed code — confirms baseline postgres service configuration.
    """
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "postgres" in services, (
        "PRESERVATION VIOLATION: 'postgres' service not found in docker-compose.yml. "
        "The postgres service must remain defined as a top-level service."
    )

    postgres = services["postgres"]

    assert "image" in postgres, (
        "PRESERVATION VIOLATION: postgres service has no 'image' defined. "
        "The postgres image must remain specified."
    )
    assert "postgres" in postgres["image"].lower(), (
        f"PRESERVATION VIOLATION: postgres service image '{postgres['image']}' does not contain 'postgres'. "
        "The postgres image must reference a postgres image."
    )

    assert "healthcheck" in postgres, (
        "PRESERVATION VIOLATION: postgres service has no 'healthcheck' defined. "
        "The postgres healthcheck must remain to ensure dependent services wait for readiness."
    )

    assert "volumes" in postgres, (
        "PRESERVATION VIOLATION: postgres service has no 'volumes' defined. "
        "The postgres volumes must remain to ensure data persistence."
    )


def test_docker_redis_service_is_intact():
    """
    Property 2d: docker-compose.yml redis service has image, healthcheck, and volumes.
    Preservation: redis service definition is unchanged after docker-compose.yml is fixed.
    MUST PASS on unfixed code — confirms baseline redis service configuration.
    """
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "redis" in services, (
        "PRESERVATION VIOLATION: 'redis' service not found in docker-compose.yml. "
        "The redis service must remain defined as a top-level service."
    )

    redis = services["redis"]

    assert "image" in redis, (
        "PRESERVATION VIOLATION: redis service has no 'image' defined. "
        "The redis image must remain specified."
    )
    assert "redis" in redis["image"].lower(), (
        f"PRESERVATION VIOLATION: redis service image '{redis['image']}' does not contain 'redis'. "
        "The redis image must reference a redis image."
    )

    assert "healthcheck" in redis, (
        "PRESERVATION VIOLATION: redis service has no 'healthcheck' defined. "
        "The redis healthcheck must remain to ensure dependent services wait for readiness."
    )

    assert "volumes" in redis, (
        "PRESERVATION VIOLATION: redis service has no 'volumes' defined. "
        "The redis volumes must remain to ensure data persistence."
    )


def test_docker_non_buggy_services_are_top_level():
    """
    Property 2d: postgres and redis are top-level services in docker-compose.yml.
    Preservation: these services remain top-level after the pgbouncer/scheduler fix.
    MUST PASS on unfixed code — confirms postgres and redis are not affected by the nesting bug.
    """
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    top_level_services = list(compose.get("services", {}).keys())

    for service in ("postgres", "redis"):
        assert service in top_level_services, (
            f"PRESERVATION VIOLATION: '{service}' is not a top-level service in docker-compose.yml. "
            f"Top-level services found: {top_level_services}. "
            f"The {service} service must remain at the top level."
        )
