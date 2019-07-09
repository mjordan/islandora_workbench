def clean_csv_values(row):
    """Strip whitespace, etc. from row values.
    """
    for field in row:
        row[field] = row[field].strip()
    return row
