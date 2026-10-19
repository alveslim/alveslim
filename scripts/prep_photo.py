import sys
import cv2
import numpy as np
from PIL import Image
from rembg import remove

def prep(input_path, output_path="source-prepped.png"):
    with open(input_path, "rb") as i:
        inp = i.read()
    nobg = remove(inp)

    from io import BytesIO
    img = Image.open(BytesIO(nobg)).convert("RGBA")
    white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white_bg, img).convert("L")

    arr = np.array(composite)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(arr)

    Image.fromarray(enhanced).save(output_path)
    print(f"Salvo em {output_path}")

if __name__ == "__main__":
    photo = sys.argv[1] if len(sys.argv) > 1 else "source-photo.png"
    prep(photo)