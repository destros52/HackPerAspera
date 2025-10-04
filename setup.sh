#!/bin/bash

echo "🛡️  Setting up Zurich Women Safety App..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/css static/js templates logs

# Set permissions
echo "🔐 Setting permissions..."
chmod +x run.py

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Update .env file with your API keys"
echo "   3. Run the app: python run.py"
echo ""
echo "📍 The app will be available at: http://localhost:5000"
echo "🛡️  Stay safe!"