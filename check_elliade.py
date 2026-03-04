import requests
import json
import os
from datetime import datetime

SEEN_FILE = "seen_products.json"
OUTPUT_HTML = "docs/index.html"
SIZES_WANTED = {"50", "50.5", "51", "51.5", "52"}
SIZES_DISPLAY = {"50": "50", "50.5": "50½", "51": "51", "51.5": "51½", "52": "52"}

def load_sites():
    with open("sites.json") as f:
        return json.load(f)

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(message):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    })

def fetch_artdeco_rings():
    urls = [
        "https://www.elliade.com/collections/style-bague-art-deco/products.json?limit=250",
        "https://www.elliade.com/collections/art-deco/products.json?limit=250",
    ]
    all_products = {}
    for url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            for p in resp.json().get("products", []):
                all_products[p["id"]] = p  # dédoublonnage par ID
        except Exception as e:
            print(f"Erreur fetch : {e}")
    return list(all_products.values())


def get_available_sizes(product):
    import re
    # Cherche la taille dans le body_html (ex: "taille 52" ou "taille 51,5")
    body = product.get("body_html", "")
    matches = re.findall(r'taille\s+([\d]+(?:[,\.]\d)?)', body, re.IGNORECASE)
    
    matched = []
    for m in matches:
        size = m.replace(",", ".")
        if size in SIZES_WANTED:
            # Vérifie si le produit est disponible
            available = any(v.get("available", False) for v in product.get("variants", []))
            if available:
                matched.append(size)
    return matched

def get_min_price(product):
    prices = [float(v["price"]) for v in product.get("variants", []) if v.get("price")]
    return min(prices) if prices else 9999

def check_new_rings(products, seen):
    new_items = []
    for product in products:
        sizes = get_available_sizes(product)
        for size in sizes:
            key = f"elliade_{product['id']}_{size}"
            if key not in seen:
                seen.add(key)
                new_items.append({
                    "product": product["title"],
                    "size": size,
                    "price": get_min_price(product),
                    "url": f"https://www.elliade.com/products/{product['handle']}"
                })
    return new_items

