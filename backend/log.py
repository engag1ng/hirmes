LOG_FILENAME = "log.csv"

def write_log(code, ID, file_name, file_extension):
    with open(LOG_FILENAME, "a") as log_file:
        log_file.write(f"{code}, {ID}, {file_name},{file_extension}\n")