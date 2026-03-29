import ast
import os

def check_file(path):
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    errors.append(f"Line {node.lineno}: Bare `except:` block found.")
            elif isinstance(node, ast.Import):
                pass
    except SyntaxError as e:
        errors.append(f"SyntaxError: {str(e)}")
    except Exception as e:
        errors.append(f"Parse error: {str(e)}")
        
    return errors

def main():
    backend_path = "backend"
    total_issues = 0
    for root, _, files in os.walk(backend_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                issues = check_file(path)
                if issues:
                    print(f"\n[!] Issues in {path}:")
                    for i in issues:
                        print(f"  - {i}")
                        total_issues += 1
                        
    if total_issues == 0:
         print("\n[+] Zero Static AST Bugs Found!")
    else:
         print(f"\n[!] Total Static Issues Found: {total_issues}")

if __name__ == "__main__":
    main()