def generate_html(products):
    os.makedirs("docs", exist_ok=True)
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    rings = []
    for p in products:
        sizes = get_available_sizes(p)
        if not sizes:
            continue
        rings.append({
            "title": p["title"],
            "handle": p["handle"],
            "price": get_min_price(p),
            "sizes": sizes,
            "image": p.get("images", [{}])[0].get("src", "")
        })
    rings.sort(key=lambda x: x["price"])

    cards_html = ""
    for i, r in enumerate(rings):
        size_tags = "".join(
            f'<span class="size-tag">{SIZES_DISPLAY.get(s, s)}</span>'
            for s in r["sizes"]
        )
        img_tag = f'<img src="{r["image"]}" alt="{r["title"]}" loading="lazy">' if r["image"] else ""
        price_str = f"{r['price']:,.0f} €".replace(",", " ")
        cards_html += f"""
        <div class="card" style="animation-delay:{i*0.05}s">
          <div class="card-img-wrap">
            {img_tag}
            <div class="card-badge">Art Déco</div>
          </div>
          <div class="card-body">
            <div class="card-title">{r['title']}</div>
            <div class="card-price">{price_str}</div>
            <div class="sizes-label">Tailles disponibles</div>
            <div class="sizes-wrap">{size_tags}</div>
            <a href="https://www.elliade.com/products/{r['handle']}" target="_blank" class="card-link">Voir le bijou →</a>
          </div>
        </div>"""

    if not cards_html:
        cards_html = """
        <div class="empty-state">
          <div class="icon">💍</div>
          <div class="empty-title">Aucune bague disponible</div>
          <p>Aucune bague Art Déco disponible dans vos tailles pour le moment.</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Elliade — Bagues Art Déco</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Cormorant+Garamond:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --gold: #b8973a; --gold-light: #d4b45a; --gold-pale: #f0e6c0;
    --dark: #1a1612; --dark-2: #2a2218; --cream: #faf6ee;
    --text: #3a2e1e; --text-light: #7a6a4e; --border: #e0d0a0;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--cream); color: var(--text); font-family: 'Cormorant Garamond', serif; min-height: 100vh; }}
  header {{ background: var(--dark); padding: 2.5rem 2rem 2rem; text-align: center; position: relative; overflow: hidden; }}
  header::before {{ content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(45deg, transparent, transparent 20px, rgba(184,151,58,0.04) 20px, rgba(184,151,58,0.04) 21px); }}
  .header-ornament {{ color: var(--gold); font-size: 0.75rem; letter-spacing: 0.4em; text-transform: uppercase; margin-bottom: 0.75rem; opacity: 0.8; }}
  header h1 {{ font-family: 'Playfair Display', serif; color: var(--gold-light); font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 400; }}
  header h1 em {{ font-style: italic; color: #fff; }}
  .header-sub {{ color: rgba(240,230,192,0.6); font-size: 0.95rem; letter-spacing: 0.15em; margin-top: 0.5rem; }}
  .update-time {{ color: rgba(184,151,58,0.5); font-size: 0.75rem; letter-spacing: 0.1em; margin-top: 0.75rem; }}
  .deco-line {{ display: flex; align-items: center; justify-content: center; gap: 1rem; margin: 1rem auto 0; width: fit-content; }}
  .deco-line::before {{ content: ''; width: 60px; height: 1px; background: linear-gradient(to right, transparent, var(--gold)); }}
  .deco-line::after {{ content: ''; width: 60px; height: 1px; background: linear-gradient(to left, transparent, var(--gold)); }}
  .deco-diamond {{ width: 6px; height: 6px; background: var(--gold); transform: rotate(45deg); }}
  .results-count {{ font-family: 'Playfair Display', serif; font-size: 0.9rem; color: var(--text-light); text-align: center; padding: 1rem; letter-spacing: 0.1em; border-bottom: 1px solid var(--border); }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; padding: 2rem; max-width: 1400px; margin: 0 auto; }}
  .card {{ background: #fff; border: 1px solid var(--border); overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; animation: fadeIn 0.5s ease both; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 40px rgba(26,22,18,0.15); }}
  .card-img-wrap {{ position: relative; aspect-ratio: 1; overflow: hidden; background: #f5f0e8; }}
  .card-img-wrap img {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s; }}
  .card:hover .card-img-wrap img {{ transform: scale(1.05); }}
  .card-badge {{ position: absolute; top: 0.75rem; left: 0.75rem; background: var(--dark); color: var(--gold-light); font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; padding: 0.25rem 0.6rem; }}
  .card-body {{ padding: 1.25rem; border-top: 1px solid var(--border); }}
  .card-title {{ font-family: 'Playfair Display', serif; font-size: 1rem; font-weight: 400; line-height: 1.4; margin-bottom: 0.75rem; }}
  .card-price {{ font-size: 1.2rem; font-weight: 500; color: var(--gold); margin-bottom: 0.75rem; }}
  .sizes-label {{ font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; color: var(--text-light); margin-bottom: 0.4rem; }}
  .sizes-wrap {{ display: flex; gap: 0.35rem; flex-wrap: wrap; }}
  .size-tag {{ background: var(--gold-pale); border: 1px solid var(--gold); color: var(--text); font-size: 0.75rem; padding: 0.15rem 0.5rem; }}
  .card-link {{ display: block; margin-top: 1rem; text-align: center; background: var(--dark); color: var(--gold-light); text-decoration: none; font-size: 0.7rem; letter-spacing: 0.3em; text-transform: uppercase; padding: 0.6rem; transition: background 0.2s; }}
  .card-link:hover {{ background: var(--gold); color: var(--dark); }}
  .empty-state {{ text-align: center; padding: 5rem 2rem; color: var(--text-light); grid-column: 1 / -1; }}
  .empty-state .icon {{ font-size: 3rem; margin-bottom: 1rem; opacity: 0.3; }}
  .empty-title {{ font-family: 'Playfair Display', serif; font-size: 1.4rem; margin-bottom: 0.5rem; color: var(--text); }}
  footer {{ text-align: center; padding: 2rem; color: var(--text-light); font-size: 0.8rem; letter-spacing: 0.1em; border-top: 1px solid var(--border); margin-top: 2rem; }}
</style>
</head>
<body>
<header>
  <div class="header-ornament">✦ Elliade Paris ✦</div>
  <h1>Bagues <em>Art Déco</em></h1>
  <div class="header-sub">Tailles 50 · 50½ · 51 · 51½ · 52</div>
  <div class="update-time">Dernière mise à jour : {now}</div>
  <div class="deco-line"><div class="deco-diamond"></div></div>
</header>
<div class="results-count">{len(rings)} bague{"s" if len(rings) > 1 else ""} trouvée{"s" if len(rings) > 1 else ""}</div>
<div class="grid">{cards_html}</div>
<footer>Données en direct depuis elliade.com · Mise à jour toutes les heures</footer>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Page HTML générée : {len(rings)} bagues")

def main():
    sites = load_sites()
    seen = load_seen()

    # 1. Vérifier les nouveautés sur tous les sites et envoyer alertes
    all_new = []
    for site in sites:
        url = site["url"]
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            products = resp.json().get("products", [])
        except:
            products = []
        new_items = check_new_rings(products, seen)
        all_new.extend(new_items)

    save_seen(seen)

    if all_new:
        for item in all_new:
            message = (
                f"🔔 <b>Nouveau bijou disponible !</b>\n\n"
                f"💍 {item['product']}\n"
                f"📏 Taille : {SIZES_DISPLAY.get(item['size'], item['size'])}\n"
                f"💶 Prix : {item['price']:.0f} €\n"
                f"👉 <a href=\"{item['url']}\">Voir le bijou</a>"
            )
            send_telegram(message)
        print(f"{len(all_new)} alerte(s) envoyée(s)")

    # 2. Générer la page HTML Art Déco
    artdeco_products = fetch_artdeco_rings()
    generate_html(artdeco_products)

if __name__ == "__main__":
    main()
