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


def test_logo_svg_exists_and_valid():
    logo_path = DOCS_DIR / "assets" / "logo.svg"
    assert logo_path.exists(), "docs/assets/logo.svg must exist"
    
    content = logo_path.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "</svg>" in content
    assert "linearGradient" in content
    assert "viewBox" in content


def test_index_html_semantic_structure_and_sections():
    index_path = DOCS_DIR / "index.html"
    assert index_path.exists(), "docs/index.html must exist"
    
    content = index_path.read_text(encoding="utf-8")
    
    # DOCTYPE and language
    assert "<!DOCTYPE html>" in content
    assert '<html lang="es">' in content or '<html lang="es"' in content
    
    # Meta tags
    assert 'name="viewport"' in content
    assert "styles.css" in content
    
    # Semantic tags
    assert "<header" in content
    assert "<main" in content
    assert "<footer" in content
    
    # Section IDs from plan
    assert 'id="hero"' in content
    assert 'id="simulator"' in content
    assert 'id="features"' in content
    assert 'id="comparison"' in content
    assert 'id="faq"' in content
    assert 'id="download"' in content
    
    # Interactive elements
    assert "waveformCanvas" in content
    assert "demoOutput" in content
    assert "micButton" in content
    
    # Download CTA and installer link
    assert "Talk-me" in content
    assert "VoiceDictation-Setup" in content or "releases" in content

