#!/usr/bin/env python3
import sys
import subprocess

# Service definitions
services = {
    'db': 'docker-compose-db.yml',
    'backend': 'docker-compose-backend.yml',
    'frontend': 'docker-compose-frontend.yml',
    'ollama': 'docker-compose-ollama.yml',
    'chromadb': 'docker-compose-chromadb.yml'
}

def run_service(action, service_file, build=True):
    cmd = ['docker', 'compose', '-f', service_file]
    if action == 'up':
        cmd.extend(['up', '-d'])
        if build:
            cmd.append('--build')
    else:
        cmd.append('down')
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'up'
    service = sys.argv[2] if len(sys.argv) > 2 else None
    
    if action in ['up', 'start']:
        if service and service in services:
            run_service('up', services[service])
        else:
            # Start all services (except ollama)
            for name, file in services.items():
                if name != 'ollama':  # Skip ollama by default
                    run_service('up', file)
                    
    elif action in ['down', 'stop']:
        if service and service in services:
            if service == 'chromadb':
                print("⚠️  WARNING: ChromaDB contains persistent data!")
                print("   Use 'python run.py down chromadb --force' to force stop ChromaDB")
                if '--force' not in sys.argv:
                    print("   Skipping ChromaDB shutdown to preserve data.")
                    return
                else:
                    print("   Force flag detected - stopping ChromaDB...")
            run_service('down', services[service], build=False)
        else:
            # Stop all services EXCEPT ChromaDB
            print("🛡️  Protecting ChromaDB from shutdown to preserve data")
            for name, file in services.items():
                if name != 'chromadb':  # Skip chromadb to preserve data
                    run_service('down', file, build=False)
            print("✅ All services stopped except ChromaDB (data preserved)")
    
    elif action == 'restart':
        service_name = service if service else 'all'
        print(f"🔄 Restarting {service_name}...")
        
        if service and service in services:
            if service == 'chromadb':
                print("⚠️  ChromaDB restart requires --force flag to avoid data loss")
                if '--force' not in sys.argv:
                    print("   Skipping ChromaDB restart. Use --force if needed.")
                    return
            run_service('down', services[service], build=False)
            run_service('up', services[service])
        else:
            # Restart all except ChromaDB
            for name, file in services.items():
                if name != 'chromadb' and name != 'ollama':
                    run_service('down', file, build=False)
                    run_service('up', file)
    
    elif action == 'status':
        print("📊 Service Status:")
        subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'])
    
    elif action == 'logs':
        if service and service in services:
            subprocess.run(['docker', 'compose', '-f', services[service], 'logs', '-f'])
        else:
            print("Please specify a service for logs: db, backend, frontend, ollama, chromadb")
    
    elif action == 'help':
        print("""
🚀 Finance Assistant Service Manager

Usage: python run.py [action] [service] [flags]

Actions:
  up/start    - Start services (default: all except ollama)
  down/stop   - Stop services (protects chromadb by default)
  restart     - Restart services (protects chromadb by default)
  status      - Show running containers
  logs        - Show logs for a service
  help        - Show this help

Services:
  db          - MySQL database
  backend     - FastAPI backend
  frontend    - Streamlit frontend
  ollama      - Ollama AI service
  chromadb    - ChromaDB vector database (protected)

Flags:
  --force     - Force action on protected services (chromadb)

Examples:
  python run.py                          # Start all services except ollama
  python run.py up ollama               # Start only ollama
  python run.py down                    # Stop all except chromadb
  python run.py down chromadb --force   # Force stop chromadb
  python run.py restart backend         # Restart only backend
  python run.py status                  # Show service status
  python run.py logs backend            # Show backend logs

🛡️  ChromaDB Protection:
   ChromaDB contains your learning data and feedback. It's protected from
   accidental shutdown. Use --force flag only if you need to stop it.
        """)
    
    else:
        print(f"Unknown action: {action}")
        print("Use 'python run.py help' for usage information")

if __name__ == '__main__':
    main()
