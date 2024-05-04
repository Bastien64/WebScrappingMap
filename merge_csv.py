import csv

def merge_csv(file1, file2):

    urls_set = set()

    unique_rows = []


    with open(file1, 'r', newline='', encoding='utf-8') as f1:
        reader1 = csv.DictReader(f1)
        for row in reader1:
            url = row['URL']
            if url not in urls_set:
                urls_set.add(url)
                unique_rows.append(row)

  
    with open(file2, 'r', newline='', encoding='utf-8') as f2:
        reader2 = csv.DictReader(f2)
        for row in reader2:
            url = row['URL']
            if url not in urls_set:
                urls_set.add(url)
                unique_rows.append(row)

    merged_file = 'merged.csv'
    with open(merged_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=reader1.fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)

    return merged_file
