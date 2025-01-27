#!/usr/bin/env python3
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

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from check_with_thresholds_as_perfdata import (
    main,
    append_thresholds_to_perfdata,
    parse_arguments,
    parse_perfdata,
)

OK_OUTPUT = "OK - Disk space is sufficient | '/var'=55%;80;90;0;100"
WARNING_OUTPUT = "WARNING - Disk space is NOT sufficient | '/var'=85%;80;90;0;100"
CRITICAL_OUTPUT = "CRITICAL - Disk space is NOT sufficient | '/var'=95%;80;90;0;100"
SINGLE_PART_CMD_LINE_ARGS = [
    "-C",
    (
        "/opt/opsview/monitoringscripts/plugins/check_nrpe"
        "-H"
        "192.168.1.1"
        "-c"
        "linux_stat"
        "-a"
        "-D -w 80 -c 90 -p /var -u %"
    ),
]
DUAL_PART_CMD_LINE_ARGS = [
    "-C",
    (
        "/opt/opsview/monitoringscripts/plugins/check_nrpe"
        "-H"
        "192.168.1.1"
        "-c"
        "linux_stat"
        "-a"
        "-D -w 80 -c 90 -p /tmp -p /var -u %"
    ),
]

TRIPLE_PART_CMD_LINE_ARGS = [
    "-C",
    (
        "/opt/opsview/monitoringscripts/plugins/check_nrpe"
        "-H"
        "192.168.1.1"
        "-c"
        "linux_stat"
        "-a"
        "-D -w 80 -c 90 -p /tmp -p /var -p / -u %"
    ),
]


