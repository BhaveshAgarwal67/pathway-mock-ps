from flask import Flask, render_template, request
import os, glob, re
import fitz  
import easyocr

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
reader = easyocr.Reader(['en'])

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == ".pdf":
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    elif ext in [".png", ".jpg", ".jpeg"]:
        result = reader.readtext(file_path, detail=0)
        text = "\n".join(result)
    else:
        raise ValueError("Unsupported file type.")
    return text

def extract_info_pan(text):
    name, dob, pan = None, None, None
    text = text.replace('\r','\n')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if "Permanent Account Number Card" in line:
            if i+1 < len(lines) and re.match(r'^[A-Z]{5}\d{4}[A-Z]$', lines[i+1].strip()):
                pan = lines[i+1].strip()
            if i+2 < len(lines):
                name = lines[i+2].strip()
            break
    for i, line in enumerate(lines):
        if re.search(r'dob|date of birth', line, re.IGNORECASE) and i+1 < len(lines):
            dob = lines[i+1].strip()
            break
    return {"name": name, "dob": dob, "pan": pan, "text": text}

def extract_info(text):
    generic_id = None

    # Aadhaar detection (12-digit, may have spaces)
    aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    if aadhaar_match:
        generic_id = aadhaar_match.group(0).replace(" ", "")
    else:
        # fallback: any 9-12 digit number, not phone
        id_matches = re.findall(r'\b\d{9,12}\b', text.replace(" ", ""))
        for m in id_matches:
            if not re.match(r'^[6-9]\d{9}$', m):  # skip 10-digit phone numbers
                generic_id = m
                break

    return {"generic_id": generic_id, "text": text}


def verify_with_pan(pan_info, other_docs):
    flags = []
    full_name = pan_info.get("name")
    ref_firstname = full_name.split()[0].lower() if full_name else None
    if not full_name: flags.append("PAN card Name not found.")
    for i, doc in enumerate(other_docs):
        doc_text_lower = ''.join(doc["text"].lower().split())
        if ref_firstname and ref_firstname not in doc_text_lower:
            flags.append(f"Document {i+1}: First name from PAN not found.")
    summary = "Verified ✅" if not flags else "Mismatch found ❌"
    return summary, flags

@app.route("/", methods=["GET", "POST"])
def index():
    result, error = None, None
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    if request.method=="POST":
        pan_file = request.files.get("pan_document")
        other_files = request.files.getlist("other_documents")

        if not pan_file or pan_file.filename=="":
            error = "Please upload your PAN card (mandatory)."
        elif not allowed_file(pan_file.filename):
            error = "PAN card must be PDF, TXT, or image (PNG/JPG/JPEG)."
        elif len(other_files)<1:
            error = "Please upload at least one other document for verification."
        else:
            invalid_files = [f.filename for f in other_files if not allowed_file(f.filename)]
            if invalid_files:
                error = f"Unsupported file type(s): {', '.join(invalid_files)}"
            else:
                try:
                    pan_path = os.path.join(UPLOAD_FOLDER, pan_file.filename)
                    pan_file.save(pan_path)
                    pan_info = extract_info_pan(extract_text(pan_path))

                    other_infos = []
                    for f in other_files:
                        if f.filename=="":
                            continue
                        path = os.path.join(UPLOAD_FOLDER, f.filename)
                        f.save(path)
                        other_infos.append(extract_info(extract_text(path)))

                    summary, flags = verify_with_pan(pan_info, other_infos)
                    result = {"pan_info": pan_info, "other_docs": other_infos, "summary": summary, "flags": flags}
                finally:
                    # delete all files and recreate folder
                    files = glob.glob(os.path.join(UPLOAD_FOLDER, "*"))
                    for file_path in files:
                        try: os.remove(file_path)
                        except: pass
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    return render_template("index.html", result=result, error=error)

if __name__=="__main__":
    app.run(debug=True)
