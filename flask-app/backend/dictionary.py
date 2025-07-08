dict_path = "backend/dictionary.txt"
def dictionary():
    with open(dict_path, "a+", encoding="utf-8") as file:
        file.seek(0)
        content = file.read().split("\n")
        return content

def add_dictionary(word):
    dic = dictionary()
    if word not in dic:
        with open(dict_path, "a", encoding="utf-8") as file:
            file.write(f"{word}\n")