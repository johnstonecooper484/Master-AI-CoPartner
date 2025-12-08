import json

with open("project_paths.json", "r") as f:
    paths = json.load(f)

print("Project Root:", paths["project_root"])
print("Resources:", paths["resources_dir"])
print("PDFs:", paths["pdf_dir"])
print("Open Source:", paths["open_source_dir"])
print("Research:", paths["research_dir"])
print("GitHub:", paths["github_url"])
