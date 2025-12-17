"""
Main entry point for the landuse package
"""

from landuse.agents import LanduseAgent


def main():
    """Run the default landuse natural language agent"""
    agent = LanduseAgent()
    agent.chat()


if __name__ == "__main__":
    main()
