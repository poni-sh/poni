"""Documentation generation for Poni."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from poni.config.loader import get_poni_dir, get_project_root
from poni.config.models import Config, DocsTarget
from poni.docs.lock import DocsLock


@dataclass
class GenerationResult:
    """Result of generating documentation."""

    target: str
    output_path: str
    success: bool
    skipped: bool = False
    error: str | None = None


class DocsGenerator:
    """Generator for project documentation."""

    def __init__(self, config: Config):
        """Initialize the docs generator.

        Args:
            config: The Poni configuration.
        """
        self.config = config
        self.docs_config = config.docs
        self.lock = DocsLock()

    async def generate_all(self, force: bool = False) -> list[GenerationResult]:
        """Generate all documentation targets.

        Args:
            force: Force regeneration even if sources haven't changed.

        Returns:
            List of generation results.
        """
        if not self.docs_config.enabled:
            return []

        results: list[GenerationResult] = []

        for target in self.docs_config.targets:
            result = await self.generate_target(target, force)
            results.append(result)

        return results

    async def generate_target(
        self,
        target: DocsTarget,
        force: bool = False,
    ) -> GenerationResult:
        """Generate a single documentation target.

        Args:
            target: The target to generate.
            force: Force regeneration even if sources haven't changed.

        Returns:
            Generation result.
        """
        try:
            project_root = get_project_root()
        except FileNotFoundError:
            project_root = Path.cwd()

        # Check if regeneration is needed
        if not force and not self.lock.needs_regeneration(target, project_root):
            return GenerationResult(
                target=target.name,
                output_path=target.output,
                success=True,
                skipped=True,
            )

        try:
            # Gather source files
            source_content = self._gather_sources(target, project_root)

            # Get prompt
            prompt = self._get_prompt(target, project_root)

            # Generate documentation
            # For now, create a placeholder - in production, this would call an LLM
            doc_content = self._generate_placeholder(target, source_content, prompt)

            # Write output
            output_path = self._write_output(target, doc_content, project_root)

            # Update lock
            self.lock.update(target, str(output_path), project_root)

            return GenerationResult(
                target=target.name,
                output_path=str(output_path),
                success=True,
            )

        except Exception as e:
            return GenerationResult(
                target=target.name,
                output_path=target.output,
                success=False,
                error=str(e),
            )

    def _gather_sources(self, target: DocsTarget, base_dir: Path) -> str:
        """Gather content from source files.

        Args:
            target: The docs target.
            base_dir: Base directory for source files.

        Returns:
            Combined source content.
        """
        sources: list[str] = []

        for pattern in target.paths:
            for file_path in base_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        content = file_path.read_text()
                        rel_path = file_path.relative_to(base_dir)
                        sources.append(f"## {rel_path}\n\n```\n{content}\n```\n")
                    except (OSError, UnicodeDecodeError):
                        pass

        return "\n".join(sources)

    def _get_prompt(self, target: DocsTarget, base_dir: Path) -> str:
        """Get the generation prompt for a target.

        Args:
            target: The docs target.
            base_dir: Base directory for prompt files.

        Returns:
            The prompt string.
        """
        if target.prompt:
            return target.prompt

        if target.prompt_file:
            prompt_path = base_dir / target.prompt_file
            if prompt_path.exists():
                return prompt_path.read_text()

            # Check in .poni/prompts
            poni_prompt = get_poni_dir() / "prompts" / target.prompt_file
            if poni_prompt.exists():
                return poni_prompt.read_text()

        # Default prompt
        return f"Generate documentation for {target.name}. {target.description}"

    def _generate_placeholder(
        self,
        target: DocsTarget,
        sources: str,
        prompt: str,
    ) -> str:
        """Generate placeholder documentation.

        In production, this would call an LLM API.

        Args:
            target: The docs target.
            sources: The gathered source content.
            prompt: The generation prompt.

        Returns:
            Generated documentation content.
        """
        return f"""# {target.name}

{target.description}

---

*This documentation was generated by Poni.*

*To generate actual docs, configure an LLM provider or use the Poni MCP server with Claude.*

## Source Files

The following files were included in this documentation:

{sources[:1000]}...

---

*Prompt used:*

{prompt}
"""

    def _write_output(
        self,
        target: DocsTarget,
        content: str,
        base_dir: Path,
    ) -> Path:
        """Write generated documentation to file.

        Args:
            target: The docs target.
            content: The generated content.
            base_dir: Base directory for output.

        Returns:
            Path to the written file.
        """
        output_path = base_dir / self.docs_config.output_dir / target.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        return output_path
