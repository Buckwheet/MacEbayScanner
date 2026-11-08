param (
    [string]$Action = "status"
)

switch ($Action.ToLower()) {
    "status" {
        ssh encoder1 "systemctl --user status mac-ebay-scanner.service --no-pager"
    }
    "logs" {
        ssh encoder1 "journalctl --user -u mac-ebay-scanner.service -f -n 50"
    }
    "restart" {
        ssh encoder1 "systemctl --user restart mac-ebay-scanner.service && systemctl --user status mac-ebay-scanner.service --no-pager"
    }
    "stop" {
        ssh encoder1 "systemctl --user stop mac-ebay-scanner.service && systemctl --user status mac-ebay-scanner.service --no-pager"
    }
    "market" {
        ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py market"
    }
    "stats" {
        ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py stats"
    }
    "matches" {
        ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py matches --limit 15"
    }
    default {
        Write-Host "Usage: .\service_encoder1.ps1 [status|logs|restart|stop|market|stats|matches]"
    }
}
