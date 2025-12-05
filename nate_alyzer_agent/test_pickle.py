# test_pickle.py
import cloudpickle
import sys
import os

# Add the current directory to path so we can import deploy_monolith
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from deploy_monolith import NateAlyzer
except ImportError as e:
    print(f"FAIL: Could not import NateAlyzer: {e}")
    sys.exit(1)

def test_pickling():
    print("--- Testing Pickling of NateAlyzer ---")
    
    # 1. Instantiate
    try:
        agent = NateAlyzer()
        print("1. Instantiation: OK")
    except Exception as e:
        print(f"1. Instantiation: FAIL ({e})")
        return

    # 2. Pickle
    try:
        pickled_data = cloudpickle.dumps(agent)
        print(f"2. Pickling: OK (Size: {len(pickled_data)} bytes)")
    except Exception as e:
        print(f"2. Pickling: FAIL ({e})")
        return

    # 3. Unpickle
    try:
        restored_agent = cloudpickle.loads(pickled_data)
        print("3. Unpickling: OK")
    except Exception as e:
        print(f"3. Unpickling: FAIL ({e})")
        return

    # 4. Check attributes
    try:
        assert restored_agent.project == agent.project
        assert len(restored_agent.tools) == len(agent.tools)
        print("4. Attribute Check: OK")
    except Exception as e:
        print(f"4. Attribute Check: FAIL ({e})")
        return

    print("\nSUCCESS: Agent is pickle-safe.")

if __name__ == "__main__":
    test_pickling()
