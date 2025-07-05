dict_path = "backend/dictionary.txt"
def dictionary():
    with open(dict_path, "a+") as file:
        return file.read().split("\n")

def add_dictionary(word):
    dic = dictionary()
    if word not in dic:
        with open(dict_path, "a") as file:
            file.write(f"{word}\n")