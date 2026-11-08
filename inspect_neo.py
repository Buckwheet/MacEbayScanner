import sqlite3
import json

conn = sqlite3.connect('/home/encoder1/MacEbayScanner/data/seen_items.db')
conn.row_factory = sqlite3.Row

# Look for item 188817784292
r1 = conn.execute("SELECT item_id, title, price, matched, filter_reason, raw_json FROM seen_items WHERE item_id LIKE '%188817784292%'").fetchone()
if r1:
    print("Item 188817784292:")
    print("  Title:", r1["title"])
    print("  Price:", r1["price"])
    print("  Matched:", r1["matched"])
    print("  Reason:", r1["filter_reason"])
    if r1["raw_json"]:
        data = json.loads(r1["raw_json"])
        print("  itemGroupType:", data.get("itemGroupType"))
        print("  aspects:", data.get("localizedAspects", []))
else:
    print("Item 188817784292 NOT found in db.")

# Look for Neo
neos = conn.execute("SELECT item_id, title, price, matched, notified, filter_reason, raw_json FROM seen_items WHERE title LIKE '%neo%' OR title LIKE '%Neo%'").fetchall()
print("\nNeos found:", len(neos))
for n in neos:
    print("  Neo:", dict(n))
    if n["raw_json"]:
        ndata = json.loads(n["raw_json"])
        print("  raw itemGroupType:", ndata.get("itemGroupType"))

# Also check recently notified items
notified = conn.execute("SELECT item_id, title, price, matched, filter_reason, first_seen_at FROM seen_items WHERE notified=1 ORDER BY first_seen_at DESC LIMIT 5").fetchall()
print("\nRecently notified items:")
for notif in notified:
    print(f"  {notif['first_seen_at']} | {notif['item_id']} | {notif['price']} | {notif['title']}")
