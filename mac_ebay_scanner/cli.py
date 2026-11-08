import sys
import os
import signal
import argparse
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import get_config, BASE_DIR
from .ebay_client import EbayClient
from .notifier import PushbulletNotifier
from .scanner import MacEbayScanner
from .storage import SeenStorage

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_build_site(args):
    """Generate the static GitHub Pages website in docs/."""
    config = get_config()
    console.print(Panel("[bold cyan]Building Static Website for GitHub Pages[/bold cyan]"))

    from .site_generator import generate_static_site
    storage = SeenStorage(db_path=config.db_path)
    docs_dir = BASE_DIR / "docs"

    generate_static_site(storage, docs_dir)
    console.print(f"[green]✓ Website successfully generated in {docs_dir}[/green]")
    console.print(f"Files: index.html, data.json")


def cmd_reconcile(args):
    """Reconcile all seen items against current filter criteria."""
    config = get_config()
    console.print(Panel("[bold cyan]Reconciling Database Items with Filter Engine[/bold cyan]"))
    storage = SeenStorage(db_path=config.db_path)
    res = storage.reconcile_all_items()
    console.print(f"[green]✓ Reconciliation complete:[/green]")
    console.print(f"  Promoted to matched: {res['promoted']}")
    console.print(f"  Demoted to filtered: {res['demoted']}")
    console.print(f"  Reasons updated:     {res['updated_reason']}")

    if getattr(args, "build_site", False):
        cmd_build_site(args)


def cmd_digest(args):
    """Test or manually trigger the 5:00 AM overnight summary digest."""
    config = get_config()
    console.print(Panel("[bold cyan]Overnight Summary Digest[/bold cyan]"))

    storage = SeenStorage(db_path=config.db_path)
    notifier = PushbulletNotifier(api_token=config.pushbullet_api_token)

    if not notifier.is_configured():
        console.print("[red]✗ Pushbullet token not configured.[/red]")
        sys.exit(1)

    queued_items = storage.get_queued_digest_items()
    # If no queued items and test requested, fall back to top recent matches for test preview
    if not queued_items and args.test:
        console.print("[yellow]No overnight items currently in queue. Using recent matches for test preview...[/yellow]")
        queued_items = storage.get_matched_items(limit=3)

    market_stats = storage.get_market_statistics()
    console.print(f"Items in digest: [bold green]{len(queued_items)}[/bold green]")

    success = notifier.notify_overnight_digest(queued_items, market_stats)
    if success:
        console.print("[bold green]✓ Overnight digest dispatched successfully to Pushbullet![/bold green]")
        if not args.test and queued_items:
            storage.mark_digest_sent([it["item_id"] for it in queued_items])
    else:
        console.print("[red]✗ Failed to send overnight digest.[/red]")


def cmd_test_loq(args):
    """Test connectivity and model inference on Lenovo LOQ local LLM server."""
    config = get_config()
    console.print(Panel("[bold cyan]Testing Lenovo LOQ Local Model (Ollama)[/bold cyan]"))
    console.print(f"Endpoint: [bold]{config.local_llm_url}[/bold] | Model: [bold]{config.local_llm_model}[/bold]")

    from .local_llm import LocalLLMVerifier
    verifier = LocalLLMVerifier(endpoint_url=config.local_llm_url, model=config.local_llm_model, enabled=True)

    if not verifier.is_available():
        console.print("[red]✗ Could not reach Ollama server or model 'qwen2.5:7b' is not loaded on LOQ.[/red]")
        sys.exit(1)

    console.print("[green]✓ LOQ Ollama server is reachable and 'qwen2.5:7b' is loaded in VRAM![/green]")
    console.print("[yellow]Running test listing verification on LOQ GPU...[/yellow]")

    sample_item = {
        "title": "Apple MacBook Pro 16\" M4 Max 128GB Unified Memory 2TB SSD Space Black",
        "seller": {"username": "apple_certified"},
    }
    result = verifier.evaluate_candidate(
        item=sample_item,
        detected_model="MacBook Pro",
        detected_chip="Apple M4 Max",
        detected_ram="128GB",
        price=4499.00,
        condition="Excellent - Refurbished",
    )

    console.print("\n[bold green]Local LLM Response:[/bold green]")
    console.print(result)


