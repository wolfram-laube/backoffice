#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Runner Auto-Setup: Automatisches Flip-Flop bei Login/Sleep
# ══════════════════════════════════════════════════════════════
#
# Installiert:
#   - LaunchAgent für Login (Mac an, GCP aus)
#   - Sleepwatcher für Sleep/Wake (GCP an wenn Mac schläft)
#
# Usage:
#   ./scripts/runner-setup-auto.sh install
#   ./scripts/runner-setup-auto.sh uninstall
#
# ══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
FLIP_SCRIPT="$REPO_ROOT/scripts/runner-flip.sh"

PLIST_LOGIN="$HOME/Library/LaunchAgents/com.blauweiss.runner-login.plist"
PLIST_SLEEP="$HOME/Library/LaunchAgents/com.blauweiss.sleepwatcher.plist"
SLEEP_SCRIPT="$HOME/.runner-sleep"
WAKE_SCRIPT="$HOME/.runner-wake"

install_login_hook() {
    echo "📝 Erstelle Login Hook..."
    
    mkdir -p "$HOME/Library/LaunchAgents"
    
    cat > "$PLIST_LOGIN" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.blauweiss.runner-login</string>
    <key>ProgramArguments</key>
    <array>
        <string>$FLIP_SCRIPT</string>
        <string>mac</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.runner-login.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.runner-login.log</string>
</dict>
</plist>
EOF

    launchctl load "$PLIST_LOGIN" 2>/dev/null
    echo "   ✓ Login Hook installiert"
}

install_sleep_hooks() {
    echo "📝 Installiere Sleepwatcher..."
    
    # Install sleepwatcher
    if ! command -v sleepwatcher &> /dev/null; then
        brew install sleepwatcher
    fi
    
    # Sleep script (Mac geht schlafen → GCP starten)
    cat > "$SLEEP_SCRIPT" << EOF
#!/bin/bash
$FLIP_SCRIPT gcp >> $HOME/.runner-sleep.log 2>&1
EOF
    chmod +x "$SLEEP_SCRIPT"
    
    # Wake script (Mac wacht auf → Mac starten, GCP stoppen)
    cat > "$WAKE_SCRIPT" << EOF
#!/bin/bash
$FLIP_SCRIPT mac >> $HOME/.runner-wake.log 2>&1
EOF
    chmod +x "$WAKE_SCRIPT"
    
    # Sleepwatcher LaunchAgent
    cat > "$PLIST_SLEEP" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.blauweiss.sleepwatcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/sbin/sleepwatcher</string>
        <string>-V</string>
        <string>-s</string>
        <string>$SLEEP_SCRIPT</string>
        <string>-w</string>
        <string>$WAKE_SCRIPT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

    launchctl load "$PLIST_SLEEP" 2>/dev/null
    echo "   ✓ Sleep/Wake Hooks installiert"
}

uninstall_all() {
    echo "🗑️  Entferne Hooks..."
    
    launchctl unload "$PLIST_LOGIN" 2>/dev/null
    launchctl unload "$PLIST_SLEEP" 2>/dev/null
    
    rm -f "$PLIST_LOGIN"
    rm -f "$PLIST_SLEEP"
    rm -f "$SLEEP_SCRIPT"
    rm -f "$WAKE_SCRIPT"
    
    echo "   ✓ Alle Hooks entfernt"
}

show_status() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  🔧 AUTO-FLIP STATUS"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo -n "Login Hook:  "
    [ -f "$PLIST_LOGIN" ] && echo "✅ installiert" || echo "❌ nicht installiert"
    echo -n "Sleep Hook:  "
    [ -f "$PLIST_SLEEP" ] && echo "✅ installiert" || echo "❌ nicht installiert"
    echo -n "Sleepwatcher: "
    command -v sleepwatcher &> /dev/null && echo "✅ installiert" || echo "❌ nicht installiert"
    echo ""
}

case "$1" in
    install)
        echo "═══════════════════════════════════════════════════════════"
        echo "  🔧 RUNNER AUTO-FLIP INSTALLATION"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        install_login_hook
        install_sleep_hooks
        echo ""
        echo "✅ Installation abgeschlossen!"
        echo ""
        echo "Verhalten:"
        echo "  • Mac Login  → Mac Runner an, GCP aus"
        echo "  • Mac Sleep  → GCP an, Mac aus"
        echo "  • Mac Wake   → Mac an, GCP aus"
        echo ""
        ;;
    uninstall)
        uninstall_all
        echo "✅ Deinstallation abgeschlossen"
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status}"
        echo ""
        echo "  install   - Installiert Login/Sleep Hooks"
        echo "  uninstall - Entfernt alle Hooks"
        echo "  status    - Zeigt Status"
        ;;
esac
