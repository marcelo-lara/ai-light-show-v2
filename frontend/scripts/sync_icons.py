import os
import xml.etree.ElementTree as ET

# Configuration
ICON_DIR = "src/shared/svg_icons"
OUTPUT_FILE = os.path.join(ICON_DIR, "index.ts")

def get_paths(svg_path):
    """Extract path 'd' attributes and their colors from an SVG file."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Simple namespace-agnostic approach for findall
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Try with namespace first, then without
        paths = root.findall('.//svg:path', ns)
        if not paths:
            paths = root.findall('.//path')
            
        result = []
        for path in paths:
            d = path.get('d')
            if not d:
                continue
            
            # Identify "accent" paths. In the source SVGs, accent paths 
            # often use specific classes (e.g., .st1) or colors.
            # We'll tag them so the frontend can apply CSS variables.
            cls = path.get('class', '')
            is_accent = 'st1' in cls or 'accent' in cls.lower()
            
            result.append({
                'd': d,
                'isAccent': is_accent
            })
        return result
    except Exception as e:
        print(f"Error parsing {svg_path}: {e}")
        return []

def main():
    icons = {}
    
    # Ensure directory exists
    if not os.path.isdir(ICON_DIR):
        print(f"Directory not found: {ICON_DIR}")
        return

    # Scan and parse SVG files
    filenames = sorted([f for f in sorted(os.listdir(ICON_DIR)) if f.endswith(".svg")])
    for f in filenames:
        name = f.replace(".svg", "")
        extracted = get_paths(os.path.join(ICON_DIR, f))
        if extracted:
            icons[name] = extracted

    if not icons:
        print("No valid SVG icons found.")
        return

    # Generate the TypeScript content
    icon_names = sorted(icons.keys())
    ts_content = "/**\n * Auto-generated icon registry. Do not edit manually.\n * Run 'npm run sync-icons' to update.\n */\n\n"
    ts_content += "export interface IconPath {\n\td: string;\n\tisAccent?: boolean;\n}\n\n"
    ts_content += 'export type IconName = "' + '" | "'.join(icon_names) + '";\n\n'
    ts_content += "export const ICON_REGISTRY: Record<IconName, IconPath[]> = {\n"
    
    for name in icon_names:
        paths = icons[name]
        ts_content += f'\t{name}: [\n'
        for p in paths:
            accent_str = ", isAccent: true" if p['isAccent'] else ""
            ts_content += f'\t\t{{ d: "{p["d"]}"{accent_str} }},\n'
        ts_content += f'\t],\n'
        
    ts_content += "};\n"

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        f.write(ts_content)
    
    print(f"Successfully synced {len(icons)} icons to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
