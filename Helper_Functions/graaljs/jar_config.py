import os
import zipfile


def _build_graal_jar_index(jar_runtime_path):
    """
    Scans all JARs under jar_runtime_path and builds an index:
        class_entry_path → jar_file_path
    Example entry:
        'com/oracle/js/parser/Parser.class' → '/path/to/graaljs.jar'
    """
    index = {}
    print(f"[GRAALJS][INDEX] Scanning JARs under {jar_runtime_path} ...")

    for jar_name in os.listdir(jar_runtime_path):
        if not jar_name.endswith(".jar"):
            continue

        jar_path = os.path.join(jar_runtime_path, jar_name)
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                for entry in jar.namelist():
                    if entry.endswith(".class"):
                        # Only index exact class paths
                        if entry not in index:
                            index[entry] = jar_path
        except Exception as e:
            print(f"[GRAALJS][INDEX][ERROR] Failed reading {jar_path}: {e}")

        print(f"[GRAALJS][INDEX] Indexed: {jar_name}")

    print(f"[GRAALJS][INDEX] Completed. Indexed {len(index)} class entries.")
    return index
def replace_mutant_in_jar(mutant_dir, jar_runtime_path, jar_index, modified_jars):
    """
    Replace the EXACT matching .class entry in the correct JAR.
    - mutant_dir contains exactly one "*.class" file.
    - jar_index maps class_entry_path → correct jar.
    - modified_jars tracks which jars were modified.
    """

    mutant_files = [f for f in os.listdir(mutant_dir) if f.endswith(".class")]
    if not mutant_files:
        return False

    mf = mutant_files[0]   # always 1 mutant class
    class_name = mf[:-6]   # "com.oracle.js.parser.Parser"
    entry_path = class_name.replace(".", "/") + ".class"   # "com/oracle/js/parser/Parser.class"

    print(f"[GRAALJS][REPLACE] Mutant maps to: {entry_path}")

    if entry_path not in jar_index:
        print(f"[GRAALJS][REPLACE][WARN] Class not found in index: {entry_path}")
        return False

    target_jar = jar_index[entry_path]
    print(f"[GRAALJS][REPLACE] Updating JAR → {target_jar}")

    tmp_path = target_jar + ".tmp"
    backup_entry = entry_path + ".backup"
    mutant_bytes = open(os.path.join(mutant_dir, mf), "rb").read()

    modified_jars.add(target_jar)

    with zipfile.ZipFile(target_jar, 'r') as zin, zipfile.ZipFile(tmp_path, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename == entry_path:
                # Write backup only once
                if backup_entry not in zin.namelist():
                    zout.writestr(backup_entry, data)
                    print(f"    ↳ Backup created: {backup_entry}")

                # Write mutated class
                zout.writestr(entry_path, mutant_bytes)
                print(f"    ↳ Replacing class: {entry_path}")

            else:
                zout.writestr(item, data)

    os.replace(tmp_path, target_jar)
    print(f"[GRAALJS][REPLACE] JAR updated OK.")

    return True
def restore_original_jars(jar_runtime_path, modified_jars, jar_index):
    """
    Restores only the jars that were actually modified.
    Works by restoring *.class.backup entries.
    """

    print(f"[GRAALJS][RESTORE] Restoring only modified jars...")

    for jar_path in modified_jars:
        tmp_path = jar_path + ".tmp"
        restored_any = False

        with zipfile.ZipFile(jar_path, 'r') as zin, zipfile.ZipFile(tmp_path, 'w') as zout:
            for item in zin.infolist():
                fname = item.filename

                # restore exact backup
                if fname.endswith(".class.backup"):
                    original_name = fname[:-7]
                    data = zin.read(fname)
                    zout.writestr(original_name, data)
                    restored_any = True
                elif fname.endswith(".class") and (fname + ".backup") in zin.namelist():
                    # skip mutated version (will be restored via backup)
                    continue
                else:
                    zout.writestr(item, zin.read(fname))

        os.replace(tmp_path, jar_path)

        print(f"[GRAALJS][RESTORE] Restored JAR: {jar_path} (entries restored: {restored_any})")

    print(f"[GRAALJS][RESTORE] Complete.")
