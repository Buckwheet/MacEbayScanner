import json
import logging
from pathlib import Path
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from typing import Dict, Any, List, Optional
from .storage import SeenStorage

logger = logging.getLogger(__name__)


def generate_static_site(
    storage: SeenStorage,
    output_dir: Path,
    last_scan_dt: Optional[datetime] = None,
    github_pages_url: str = "https://buckwheet.github.io/MacEbayScanner/",
):
    """Generate static HTML dashboard and JSON data in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cst_tz = ZoneInfo("America/Chicago")
    now_cst = last_scan_dt.astimezone(cst_tz) if last_scan_dt else datetime.now(cst_tz)
    timestamp_str = now_cst.strftime("%B %d, %Y at %I:%M %p CST")
    time_only_str = now_cst.strftime("%I:%M %p CST")

    # Get stats, market statistics, and matched items
    db_stats = storage.get_stats()
    market_stats = storage.get_market_statistics()
    matched_items = storage.get_matched_items(limit=100)

    # Format the time of the most recent match
    last_match_time_str = "None yet"
    if matched_items:
        try:
            m_dt = datetime.fromisoformat(matched_items[0]["first_seen_at"])
            last_match_time_str = m_dt.astimezone(cst_tz).strftime("%b %d, %I:%M %p CST")
        except Exception:
            last_match_time_str = matched_items[0].get("first_seen_at", "")[:16]

    # Process items to attach market delta and deal badges
    processed_items = []
    for it in matched_items:
        price = it.get("price") or 0.0
        model = it.get("model") or "MacBook Pro"
        chip = it.get("chip") or "M3 Max"
        raw_ram = str(it.get("ram") or "128GB")
        ram = "256GB" if "256" in raw_ram else "128GB"
        ram_display = f"{ram} Unified Memory"
        cat_key = storage.get_category_key(model, chip, ram)

        stat = market_stats.get(cat_key, {})
        avg_price = stat.get("avg")
        discount_pct = 0.0
        diff = 0.0
        is_deal = False

        if avg_price and avg_price > 0 and price < avg_price:
            diff = avg_price - price
            discount_pct = round((diff / avg_price) * 100.0, 1)
            if discount_pct >= 15.0:
                is_deal = True

        raw_item = {}
        try:
            if it.get("raw_json"):
                raw_item = json.loads(it["raw_json"])
        except Exception:
            pass

        image_url = ""
        if raw_item.get("image", {}).get("imageUrl"):
            image_url = raw_item["image"]["imageUrl"]
        elif raw_item.get("thumbnailImages") and len(raw_item["thumbnailImages"]) > 0:
            image_url = raw_item["thumbnailImages"][0].get("imageUrl", "")

        processed_items.append({
            "item_id": it["item_id"],
            "title": it["title"],
            "price": price,
            "currency": it.get("currency", "USD"),
            "url": it["url"],
            "model": model,
            "chip": chip,
            "ram": ram,
            "ram_display": ram_display,
            "condition": it.get("condition") or "Pre-owned",
            "seller": it.get("seller") or "eBay Seller",
            "llm_analysis": it.get("llm_analysis") or "",
            "image_url": image_url,
            "category": cat_key,
            "market_avg": avg_price,
            "diff": round(diff, 2),
            "discount_pct": discount_pct,
            "is_deal": is_deal,
            "first_seen_at": it.get("first_seen_at", ""),
        })

    site_data = {
        "last_scanned": timestamp_str,
        "last_scanned_short": time_only_str,
        "last_match_time": last_match_time_str,
        "total_processed": db_stats["total_seen"],
        "total_matches": len(processed_items),
        "market_stats": market_stats,
        "items": processed_items,
    }
    (output_dir / "data.json").write_text(json.dumps(site_data, indent=2), encoding="utf-8")

    html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apple Silicon 128GB & 256GB Mac Deal Tracker</title>
  <meta name="description" content="Live 24/7 eBay monitor and price tracker for M3+ 128GB/256GB MacBook Pro and Mac Studio machines.">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ background-color: #0b0f17; color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .glass {{ background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
    .glass-card {{ background: #131b2e; border: 1px solid rgba(255, 255, 255, 0.07); transition: transform 0.2s, border-color 0.2s; }}
    .glass-card:hover {{ transform: translateY(-2px); border-color: rgba(59, 130, 246, 0.5); }}
  </style>
</head>
<body class="min-h-screen pb-16">

  <!-- Header -->
  <header class="glass sticky top-0 z-50 py-3.5 px-6 mb-8 border-b border-gray-800">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center text-xl font-bold border border-blue-500/30">
          <i class="fab fa-apple"></i>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-bold tracking-tight text-white">Apple Silicon High-Memory Tracker</h1>
            <span class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-medium">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> ONLINE 24/7
            </span>
          </div>
          <p class="text-xs text-gray-400">eBay monitor for M3+ MacBook Pro & Mac Studio (128GB & 256GB Unified Memory)</p>
        </div>
      </div>
      <div class="text-xs text-gray-400 text-center md:text-right flex flex-col gap-1 items-center md:items-end">
        <div class="flex items-center gap-2">
          <span><i class="fas fa-satellite-dish text-blue-400 mr-1"></i> <span class="font-semibold text-gray-300">encoder1</span> (Every 3 mins)</span>
          <button onclick="triggerImmediateRefresh()" title="Click to refresh listings now" class="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-0.5 rounded-lg bg-gray-800/90 text-gray-300 hover:text-white hover:bg-gray-700 border border-gray-700/60 transition cursor-pointer">
            <i class="fas fa-arrows-rotate text-blue-400" id="refreshIcon"></i>
            <span>Refresh: <span id="autoRefreshTimer" class="font-mono text-white font-semibold">3:00</span></span>
          </button>
        </div>
        <div class="text-gray-400">
          Last Scan: <span id="lastScanTime" class="text-emerald-400 font-semibold">{time_only_str}</span> • 
          Last Match: <span id="lastMatchTime" class="text-gray-300 font-medium">{last_match_time_str}</span>
        </div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6">

    <!-- Status Strip -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
      <div class="glass p-3 rounded-xl border border-gray-800/80">
        <div class="text-[11px] uppercase tracking-wider text-gray-400">Scanner Status</div>
        <div class="text-sm font-semibold text-emerald-400 mt-0.5 flex items-center gap-1.5">
          <i class="fas fa-check-circle"></i> Active & Polling
        </div>
      </div>
      <div class="glass p-3 rounded-xl border border-gray-800/80">
        <div class="text-[11px] uppercase tracking-wider text-gray-400">Evaluated Today</div>
        <div id="evaluatedCount" class="text-sm font-bold text-white mt-0.5">{db_stats["total_seen"]} listings</div>
      </div>
      <div class="glass p-3 rounded-xl border border-gray-800/80">
        <div class="text-[11px] uppercase tracking-wider text-gray-400">Matching Machines</div>
        <div id="matchingCount" class="text-sm font-bold text-blue-400 mt-0.5">{len(processed_items)} verified</div>
      </div>
      <div class="glass p-3 rounded-xl border border-gray-800/80">
        <div class="text-[11px] uppercase tracking-wider text-gray-400">AI Evaluator</div>
        <div class="text-sm font-semibold text-amber-400 mt-0.5 flex items-center gap-1.5">
          <i class="fas fa-microchip"></i> LOQ RTX 3050 (qwen2.5)
        </div>
      </div>
    </div>

    <!-- Market Overview Cards -->
    <section class="mb-10">
      <h2 class="text-sm font-semibold tracking-wider uppercase text-gray-400 mb-4 flex items-center gap-2">
        <i class="fas fa-chart-line text-blue-400"></i> Market Price Trends (eBay Baseline)
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" id="statsGrid">
        <!-- Rendered by JS -->
      </div>
    </section>

    <!-- Controls / Filters -->
    <section class="glass p-4 rounded-2xl mb-8 flex flex-col md:flex-row gap-4 items-center justify-between">
      <div class="flex flex-wrap items-center gap-2 w-full md:w-auto">
        <span class="text-xs text-gray-400 font-medium mr-1">Filter:</span>
        <button onclick="setFilter('all')" class="filter-btn active text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium" data-filter="all">All</button>
        <button onclick="setFilter('MacBook Pro')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-filter="MacBook Pro">MacBook Pro</button>
        <button onclick="setFilter('Mac Studio')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-filter="Mac Studio">Mac Studio</button>
        <button onclick="setFilter('256GB')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30 hover:bg-purple-500/30" data-filter="256GB">256GB RAM Only</button>
        <button onclick="setFilter('deal')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30" data-filter="deal">🔥 Deals Only</button>
      </div>

      <div class="flex items-center gap-3 w-full md:w-auto">
        <div class="relative w-full md:w-64">
          <i class="fas fa-search absolute left-3 top-2.5 text-gray-400 text-xs"></i>
          <input type="text" id="searchInput" oninput="applyFilters()" placeholder="Search title or specs..." class="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-gray-900 border border-gray-700 text-white focus:outline-none focus:border-blue-500">
        </div>
        <select id="sortSelect" onchange="applyFilters()" class="text-xs px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 text-white focus:outline-none focus:border-blue-500">
          <option value="price-asc">Price: Low to High</option>
          <option value="price-desc">Price: High to Low</option>
          <option value="discount-desc">Best Value (% Under Market)</option>
        </select>
      </div>
    </section>

    <!-- Listings Grid -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-sm font-semibold tracking-wider uppercase text-gray-400 flex items-center gap-2">
        <i class="fas fa-laptop text-blue-400"></i> Active Listings (<span id="itemCount">0</span>)
      </h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="itemsGrid">
      <!-- Populated by JS -->
    </div>

  </main>

  <script>
    let DATA = {json.dumps(site_data)};
    let currentFilter = 'all';

    const REFRESH_INTERVAL_MS = 180000; // 3 minutes
    let nextRefreshEpoch = Date.now() + REFRESH_INTERVAL_MS;
    let isFetching = false;

    function updateRefreshTimer() {{
      const remainingSec = Math.max(0, Math.round((nextRefreshEpoch - Date.now()) / 1000));
      const min = Math.floor(remainingSec / 60);
      const sec = remainingSec % 60;
      const timerElem = document.getElementById('autoRefreshTimer');
      if (timerElem) {{
        timerElem.innerText = `${{min}}:${{sec < 10 ? '0' : ''}}${{sec}}`;
      }}
      if (remainingSec <= 0 && !isFetching) {{
        checkAndRefreshData();
      }}
    }}

    async function checkAndRefreshData() {{
      if (isFetching) return;
      isFetching = true;
      const icon = document.getElementById('refreshIcon');
      if (icon) icon.classList.add('fa-spin');

      try {{
        const resp = await fetch(`data.json?t=${{Date.now()}}`, {{ cache: 'no-store' }});
        if (resp.ok) {{
          const freshData = await resp.json();
          DATA = freshData;

          const scanElem = document.getElementById('lastScanTime');
          if (scanElem && freshData.last_scanned_short) scanElem.innerText = freshData.last_scanned_short;

          const matchElem = document.getElementById('lastMatchTime');
          if (matchElem && freshData.last_match_time) matchElem.innerText = freshData.last_match_time;

          const evalElem = document.getElementById('evaluatedCount');
          if (evalElem && freshData.total_processed !== undefined) evalElem.innerText = `${{freshData.total_processed}} listings`;

          const matchCountElem = document.getElementById('matchingCount');
          if (matchCountElem && freshData.total_matches !== undefined) matchCountElem.innerText = `${{freshData.total_matches}} verified`;

          renderStats();
          applyFilters();
        }} else {{
          console.warn('Auto-refresh HTTP', resp.status, '- attempting reload');
          window.location.reload();
        }}
      }} catch (err) {{
        console.warn('Auto-refresh fetch error:', err);
      }} finally {{
        nextRefreshEpoch = Date.now() + REFRESH_INTERVAL_MS;
        isFetching = false;
        if (icon) icon.classList.remove('fa-spin');
      }}
    }}

    function triggerImmediateRefresh() {{
      checkAndRefreshData();
    }}

    setInterval(updateRefreshTimer, 1000);

    function renderStats() {{
      const grid = document.getElementById('statsGrid');
      grid.innerHTML = '';
      for (const [cat, s] of Object.entries(DATA.market_stats)) {{
        const card = document.createElement('div');
        card.className = 'glass p-4 rounded-xl border border-gray-800';
        card.innerHTML = `
          <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span class="font-medium text-gray-200">${{cat}}</span>
            <span class="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">${{s.count}} listings</span>
          </div>
          <div class="flex items-baseline justify-between mt-2">
            <div>
              <span class="text-2xl font-bold text-white">$${{s.min.toLocaleString()}}</span>
              <span class="text-xs text-gray-400 ml-1">lowest</span>
            </div>
            <div class="text-right text-xs">
              <div class="text-yellow-400 font-medium">Avg: $${{s.avg.toLocaleString()}}</div>
              <div class="text-gray-400">Median: $${{s.median.toLocaleString()}}</div>
            </div>
          </div>
        `;
        grid.appendChild(card);
      }}
    }}

    function setFilter(filter) {{
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => {{
        if (b.dataset.filter === filter) {{
          b.className = 'filter-btn active text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium';
        }} else {{
          b.className = 'filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700';
        }}
      }});
      applyFilters();
    }}

    function applyFilters() {{
      const query = document.getElementById('searchInput').value.toLowerCase();
      const sort = document.getElementById('sortSelect').value;

      let items = DATA.items.filter(it => {{
        if (currentFilter === 'MacBook Pro' && it.model !== 'MacBook Pro') return false;
        if (currentFilter === 'Mac Studio' && it.model !== 'Mac Studio') return false;
        if (currentFilter === '256GB' && !it.ram.includes('256')) return false;
        if (currentFilter === 'deal' && !it.is_deal) return false;
        if (query && !it.title.toLowerCase().includes(query) && !it.chip.toLowerCase().includes(query)) return false;
        return true;
      }});

      if (sort === 'price-asc') items.sort((a, b) => a.price - b.price);
      else if (sort === 'price-desc') items.sort((a, b) => b.price - a.price);
      else if (sort === 'discount-desc') items.sort((a, b) => b.discount_pct - a.discount_pct);

      document.getElementById('itemCount').innerText = items.length;
      renderItems(items);
    }}

    function renderItems(items) {{
      const grid = document.getElementById('itemsGrid');
      grid.innerHTML = '';

      if (items.length === 0) {{
        grid.innerHTML = '<div class="col-span-full py-12 text-center text-gray-500">No matching listings found.</div>';
        return;
      }}

      items.forEach(it => {{
        const card = document.createElement('div');
        card.className = 'glass-card rounded-2xl p-5 flex flex-col justify-between';

        const dealBadge = it.is_deal ? 
          `<span class="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold">🔥 ${{it.discount_pct}}% Under Market</span>` : '';

        const aiSection = it.llm_analysis ? `
          <div class="mt-3 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs text-gray-300 leading-relaxed">
            <span class="text-blue-400 font-semibold"><i class="fas fa-brain mr-1"></i>LOQ AI:</span> ${{it.llm_analysis}}
          </div>` : '';

        const diffStr = it.diff > 0 ? 
          `<span class="text-emerald-400 text-xs font-medium">(-$${{it.diff.toLocaleString()}} vs avg)</span>` : '';

        const imgPlaceholder = it.image_url ? 
          `<img src="${{it.image_url}}" alt="Mac" class="w-20 h-20 object-cover rounded-xl border border-gray-800 shrink-0">` : 
          `<div class="w-20 h-20 rounded-xl bg-gray-800 flex items-center justify-center text-gray-600 shrink-0"><i class="fas fa-laptop text-2xl"></i></div>`;

        const is256 = (it.ram && it.ram.includes('256')) || (it.title && it.title.includes('256'));
        const ramBadgeClass = is256 
          ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' 
          : 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30';
        const ramBadgeText = is256 ? '256GB RAM' : '128GB RAM';
        const ramFooterText = is256 ? '256GB Unified Memory' : '128GB Unified Memory';
        const ramFooterColor = is256 ? 'text-purple-300 font-semibold' : 'text-gray-300 font-medium';

        card.innerHTML = `
          <div>
            <div class="flex items-center justify-between mb-3 gap-2">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-xs px-2.5 py-0.5 rounded bg-blue-500/10 text-blue-400 font-semibold border border-blue-500/20">${{it.model}} • ${{it.chip}}</span>
                <span class="text-xs px-2 py-0.5 rounded font-mono font-bold ${{ramBadgeClass}}">
                  <i class="fas fa-memory mr-1"></i>${{ramBadgeText}}
                </span>
              </div>
              ${{dealBadge}}
            </div>

            <div class="flex gap-4 items-start mb-3">
              ${{imgPlaceholder}}
              <div>
                <h3 class="text-sm font-semibold text-white line-clamp-2 leading-snug">${{it.title}}</h3>
                <div class="text-xs text-gray-400 mt-1">${{it.condition}} • ${{it.seller}}</div>
              </div>
            </div>

            <div class="flex items-baseline gap-2 mt-2">
              <span class="text-2xl font-bold text-white">$${{it.price.toLocaleString()}}</span>
              <span class="text-xs text-gray-400">${{it.currency}}</span>
              ${{diffStr}}
            </div>

            ${{aiSection}}
          </div>

          <div class="mt-4 pt-3 border-t border-gray-800/80 flex items-center justify-between">
            <span class="text-xs ${{ramFooterColor}} font-mono flex items-center gap-1.5">
              <i class="fas fa-microchip ${{is256 ? 'text-purple-400' : 'text-blue-400'}}"></i>
              ${{ramFooterText}}
            </span>
            <a href="${{it.url}}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition">
              View on eBay <i class="fas fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    renderStats();
    applyFilters();
  </script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html_content, encoding="utf-8")
    logger.info(f"Static dashboard generated in {output_dir} ({len(processed_items)} items).")
