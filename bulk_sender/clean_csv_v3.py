import csv
import io
import argparse
import sys

def restore_csv(input_path: str, output_path: str):
    print(f"--- Starting restoration of: '{input_path}' ---")
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as input_f, \
             open(output_path, 'w', encoding='utf-8', newline='') as output_f:

            csv_writer = csv.writer(output_f, quoting=csv.QUOTE_MINIMAL)
            processed_lines = 0

            for i, line in enumerate(input_f):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]

                sanitized_string = line.replace('""', '"')
                string_io = io.StringIO(sanitized_string)
                csv_reader = csv.reader(string_io)

                for fields in csv_reader:
                    csv_writer.writerow(fields)
                    processed_lines += 1

            print(f"✅ Restoration complete. Processed {processed_lines} lines.")
            print(f"   Clean file saved to: '{output_path}'")

    except FileNotFoundError:
        print(f"❌ FATAL: Input file not found at '{input_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FATAL: An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restores a severely malformed CSV file.")
    parser.add_argument("input_file", help="Path to the corrupted CSV file.")
    parser.add_argument("output_file", help="Path to save the clean CSV file.")
    args = parser.parse_args()
    restore_csv(args.input_file, args.output_file)