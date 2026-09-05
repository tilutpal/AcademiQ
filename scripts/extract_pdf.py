import csv

input_file = "output/semester2_data.csv"
output_file = "output/semester2_clean.csv"

with open(input_file, "r", encoding="utf-8-sig", newline="") as infile:

    reader = csv.reader(infile)
    rows = list(reader)


# Find the actual header row
header_index = None

for i, row in enumerate(rows):

    if not row:
        continue

    # Look for the registration number column
    if any(
        cell.strip().lower() in ["regn. no.", "regn no.", "regn. no"]
        for cell in row
    ):
        header_index = i
        break


if header_index is None:
    raise ValueError("Could not find the header row.")


# Original header
original_header = rows[header_index]


# Remove SlNo column
header = original_header[1:]


clean_rows = []


# Process rows after the header
for row in rows[header_index + 1:]:

    # Skip empty rows
    if not row:
        continue

    # Skip repeated header rows
    if any(
        cell.strip().lower() in ["slno", "sl no"]
        for cell in row[:2]
    ):
        continue

    # Skip rows where second column is Regn. No.
    if len(row) > 1:
        second_column = row[1].strip().lower()

        if second_column in ["regn. no.", "regn no.", "regn. no"]:
            continue

    # Remove SlNo
    row_without_slno = row[1:]

    clean_rows.append(row_without_slno)


# Write cleaned CSV
with open(output_file, "w", encoding="utf-8", newline="") as outfile:

    writer = csv.writer(outfile)

    # Write dynamic header
    writer.writerow(header)

    # Write student data
    writer.writerows(clean_rows)


print("Cleaning completed!")
print(f"Total student rows: {len(clean_rows)}")
print(f"Total columns: {len(header)}")
print(f"Subjects/data columns preserved: {len(header) - 1}")
print(f"Saved to: {output_file}")