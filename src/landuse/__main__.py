"""
Main entry point for the landuse package
"""

from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent


def main():
    """Run the default landuse natural language agent"""
    agent = LanduseNaturalLanguageAgent()
    agent.chat()

if __name__ == "__main__":
    main()
