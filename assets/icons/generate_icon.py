"""Generates modern visionOS-styled icons (ICO and PNG) for Voice Dictation.

Produces:
- app_icon.png (256x256)
- app_icon.ico (layers: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def create_visionos_mic_icon(size: int = 1024) -> Image.Image:
    """Renders a high-resolution visionOS aesthetic microphone icon on a dark translucent plate."""
    # Master image with RGBA
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark frosted squircle background
    margin = int(size * 0.06)
    bg_rect = [margin, margin, size - margin, size - margin]
    radius = int(size * 0.22)

    # Base dark gradient plate
    bg_plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    plate_draw = ImageDraw.Draw(bg_plate)
    plate_draw.rounded_rectangle(bg_rect, radius=radius, fill=(15, 23, 42, 240))  # Deep slate #0f172a

    # Soft glowing radial aura / subtle gradient overlay
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = size // 2, size // 2
    glow_radius = int(size * 0.42)
    for r in range(glow_radius, 0, -6):
        alpha = int(28 * (1.0 - r / glow_radius))
        glow_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(0, 210, 255, alpha)
        )
    glow = glow.filter(ImageFilter.GaussianBlur(12))

    # Mask glow to squircle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(bg_rect, radius=radius, fill=255)
    
    img.paste(bg_plate, (0, 0), mask)
    img.paste(glow, (0, 0), mask)

    # Subtle inner border / rim light (visionOS frosted edge)
    border_draw = ImageDraw.Draw(img)
    border_draw.rounded_rectangle(bg_rect, radius=radius, outline=(255, 255, 255, 45), width=max(2, size // 128))

    # 2. Draw Microphone Icon
    # Colors: Electric cyan (0, 229, 255) to Azure blue (0, 102, 255)
    c_cyan = (0, 230, 255, 255)
    c_blue = (20, 120, 255, 255)
    
    mic_w = int(size * 0.16)
    mic_h = int(size * 0.32)
    mic_cx = cx
    mic_top = int(size * 0.22)
    mic_bottom = mic_top + mic_h
    mic_left = mic_cx - mic_w // 2
    mic_right = mic_cx + mic_w // 2

    # Mic capsule body
    mic_capsule = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    capsule_draw = ImageDraw.Draw(mic_capsule)
    capsule_draw.rounded_rectangle(
        [mic_left, mic_top, mic_right, mic_bottom],
        radius=mic_w // 2,
        fill=c_cyan,
    )

    # Gradient mask on capsule (top bright cyan, bottom deep azure)
    grad_mask = Image.new("L", (size, size), 0)
    g_draw = ImageDraw.Draw(grad_mask)
    for y in range(mic_top, mic_bottom + 1):
        progress = (y - mic_top) / max(1, mic_bottom - mic_top)
        alpha = int(255 * (1.0 - progress * 0.5))
        g_draw.line([(mic_left, y), (mic_right, y)], fill=alpha)
    
    img.paste(mic_capsule, (0, 0), mic_capsule)

    # Mic acoustic mesh lines / details
    mesh_y = mic_top + int(mic_h * 0.38)
    border_draw.line([(mic_left + 6, mesh_y), (mic_right - 6, mesh_y)], fill=(15, 23, 42, 160), width=max(2, size // 180))

    # 3. U-shaped cradle holder
    cradle_w = int(mic_w * 1.85)
    cradle_h = int(mic_h * 0.72)
    cradle_top = mic_top + int(mic_h * 0.42)
    cradle_box = [mic_cx - cradle_w // 2, cradle_top, mic_cx + cradle_w // 2, cradle_top + cradle_h]
    line_w = max(4, int(size * 0.038))

    border_draw.arc(cradle_box, start=0, end=180, fill=c_cyan, width=line_w)

    # 4. Vertical stem connecting cradle to base
    stem_top = cradle_top + cradle_h // 2 + cradle_h // 2
    stem_bottom = stem_top + int(size * 0.09)
    border_draw.line([(mic_cx, stem_top), (mic_cx, stem_bottom)], fill=c_cyan, width=line_w)

    # 5. Base plate
    base_w = int(size * 0.24)
    base_y = stem_bottom
    border_draw.line([(mic_cx - base_w // 2, base_y), (mic_cx + base_w // 2, base_y)], fill=c_cyan, width=line_w)

    # 6. Soundwave arcs on left and right (visionOS dynamic vibe)
    for offset, alpha, radius_mult in [(0.26, 180, 0.22), (0.33, 100, 0.30)]:
        wave_color = (0, 230, 255, alpha)
        # Left wave
        l_cx = mic_cx - int(size * offset)
        l_cy = mic_top + mic_h // 2
        r_dist = int(size * radius_mult)
        border_draw.arc([l_cx - r_dist, l_cy - r_dist, l_cx + r_dist, l_cy + r_dist], start=305, end=415, fill=wave_color, width=max(2, line_w // 2))
        
        # Right wave
        r_cx = mic_cx + int(size * offset)
        border_draw.arc([r_cx - r_dist, l_cy - r_dist, r_cx + r_dist, l_cy + r_dist], start=125, end=235, fill=wave_color, width=max(2, line_w // 2))

    return img


def generate_all_icons(target_dir: Path | None = None) -> tuple[Path, Path]:
    """Generates app_icon.png and multi-resolution app_icon.ico."""
    if target_dir is None:
        target_dir = Path(__file__).resolve().parent
    target_dir.mkdir(parents=True, exist_ok=True)

    master = create_visionos_mic_icon(size=1024)

    # High-quality PNG (256x256)
    png_256 = master.resize((256, 256), Image.Resampling.LANCZOS)
    png_path = target_dir / "app_icon.png"
    png_256.save(png_path, format="PNG", optimize=True)

    # Multi-resolution ICO (16, 32, 48, 64, 128, 256)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path = target_dir / "app_icon.ico"
    
    # Save multi-size icon
    master.save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
    )

    return ico_path, png_path


if __name__ == "__main__":
    ico, png = generate_all_icons()
    print(f"Generated icons successfully:\n  - {png}\n  - {ico}")
