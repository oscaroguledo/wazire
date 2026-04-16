from __future__ import annotations

from typing import Optional, Any
import re

# HTML tags that are allowed (can be customized)
ALLOWED_TAGS = {
    'b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'code', 'pre'
}

# HTML attributes that are allowed
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
}


class Sanitizer:
    """Input sanitization utility for preventing XSS attacks."""
    
    @staticmethod
    def sanitize_string(value: Optional[str]) -> Optional[str]:
        """Sanitize a string by removing potentially dangerous content.
        
        This removes HTML tags and scripts to prevent XSS attacks.
        For rich text content, use a proper HTML sanitizer library like bleach.
        """
        if value is None:
            return None
        
        if not isinstance(value, str):
            return str(value)
        
        # Remove script tags and their content
        value = re.sub(r'<script.*?>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers (onclick, onerror, etc.)
        value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
        
        # Remove javascript: protocol
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        
        # Remove other potentially dangerous HTML tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
        for tag in dangerous_tags:
            value = re.sub(f'<{tag}.*?>', '', value, flags=re.IGNORECASE)
            value = re.sub(f'</{tag}>', '', value, flags=re.IGNORECASE)
        
        return value.strip()
    
    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        """Recursively sanitize all string values in a dictionary."""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = Sanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = Sanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = Sanitizer.sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_list(data: list) -> list:
        """Recursively sanitize all string values in a list."""
        if not isinstance(data, list):
            return data
        
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(Sanitizer.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(Sanitizer.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(Sanitizer.sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    @staticmethod
    def sanitize_email(email: Optional[str]) -> Optional[str]:
        """Sanitize and validate email format."""
        if email is None:
            return None
        
        email = email.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        return email
    
    @staticmethod
    def sanitize_filename(filename: Optional[str]) -> Optional[str]:
        """Sanitize filename to prevent path traversal attacks."""
        if filename is None:
            return None
        
        # Remove path traversal characters
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Keep only safe characters
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        
        return filename


def sanitize_input(value: Any) -> Any:
    """Convenience function to sanitize any input."""
    if value is None:
        return None
    
    if isinstance(value, str):
        return Sanitizer.sanitize_string(value)
    elif isinstance(value, dict):
        return Sanitizer.sanitize_dict(value)
    elif isinstance(value, list):
        return Sanitizer.sanitize_list(value)
    
    return value
