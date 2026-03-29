import os
import glob

replacements = {
    # THETA -> PRISM (Sentinel)
    "AgentTheta": "AgentPrism",
    "agent_theta": "agent_prism",
    "AgentID.THETA": "AgentID.PRISM",
    "backend.agents.sentinel": "backend.agents.prism",
    '"THETA"': '"agent_prism"', # Fix Frontend string refs to proper backend ID
    
    # IOTA -> CHI (Inspector)
    "AgentIota": "AgentChi",
    "agent_iota": "agent_chi",
    "AgentID.IOTA": "AgentID.CHI",
    "backend.agents.inspector": "backend.agents.chi",
    '"IOTA"': '"agent_chi"' # Fix Frontend string refs
}

def safe_replace():
    files = []
    # Collect Python Backend
    for rp in glob.glob("backend/**/*.py", recursive=True):
        files.append(rp)
    # Collect React Frontend
    for rp in glob.glob("src/**/*.js", recursive=True):
         files.append(rp)
    for rp in glob.glob("src/**/*.jsx", recursive=True):
         files.append(rp)
         
    changed_count = 0
    
    for fw in files:
        try:
            with open(fw, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            original_content = content
            for k, v in replacements.items():
                content = content.replace(k, v)
                
            if content != original_content:
                with open(fw, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Refactored: {fw}")
                changed_count += 1
        except Exception as e:
            print(f"Failed to read/write {fw}: {e}")
            
    print(f"Total Files Refactored: {changed_count}")

if __name__ == "__main__":
    safe_replace()
