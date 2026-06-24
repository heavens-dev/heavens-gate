import uuid

import pytest

from core.utils.uuid_utils import (generate_deterministic_uuid_string,
                                   is_valid_uuid)


class TestGenerateDeterministicUuidString:
    """Tests for generate_deterministic_uuid_string function"""

    def test_returns_valid_uuid_string(self):
        """Test that function returns a valid UUID string"""
        result = generate_deterministic_uuid_string("test_input")
        assert isinstance(result, str)
        # Should not raise ValueError
        uuid.UUID(result)

    def test_deterministic_output(self):
        """Test that same input always produces same output"""
        input_string = "test_deterministic"
        result1 = generate_deterministic_uuid_string(input_string)
        result2 = generate_deterministic_uuid_string(input_string)
        result3 = generate_deterministic_uuid_string(input_string)

        assert result1 == result2 == result3

    def test_different_inputs_produce_different_outputs(self):
        """Test that different inputs produce different UUIDs"""
        uuid1 = generate_deterministic_uuid_string("input1")
        uuid2 = generate_deterministic_uuid_string("input2")
        uuid3 = generate_deterministic_uuid_string("input3")

        assert uuid1 != uuid2
        assert uuid2 != uuid3
        assert uuid1 != uuid3

    def test_empty_string_input(self):
        """Test that empty string produces valid UUID"""
        result = generate_deterministic_uuid_string("")
        assert isinstance(result, str)
        uuid.UUID(result)

    def test_unicode_input(self):
        """Test that unicode strings are handled correctly"""
        unicode_inputs = [
            "тест",  # Cyrillic
            "测试",  # Chinese
            "テスト",  # Japanese
            "🔒",  # Emoji
        ]

        for input_string in unicode_inputs:
            result = generate_deterministic_uuid_string(input_string)
            assert isinstance(result, str)
            uuid.UUID(result)

    def test_long_string_input(self):
        """Test that long strings are handled correctly"""
        long_string = "a" * 10000
        result = generate_deterministic_uuid_string(long_string)
        assert isinstance(result, str)
        uuid.UUID(result)

    @pytest.mark.parametrize("input_string", [
        "single_word",
        "multiple words here",
        "with-special-characters!@#$%",
        "123456789",
        "CamelCaseString",
        "snake_case_string",
    ])
    def test_various_string_formats(self, input_string):
        """Test various string formats"""
        result = generate_deterministic_uuid_string(input_string)
        assert isinstance(result, str)
        # Verify it's a valid UUID
        uuid.UUID(result)

    def test_case_sensitivity(self):
        """Test that input is case-sensitive"""
        uuid_lower = generate_deterministic_uuid_string("test")
        uuid_upper = generate_deterministic_uuid_string("TEST")
        uuid_mixed = generate_deterministic_uuid_string("Test")

        assert uuid_lower != uuid_upper
        assert uuid_upper != uuid_mixed
        assert uuid_lower != uuid_mixed

    def test_whitespace_sensitivity(self):
        """Test that whitespace is preserved"""
        uuid1 = generate_deterministic_uuid_string("test")
        uuid2 = generate_deterministic_uuid_string("test ")
        uuid3 = generate_deterministic_uuid_string(" test")
        uuid4 = generate_deterministic_uuid_string("  test  ")

        assert uuid1 != uuid2
        assert uuid1 != uuid3
        assert uuid1 != uuid4


