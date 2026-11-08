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

    from .filter_engine import MacFilterEngine
    filter_engine = MacFilterEngine()

    # Get stats, market statistics, and all seen items
    db_stats = storage.get_stats()
    market_stats = storage.get_market_statistics()
    all_seen = storage.get_all_seen_items(limit=1000)
    matched_items = [it for it in all_seen if it.get("matched") == 1]
    filtered_items = [it for it in all_seen if it.get("matched") != 1]

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
    for it in all_seen:
        is_matched = bool(it.get("matched"))
        price = it.get("price") or 0.0

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

        filter_reason = None
        if is_matched:
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
        else:
            model = it.get("model") or "Non-Target"
            chip = it.get("chip") or "Other"
            raw_ram = str(it.get("ram") or "")
            ram = "256GB" if "256" in raw_ram else ("128GB" if "128" in raw_ram else "Non-target")
            ram_display = "Excluded"
            cat_key = "Filtered Out"
            avg_price = None
            discount_pct = 0.0
            diff = 0.0
            is_deal = False

            filter_reason = it.get("filter_reason")
            if not filter_reason:
                eval_target = raw_item if raw_item else {"title": it.get("title", "")}
                eval_res = filter_engine.evaluate_item(eval_target)
                filter_reason = eval_res.reason

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
            "filter_reason": filter_reason,
            "is_matched": is_matched,
            "image_url": image_url,
            "category": cat_key,
            "market_avg": avg_price,
            "diff": round(diff, 2),
            "discount_pct": discount_pct,
            "is_deal": is_deal,
            "first_seen_at": it.get("first_seen_at", ""),
        })

    trend_analysis = storage.get_detailed_trend_analysis()

    site_data = {
        "last_scanned": timestamp_str,
        "last_scanned_short": time_only_str,
        "last_match_time": last_match_time_str,
        "total_processed": len(processed_items),
        "total_matches": len(matched_items),
        "total_filtered": len(filtered_items),
        "market_stats": market_stats,
        "trend_analysis": trend_analysis,
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

    <!-- Model Combination Trend Analysis -->
    <section class="mb-10">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h2 class="text-sm font-semibold tracking-wider uppercase text-gray-400 flex items-center gap-2">
            <i class="fas fa-chart-line text-blue-400"></i> Model Combination Trend Analysis
          </h2>
          <p class="text-xs text-gray-400 mt-0.5">Real-time market price spectrums, medians, and deal targets across Apple Silicon hardware tiers</p>
        </div>
        <div class="flex items-center gap-1.5 self-start sm:self-auto">
          <button onclick="setTrendTab('all')" class="trend-tab active text-[11px] px-2.5 py-1 rounded-lg bg-blue-600 text-white font-medium" data-trend-tab="all">All Combinations</button>
          <button onclick="setTrendTab('MacBook Pro')" class="trend-tab text-[11px] px-2.5 py-1 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-trend-tab="MacBook Pro">MacBook Pro</button>
          <button onclick="setTrendTab('Mac Studio')" class="trend-tab text-[11px] px-2.5 py-1 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-trend-tab="Mac Studio">Mac Studio</button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="trendsGrid">
        <!-- Rendered by JS -->
      </div>
    </section>

    <!-- Controls / Filters -->
    <section class="glass p-4 rounded-2xl mb-8 flex flex-col md:flex-row gap-4 items-center justify-between" id="listingsSection">
      <div class="flex flex-wrap items-center gap-2 w-full md:w-auto">
        <span class="text-xs text-gray-400 font-medium mr-1">Filter:</span>
        <button onclick="setFilter('all')" class="filter-btn active text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium" data-filter="all">All</button>
        <button onclick="setFilter('MacBook Pro')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-filter="MacBook Pro">MacBook Pro</button>
        <button onclick="setFilter('Mac Studio')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700" data-filter="Mac Studio">Mac Studio</button>
        <button onclick="setFilter('256GB')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30 hover:bg-purple-500/30" data-filter="256GB">256GB RAM Only</button>
        <button onclick="setFilter('deal')" class="filter-btn text-xs px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30" data-filter="deal">🔥 Deals Only</button>
        <span id="activeFilterBadge" class="hidden text-xs px-2.5 py-1 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/30 font-medium items-center gap-1.5">
          <span id="activeFilterText"></span>
          <button onclick="setFilter('all')" class="hover:text-white ml-1"><i class="fas fa-xmark"></i></button>
        </span>
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

    <!-- Listings View Mode Switcher -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-1.5 p-1 rounded-xl bg-gray-900 border border-gray-800 self-start">
        <button onclick="setViewMode('matched')" id="tabMatched" class="view-mode-tab active text-xs px-3.5 py-1.5 rounded-lg bg-blue-600 text-white font-semibold transition cursor-pointer" data-view="matched">
          <i class="fas fa-check-circle mr-1 text-emerald-400"></i> Verified Matches (<span id="matchedCountTab">0</span>)
        </button>
        <button onclick="setViewMode('filtered')" id="tabFiltered" class="view-mode-tab text-xs px-3.5 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition cursor-pointer" data-view="filtered">
          <i class="fas fa-filter-circle-xmark mr-1 text-amber-400"></i> Filtered Out (<span id="filteredCountTab">0</span>)
        </button>
        <button onclick="setViewMode('all')" id="tabAll" class="view-mode-tab text-xs px-3.5 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition cursor-pointer" data-view="all">
          <i class="fas fa-list mr-1 text-blue-400"></i> All Evaluated (<span id="allCountTab">0</span>)
        </button>
      </div>

      <div class="text-xs text-gray-400">
        Showing <span id="itemCount" class="font-bold text-white">0</span> listings
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="itemsGrid">
      <!-- Populated by JS -->
    </div>

  </main>

  <script>
    let DATA = {json.dumps(site_data)};
    let currentFilter = 'all';
    let currentViewMode = 'matched';

    function setViewMode(mode) {{
      currentViewMode = mode;
      document.querySelectorAll('.view-mode-tab').forEach(b => {{
        if (b.dataset.view === mode) {{
          b.className = 'view-mode-tab active text-xs px-3.5 py-1.5 rounded-lg bg-blue-600 text-white font-semibold transition cursor-pointer';
        }} else {{
          b.className = 'view-mode-tab text-xs px-3.5 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition cursor-pointer';
        }}
      }});
      applyFilters();
    }}

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

          renderTrends();
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

    let currentTrendTab = 'all';

    function setTrendTab(tab) {{
      currentTrendTab = tab;
      document.querySelectorAll('.trend-tab').forEach(b => {{
        if (b.dataset.trendTab === tab) {{
          b.className = 'trend-tab active text-[11px] px-2.5 py-1 rounded-lg bg-blue-600 text-white font-medium';
        }} else {{
          b.className = 'trend-tab text-[11px] px-2.5 py-1 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700';
        }}
      }});
      renderTrends();
    }}

    function renderTrends() {{
      const grid = document.getElementById('trendsGrid');
      if (!grid) return;
      grid.innerHTML = '';

      const trends = (DATA.trend_analysis || []).filter(t => {{
        if (currentTrendTab === 'MacBook Pro' && !t.model.includes('MacBook')) return false;
        if (currentTrendTab === 'Mac Studio' && !t.model.includes('Studio')) return false;
        return true;
      }});

      if (trends.length === 0) {{
        grid.innerHTML = '<div class="col-span-full py-8 text-center text-gray-500">No trend data available for this selection.</div>';
        return;
      }}

      trends.forEach(t => {{
        const is256 = t.ram && t.ram.includes('256');
        const iconClass = t.model.includes('Studio') ? 'fa-desktop text-purple-400' : 'fa-laptop text-blue-400';
        const ramBadge = is256 
          ? '<span class="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono font-semibold">256GB RAM</span>'
          : '<span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono font-semibold">128GB RAM</span>';

        const storageList = Object.entries(t.storage_spread || {{}})
          .filter(([k, _]) => k !== 'Standard')
          .slice(0, 3)
          .map(([k, count]) => `<span class="px-1.5 py-0.5 rounded bg-gray-800/90 text-gray-300 text-[10px] font-mono border border-gray-700/50">${{k}} (${{count}})</span>`)
          .join(' ');

        const card = document.createElement('div');
        card.className = 'glass p-4 rounded-xl border border-gray-800 hover:border-gray-700 transition flex flex-col justify-between';
        card.innerHTML = `
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <i class="fas ${{iconClass}} text-sm"></i>
                <span class="font-bold text-sm text-white">${{t.model}} ${{t.chip}}</span>
              </div>
              <div class="flex items-center gap-1.5">
                ${{ramBadge}}
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">${{t.count}} active</span>
              </div>
            </div>

            <!-- Price Spectrum Box -->
            <div class="mb-3 bg-gray-950/70 p-3 rounded-lg border border-gray-800/90">
              <div class="flex justify-between items-baseline text-[11px] font-mono text-gray-400 mb-1.5">
                <div>Low: <strong class="text-emerald-400 font-bold">$${{t.min.toLocaleString()}}</strong></div>
                <div>Avg: <strong class="text-yellow-400 font-bold">$${{t.avg.toLocaleString()}}</strong></div>
                <div>Max: <strong class="text-gray-300">$${{t.max.toLocaleString()}}</strong></div>
              </div>
              <div class="relative w-full h-2 rounded-full bg-gray-800 overflow-hidden mb-2">
                <div class="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500 rounded-full" style="width: 100%;"></div>
              </div>
              <div class="flex justify-between items-center text-[10px] text-gray-400">
                <span class="text-amber-400 font-medium">Median: <strong>$${{t.median.toLocaleString()}}</strong></span>
                <span class="text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Target: &lt; $${{t.deal_threshold.toLocaleString()}}</span>
              </div>
            </div>

            <!-- Storage Spread -->
            <div class="flex items-center gap-1.5 flex-wrap text-xs text-gray-400 mb-3">
              <span class="text-[11px] text-gray-500">Storage seen:</span>
              ${{storageList || '<span class="text-[10px] text-gray-500 font-mono">Standard SSD</span>'}}
            </div>
          </div>

          <!-- Quick Action -->
          <div class="pt-3 border-t border-gray-800/80 flex items-center justify-between">
            <span class="text-[11px] text-gray-400">Spread: <span class="font-mono text-gray-300">+${{t.price_spread_pct}}%</span></span>
            <button onclick="filterByCombination('${{t.category}}')" class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-blue-600 text-blue-400 hover:text-white transition cursor-pointer">
              View ${{t.count}} listings <i class="fas fa-arrow-down text-[10px]"></i>
            </button>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    function filterByCombination(catKey) {{
      currentFilter = catKey;
      document.querySelectorAll('.filter-btn').forEach(b => {{
        b.className = 'filter-btn text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700';
      }});
      const badge = document.getElementById('activeFilterBadge');
      const text = document.getElementById('activeFilterText');
      if (badge && text) {{
        text.innerText = catKey;
        badge.classList.remove('hidden');
        badge.classList.add('inline-flex');
      }}
      const searchBox = document.getElementById('searchInput');
      if (searchBox) searchBox.value = '';
      applyFilters();
      const section = document.getElementById('listingsSection');
      if (section) section.scrollIntoView({{ behavior: 'smooth' }});
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
      const badge = document.getElementById('activeFilterBadge');
      if (badge) {{
        badge.classList.add('hidden');
        badge.classList.remove('inline-flex');
      }}
      applyFilters();
    }}

    function applyFilters() {{
      const query = document.getElementById('searchInput').value.toLowerCase();
      const sort = document.getElementById('sortSelect').value;

      const matchedTotal = DATA.items.filter(it => it.is_matched).length;
      const filteredTotal = DATA.items.filter(it => !it.is_matched).length;
      const allTotal = DATA.items.length;

      const mTab = document.getElementById('matchedCountTab');
      if (mTab) mTab.innerText = matchedTotal;
      const fTab = document.getElementById('filteredCountTab');
      if (fTab) fTab.innerText = filteredTotal;
      const aTab = document.getElementById('allCountTab');
      if (aTab) aTab.innerText = allTotal;

      let items = DATA.items.filter(it => {{
        if (currentViewMode === 'matched' && !it.is_matched) return false;
        if (currentViewMode === 'filtered' && it.is_matched) return false;

        if (currentFilter === 'MacBook Pro' && it.model !== 'MacBook Pro') return false;
        if (currentFilter === 'Mac Studio' && it.model !== 'Mac Studio') return false;
        if (currentFilter === '256GB' && !it.ram.includes('256')) return false;
        if (currentFilter === 'deal' && !it.is_deal) return false;
        if (currentFilter.startsWith('Mac') && it.category !== currentFilter) return false;
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
        grid.innerHTML = '<div class="col-span-full py-12 text-center text-gray-500">No matching listings found for this view and filter.</div>';
        return;
      }}

      items.forEach(it => {{
        const card = document.createElement('div');

        if (!it.is_matched) {{
          card.className = 'glass-card rounded-2xl p-5 flex flex-col justify-between border-amber-500/20 bg-gray-900/40 hover:border-amber-500/40 transition';
          const imgPlaceholder = it.image_url ? 
            `<img src="${{it.image_url}}" alt="Mac" class="w-16 h-16 object-cover rounded-xl border border-gray-800 shrink-0 opacity-70">` : 
            `<div class="w-16 h-16 rounded-xl bg-gray-800/60 flex items-center justify-center text-gray-500 shrink-0"><i class="fas fa-filter text-xl"></i></div>`;

          card.innerHTML = `
            <div>
              <div class="flex items-center justify-between mb-3 gap-2">
                <span class="text-[11px] px-2.5 py-0.5 rounded bg-gray-800 text-gray-400 font-medium border border-gray-700">Non-Target Listing</span>
                <span class="text-[11px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold"><i class="fas fa-ban mr-1"></i>Filtered Out</span>
              </div>

              <div class="flex gap-3 items-start mb-3">
                ${{imgPlaceholder}}
                <div>
                  <h3 class="text-sm font-medium text-gray-300 line-clamp-2 leading-snug">${{it.title}}</h3>
                  <div class="text-xs text-gray-500 mt-1">${{it.condition}} • ${{it.seller}}</div>
                </div>
              </div>

              <div class="mt-2.5 mb-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 leading-snug">
                <span class="font-bold text-amber-300 mr-1"><i class="fas fa-circle-info mr-1"></i>Rejection Reason:</span>
                ${{it.filter_reason || 'Did not meet target processor or memory criteria'}}
              </div>

              <div class="flex items-baseline gap-2 mt-1">
                <span class="text-xl font-bold text-gray-300">$${{it.price.toLocaleString()}}</span>
                <span class="text-xs text-gray-500">${{it.currency}}</span>
              </div>
            </div>

            <div class="mt-4 pt-3 border-t border-gray-800/80 flex items-center justify-between">
              <span class="text-[11px] text-gray-500 font-mono">Excluded by Rule Engine</span>
              <a href="${{it.url}}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700 transition">
                Inspect on eBay <i class="fas fa-arrow-up-right-from-square text-[10px]"></i>
              </a>
            </div>
          `;
          grid.appendChild(card);
          return;
        }}

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

    renderTrends();
    applyFilters();
  </script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html_content, encoding="utf-8")
    logger.info(f"Static dashboard generated in {output_dir} ({len(processed_items)} items).")
