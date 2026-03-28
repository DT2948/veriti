import imagehash
from PIL import Image


def compute_phash(image_path: str) -> str:
    with Image.open(image_path) as image:
        return str(imagehash.phash(image))


def hamming_distance(hash1: str, hash2: str) -> int:
    if not hash1 or not hash2:
        return 64

    value1 = int(hash1, 16)
    value2 = int(hash2, 16)
    return (value1 ^ value2).bit_count()
