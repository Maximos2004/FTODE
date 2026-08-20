import os
from PIL import Image

def generate_icons():
    base_dir = os.path.dirname(__file__)
    icons_dir = os.path.join(base_dir, "extension", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    icon_master = os.path.join(icons_dir, "icon.png")
    logo_master = os.path.join(icons_dir, "logo.png")
    
    sizes = [16, 32, 48, 128, 512]
    
    if os.path.exists(icon_master):
        img_icon = Image.open(icon_master).convert("RGBA")
        for sz in sizes:
            out_path = os.path.join(icons_dir, f"icon{sz}.png")
            resized = img_icon.resize((sz, sz), Image.Resampling.LANCZOS)
            resized.save(out_path, "PNG")
            print(f"Generated {out_path} ({sz}x{sz})")
            
    if os.path.exists(logo_master):
        img_logo = Image.open(logo_master).convert("RGBA")
        for sz in sizes:
            out_path = os.path.join(icons_dir, f"logo{sz}.png")
            resized = img_logo.resize((sz, sz), Image.Resampling.LANCZOS)
            resized.save(out_path, "PNG")
            print(f"Generated {out_path} ({sz}x{sz})")

def main():
    generate_icons()

if __name__ == "__main__":
    main()

