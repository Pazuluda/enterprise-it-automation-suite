import unicodedata


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace(" ", "-")
    return value


def generate_username(first_name: str, last_name: str) -> str:
    first = normalize_text(first_name)
    last = normalize_text(last_name)
    return f"{first[0]}.{last}"


def generate_email(first_name: str, last_name: str) -> str:
    first = normalize_text(first_name).replace("-", ".")
    last = normalize_text(last_name).replace("-", ".")
    return f"{first}.{last}@lab.local"
