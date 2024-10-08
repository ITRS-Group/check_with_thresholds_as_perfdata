#!/opt/opsview/python3/bin/python
#
# Copyright 2024 ITRS Group Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run your check command and append warning and critical thresholds as perfdata."""
import argparse
import subprocess
import sys
import shlex
import re


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Opsview Plugin Wrapper Script")
    parser.add_argument("-w", "--warning", type=str, help="Warning threshold")
    parser.add_argument("-c", "--critical", type=str, help="Critical threshold")
    parser.add_argument(
        "-C",
        "--command",
        help="Command to execute (double quotes required)",
        type=str,
        required=True,
    )

    return parser.parse_args()


def execute_command(command):
    """Execute the command and return the result."""
    if command.startswith('"') and command.endswith('"'):
        command = command[1:-1]
    elif command.startswith("'") and command.endswith("'"):
        command = command[1:-1]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, shell=True)
    except FileNotFoundError:
        sys.stderr.write(f"Error: Command not found: {command}\n")
        sys.exit(127)
    except Exception as e:  # pylint: disable=broad-except
        # It's acceptable to have a broad except here
        sys.stderr.write(f"Error: Failed to execute command: {str(e)}\n")
        sys.exit(3)
    return result


def process_command_output(result):
    """Process the command output and return stdout, stderr, and return code."""
    if result.returncode > 2:
        print(result.stdout)
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def extract_perfdata(stdout):
    """Extract performance data from the command output."""
    if "|" in stdout:
        output, perfdata = stdout.split("|", 1)
        perfdata = perfdata.strip()
    else:
        output, perfdata = stdout, ""
    return output, perfdata


def parse_perfdata(perfdata):
    """Parse the performance data and return a list of dictionaries."""
    perfdata_entries = []
    for entry in perfdata.split():
        label, value, uom, warn, crit, min_val, max_val = parse_perfdata_entry(entry)
        if label is not None:
            perfdata_entries.append(
                {
                    "label": label,
                    "value": value,
                    "uom": uom,
                    "warn": warn,
                    "crit": crit,
                    "min": min_val,
                    "max": max_val,
                }
            )
    return perfdata_entries


def parse_perfdata_entry(entry):
    """Parse a single performance data entry and return label, value, uom, warn, crit, min, max."""
    # Extract label and value with optional unit of measurement
    label_value_match = re.match(r"(?P<label>\S+)=(?P<value>\d+(\.\d+)?)(?P<uom>[a-zA-Z%]*)", entry)
    if not label_value_match:
        return None, None, None, None, None, None, None

    label = label_value_match.group("label")
    value = label_value_match.group("value")
    uom = label_value_match.group("uom")

    # Extract warning, critical, min, and max thresholds
    remaining = entry[label_value_match.end() :].lstrip(";")
    warn, crit, min_val, max_val = None, None, None, None
    thresholds = remaining.split(";")
    if len(thresholds) > 0 and thresholds[0]:
        warn = thresholds[0]
    if len(thresholds) > 1 and thresholds[1]:
        crit = thresholds[1]
    if len(thresholds) > 2 and thresholds[2]:
        min_val = thresholds[2]
    if len(thresholds) > 3 and thresholds[3]:
        max_val = thresholds[3]

    return label, value, uom, warn, crit, min_val, max_val


def append_thresholds_to_perfdata(perfdata, parsed_perfdata, warning, critical):
    """Append warning and critical thresholds to the performance data."""
    if not warning and not critical:
        return perfdata

    perfdata_strings = []
    for original_entry in perfdata.split():
        perfdata_strings.append(original_entry)

    for entry in parsed_perfdata:
        label = entry.get("label").replace("'", "")
        uom = entry.get("uom", "")
        min_val = entry.get("min", "")
        max_val = entry.get("max", "")
        min_str = f";{min_val}" if min_val else ";"
        max_str = f";{max_val}" if max_val else ";"

        if warning:
            warning_string = (
                f"'{label}_warning_threshold'={warning}{uom};;{min_str}{max_str}".strip(";")
            )
            perfdata_strings.append(warning_string)

        if critical:
            critical_string = (
                f"'{label}_critical_threshold'={critical}{uom};;{min_str}{max_str}".strip(";")
            )
            perfdata_strings.append(critical_string)

    return " ".join(sorted(perfdata_strings))


def main():
    """Run the plugin command and append warning and critical thresholds as perfdata."""
    args = parse_arguments()

    if not args.warning and not args.critical:
        sys.stderr.write("Error: --warning and/or --critical must be provided\n")
        sys.exit(3)

    result = execute_command(args.command)
    stdout, stderr, return_code = process_command_output(result)
    output, perfdata = extract_perfdata(stdout)

    if not perfdata:
        sys.stderr.write("Error: No performance data found. Got the following output:\n")
        sys.stderr.write(stdout + "\n")
        sys.exit(3)

    perfdata_entries = parse_perfdata(perfdata)

    updated_perfdata = append_thresholds_to_perfdata(
        perfdata, perfdata_entries, args.warning, args.critical
    )

    # Print the output with the updated performance data
    if updated_perfdata:
        print(f"{output}| {updated_perfdata}")
    else:
        print(output)

    # Print stderr if any
    if stderr:
        sys.stderr.write(stderr + "\n")

    # Exit with the same return code as the command
    sys.exit(return_code)


if __name__ == "__main__":
    main()
