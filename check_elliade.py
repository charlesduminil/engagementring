import requests
import json
import os

SEEN_FILE = "seen_products.json"

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

def check_site(site, seen):
    new_items = []
    sizes_wanted = set(s.replace(",", ".") for s in site["sizes"])

    try:
        resp = requests.get(site["url"], timeout=15)
        resp.raise_for_status()
        products = resp.json().get("products", [])
    except Exception as e:
        print(f"Erreur pour {site['name']}: {e}")
        return new_items

    for product in products:
        for variant in product.get("variants", []):
            variant_title = variant.get("title", "").strip().replace(",", ".")
            for size in sizes_wanted:
                if size == variant_title or size in variant_title:
                    key = f"{site['name']}_{product['id']}_{variant['id']}"
                    if key not in seen:
                        seen.add(key)
                        if variant.get("available", False):
                            new_items.append({
                                "site": site["name"],
                                "product": product["title"],
                                "size": variant["title"],
                                "price": variant["price"],
                                "url": f"{site['base_url']}/products/{product['handle']}"
                            })
    return new_items

def main():
    sites = load_sites()
    seen = load_seen()
    all_new_items = []

    for site in sites:
        items = check_site(site, seen)
        all_new_items.extend(items)
        print(f"{site['name']}: {len(items)} nouveau(x)")

    save_seen(seen)

    if all_new_items:
        for item in all_new_items:
            message = (
                f"🔔 <b>Nouveau bijou disponible !</b>\n\n"
                f"🏪 {item['site']}\n"
                f"💍 {item['product']}\n"
                f"📏 Taille : {item['size']}\n"
                f"💶 Prix : {item['price']} €\n"
                f"👉 <a href=\"{item['url']}\">Voir le bijou</a>"
            )
            send_telegram(message)
        print(f"{len(all_new_items)} notification(s) envoyée(s)")
    else:
        print("Aucune nouveauté.")

if __name__ == "__main__":
    main()
