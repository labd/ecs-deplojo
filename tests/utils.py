def deindent_text(value):
    value = value.lstrip("\n")
    indent_size = len(value) - len(value.lstrip(" "))
    result = "\n".join(line[indent_size:] for line in value.split("\n"))
    return result.strip()
