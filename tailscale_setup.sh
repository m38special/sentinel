#!/bin/bash
# tailscale_setup.sh — Install and configure Tailscale for OpenClaw
# Usage: ./tailscale_setup.sh [up|down|status]

set -e

TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-}"
OPENCLAW_PORT=18789

install_tailscale() {
    echo "Installing Tailscale..."
    
    # Check if macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Try Homebrew first
        if command -v brew &> /dev/null; then
            brew install tailscale
        else
            echo "Homebrew not found. Installing Tailscale manually..."
            curl -fsSL https://tailscale.com/install.sh | sh
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        curl -fsSL https://tailscale.com/install.sh | sh
    else
        echo "Unsupported OS: $OSTYPE"
        exit 1
    fi
    
    echo "Tailscale installed."
}

start_tailscale() {
    if ! command -v tailscale &> /dev/null; then
        install_tailscale
    fi
    
    echo "Starting Tailscale..."
    
    # Check if already logged in
    if ! tailscale status &> /dev/null; then
        if [ -z "$TAILSCALE_AUTH_KEY" ]; then
            echo "No TAILSCALE_AUTH_KEY set."
            echo "Please either:"
            echo "  1. Set TAILSCALE_AUTH_KEY environment variable"
            echo "  2. Run 'tailscale up' and authenticate manually"
            exit 1
        fi
        tailscale up --authkey="$TAILSCALE_AUTH_KEY" --advertise-exit-node=false
    fi
    
    echo "Tailscale is up."
}

serve_tailscale() {
    # This creates a Tailscale funnel (not what we want)
    # Instead we use tailscale serve to expose the port
    
    if ! command -v tailscale &> /dev/null; then
        install_tailscale
    fi
    
    # Make sure Tailscale is up
    tailscale status &> /dev/null || tailscale up
    
    # Use Tailscale to serve the OpenClaw port
    # This makes it accessible via your Tailscale network
    echo "Setting up Tailscale to serve port $OPENCLAW_PORT..."
    
    tailscale serve --bg tcp/$OPENCLAW_PORT
    
    echo "OpenClaw now accessible via Tailscale at:"
    echo "  tcp://$(tailscale ip -4):$OPENCLAW_PORT"
}

stop_tailscale_serve() {
    echo "Stopping Tailscale serve..."
    tailscale serve --down 2>/dev/null || true
    echo "Tailscale serve stopped."
}

show_status() {
    echo "=== Tailscale Status ==="
    tailscale status 2>/dev/null || echo "Tailscale not running"
    
    echo ""
    echo "=== OpenClaw via Tailscale ==="
    if command -v tailscale &> /dev/null; then
        IP=$(tailscale ip -4 2>/dev/null || echo "Not connected")
        echo "Tailscale IP: $IP"
        echo "OpenClaw: tcp://$IP:$OPENCLAW_PORT"
    fi
}

case "${1:-}" in
    up)
        start_tailscale
        ;;
    serve)
        start_tailscale
        serve_tailscale
        ;;
    down)
        stop_tailscale_serve
        ;;
    status)
        show_status
        ;;
    install)
        install_tailscale
        ;;
    *)
        echo "Usage: $0 {up|serve|down|status|install}"
        echo ""
        echo "Commands:"
        echo "  up      — Start Tailscale (requires TAILSCALE_AUTH_KEY)"
        echo "  serve   — Serve OpenClaw via Tailscale network"
        echo "  down    — Stop Tailscale serve"
        echo "  status  — Show Tailscale and OpenClaw status"
        echo "  install — Install Tailscale only"
        exit 1
        ;;
esac
