"""Language and framework presets for Poni."""

from typing import Any

from poni.config.detection import DetectedProject


def get_preset(preset_name: str) -> dict[str, Any]:
    """Get a preset configuration by name."""
    if preset_name == "typescript":
        from poni.presets.typescript import generate_config

        return generate_config(DetectedProject(languages=["typescript"]))
    elif preset_name == "python":
        from poni.presets.python import generate_config

        return generate_config(DetectedProject(languages=["python"]))
    elif preset_name == "rust":
        from poni.presets.rust import generate_config

        return generate_config(DetectedProject(languages=["rust"]))
    elif preset_name == "go":
        from poni.presets.go import generate_config

        return generate_config(DetectedProject(languages=["go"]))
    else:
        raise ValueError(f"Unknown preset: {preset_name}")


__all__ = ["get_preset"]
