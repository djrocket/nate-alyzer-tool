try:
    with open("output.txt", "r", encoding="utf-16") as f:
        for line in f:
            if "Layer" in line:
                print(line.strip())
except Exception as e:
    print(f"Failed to read output.txt: {e}")
    # Try utf-8 just in case
    try:
        with open("output.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "Layer" in line:
                    print(line.strip())
    except Exception as e2:
        print(f"Failed with utf-8 too: {e2}")
