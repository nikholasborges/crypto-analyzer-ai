import sys
from src.crew.research import ResearchCrew


# if command line args contains --research flag, get the remaining args as the topic
def run():
    topic = None

    if "--research" in sys.argv:
        # Find the index of --research flag
        research_index = sys.argv.index("--research")
        # Get all args after --research as the topic
        if research_index + 1 < len(sys.argv):
            topic = " ".join(sys.argv[research_index + 1 :])

    if not topic:
        print("No topic provided. Usage: python -m src.cli --research <topic>")
        return

    try:
        app = ResearchCrew()
        result = app.start(inputs={"topic": topic})
        print(result)
    except Exception as e:
        print(f"Error during research execution: {e}")
        raise


if __name__ == "__main__":
    run()
