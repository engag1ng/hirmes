import datetime
import os
LOG_FILENAME = "_log.csv"

ignore_list = ["!automatic_id.py", LOG_FILENAME, ".git", ".backend", "LICENSE", "README.md"]

def get_files_without_id(path, is_recursive):
    i = 0
    without_id = []
    
    entries = os.listdir(path)

    for entry in entries:
        full_path = os.path.join(path, entry)
        if entry not in ignore_list:
            if os.path.isdir(full_path) and is_recursive:
                additional_i, additional_without_id = get_files_without_id(full_path, is_recursive)
                i += additional_i
                without_id += additional_without_id
            elif os.path.isfile(full_path):
                if "★" not in entry:
                    without_id.append(full_path)
                    i += 1

    return i, without_id

def assign_id(is_replace_full, without_id):
    for file in without_id:
        ID = datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")
        dir_name = os.path.dirname(file)
        base_name = os.path.basename(file)
        file_name, file_extension = os.path.splitext(base_name)

        if is_replace_full:
            new_name = "★ " + ID + file_extension
        else:
            new_name = file_name + " ★ " + ID + file_extension

        new_path = os.path.join(dir_name, new_name)
        os.rename(file, new_path)

        with open(LOG_FILENAME, "a") as log_file:
            log_file.write(f"{file},{ID},{file_extension}\n")

use_recursive_search = True if input(f"Would you like to include subfolders in the ID assignment? Y/n ") == "Y" else False

i, unsorted_files = get_files_without_id(os.getcwd(), use_recursive_search)
print(unsorted_files)

if i == 0:
    exit()
is_answered = False
while not is_answered:
    replace_full_name_input = input(f"There are {i} files without an ID. Would you like to replace the FULL file name? Y/n or help ")
    if replace_full_name_input == "Y":
        assign_id(True, unsorted_files)
        is_answered = True
    elif replace_full_name_input == "n":
        assign_id(False, unsorted_files)
        is_answered = True
    elif replace_full_name_input == "help":
        print("There are currently two options for assigning an ID:\n'Y' means the full filename gets replaced like this:\ntest.txt -> ★ ID.txt\n'n' means the ID only gets appended to the filename like this:\ntest.txt -> test ★ ID.txt")