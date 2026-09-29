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


def test_app_js_exists_and_implements_interactive_features():
    app_js_path = DOCS_DIR / "app.js"
    assert app_js_path.exists(), "docs/app.js must exist"
    
    content = app_js_path.read_text(encoding="utf-8")
    
    # Waveform canvas rendering
    assert "getContext" in content
    assert "requestAnimationFrame" in content
    
    # State handling & audio simulation
    assert "recording" in content
    assert "processing" in content
    assert "statusBadge" in content
    
    # Event listeners
    assert "pointerdown" in content or "mousedown" in content
    assert "pointerup" in content or "mouseup" in content
    assert "keydown" in content
    
    # Real speech recognition & space-preserving text node typing
    assert "SpeechRecognition" in content
    assert "createTextNode" in content
    assert "appendData" in content
    
    # Accessibility and reduced motion
    assert "prefers-reduced-motion" in content


def test_accessibility_and_responsive_audit():
    css_content = (DOCS_DIR / "styles.css").read_text(encoding="utf-8")
    html_content = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    
    # Whitespace preservation in editor
    assert "pre-wrap" in css_content
    
    # Responsive breakpoints
    assert "@media (max-width: 768px)" in css_content
    assert "@media (max-width: 480px)" in css_content
    assert "@media (max-width: 992px)" in css_content
    
    # Touch target accessibility
    assert "44px" in css_content
    assert "min-height" in css_content
    
    # WCAG high contrast text tokens
    assert "#0f172a" in css_content  # primary text Slate-900
    assert "#334155" in css_content  # secondary text Slate-700
    
    # Screen reader utility
    assert ".sr-only" in css_content
    assert 'class="sr-only"' in html_content
    
    # Meta viewport tag
    assert 'name="viewport"' in html_content
    assert "width=device-width" in html_content


def test_github_pages_workflow_and_readme_sync():
    root_dir = DOCS_DIR.parent
    workflow_path = root_dir / ".github" / "workflows" / "deploy-pages.yml"
    readme_path = root_dir / "README.md"
    
    assert workflow_path.exists(), ".github/workflows/deploy-pages.yml must exist"
    workflow_content = workflow_path.read_text(encoding="utf-8")
    assert "actions/deploy-pages" in workflow_content
    assert "docs" in workflow_content
    assert "main" in workflow_content
    
    assert readme_path.exists(), "README.md must exist"
    readme_content = readme_path.read_text(encoding="utf-8")
    assert "https://davidcaroo.github.io/Talk-me/" in readme_content


def test_direct_installer_download_and_author_attribution():
    html_content = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    
    # Direct installer link
    assert "releases/download/V1.0.0/VoiceDictation-Setup-1.0.0.exe" in html_content
    assert 'download="VoiceDictation-Setup-1.0.0.exe"' in html_content
    
    # LinkedIn author link
    assert "@Ing.davidcaro" in html_content
    assert "https://www.linkedin.com/in/ingdavid-caro/" in html_content


def test_mit_license_file_and_readme_section():
    root_dir = DOCS_DIR.parent
    license_path = root_dir / "LICENSE"
    readme_path = root_dir / "README.md"
    
    assert license_path.exists(), "LICENSE file must exist in root"
    license_content = license_path.read_text(encoding="utf-8")
    assert "MIT License" in license_content
    assert "David Caro" in license_content
    assert "@Ing.davidcaro" in license_content
    
    readme_content = readme_path.read_text(encoding="utf-8")
    assert "## 📄 Licencia" in readme_content
    assert "Licencia MIT" in readme_content
    assert "https://www.linkedin.com/in/ingdavid-caro/" in readme_content






