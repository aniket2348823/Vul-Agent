import xml.etree.ElementTree as ET
import os

def extract_failures(xml_path, output_path):
    if not os.path.exists(xml_path):
        print(f"Error: {xml_path} not found.")
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    failures = root.findall(".//testcase[failure]")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Raw Failure Extraction Data\n\n")
        for ft in failures:
            name = ft.get("name")
            failure = ft.find("failure")
            text = failure.text if failure is not None else "No failure text"
            f.write(f"## TEST: {name}\n")
            f.write(f"```\n{text[:500]}\n```\n\n")
            f.write("---\n\n")

if __name__ == "__main__":
    extract_failures("pytest-report.xml", "testsprite_tests/extracted_failures.md")