class TestOpsviewPluginWrapper(unittest.TestCase):

    def test_append_thresholds_to_perfdata(self):
        perfdata_entries = parse_perfdata("'/var'=55%;80;90;0;100")
        updated_perfdata = append_thresholds_to_perfdata(
            "'/var'=55%;80;90;0;100", perfdata_entries, warning="80", critical="90"
        )
        expected_perfdata = (
            "'/var'=55%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100"
        )
        self.assertEqual(updated_perfdata, expected_perfdata)

    def test_append_multiple_thresholds_to_perfdata(self):
        perfdata_entries = parse_perfdata("'/var'=55%;80;90;0;100 '/tmp'=55%;80;90;0;100")
        updated_perfdata = append_thresholds_to_perfdata(
            "'/var'=55%;80;90;0;100 '/tmp'=55%;80;90;0;100",
            perfdata_entries,
            warning="80",
            critical="90",
        )
        expected_perfdata = (
            "'/tmp'=55%;80;90;0;100 "
            "'/tmp_critical_threshold'=90%;;;0;100 "
            "'/tmp_warning_threshold'=80%;;;0;100 "
            "'/var'=55%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100"
        )
        self.assertEqual(updated_perfdata, expected_perfdata)

    def test_append_multiple_thresholds_to_perfdata_with_static_thresholds(self):
        self.maxDiff = None
        perfdata_entries = parse_perfdata("'/var'=55%;75;85;0;100 '/tmp'=55%;75;85;0;100")
        updated_perfdata = append_thresholds_to_perfdata(
            "'/var'=55%;75;85;0;100 '/tmp'=55%;75;85;0;100",
            perfdata_entries,
            warning="75",
            critical="85",
            static=["static_warning_threshold=80", "static_critical_threshold=90"],
        )
        expected_perfdata = (
            "'/tmp'=55%;75;85;0;100 "
            "'/tmp_critical_threshold'=85%;;;0;100 "
            "'/tmp_static_critical_threshold'=90%;;;0;100 "
            "'/tmp_static_warning_threshold'=80%;;;0;100 "
            "'/tmp_warning_threshold'=75%;;;0;100 "
            "'/var'=55%;75;85;0;100 "
            "'/var_critical_threshold'=85%;;;0;100 "
            "'/var_static_critical_threshold'=90%;;;0;100 "
            "'/var_static_warning_threshold'=80%;;;0;100 "
            "'/var_warning_threshold'=75%;;;0;100"
        )
        self.assertEqual(updated_perfdata, expected_perfdata)

    @patch("sys.stderr", new_callable=StringIO)
    @patch("subprocess.run")
    def test_command_not_found(self, mock_subprocess_run, _mock_stderr):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = (
            "Error: Command not found: "
            "/opt/opsview/monitoringscripts/plugins/check_non_existing_plugin\n"
        )
        mock_result.returncode = 127
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as _mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
                "-C",
                '"/opt/opsview/monitoringscripts/plugins/check_non_existing_plugin -H localhost"',
            ]
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 127)

        expected_output = (
            "Error: Command not found: "
            "/opt/opsview/monitoringscripts/plugins/check_non_existing_plugin\n"
        )
        self.assertEqual(expected_output, mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=StringIO)
    @patch("subprocess.run")
    def test_invalid_command_without_perfdata(self, mock_subprocess_run, _mock_stdout):
        mock_result = MagicMock()
        mock_result.stdout = "OK - Disk space is sufficient"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as _mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 3)

        expected_output = (
            "Error: No performance data found. "
            "Got the following output:\n"
            "OK - Disk space is sufficient\n"
        )
        self.assertEqual(expected_output, mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_no_warning_no_critical(self, mock_subprocess_run, mock_stdout):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Error: --warning and/or --critical must be provided"
        mock_result.returncode = 3
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as _mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as mock_stderr:
            test_args = [
                "script_name",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 3)

        expected_output = "Error: --warning and/or --critical must be provided\n"
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_ok_command_output_with_warning_only(self, mock_subprocess_run, mock_stdout):
        mock_result = MagicMock()
        mock_result.stdout = OK_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

        expected_output = (
            "OK - Disk space is sufficient | '/var'=55%;80;90;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_ok_command_output_with_critical_only(self, mock_subprocess_run, mock_stdout):
        mock_result = MagicMock()
        mock_result.stdout = OK_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

        expected_output = (
            "OK - Disk space is sufficient | "
            "'/var'=55%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_ok_command_output_with_both_warning_and_critical(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = OK_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

        expected_output = (
            "OK - Disk space is sufficient | "
            "'/var'=55%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_warning_command_output_with_warning_only(self, mock_subprocess_run, mock_stdout):
        mock_result = MagicMock()
        mock_result.stdout = WARNING_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 1)

        expected_output = (
            "WARNING - Disk space is NOT sufficient | "
            "'/var'=85%;80;90;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_warning_command_output_with_critical_only(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = WARNING_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 1)

        expected_output = (
            "WARNING - Disk space is NOT sufficient | "
            "'/var'=85%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_warning_command_output_with_both_warning_and_critical(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = WARNING_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 1)

        expected_output = (
            "WARNING - Disk space is NOT sufficient | "
            "'/var'=85%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_critical_command_output_with_warning_only(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = CRITICAL_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 2
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 2)

        expected_output = (
            "CRITICAL - Disk space is NOT sufficient | "
            "'/var'=95%;80;90;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_critical_command_output_with_critical_only(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = CRITICAL_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 2
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 2)

        expected_output = (
            "CRITICAL - Disk space is NOT sufficient | "
            "'/var'=95%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_critical_command_output_with_both_warning_and_critical(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = CRITICAL_OUTPUT
        mock_result.stderr = ""
        mock_result.returncode = 2
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + SINGLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 2)

        expected_output = (
            "CRITICAL - Disk space is NOT sufficient | "
            "'/var'=95%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_critical_command_output_with_both_warning_and_critical_and_two_metrics(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = CRITICAL_OUTPUT + " '/tmp'=95%;80;90;0;100"
        mock_result.stderr = ""
        mock_result.returncode = 2
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + DUAL_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 2)

        expected_output = (
            "CRITICAL - Disk space is NOT sufficient | "
            "'/tmp'=95%;80;90;0;100 "
            "'/tmp_critical_threshold'=90%;;;0;100 "
            "'/tmp_warning_threshold'=80%;;;0;100 "
            "'/var'=95%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("subprocess.run")
    def test_valid_critical_command_output_with_both_warning_and_critical_and_three_metrics(
        self, mock_subprocess_run, mock_stdout
    ):
        mock_result = MagicMock()
        mock_result.stdout = "CRITICAL - Disk space is NOT sufficient | '/'=40%;80;90;0;100 '/var'=95%;80;90;0;100 '/tmp'=95%;80;90;0;100"
        mock_result.stderr = ""
        mock_result.returncode = 2
        mock_subprocess_run.return_value = mock_result

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as _mock_stderr:
            test_args = [
                "script_name",
                "-w",
                "80",
                "-c",
                "90",
            ] + TRIPLE_PART_CMD_LINE_ARGS
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 2)

        expected_output = (
            "CRITICAL - Disk space is NOT sufficient | "
            "'/'=40%;80;90;0;100 "
            "'/_critical_threshold'=90%;;;0;100 "
            "'/_warning_threshold'=80%;;;0;100 "
            "'/tmp'=95%;80;90;0;100 "
            "'/tmp_critical_threshold'=90%;;;0;100 "
            "'/tmp_warning_threshold'=80%;;;0;100 "
            "'/var'=95%;80;90;0;100 "
            "'/var_critical_threshold'=90%;;;0;100 "
            "'/var_warning_threshold'=80%;;;0;100\n"
        )
        self.maxDiff = None
        self.assertEqual(expected_output, mock_stdout.getvalue())

    @patch("sys.stderr", new_callable=StringIO)
    def test_invalid_path_of_command_results_in_error(self, mock_stderr):
        mock_result = MagicMock()

        with patch("sys.stdout", new_callable=lambda: sys.stdout) as _mock_stdout, patch(
            "sys.stderr", new_callable=lambda: sys.stderr
        ) as mock_stderr:
            test_args = ["script_name", "-w", "80", "-c", "90", "-C", '"/bin/echo foo"']
            with patch.object(sys, "argv", test_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 3)

        expected_output = (
            "Error: Command MUST start with a path in the "
            "/opt/opsview/monitoringscripts directory\n"
        )
        self.maxDiff = None
        self.assertEqual(expected_output, mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