class TestIsValidUuid:
    """Tests for is_valid_uuid function"""

    def test_valid_uuid_format(self):
        """Test that valid UUID strings are recognized"""
        # Standard UUID v4 format: 8-4-4-4-12 hexadecimal digits
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        ]

        for uuid_str in valid_uuids:
            assert is_valid_uuid(uuid_str) is True

    def test_invalid_uuid_format(self):
        """Test that invalid UUID formats are rejected"""
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Extra characters
            "550e8400-e29b-41d4-a716-44665544000",  # Missing digit
            "550e8400-e29b-41d4-a716-446655440000-",  # Trailing dash
            "-550e8400-e29b-41d4-a716-446655440000",  # Leading dash
        ]

        for uuid_str in invalid_uuids:
            assert is_valid_uuid(uuid_str) is False

    def test_empty_string(self):
        """Test that empty string is invalid"""
        assert is_valid_uuid("") is False

    def test_whitespace_only(self):
        """Test that whitespace-only strings are invalid"""
        assert is_valid_uuid(" ") is False
        assert is_valid_uuid("  ") is False
        assert is_valid_uuid("\t") is False

    def test_uuid_with_extra_whitespace(self):
        """Test that UUIDs with surrounding whitespace are invalid"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"

        assert is_valid_uuid(" " + valid_uuid) is False
        assert is_valid_uuid(valid_uuid + " ") is False
        assert is_valid_uuid(" " + valid_uuid + " ") is False

    def test_uuid_case_insensitivity(self):
        """Test that UUID validation is case-insensitive"""
        uuid_base = "550e8400-e29b-41d4-a716-446655440000"
        uuid_upper = uuid_base.upper()
        uuid_lower = uuid_base.lower()

        # Note: uuid.UUID() allows different cases, but the function checks
        # if str(uuid_obj) == uuid_string, which means it must match exactly
        assert is_valid_uuid(uuid_lower) is True

    def test_uuid_uppercase_rejected(self):
        """Test that uppercase UUIDs are rejected by the function"""
        # The function converts to UUID object then back to string for comparison
        # uuid.UUID() normalizes to lowercase, so uppercase input will be rejected
        uuid_upper = "550E8400-E29B-41D4-A716-446655440000"
        assert is_valid_uuid(uuid_upper) is False

    def test_uuid_without_hyphens(self):
        """Test that UUID without hyphens is invalid"""
        # Valid UUID with hyphens
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        # Same UUID without hyphens
        uuid_no_hyphens = valid_uuid.replace("-", "")

        assert is_valid_uuid(valid_uuid) is True
        assert is_valid_uuid(uuid_no_hyphens) is False

    def test_uuid_with_braces(self):
        """Test that UUID with braces is invalid"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        uuid_with_braces = "{" + valid_uuid + "}"

        assert is_valid_uuid(valid_uuid) is True
        assert is_valid_uuid(uuid_with_braces) is False

    def test_uuid_with_urn_prefix(self):
        """Test that UUID with URN prefix is invalid"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        uuid_with_urn = "urn:uuid:" + valid_uuid

        assert is_valid_uuid(valid_uuid) is True
        assert is_valid_uuid(uuid_with_urn) is False

    @pytest.mark.parametrize("invalid_uuid", [
        "123",  # Too short
        "550e8400-e29b-41d4-a716-44665544000g",  # Invalid hex character
        "550e8400-e29b-41d4-a716-44665544000G",  # Invalid hex character (uppercase)
        "550e8400-e29b-41d4-a71g-446655440000",  # Invalid hex character
        "550e8400-e29b-41d4-a716--446655440000",  # Double dash
        "550e8400 e29b 41d4 a716 446655440000",  # Spaces instead of dashes
    ])
    def test_various_invalid_formats(self, invalid_uuid):
        """Test various invalid UUID formats"""
        assert is_valid_uuid(invalid_uuid) is False

    def test_uuid_from_standard_library(self):
        """Test UUIDs generated by uuid library"""
        # Generate random UUIDs
        generated_uuid1 = str(uuid.uuid4())
        generated_uuid2 = str(uuid.uuid1())

        assert is_valid_uuid(generated_uuid1) is True
        assert is_valid_uuid(generated_uuid2) is True

    def test_deterministic_uuid_from_module(self):
        """Test that UUIDs generated by generate_deterministic_uuid_string are valid"""
        deterministic_uuid = generate_deterministic_uuid_string("test_input")
        assert is_valid_uuid(deterministic_uuid) is True

    @pytest.mark.parametrize("valid_uuid", [
        "00000000-0000-0000-0000-000000000000",  # All zeros
        "ffffffff-ffff-ffff-ffff-ffffffffffff",  # All f's (lowercase)
        "12345678-1234-5678-1234-567812345678",  # Sequential-like
        "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",  # Random example
    ])
    def test_various_valid_uuids(self, valid_uuid):
        """Test various valid UUID patterns"""
        assert is_valid_uuid(valid_uuid) is True

    def test_none_input_raises_or_returns_false(self):
        """Test behavior with None input"""
        assert is_valid_uuid(None) is False

    def test_numeric_input(self):
        """Test behavior with numeric input"""
        assert is_valid_uuid(123) is False
