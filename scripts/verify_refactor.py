"""Verification script for the refactored architecture."""
import sys
sys.path.insert(0, '.')
errors = []

# Test 1: Core cluster imports
try:
    from backend.core.cluster import PinchTabInstance, MasterNode, WorkerNode
    print('[PASS] Cluster package imports OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] Cluster: {e}')

# Test 2: BaseArsenalModule re-export
try:
    from backend.core.base import BaseArsenalModule
    print('[PASS] BaseArsenalModule re-export OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] BaseArsenalModule: {e}')

# Test 3: Arsenal base direct import
try:
    from backend.core.arsenal_base import BaseArsenalModule as BAM
    assert hasattr(BAM, 'generate_payloads')
    assert hasattr(BAM, 'safe_json_parse')
    print('[PASS] Arsenal base direct import OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] Arsenal base: {e}')

# Test 4: Module imports (all 9 attack modules)
modules = [
    'backend.modules.tech.sqli',
    'backend.modules.tech.jwt',
    'backend.modules.tech.fuzzer',
    'backend.modules.tech.auth_bypass',
    'backend.modules.logic.tycoon',
    'backend.modules.logic.escalator',
    'backend.modules.logic.skipper',
    'backend.modules.logic.doppelganger',
    'backend.modules.logic.chronomancer',
]
for mod in modules:
    try:
        __import__(mod)
        name = mod.rsplit('.', 1)[-1]
        print(f'[PASS] {name} import OK')
    except Exception as e:
        errors.append(str(e))
        print(f'[FAIL] {mod}: {e}')

# Test 5: Graph engine
try:
    from backend.core.graph_engine import GraphEngine
    print('[PASS] GraphEngine import OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] GraphEngine: {e}')

# Test 6: Cortex LRU cache
try:
    import collections
    from backend.ai.cortex import CortexEngine
    print('[PASS] CortexEngine import OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] CortexEngine: {e}')

# Test 7: Orchestrator imports cleanly
try:
    from backend.core.orchestrator import HiveOrchestrator
    print('[PASS] HiveOrchestrator import OK')
except Exception as e:
    errors.append(str(e))
    print(f'[FAIL] HiveOrchestrator: {e}')

total = len(modules) + 7
passed = total - len(errors)
print(f'\n=== RESULTS: {passed}/{total} passed, {len(errors)} failed ===')
if errors:
    for e in errors:
        print(f'  ERROR: {e}')
