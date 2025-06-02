import datetime
import os
LOG_FILENAME = "_log.csv"

def get_files_without_id():
    current_dir = os.getcwd()
    all_files = os.listdir(current_dir)

    i = 0
    without_id = []
    for file_name in all_files:
        if file_name != "!automatic_id.py" and file_name != LOG_FILENAME:
            if "★" not in file_name:
                without_id.append(file_name)
                i += 1
    return i, without_id

def assign_id(is_replace_full, without_id):
    for file in without_id:
        ID = datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")
        file_name, file_extension = os.path.splitext(file)
        if is_replace_full:
            file_name_with_id = "★ " + ID + file_extension
        else:
            file_name_with_id = file_name + " ★ " + ID + file_extension
        os.rename(file, file_name_with_id)

        with open(LOG_FILENAME, "a") as log_file:
            log_file.write(f"{file},{ID},{file_extension}\n")

i, unsorted_files = get_files_without_id()
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