import os
import re
from functools import reduce


# Function to process files based on the regex
def process_files(regex, directory="."):
    # Compile the regex pattern
    pattern = re.compile(regex)

    # Iterate over files in the specified directory
    for filename in os.listdir(directory):
        if pattern.match(filename):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                print(filepath)
                # write_to_new_file(filepath)
                # mod_cmd(filepath)


# Function to read the third line, remove it, and write to a new file
def write_to_new_file(filepath):
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()

        if len(lines) >= 3:
            # Extract the third line
            third_line = lines.pop(2)

            # Construct the new filename
            dir_name, original_name = os.path.split(filepath)
            new_name = re.sub(r"-c(\.csv)$", r"\1", original_name)
            new_filepath = os.path.join(dir_name, new_name)

            # Write the modified content to the new file
            with open(new_filepath, "w") as file:
                file.writelines(lines)

            print(f"Processed file: {filepath} -> {new_filepath}")
        else:
            print(f"File {filepath} has fewer than 3 lines; skipping.")

    except Exception as e:
        print(f"Error processing file {filepath}: {e}")


def write_comma(a, b):
    return "{},{}".format(a, b)


def mod_cmd(filepath):
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()
        cmd_mappings = [
            "INIT",
            "CMD",
            "HO",
            "SOL_HANDLEDUP",
            "SOL_HANDLERW",
            "SOL_INIT_SCHED",
            "SOL_HO",
            "UNKNOWN",
        ]
        newlines = []
        if len(lines) >= 3:
            for line in lines:
                tokens = line.split(",")
                tokens[1] = cmd_mappings[int(tokens[1])]
                newlines.append(reduce(write_comma, tokens))

            with open(filepath, "w") as file:
                file.writelines(newlines)

            print(f"Processed file: {filepath}")
        else:
            print(f"File {filepath} has fewer than 3 lines; skipping.")

    except Exception as e:
        print(f"Error processing file {filepath}: {e}")


# Example usage
# Update the regex pattern and directory as needed
# regex_pattern = r"^.*-c\.csv$"  # Match all original .csv files
regex_pattern = r"^.*trace-[0-9]+\.csv$"
process_files(regex_pattern)
