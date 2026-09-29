from pathlib import Path
import re
import pytest

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def test_styles_css_exists_and_contains_design_tokens():
    css_path = DOCS_DIR / "styles.css"
    assert css_path.exists(), "docs/styles.css must exist"
    
    content = css_path.read_text(encoding="utf-8")
    
    # Verify light theme core tokens
    assert ":root" in content
    assert "--bg-canvas" in content
    assert "--text-primary" in content
    assert "--accent-primary" in content
    assert "--glass-bg" in content
    assert "--glass-border" in content
    assert "--glass-shadow" in content
    
    # Verify craft classes
    assert ".glass-card" in content
    assert ".btn-primary" in content
    assert ".hero-title" in content
    assert ".bento-grid" in content
    
    # Verify responsive and accessibility rules
    assert "@media" in content
    assert "prefers-reduced-motion" in content
