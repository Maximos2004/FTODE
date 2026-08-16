import os
from PIL import Image, ImageDraw

def create_icon(size):
    # Create image with transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    s = size / 128.0
    
    # Background rounded rectangle or circle with gradient-like look
    # Main outer glowing circle / squircle
    margin = int(4 * s)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=int(28 * s),
        fill=(15, 17, 23, 255),
        outline=(99, 102, 241, 230),
        width=max(1, int(3 * s))
    )
    
    # Inner accent glow / decorative ring
    inner_m = int(12 * s)
    draw.rounded_rectangle(
        [inner_m, inner_m, size - inner_m, size - inner_m],
        radius=int(20 * s),
        fill=(26, 29, 39, 255),
        outline=(16, 185, 129, 180),
        width=max(1, int(1.5 * s))
    )
    
    # Draw download arrow and media disc/waveform symbol
    center_x = size / 2.0
    
    # Downward arrow
    arrow_w = 28 * s
    arrow_h = 24 * s
    arrow_top = 34 * s
    stem_w = 12 * s
    
    # Arrow stem
    draw.rounded_rectangle(
        [center_x - stem_w/2, arrow_top, center_x + stem_w/2, arrow_top + arrow_h],
        radius=int(3 * s),
        fill=(99, 102, 241, 255)
    )
    
    # Arrow head (triangle)
    head_top = arrow_top + arrow_h - 4 * s
    head_bot = head_top + 22 * s
    draw.polygon(
        [
            (center_x, head_bot),
            (center_x - arrow_w, head_top),
            (center_x + arrow_w, head_top)
        ],
        fill=(16, 185, 129, 255)
    )
    
    # Bottom tray bar
    bar_y = int(88 * s)
    bar_w = int(36 * s)
    bar_h = max(2, int(6 * s))
    draw.rounded_rectangle(
        [center_x - bar_w, bar_y, center_x + bar_w, bar_y + bar_h],
        radius=int(3 * s),
        fill=(6, 182, 212, 255)
    )
    
    return img

def main():
    icons_dir = os.path.join(os.path.dirname(__file__), "extension", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    sizes = [16, 32, 48, 128]
    for sz in sizes:
        img = create_icon(sz)
        out_path = os.path.join(icons_dir, f"icon{sz}.png")
        img.save(out_path, "PNG")
        print(f"Generated {out_path} ({sz}x{sz})")

if __name__ == "__main__":
    main()
