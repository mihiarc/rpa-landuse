#!/usr/bin/env python3
"""
Deploy RPA Land Use Analytics documentation to GitHub Pages
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Deploy documentation using MkDocs"""
    print("🌲 Deploying RPA Land Use Analytics Documentation...")
    print("📚 This will build and push to the gh-pages branch")
    print("🌐 Site will be available at: https://mihiarc.github.io/langchain-landuse\n")

    try:
        # Check if we're in the right directory
        if not Path("mkdocs.yml").exists():
            print("❌ Error: mkdocs.yml not found. Please run from project root.")
            sys.exit(1)

        # Build and deploy
        print("🔨 Building and deploying documentation...")
        subprocess.run(["mkdocs", "gh-deploy", "--force"], check=True)

        print("\n✅ Documentation deployed successfully!")
        print("🌐 Available at: https://mihiarc.github.io/langchain-landuse")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error deploying documentation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ mkdocs not found. Please install with: pip install mkdocs mkdocs-material")
        sys.exit(1)

if __name__ == "__main__":
    main()
