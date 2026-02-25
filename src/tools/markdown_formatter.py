import re
import mdformat
from crewai.tools import BaseTool
from core.audit import audit_tool_call


class MarkdownFormatterTool(BaseTool):
    name: str = "MarkdownFormatterTool"
    description: str = "Formats and cleans markdown content using mdformat with proper structure, headers, sections, and tables."

    @audit_tool_call(tool_name="MarkdownFormatterTool")
    def _run(self, content: str, style: str = "report") -> str:
        """
        Format and clean markdown content using mdformat.

        Args:
            content: The markdown content to format
            style: Format style - "report" (default), "compact", "detailed", or "mdformat"

        Returns:
            Properly formatted markdown string
        """
        if not content or not isinstance(content, str):
            return "# Error: Invalid Content\n\nNo content provided."

        # Step 1: Clean up the input
        cleaned = self._clean_markdown(content)
        formatted = self._format_with_mdformat(cleaned)
        formatted = self._normalize_spacing(formatted)
        formatted = self._validate_structure(formatted)

        return formatted

    @staticmethod
    def _format_with_mdformat(content: str) -> str:
        """
        Format markdown using mdformat library.

        Uses mdformat with GitHub Flavored Markdown support for:
        - Consistent formatting
        - Proper spacing and indentation
        - Code block and table handling
        - Link and reference formatting
        """

        try:
            # Format with mdformat using GitHub Flavored Markdown
            formatted = mdformat.text(
                content,
                options={
                    "number": False,  # Don't auto-number lists
                    "wrap": 100,  # Wrap at 100 chars
                },
            )
            return formatted
        except Exception:
            # Fall back to basic formatting if mdformat fails
            return content

    @staticmethod
    def _clean_markdown(content: str) -> str:
        """
        Clean up raw markdown content.

        - Remove excessive whitespace
        - Fix improper headers
        - Remove duplicate blank lines
        - Fix common markdown issues
        """
        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove excessive blank lines (more than 2 consecutive)
        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Fix improper headers (must start at line beginning)
        content = re.sub(r"^[ \t]+#", "#", content, flags=re.MULTILINE)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in content.split("\n")]
        content = "\n".join(lines)

        return content

    @staticmethod
    def _normalize_spacing(content: str) -> str:
        """
        Normalize spacing in markdown.
        """
        lines = content.split("\n")
        normalized = []

        for i, line in enumerate(lines):
            # Add blank line before headers (except first line)
            if line.startswith("#") and i > 0 and normalized and normalized[-1].strip():
                normalized.append("")

            normalized.append(line)

        return "\n".join(normalized)

    @staticmethod
    def _validate_structure(content: str) -> str:
        """Validate markdown structure."""
        lines = content.split("\n")

        # Ensure first non-empty line is a header
        for i, line in enumerate(lines):
            if line.strip():
                if not line.startswith("#"):
                    lines.insert(i, "# Report")
                    lines.insert(i + 1, "")
                break

        return "\n".join(lines)
