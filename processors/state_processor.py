import re
import csv
import random
import string
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path


# --- STEP 2: Build W2 SSN Index (unchanged) ---
def build_w2_index(w2_path: Path):
    """Build {SSN_digits_only → (pdf_path, first_page_index)} index for all W2 files."""
    index = {}
    for w2_file in sorted(w2_path.glob("*.pdf")):
        try:
            reader = PdfReader(str(w2_file))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                ssn_matches = re.findall(r"\d{3}-\d{2}-\d{4}", text)
                for match in ssn_matches:
                    ssn_digits = match.replace("-", "")
                    if len(ssn_digits) == 9 and ssn_digits not in index:
                        index[ssn_digits] = (w2_file, i)
            print(f"📄 Indexed {len(index)} total entries so far from {w2_file.name}")
        except Exception as e:
            print(f"⚠️ Failed to index {w2_file.name}: {e}")
    print(f"🔍 Total W2 entries: {len(index)}")
    return index


# --- STEP 3: Random filename helper ---
def generate_random_filename(first: str, last: str) -> str:
    rand_digits = ''.join(random.choices(string.digits, k=6))
    return f"{last}_{first}_{rand_digits}.pdf"


# --- NEW HELPER: Load CSV/XLSX data (no header, use column index) ---
def load_people_data(used_people_dir: Path):
    """
    Load all CSV/XLSX files from used_people_dir.
    No headers → use column index:
        0: first_name, 1: last_name, 8: zip_code, 9: ssn, 39: state_filename
    Return a list of unique person dicts.
    """
    people = []

    for file in used_people_dir.glob("*"):
        try:
            if file.suffix.lower() == ".csv":
                with open(file, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) <= 39:
                            continue
                        people.append({
                            "first_name": str(row[0]).strip(),
                            "last_name": str(row[1]).strip(),
                            "zip_code": str(row[8]).strip(),
                            "ssn": str(row[9]).strip(),
                            "state_filename": str(row[39]).strip()
                        })

            elif file.suffix.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(file, header=None)
                for _, row in df.iterrows():
                    if len(row) <= 39:
                        continue
                    people.append({
                        "first_name": str(row[0]).strip(),
                        "last_name": str(row[1]).strip(),
                        "zip_code": str(row[8]).strip(),
                        "ssn": str(row[9]).strip(),
                        "state_filename": str(row[39]).strip()
                    })
        except Exception as e:
            print(f"⚠️ Failed to load {file.name}: {e}")

    # Remove duplicates
    unique_people = {
        (p["first_name"], p["last_name"], p["ssn"], p["zip_code"]): p
        for p in people
    }
    final_people = list(unique_people.values())

    print(f"📋 Loaded {len(final_people)} unique records from {used_people_dir}")
    return final_people


# --- STEP 4: Updated main process ---
def attach_w2_to_stfcs(company_path: Path, state_path: Path, w2_path: Path, used_people: Path):
    """
    Process STFCS files using data from CSV/XLSX:
      - Use first, last, zip, ssn, and state_filename from files
      - Find matching W2 using SSN
      - Remove first two pages from STFCS
      - Append first page from matching W2
      - Save merged file into state_path as Last_First_######.pdf
    """
    state_path.mkdir(exist_ok=True)
    w2_index = build_w2_index(w2_path)
    people = load_people_data(used_people)

    for person in people:
        first = str(person["first_name"]).title()
        last = str(person["last_name"]).title()
        zip_code = str(person["zip_code"]).strip()
        ssn = re.sub(r"\D", "", str(person["ssn"]).strip())  # digits only
        filename = str(person["state_filename"]).strip()

        if not all([first, last, ssn, filename]):
            print(f"⚠️ Skipping incomplete record: {person}")
            continue

        # Find matching STFCS file in company_path subfolders
        pdf_path = None
        for subfolder in sorted(company_path.iterdir()):
            if not subfolder.is_dir():
                continue
            candidate = subfolder / filename
            if candidate.exists():
                pdf_path = candidate
                break

        if not pdf_path:
            print(f"⚠️ STFCS file not found for {first} {last} ({filename})")
            continue

        if ssn not in w2_index:
            print(f"⚠️ No W2 found for SSN {ssn}, skipping {first} {last}")
            continue

        try:
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()

            # Remove first page
            for page in reader.pages[1:]:
                writer.add_page(page)

            # Append first page from W2
            w2_file, w2_page_idx = w2_index[ssn]
            w2_reader = PdfReader(str(w2_file))
            writer.add_page(w2_reader.pages[w2_page_idx])
            print(f"➕ Attached W2 page for {first} {last} (SSN: {ssn}) from {w2_file.name}")

            # Save merged file
            output_filename = generate_random_filename(first, last)
            output_path = state_path / output_filename
            with open(output_path, "wb") as f:
                writer.write(f)

            print(f"✅ Saved merged file: {output_filename}")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
