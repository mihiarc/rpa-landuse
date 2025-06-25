#!/usr/bin/env python3
"""
Serve the RPA Land Use Analytics documentation locally
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Serve documentation using MkDocs"""
    print("🌲 Starting RPA Land Use Analytics Documentation Server...")
    print("📚 Documentation will be available at: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server\n")
    
    try:
        # Run mkdocs serve
        subprocess.run(["mkdocs", "serve"], check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Documentation server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running mkdocs: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ mkdocs not found. Please install with: pip install mkdocs mkdocs-material")
        sys.exit(1)

if __name__ == "__main__":
    main()