def cmd_test_ebay(args):
    """Test eBay API authentication and a sample search."""
    config = get_config()
    console.print(Panel("[bold cyan]Testing eBay API Connection[/bold cyan]"))

    client = EbayClient(
        client_id=config.ebay_client_id,
        client_secret=config.ebay_client_secret,
        marketplace=config.ebay_marketplace,
    )

    try:
        console.print("[yellow]Fetching OAuth 2.0 application access token...[/yellow]")
        token = client.get_access_token()
        console.print(f"[green]✓ Successfully authenticated with eBay API![/green] (Token preview: {token[:20]}...)")
    except Exception as e:
        console.print(f"[red]✗ eBay authentication failed: {e}[/red]")
        sys.exit(1)

    console.print("\n[yellow]Executing sample query: 'MacBook Pro 128GB'...[/yellow]")
    items = client.search_items("MacBook Pro 128GB", limit=5)
    console.print(f"[green]✓ Retrieved {len(items)} items from eBay Browse API.[/green]")

    table = Table(title="Sample eBay Search Results")
    table.add_column("Item ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Price", style="green")

    for item in items[:5]:
        price_val = item.get("price", {}).get("value", "N/A")
        curr = item.get("price", {}).get("currency", "")
        table.add_row(item.get("itemId", "")[:18] + "...", item.get("title", "")[:60], f"${price_val} {curr}")

    console.print(table)


def cmd_test_pushbullet(args):
    """Test Pushbullet configuration and send a test notification."""
    config = get_config()
    token = args.token or config.pushbullet_api_token

    console.print(Panel("[bold cyan]Testing Pushbullet Notification[/bold cyan]"))

    if not token:
        console.print("[red]✗ No Pushbullet token provided.[/red]")
        console.print("Please set PUSHBULLET_API_TOKEN in `.env` or pass `--token <your-token>`.")
        sys.exit(1)

    notifier = PushbulletNotifier(api_token=token)
    verify_info = notifier.verify_token()

    if not verify_info.get("valid"):
        console.print(f"[red]✗ Pushbullet validation error: {verify_info.get('error')}[/red]")
        sys.exit(1)

    console.print(f"[green]✓ Pushbullet token verified![/green]")
    console.print(f"User: [bold]{verify_info.get('name')}[/bold] ({verify_info.get('email')})")

    console.print("[yellow]Sending test push notification...[/yellow]")
    success = notifier.send_notification(
        title="MacEbayScanner Test",
        body="This is a test notification from your MacEbayScanner. Price trends & 24/7 monitor is active!",
        url="https://www.ebay.com",
    )

    if success:
        console.print("[bold green]✓ Push notification delivered successfully to your Pushbullet devices![/bold green]")
    else:
        console.print("[red]✗ Failed to send push notification.[/red]")


