import csv
import json


def run(input, output):
    # open TSV file for reading
    with open(input, 'r', encoding='utf-8') as tsv_file:

        # use the csv module to read the TSV file
        reader = csv.DictReader(tsv_file, delimiter='\t')

        # create an empty list to hold the rows
        rows = []

        # iterate over each row in the TSV file
        for row in reader:

            # add the row to the list
            rows.append(row)

    # open JSON file for writing
    with open(output, 'w', encoding='utf-8') as json_file:

        # use the json module to write the JSON file
        json.dump(rows, json_file)
