from datetime import datetime
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re

def combine_state_files(state_path: Path, combined_path: Path):
    combined_path.mkdir(exist_ok=True)
    print(f"📁 Ensured combined directory exists: {combined_path}")

    all_files = sorted(state_path.glob("*.pdf"))
    pdf_entries = []

    for file in all_files:
        match = re.match(r'([A-Za-z\-]+)_([A-Za-z]+)_(\d{6})\.pdf$', file.name)
        if match:
            last, first, digits = match.groups()
            pdf_entries.append((file, last.title(), first.title(), int(digits)))
        else:
            print(f"⚠️ Skipped {file.name}: filename pattern mismatch")

    pdf_entries.sort(key=lambda x: x[3])
    total_files = len(pdf_entries)
    print(f"📄 Found {total_files} valid PDF files to combine")

    combined_info = []
    index = 0
    batch_num = 1

    while index < total_files:
        batch_entries = pdf_entries[index:index + 30]
        writer = PdfWriter()
        names_in_batch = []

        print(f"\n🧩 Starting batch {batch_num} with {len(batch_entries)} files")

        for file, last, first, _ in batch_entries:
            try:
                reader = PdfReader(str(file))
                for page in reader.pages:
                    writer.add_page(page)
                names_in_batch.append((last, first))
                print(f"✅ Added {file.name} ({len(reader.pages)} pages) to batch {batch_num}")
            except Exception as e:
                print(f"❌ Skipped {file.name} (unreadable or corrupt): {e}")

        if names_in_batch:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_filename = f"combined_{timestamp}.pdf"
            output_path = combined_path / output_filename

            try:
                print(f"📦 Writing merged file: {output_path}")
                with open(output_path, 'wb') as f_out:
                    writer.write(f_out)
                print(f"✅ Successfully created: {output_filename}")
                combined_info.append({'pdf': output_path, 'names': names_in_batch})
            except Exception as e:
                print(f"💥 Failed to merge batch {batch_num}: {e}")

        index += 30
        batch_num += 1

    print("\n✅ All state files combined successfully (no duplicates).")
    return combined_info
