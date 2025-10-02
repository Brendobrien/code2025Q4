# pip install torch torchvision transformers pillow regex unidecode
import os, re, argparse, itertools
from unidecode import unidecode
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

def slugify(txt):
    txt = unidecode(txt.lower())
    txt = re.sub(r"[^a-z0-9]+", "-", txt).strip("-")
    return re.sub(r"-{2,}", "-", txt)

# crude noun-ish filter: keep content words; shorten
STOP = {"a","an","the","of","with","and","in","on","at","to","for","from","by","near","is","are"}
def compress(caption, max_words=4):
    words = [w for w in re.findall(r"[A-Za-z0-9']+", caption)]
    keep = [w for w in words if w.lower() not in STOP]
    # prefer longer tokens first
    keep.sort(key=lambda w: (-len(w), w.lower()))
    # unique order-preserving
    seen=set(); uniq=[x for x in keep if not (x.lower() in seen or seen.add(x.lower()))]
    return " ".join(uniq[:max_words]) or "photo"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True, help="Folder of images")
    p.add_argument("--hint", default="", help="Optional context, e.g. 'Jordan People'")
    p.add_argument("--exts", default=".jpg,.jpeg,.png,.heic")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

    exts = tuple(e.strip().lower() for e in args.exts.split(","))
    files = [f for f in os.listdir(args.dir) if f.lower().endswith(exts)]
    files.sort()

    for f in files:
        path = os.path.join(args.dir, f)
        try:
            img = Image.open(path).convert("RGB")
            prompt = f"{args.hint}. a concise photo description:" if args.hint else "a concise photo description:"
            inputs = processor(img, text=prompt, return_tensors="pt").to(device)
            out = model.generate(**inputs, max_new_tokens=20)
            caption = processor.decode(out[0], skip_special_tokens=True)

            short = compress(caption, max_words=4)
            base = slugify(f"{args.hint} {short}".strip()) if args.hint else slugify(short)
            new_name = base + os.path.splitext(f)[1].lower()
            new_path = os.path.join(args.dir, new_name)

            # avoid collisions: add -1, -2...
            if os.path.exists(new_path) and not args.overwrite:
                for i in itertools.count(1):
                    cand = os.path.join(args.dir, f"{base}-{i}{os.path.splitext(f)[1].lower()}")
                    if not os.path.exists(cand):
                        new_path = cand; break

            print(f"{f}  →  {os.path.basename(new_path)}   [{caption}]")
            if not args.dry:
                os.rename(path, new_path)
        except Exception as e:
            print(f"Skip {f}: {e}")

if __name__ == "__main__":
    main()
