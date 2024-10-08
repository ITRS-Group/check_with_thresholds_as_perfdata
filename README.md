# check_with_thresholds_as_perfdata

A simple Opsview plugin to append provided thresholds to the output as perfdata.

It's a naive implementation, use with caution. Special cases are not handled.

## Usage

``` shell
usage: check_with_thresholds_as_perfdata.py [-h] [-w WARNING] [-c CRITICAL] -C "COMMAND"

Opsview Plugin Wrapper Script

options:
  -h, --help            show this help message and exit
  -w WARNING, --warning WARNING
                        Warning threshold
  -c CRITICAL, --critical CRITICAL
                        Critical threshold
  -C COMMAND, --command COMMAND
                        Command to execute (double quotes required)

```

* Each threshold is optional, but at least one must be provided.
* Each perfdata metric will be appended with the provided thresholds.
* The label of the perfdata metric will be the original metric name with
  `_warning` or `_critical` appended.
* Perfdata metrics will be sorted in the output.
* The return code of the executed command will be passed through.
* Exceptions will be caught and the return code will be 3 (UNKNOWN).
* The COMMAND should be surrounded by double quotes.

## Example

``` shell
$ ./check_with_thresholds_as_perfdata.py -w 80 -c 90 -C "/bin/echo 'OK - Everything is fine | metric=1;2;3;4'"
OK - Everything is fine | metric_critical=90;;;4 metric_warning=80;;;4 metric=1;2;3;4
```

## License

``` text
Copyright 2024 ITRS Group Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
