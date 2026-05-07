"""
Bug Condition Exploration Tests — Property 1
============================================
These tests encode the EXPECTED (fixed) behavior.
On UNFIXED code, every test in this file MUST FAIL.
Failure = the bug exists and has been confirmed.

DO NOT fix the code or the tests when they fail.
Run with: cd backend && python -m pytest tests/test_bug_condition_exploration.py -v

Validates: Requirements 1.1, 1.4, 1.6, 1.7, 1.9, 1.10, 1.12, 1.13, 1.22, 1.30, 1.52
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


# ---------------------------------------------------------------------------
# Test 1 — Lifespan yield
# Validates: Requirement 1.1
# ---------------------------------------------------------------------------
def test_lifespan_has_yield():
    """
    Bug 1.1: lifespan context manager has no yield.
    Expected: lifespan function body contains a yield statement.
    On unfixed code: FAILS — no yield found.
    """
    tree = _parse_file("main.py")

    lifespan_func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == "lifespan":
            lifespan_func = node
            break

    assert lifespan_func is not None, "lifespan function not found in main.py"

    has_yield = any(
        isinstance(node, (ast.Yield, ast.YieldFrom))
        for node in ast.walk(lifespan_func)
    )
    assert has_yield, (
        "BUG 1.1 CONFIRMED: lifespan() has no yield statement. "
        "The server runs startup code then immediately runs shutdown code, "
        "never entering the application runtime."
    )


# ---------------------------------------------------------------------------
# Test 2 — Invoice.to_dict crash
# Validates: Requirement 1.9
# ---------------------------------------------------------------------------
def test_invoice_has_status_column():
    """
    Bug 1.9: Invoice model missing 'status' column.
    Expected: Invoice has a 'status' mapped column.
    On unfixed code: FAILS — AttributeError when accessing self.status.
    """
    tree = _parse_file("models", "billings", "invoice.py")

    invoice_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Invoice":
            invoice_class = node
            break

    assert invoice_class is not None, "Invoice class not found in models/billings/invoice.py"

    has_status_column = any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "status"
        for node in ast.walk(invoice_class)
    )
    assert has_status_column, (
        "BUG 1.9 CONFIRMED: Invoice model has no 'status' mapped column. "
        "Calling Invoice().to_dict() raises AttributeError: 'Invoice' object has no attribute 'status'."
    )


# ---------------------------------------------------------------------------
# Test 3 — BillingPlan.to_dict crash
# Validates: Requirement 1.10
# ---------------------------------------------------------------------------
def test_billing_plan_has_is_active_column():
    """
    Bug 1.10: BillingPlan model missing 'is_active' column.
    Expected: BillingPlan has an 'is_active' mapped column.
    On unfixed code: FAILS — AttributeError when accessing self.is_active.
    """
    tree = _parse_file("models", "billings", "plan.py")

    billing_plan_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BillingPlan":
            billing_plan_class = node
            break

    assert billing_plan_class is not None, "BillingPlan class not found in models/billings/plan.py"

    has_is_active_column = any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "is_active"
        for node in ast.walk(billing_plan_class)
    )
    assert has_is_active_column, (
        "BUG 1.10 CONFIRMED: BillingPlan model has no 'is_active' mapped column. "
        "Calling BillingPlan().to_dict() raises AttributeError: 'BillingPlan' object has no attribute 'is_active'."
    )


# ---------------------------------------------------------------------------
# Test 4 — models/__init__ import crash
# Validates: Requirement 1.4
# ---------------------------------------------------------------------------
def test_models_init_has_no_broken_imports():
    """
    Bug 1.4: models/__init__.py imports from non-existent modules.
    Expected: models/__init__.py imports only from modules that exist.
    On unfixed code: FAILS — ModuleNotFoundError for oauth, ImportError for PaymentMethodDetails.
    """
    tree = _parse_file("models", "__init__.py")

    broken_imports = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        names = [alias.name for alias in node.names]

        # Check for oauth import — file models/account/oauth.py must exist
        if "oauth" in module.lower() and "account" in module.lower():
            module_path = module.replace(".", os.sep) + ".py"
            full_path = os.path.join(BACKEND_DIR, module_path)
            if not os.path.exists(full_path):
                broken_imports.append(
                    f"Module '{module}' does not exist (file not found: {full_path}); "
                    f"imports: {names}"
                )

        # Check for PaymentMethodDetails — class must exist in the target module
        if "PaymentMethodDetails" in names:
            module_path = module.replace(".", os.sep) + ".py"
            full_path = os.path.join(BACKEND_DIR, module_path)
            if os.path.exists(full_path):
                with open(full_path) as mf:
                    module_source = mf.read()
                module_tree = ast.parse(module_source)
                class_names = [
                    n.name for n in ast.walk(module_tree)
                    if isinstance(n, ast.ClassDef)
                ]
                if "PaymentMethodDetails" not in class_names:
                    broken_imports.append(
                        f"Class 'PaymentMethodDetails' not found in '{module}' "
                        f"(classes present: {class_names})"
                    )
            else:
                broken_imports.append(
                    f"Module '{module}' does not exist; cannot import PaymentMethodDetails"
                )

    assert not broken_imports, (
        "BUG 1.4 CONFIRMED: models/__init__.py has broken imports:\n"
        + "\n".join(f"  - {b}" for b in broken_imports)
    )


# ---------------------------------------------------------------------------
# Test 5 — SubmissionService field mismatch
# Validates: Requirement 1.7
# ---------------------------------------------------------------------------
def test_submission_service_uses_correct_field_name():
    """
    Bug 1.7: SubmissionService uses 'attempts_count' but model column is 'attempts'.
    Expected: SubmissionService uses 'attempts=0' not 'attempts_count=0'.
    On unfixed code: FAILS — wrong field name found in service.
    """
    tree = _parse_file("services", "academic", "submission.py")

    wrong_field_usages = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "attempts_count":
                    wrong_field_usages.append(
                        f"Found 'attempts_count=' keyword argument at line {node.lineno}"
                    )

    assert not wrong_field_usages, (
        "BUG 1.7 CONFIRMED: SubmissionService uses wrong field name 'attempts_count':\n"
        + "\n".join(f"  - {u}" for u in wrong_field_usages)
        + "\nThe Submission model column is named 'attempts', not 'attempts_count'. "
        "This raises TypeError: unexpected keyword argument 'attempts_count'."
    )


# ---------------------------------------------------------------------------
# Test 6 — get_db() misuse
# Validates: Requirement 1.6
# ---------------------------------------------------------------------------
def test_grade_attempt_background_uses_correct_db_pattern():
    """
    Bug 1.6: grade_attempt_background uses 'async with get_db()' but get_db() is an async generator.
    Expected: Uses 'async for db in get_db()' pattern (or equivalent).
    On unfixed code: FAILS — async context manager pattern found.
    """
    tree = _parse_file("services", "academic", "submission.py")

    grade_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "grade_attempt_background":
            grade_func = node
            break

    assert grade_func is not None, "grade_attempt_background function not found in services/academic/submission.py"

    async_with_get_db = False
    for node in ast.walk(grade_func):
        if isinstance(node, ast.AsyncWith):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call):
                    func = ctx.func
                    func_name = (
                        func.id if isinstance(func, ast.Name)
                        else func.attr if isinstance(func, ast.Attribute)
                        else ""
                    )
                    if func_name == "get_db":
                        async_with_get_db = True

    assert not async_with_get_db, (
        "BUG 1.6 CONFIRMED: grade_attempt_background() uses 'async with get_db() as db:' "
        "but get_db() is an async generator, not an async context manager. "
        "This raises AttributeError: __aenter__. "
        "Fix: use 'async for db in get_db(): ...' instead."
    )


# ---------------------------------------------------------------------------
# Test 7 — Docker compose structure
# Validates: Requirements 1.12, 1.13
# ---------------------------------------------------------------------------
def test_docker_compose_pgbouncer_and_scheduler_are_top_level():
    """
    Bug 1.12 & 1.13: pgbouncer and scheduler are nested under sibling services.
    Expected: Both are top-level services in docker-compose.yml.
    On unfixed code: FAILS — both are nested (not top-level).
    """
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    top_level_services = list(compose.get("services", {}).keys())

    missing = []
    if "pgbouncer" not in top_level_services:
        missing.append(
            "pgbouncer is NOT a top-level service — it is nested under 'postgres' "
            "(indented one level too deep). Docker Compose silently ignores it."
        )
    if "scheduler" not in top_level_services:
        missing.append(
            "scheduler is NOT a top-level service — it is nested under 'worker' "
            "(indented one level too deep). The scheduler process never runs."
        )

    assert not missing, (
        "BUG 1.12/1.13 CONFIRMED:\n"
        + "\n".join(f"  - {m}" for m in missing)
        + f"\nTop-level services found: {top_level_services}"
    )


# ---------------------------------------------------------------------------
# Test 8 — Answer PATCH method
# Validates: Requirement 1.22
# ---------------------------------------------------------------------------
def test_answer_route_uses_patch_not_put():
    """
    Bug 1.22: Answer upsert route uses PUT instead of PATCH, and writes directly to DB.
    Expected: Route uses @router.patch() and emits a Kafka event.
    On unfixed code: FAILS — PUT method found, no Kafka emit.
    """
    tree = _parse_file("routes", "academic", "answers.py")

    issues = []

    # Check for @router.put decorator on upsert_answer
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "upsert_answer":
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "put":
                            issues.append(
                                f"upsert_answer uses @router.put() at line {node.lineno} — should be @router.patch()"
                            )

    # Check that a Kafka emit call exists in upsert_answer
    upsert_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "upsert_answer":
            upsert_func = node
            break

    if upsert_func:
        kafka_keywords = {"emit", "publish", "publish_safe", "kafka_manager", "producer_service"}
        has_kafka_emit = any(
            (
                isinstance(node, ast.Call)
                and (
                    (isinstance(node.func, ast.Attribute) and node.func.attr in kafka_keywords)
                    or (isinstance(node.func, ast.Name) and node.func.id in kafka_keywords)
                )
            )
            for node in ast.walk(upsert_func)
        )
        if not has_kafka_emit:
            issues.append(
                "upsert_answer does NOT emit a Kafka event — writes directly to DB via "
                "StudentAnswerService.upsert(). This bypasses the intended Kafka buffer."
            )

    assert not issues, (
        "BUG 1.22 CONFIRMED:\n"
        + "\n".join(f"  - {i}" for i in issues)
    )


# ---------------------------------------------------------------------------
# Test 9 — StudentAnswer UPSERT race (no UNIQUE constraint)
# Validates: Requirement 1.30
# ---------------------------------------------------------------------------
def test_student_answer_has_unique_constraint():
    """
    Bug 1.30: StudentAnswer model has no UNIQUE constraint on (student_id, exam_id, question_id).
    Expected: UniqueConstraint('student_id', 'exam_id', 'question_id') exists in __table_args__.
    On unfixed code: FAILS — no unique constraint found.
    """
    tree = _parse_file("models", "academic", "student_answer.py")

    sa_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "StudentAnswer":
            sa_class = node
            break

    assert sa_class is not None, "StudentAnswer class not found in models/academic/student_answer.py"

    has_unique_constraint = False
    for node in ast.walk(sa_class):
        if isinstance(node, ast.Call):
            func = node.func
            func_name = (
                func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute)
                else ""
            )
            if func_name == "UniqueConstraint":
                args = [
                    arg.value if isinstance(arg, ast.Constant) else ""
                    for arg in node.args
                ]
                if all(col in args for col in ("student_id", "exam_id", "question_id")):
                    has_unique_constraint = True
                    break

    assert has_unique_constraint, (
        "BUG 1.30 CONFIRMED: StudentAnswer model has no UniqueConstraint on "
        "(student_id, exam_id, question_id). "
        "Concurrent PATCH requests for the same tuple can produce duplicate rows "
        "because there is no database-level UNIQUE constraint and no ON CONFLICT DO UPDATE clause."
    )


# ---------------------------------------------------------------------------
# Test 10 — Dashboard GET write
# Validates: Requirement 1.52
# ---------------------------------------------------------------------------
def test_dashboard_get_handlers_are_read_only():
    """
    Bug 1.52: Dashboard GET handlers call db.add() and db.commit() (OLAP/OLTP violation).
    Expected: get_or_create_* methods do NOT write to DB.
    On unfixed code: FAILS — db.add() and db.commit() found in get_or_create methods.
    """
    tree = _parse_file("services", "analytics", "dashboard.py")

    write_violations = []
    get_or_create_methods = {
        "get_or_create_lecturer_dashboard",
        "get_or_create_admin_dashboard",
        "get_or_create_student_dashboard",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name in get_or_create_methods:
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute) and func.attr in ("add", "commit"):
                        write_violations.append(
                            f"{node.name}() calls self.db.{func.attr}() at line {child.lineno} "
                            "— GET handlers must not write to the database (OLAP/OLTP violation)"
                        )

    assert not write_violations, (
        "BUG 1.52 CONFIRMED: Dashboard GET handlers perform DB writes:\n"
        + "\n".join(f"  - {v}" for v in write_violations)
    )
