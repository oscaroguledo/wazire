"""Unit tests for core.utils.sanitization module.

Tests the Sanitizer class and sanitize_input convenience function.
"""
import pytest
from core.utils.sanitization import Sanitizer, sanitize_input


class TestSanitizerString:
    """Tests for Sanitizer.sanitize_string."""

    def test_sanitize_none_returns_none(self):
        """Test that sanitize_string returns None for None input."""
        assert Sanitizer.sanitize_string(None) is None

    def test_sanitize_plain_text_unchanged(self):
        """Test that plain text without HTML is returned unchanged."""
        text = "Hello, World!"
        assert Sanitizer.sanitize_string(text) == text

    def test_sanitize_removes_script_tags(self):
        """Test that script tags and their content are removed."""
        text = 'Hello <script>alert("xss")</script> World'
        result = Sanitizer.sanitize_string(text)
        
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_removes_event_handlers(self):
        """Test that event handler attributes are removed."""
        text = '<img src="x" onerror="alert(1)">'
        result = Sanitizer.sanitize_string(text)
        
        assert "onerror" not in result

    def test_sanitize_removes_javascript_protocol(self):
        """Test that javascript: protocol is removed."""
        text = '<a href="javascript:alert(1)">click</a>'
        result = Sanitizer.sanitize_string(text)
        
        assert "javascript:" not in result

    def test_sanitize_removes_iframe(self):
        """Test that iframe tags are removed."""
        text = '<iframe src="evil.com"></iframe>'
        result = Sanitizer.sanitize_string(text)
        
        assert "<iframe" not in result

    def test_sanitize_non_string_converts_to_string(self):
        """Test that non-string values are converted to string."""
        result = Sanitizer.sanitize_string(42)
        assert result == "42"


class TestSanitizerDict:
    """Tests for Sanitizer.sanitize_dict."""

    def test_sanitize_dict_cleans_string_values(self):
        """Test that string values in dict are sanitized."""
        data = {
            "name": 'Test <script>alert("xss")</script>',
            "age": 25,
        }
        result = Sanitizer.sanitize_dict(data)
        
        assert "<script>" not in result["name"]
        assert result["age"] == 25

    def test_sanitize_dict_recursive(self):
        """Test that nested dicts are recursively sanitized."""
        data = {
            "user": {
                "name": '<script>evil</script>',
                "email": "test@test.com",
            }
        }
        result = Sanitizer.sanitize_dict(data)
        
        assert "<script>" not in result["user"]["name"]
        assert result["user"]["email"] == "test@test.com"

    def test_sanitize_dict_with_list_values(self):
        """Test that list values in dict are sanitized."""
        data = {
            "tags": ['<script>evil</script>', "safe_tag"],
        }
        result = Sanitizer.sanitize_dict(data)
        
        assert "<script>" not in result["tags"][0]
        assert result["tags"][1] == "safe_tag"


class TestSanitizerEmail:
    """Tests for Sanitizer.sanitize_email."""

    def test_sanitize_valid_email(self):
        """Test that valid email is returned lowercased and stripped."""
        result = Sanitizer.sanitize_email("  Test@Example.COM  ")
        assert result == "test@example.com"

    def test_sanitize_none_email_returns_none(self):
        """Test that None email returns None."""
        assert Sanitizer.sanitize_email(None) is None

    def test_sanitize_invalid_email_raises(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Sanitizer.sanitize_email("not_an_email")


class TestSanitizerFilename:
    """Tests for Sanitizer.sanitize_filename."""

    def test_sanitize_safe_filename_unchanged(self):
        """Test that safe filenames are returned unchanged."""
        result = Sanitizer.sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_removes_path_traversal(self):
        """Test that path traversal characters are removed."""
        result = Sanitizer.sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_none_filename_returns_none(self):
        """Test that None filename returns None."""
        assert Sanitizer.sanitize_filename(None) is None


class TestSanitizeInput:
    """Tests for the sanitize_input convenience function."""

    def test_sanitize_string(self):
        """Test that sanitize_input handles strings."""
        result = sanitize_input('<script>evil</script>')
        assert "<script>" not in result

    def test_sanitize_dict(self):
        """Test that sanitize_input handles dicts."""
        data = {"key": '<script>evil</script>'}
        result = sanitize_input(data)
        assert "<script>" not in result["key"]

    def test_sanitize_list(self):
        """Test that sanitize_input handles lists."""
        data = ['<script>evil</script>', "safe"]
        result = sanitize_input(data)
        assert "<script>" not in result[0]

    def test_sanitize_none_returns_none(self):
        """Test that sanitize_input returns None for None."""
        assert sanitize_input(None) is None

    def test_sanitize_number_returns_unchanged(self):
        """Test that sanitize_input returns numbers unchanged."""
        assert sanitize_input(42) == 42
