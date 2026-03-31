import json
import hashlib

def recursive_sanitize(data):
    """Recursively remove ephemeral keys from dictionary or list."""
    if isinstance(data, dict):
        return {
            k: recursive_sanitize(v) 
            for k, v in data.items() 
            if k not in ['element_api_id', 'antigravity_id', 'timestamp', 'id', 'scan_id', 'session_id']
        }
    elif isinstance(data, list):
        return [recursive_sanitize(item) for item in data]
    return data

def test_recursive():
    print("--- [RECURSIVE DEDUPLICATION STRESS TEST] ---")
    
    # Case 1: Deeply nested ephemeral IDs
    data1 = {
        "outer": {
            "inner": {
                "element_api_id": "random-1",
                "content": "Secret text",
                "meta": {"timestamp": 12345}
            }
        }
    }
    
    data2 = {
        "outer": {
            "inner": {
                "element_api_id": "random-2", # DIFFERENT
                "content": "Secret text",
                "meta": {"timestamp": 67890} # DIFFERENT
            }
        }
    }
    
    s1 = recursive_sanitize(data1)
    s2 = recursive_sanitize(data2)
    
    print(f"Sanitized 1: {s1}")
    print(f"Sanitized 2: {s2}")
    
    h1 = hashlib.md5(json.dumps(s1, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.md5(json.dumps(s2, sort_keys=True).encode()).hexdigest()
    
    if h1 == h2:
        print("\nSUCCESS: Recursive sanitization matches nested structures correctly.")
    else:
        print("\nFAILURE: Hashes do not match for identical content with different ephemeral IDs.")
        exit(1)

if __name__ == "__main__":
    test_recursive()
