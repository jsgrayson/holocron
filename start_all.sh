#!/bin/bash
# Holocron Unified Startup Script

echo "🚀 Starting Holocron Systems..."

# Set database URL
export DATABASE_URL='postgresql://holocron:password@localhost:5432/holocron_db'

# Start Holocron (main dashboard) on port 5001
echo "📊 Starting Holocron Dashboard (port 5001)..."
cd /Users/jgrayson/Documents/holocron
python3 server.py &
HOLOCRON_PID=$!

# Wait a moment for Holocron to start
sleep 2

# Start PetWeaver on port 5002
echo "🐾 Starting PetWeaver (port 5002)..."
cd /Users/jgrayson/Documents/petweaver
python3 app.py &
PETWEAVER_PID=$!

echo ""
echo "✅ All systems online!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Holocron Dashboard: http://127.0.0.1:5001"
echo "🐾 PetWeaver:         http://127.0.0.1:5002"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Process IDs:"
echo "   Holocron:  $HOLOCRON_PID"
echo "   PetWeaver: $PETWEAVER_PID"
echo ""
echo "To stop all servers: kill $HOLOCRON_PID $PETWEAVER_PID"
echo "Or press Ctrl+C and run: killall python3"
echo ""

# Wait for either process to exit
wait
