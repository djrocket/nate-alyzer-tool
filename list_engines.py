
import vertexai
from vertexai.preview import reasoning_engines

def list_engines():
    project = "nate-digital-twin"
    location = "us-central1"
    
    vertexai.init(project=project, location=location)
    
    # ReasoningEngine.list() returns a list of ReasoningEngine objects
    engines = reasoning_engines.ReasoningEngine.list()
    
    print(f"Found {len(engines)} engines:")
    for engine in engines:
        print(f"Name: {engine.resource_name}")
        print(f"Display Name: {engine.display_name}")
        print("-" * 20)

if __name__ == "__main__":
    list_engines()
