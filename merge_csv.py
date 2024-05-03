import csv

def merge_csv(file1, file2):
    with open(file1, 'r', newline='', encoding='utf-8') as f1, open(file2, 'r', newline='', encoding='utf-8') as f2:
        reader1 = csv.DictReader(f1)
        reader2 = csv.DictReader(f2)

        unique_rows = set()

        for row in reader1:
            unique_rows.add(tuple(row.items()))

        for row in reader2:
            unique_rows.add(tuple(row.items()))

    merged_file = 'merged.csv'
    with open(merged_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(reader1.fieldnames)
        for row in unique_rows:
            writer.writerow(dict(row).values())

    return merged_file
