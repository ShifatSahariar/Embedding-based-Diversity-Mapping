import os
import re

PRINT_REGEX = re.compile(r'\bprint\s*\(')

def convert_rhino_to_karate(root_dir):
    """
    Recursively scan input_pool_by_run_X folders and convert
    print(...) to console.log(...)
    """

    total_modified = 0
    folder_stats = {}

    # iterate over run folders
    for run_folder in sorted(os.listdir(root_dir)):
        run_path = os.path.join(root_dir, run_folder)
        if not os.path.isdir(run_path):
            continue

        modified_in_folder = 0

        # iterate input files
        for filename in os.listdir(run_path):
            if not filename.endswith(".txt"):
                continue

            file_path = os.path.join(run_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original = f.read()

                # apply replacement
                updated = PRINT_REGEX.sub("console.log(", original)

                if updated != original:
                    # write only if modified
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(updated)
                    modified_in_folder += 1
                    total_modified += 1

            except Exception as e:
                print(f"[WARN] Could not process {file_path}: {e}")

        folder_stats[run_folder] = modified_in_folder

    # summary printing
    print("\n=== Replacement summary ===")
    for folder, count in folder_stats.items():
        print(f"{folder}: modified {count} files")
    print(f"TOTAL modified: {total_modified}")

    return folder_stats, total_modified


if __name__ == "__main__":
    base_dir = "../../GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/KARATEJS"   # <-- you set this
    convert_rhino_to_karate(base_dir)
