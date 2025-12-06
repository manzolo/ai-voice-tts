.PHONY: help setup setup-gpu build up up-gpu down restart logs clean clean-all status test

help:
	@echo "AI Voice TTS - Text-to-Speech Service"
	@echo ""
	@echo "Setup & Build:"
	@echo "  make setup      - Initial setup (CPU mode)"
	@echo "  make setup-gpu  - Initial setup (GPU mode)"
	@echo "  make build      - Build Docker images"
	@echo ""
	@echo "Start/Stop:"
	@echo "  make up         - Start services (CPU mode)"
	@echo "  make up-gpu     - Start services (GPU mode)"
	@echo "  make down       - Stop services"
	@echo "  make restart    - Restart services"
	@echo ""
	@echo "Operations:"
	@echo "  make logs       - Show service logs"
	@echo "  make status     - Show container status"
	@echo "  make test       - Test TTS API"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Stop and remove containers"
	@echo "  make clean-all  - Remove everything (containers + models)"

setup:
	@echo "🚀 Setting up AI Voice TTS (CPU mode)..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from .env.example..."; \
		cp .env.example .env; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@echo "🔧 Creating models directory..."
	@mkdir -p models
	@echo "📦 Building Docker images..."
	docker compose build
	@echo "🚀 Starting services..."
	docker compose up -d
	@echo "⏳ Waiting for services to initialize (30s)..."
	@sleep 30
	@echo "✅ Setup complete!"
	@echo "🌐 Web Interface: http://localhost:8080"
	@echo "🔌 TTS API: http://localhost:9876"

setup-gpu:
	@echo "🚀 Setting up AI Voice TTS (GPU mode)..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from .env.example..."; \
		cp .env.example .env; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@echo "🔧 Creating models directory..."
	@mkdir -p models
	@echo "📦 Building Docker images..."
	docker compose -f docker-compose.gpu.yml build
	@echo "🚀 Starting services..."
	docker compose -f docker-compose.gpu.yml up -d
	@echo "⏳ Waiting for services to initialize (30s)..."
	@sleep 30
	@echo "✅ Setup complete!"
	@echo "🌐 Web Interface: http://localhost:8080"
	@echo "🔌 TTS API: http://localhost:9876"

build:
	docker compose build

up:
	@echo "🚀 Starting TTS services (CPU mode)..."
	docker compose up -d

up-gpu:
	@echo "🚀 Starting TTS services (GPU mode)..."
	docker compose -f docker-compose.gpu.yml up -d

down:
	@echo "🛑 Stopping TTS services..."
	@docker compose down 2>/dev/null || true
	@docker compose -f docker-compose.gpu.yml down 2>/dev/null || true

restart:
	docker compose restart

logs:
	docker compose logs -f

status:
	@echo "📊 Container Status:"
	@docker compose ps
	@echo ""
	@echo "💾 Model Storage:"
	@du -sh models 2>/dev/null || echo "No models downloaded yet"

clean:
	@echo "🧹 Stopping and removing containers..."
	@docker compose down 2>/dev/null || true
	@docker compose -f docker-compose.gpu.yml down 2>/dev/null || true

clean-all:
	@echo "⚠️  WARNING: This will remove all containers and downloaded models!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo "🧹 Removing containers and models..."
	@docker compose down -v 2>/dev/null || true
	@docker compose -f docker-compose.gpu.yml down -v 2>/dev/null || true
	@if [ -d models ] && [ "$$(ls -A models 2>/dev/null)" ]; then \
		echo "🗑️  Removing model files (using Docker for proper permissions)..."; \
		docker run --rm -v "$$(pwd)/models:/models" alpine sh -c "rm -rf /models/*" 2>/dev/null || \
		sudo rm -rf models 2>/dev/null || \
		echo "⚠️  Could not remove models directory. You may need to run: sudo rm -rf models"; \
	else \
		echo "📁 Models directory is empty or doesn't exist"; \
	fi
	@echo "✅ Complete cleanup done"

test:
	@echo "🧪 Testing TTS API..."
	@curl -X POST http://localhost:9876/api/tts \
		-H "Content-Type: application/json" \
		-d '{"text": "Hello, this is a test of the text to speech system.", "language": "en", "speaker": "male"}' \
		--output /tmp/test_tts.wav && \
		echo "✅ TTS test successful! Audio saved to /tmp/test_tts.wav" || \
		echo "❌ TTS test failed"
