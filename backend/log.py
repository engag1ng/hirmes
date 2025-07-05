LOG_FILENAME = "log.csv"

def write_log(ID, file_name, file_extension):
    with open(LOG_FILENAME, "a") as log_file:
        log_file.write(f"{ID},{file_name},{file_extension}\n")