"""Generate the original, deterministic SuperSports SVG brand and product art."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "apps/storefront/public"
PRODUCTS = {
    "cricket-bat.svg": ("CRICKET", "PRO WILLOW BAT", "#e6b45d", '<path d="M190 90h44v375q0 18-22 35-22-17-22-35z" fill="#c78c4a"/><path d="M201 95h22v355h-22z" fill="#f1ca82"/><rect x="197" y="58" width="30" height="48" rx="8" fill="#263d35"/><path d="M198 68h28M198 80h28M198 92h28" stroke="#f4e7c7" stroke-width="3"/>'),
    "cricket-ball.svg": ("CRICKET", "MATCH LEATHER BALL", "#e45d52", '<circle cx="212" cy="250" r="114" fill="#cf3f40"/><circle cx="212" cy="250" r="101" fill="none" stroke="#f2d0a3" stroke-width="7"/><path d="M137 162q75 88 150 176M287 162q-75 88-150 176" fill="none" stroke="#f8ebd8" stroke-width="5" stroke-dasharray="9 9"/>'),
    "cricket-gloves.svg": ("CRICKET", "PRO BATTING GLOVES", "#74a998", '<path d="M125 315V176q0-18 17-18t17 18v-54q0-18 17-18t17 18v48-71q0-18 18-18t18 18v71-56q0-18 18-18t18 18v95q15-25 30-17 15 8 4 30l-46 91q-17 31-57 27l-40-5q-39-5-51-40z" fill="#f1d4a2" stroke="#263d35" stroke-width="9"/><path d="M147 267h125M157 290h105" stroke="#e36b4c" stroke-width="10"/>'),
    "football.svg": ("FOOTBALL", "CONTROL MATCH BALL", "#5b86d7", '<circle cx="212" cy="250" r="125" fill="#f8f6ec" stroke="#263d35" stroke-width="8"/><path d="m212 178 52 38-20 61h-64l-20-61z" fill="#315b9d"/><path d="m212 178 14-50m38 88 56-12m-76 73 20 58m-84-58-20 58m-24-119-56-12" fill="none" stroke="#263d35" stroke-width="8"/><path d="m212 178-52 38m104 0-52-38m-32 99-38 42m102-42 38 42" stroke="#315b9d" stroke-width="7"/>'),
    "football-cones.svg": ("FOOTBALL", "PITCH TRAINING SET", "#f08b49", '<g fill="#ed713e" stroke="#263d35" stroke-width="7"><path d="m96 340 30-125 31 125z"/><path d="m172 340 30-155 31 155z"/><path d="m252 340 30-125 31 125z"/></g><path d="M79 350h226" stroke="#263d35" stroke-width="13" stroke-linecap="round"/><path d="m119 255 15-2m57-25 14-2m58 27 15-2" stroke="#ffd8a8" stroke-width="8"/>'),
    "goalkeeper-gloves.svg": ("FOOTBALL", "GRIP GOALKEEPER GLOVES", "#6aa397", '<path d="M126 318V177q0-18 17-18t17 18v-54q0-18 17-18t17 18v48-72q0-18 18-18t18 18v72-57q0-18 18-18t18 18v96q15-25 30-17 15 8 4 30l-46 91q-17 31-57 27l-40-5q-39-5-51-40z" fill="#e9f0dc" stroke="#263d35" stroke-width="9"/><path d="M148 266h125M158 290h105" stroke="#76a990" stroke-width="11"/><path d="M140 173v78m36-119v120m36-144v145m36-130v124" stroke="#ed713e" stroke-width="5"/>')
}

def main():
    (PUBLIC / "products").mkdir(parents=True, exist_ok=True)
    (PUBLIC / "supersports-mark.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 76" role="img" aria-label="SuperSports"><rect width="76" height="76" rx="22" fill="#ed713e"/><path d="M20 47c13-1 19-15 31-18 8-2 13 2 20 9-13 0-19 15-31 18-8 2-13-2-20-9Z" fill="#fff8e9"/><path d="M24 27h30" stroke="#fff8e9" stroke-width="5" stroke-linecap="round"/><text x="94" y="51" font-family="Arial,sans-serif" font-size="38" font-weight="800" letter-spacing="-1" fill="#263d35">SUPERSPORTS</text></svg>''')
    for filename, (category, title, accent, illustration) in PRODUCTS.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 480" role="img" aria-label="{title.title()}"><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#fbf3e1"/><stop offset="1" stop-color="#e8eddf"/></linearGradient><filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#263d35" flood-opacity=".14"/></filter></defs><rect width="420" height="480" rx="36" fill="url(#bg)"/><circle cx="324" cy="102" r="72" fill="{accent}" opacity=".13"/><path d="M0 388q125-67 237-8t183-5v105H0z" fill="#dbe3d2"/><g filter="url(#shadow)">{illustration}</g><text x="34" y=" fifty" font-family="Arial,sans-serif" font-size="15" font-weight="700" letter-spacing="3" fill="#65766a">{category}</text><text x="34" y="430" font-family="Arial,sans-serif" font-size="18" font-weight="800" letter-spacing="1" fill="#263d35">{title}</text></svg>'''.replace('y=" fifty"','y="50"')
        (PUBLIC / "products" / filename).write_text(svg)


if __name__ == "__main__":
    main()
