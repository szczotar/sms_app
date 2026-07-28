_TRANSLIT = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
    "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
})


def strip_diacritics(text: str) -> str:
    return text.translate(_TRANSLIT)


def normalize_name(name: str) -> str:
    return " ".join(strip_diacritics(name).lower().split())
