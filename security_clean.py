import os

clean_path = input("Input the path you would like to clean. This includes all subfolders.\ni.e. C:\\Users\\<User>\\Documents\n>>>")

print("\n")

def clean(path):
    i = 0
    try:
        entries = os.listdir(path)
    except FileNotFoundError:
        print(f"Path not found: {path}")
        return 0

    for entry in entries:
        full_path = os.path.join(path, entry)

        if os.path.isdir(full_path):
            i += clean(full_path)

        elif os.path.isfile(full_path):
            if "★" in entry:
                dir_name = os.path.dirname(full_path)
                base_name = os.path.basename(full_path)
                file_name, file_extension = os.path.splitext(base_name)

                cutoff_char = " ★"
                trimmed = file_name.split(cutoff_char)[0] + file_extension

                new_path = os.path.join(dir_name, trimmed)

                if not os.path.exists(new_path):
                    os.rename(full_path, new_path)
                    print(f"Renamed: {full_path} -> {new_path}\n")
                    i += 1
                else:
                    print(f"Skipped (target exists): {new_path}\n")
    return i

renamed_count = clean(clean_path)
print(f"\n\n\nDone! Cleaned up {renamed_count} files.")