def cmd_set_token(args):
    """Save Pushbullet token into .env file."""
    token = args.token.strip()
    env_file = BASE_DIR / ".env"

    if not env_file.exists():
        console.print("[red]✗ .env file not found.[/red]")
        sys.exit(1)

    content = env_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith("PUSHBULLET_API_TOKEN="):
            new_lines.append(f"PUSHBULLET_API_TOKEN={token}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"PUSHBULLET_API_TOKEN={token}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    console.print(f"[green]✓ Pushbullet token saved to {env_file} successfully![/green]")


def cmd_market(args):
    """Display market pricing trends and statistics for M3+ 128GB Macs."""
    config = get_config()
    storage = SeenStorage(db_path=config.db_path)
    stats = storage.get_market_statistics()

    if not stats:
        console.print("[yellow]No market data accumulated yet. Run a scan pass first: `python main.py scan --once`[/yellow]")
        return

    table = Table(title="M3+ 128GB Mac Market Price Trends (eBay)")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Sample Count", justify="right", style="magenta")
    table.add_column("Min Price", justify="right", style="green")
    table.add_column("Average", justify="right", style="bold yellow")
    table.add_column("Median", justify="right", style="blue")
    table.add_column("Max Price", justify="right", style="red")

    for cat, s in sorted(stats.items()):
        table.add_row(
            cat,
            str(s["count"]),
            f"${s['min']:,.2f}",
            f"${s['avg']:,.2f}",
            f"${s['median']:,.2f}",
            f"${s['max']:,.2f}",
        )

    console.print(table)
    console.print(f"[dim]Deal threshold: Listings >= {config.deal_discount_percent:.1f}% below category average trigger 🔥 DEAL ALERTS.[/dim]")


def cmd_stats(args):
    """Display monitoring stats from database."""
    config = get_config()
    storage = SeenStorage(db_path=config.db_path)
    stats = storage.get_stats()

    table = Table(title="MacEbayScanner Database Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Total Items Processed", str(stats["total_seen"]))
    table.add_row("Matched M3+ 128GB Mac Items", str(stats["total_matched"]))
    table.add_row("Push Notifications Sent", str(stats["total_notified"]))
    table.add_row("Price History Data Points", str(stats["price_history_records"]))

    console.print(table)


def cmd_matches(args):
    """List recent matches found in database."""
    config = get_config()
    storage = SeenStorage(db_path=config.db_path)
    matches = storage.get_matched_items(limit=args.limit)

    if not matches:
        console.print("[yellow]No matched items found in database yet.[/yellow]")
        return

    table = Table(title=f"Recent Matches (Showing {len(matches)})")
    table.add_column("Model", style="cyan")
    table.add_column("Chip", style="magenta")
    table.add_column("RAM", style="blue")
    table.add_column("Price", style="green")
    table.add_column("Title", style="white")
    table.add_column("URL", style="dim")

    for m in matches:
        price_str = f"${m['price']:,.2f} {m['currency']}" if m['price'] else "N/A"
        table.add_row(
            m["model"] or "Mac",
            m["chip"] or "M3+",
            m["ram"] or "128GB",
            price_str,
            (m["title"] or "")[:45],
            (m["url"] or "")[:40] + "...",
        )

    console.print(table)


def cmd_scan(args):
    """Run scanner (once or daemon loop)."""
    setup_logging(args.verbose)
    config = get_config()

    errors = config.validate(require_pushbullet=False)
    if errors:
        for err in errors:
            console.print(f"[red]Configuration Error: {err}[/red]")
        sys.exit(1)

    if not config.pushbullet_api_token:
        console.print(
            "[yellow]Warning: PUSHBULLET_API_TOKEN is not configured. "
            "Matches will be recorded in database, but notifications will not be pushed.[/yellow]"
        )

    scanner = MacEbayScanner(config)

    def handle_signal(sig, frame):
        console.print("\n[yellow]Shutdown signal received. Stopping scanner gracefully...[/yellow]")
        scanner.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if args.once:
        console.print("[cyan]Running single scan pass...[/cyan]")
        stats = scanner.scan_once()
        console.print(f"[green]Scan pass complete: {stats}[/green]")
    else:
        interval = args.interval or config.scan_interval_seconds
        console.print(f"[bold green]Starting continuous eBay monitor daemon (Interval: {interval}s)...[/bold green]")
        console.print("Press Ctrl+C to stop.")
        scanner.run_daemon(interval_seconds=interval)


def main():
    parser = argparse.ArgumentParser(
        prog="mac-ebay-scanner",
        description="Automated monitor for M3 or higher MacBook Pro / Mac Studio with 128GB RAM via eBay API & Pushbullet.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # build-site
    subparsers.add_parser("build-site", help="Generate public GitHub Pages website in docs/")

    # digest
    digest_parser = subparsers.add_parser("digest", help="Trigger or test the 5am overnight summary digest")
    digest_parser.add_argument("--test", action="store_true", help="Send test digest using recent matches")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan eBay for target Mac listings")
    scan_parser.add_argument("--once", action="store_true", help="Perform a single scan and exit")
    scan_parser.add_argument("--interval", type=int, help="Scan interval in seconds (default: 180)")
    scan_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    # market
    subparsers.add_parser("market", help="Show market pricing statistics and price trends")

    # test-loq
    subparsers.add_parser("test-loq", help="Test LOQ laptop local LLM connectivity and inference")

    # test-ebay
    subparsers.add_parser("test-ebay", help="Test eBay OAuth authentication and search API")

    # test-pushbullet
    pb_parser = subparsers.add_parser("test-pushbullet", help="Test Pushbullet notification")
    pb_parser.add_argument("--token", type=str, help="Pushbullet API token to test")

    # set-token
    set_token_parser = subparsers.add_parser("set-token", help="Save Pushbullet token into .env")
    set_token_parser.add_argument("token", type=str, help="Pushbullet Access Token")

    # stats
    subparsers.add_parser("stats", help="Show monitoring statistics")

    # matches
    matches_parser = subparsers.add_parser("matches", help="List matches saved in database")
    matches_parser.add_argument("--limit", type=int, default=20, help="Max matches to display")

    # reconcile
    reconcile_parser = subparsers.add_parser("reconcile", help="Reconcile database items with filter criteria")
    reconcile_parser.add_argument("--build-site", action="store_true", help="Automatically rebuild site after reconcile")

    args = parser.parse_args()

    if args.command == "build-site":
        cmd_build_site(args)
    elif args.command == "reconcile":
        cmd_reconcile(args)
    elif args.command == "digest":
        cmd_digest(args)
    elif args.command == "test-loq":
        cmd_test_loq(args)
    elif args.command == "test-ebay":
        cmd_test_ebay(args)
    elif args.command == "test-pushbullet":
        cmd_test_pushbullet(args)
    elif args.command == "set-token":
        cmd_set_token(args)
    elif args.command == "market":
        cmd_market(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "matches":
        cmd_matches(args)
    elif args.command == "scan":
        cmd_scan(args)
    else:
        scan_parser.print_help()


if __name__ == "__main__":
    main()
