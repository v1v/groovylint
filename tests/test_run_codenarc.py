# Copyright (c) 2019 Ableton AG, Berlin. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

"""Tests for run_codenarc script."""

import os
import subprocess

from unittest.mock import patch

import pytest

from run_codenarc import (
    CodeNarcViolationsException,
    parse_args,
    parse_xml_report,
    run_codenarc,
)

MOCK_CODENARC_SUMMARY = b'CodeNarc completed: (p1=0; p2=0; p3=0) 6664ms\n'


def _report_file_contents(name):
    with open(_report_file_path(name)) as report_file:
        return report_file.read()


def _report_file_path(name):
    return os.path.join(os.path.dirname(__file__), 'xml-reports', name)


def test_parse_xml_report():
    """Test that parse_xml_report handles a successful report file as expected."""
    parse_xml_report(_report_file_contents('success.xml'))


@pytest.mark.parametrize('report_file, num_violations', [
    ('multiple-violations-multiple-files-2.xml', 5),
    ('multiple-violations-multiple-files.xml', 3),
    ('multiple-violations-single-file.xml', 3),
    ('single-violation-multiple-files.xml', 2),
    ('single-violation-single-file.xml', 1),
])
def test_parse_xml_report_failed(report_file, num_violations):
    """Test that parse_xml_report handles a report file with violations as expected.

    These report files were generated by CodeNarc itself.
    """
    with pytest.raises(CodeNarcViolationsException) as raised_error:
        parse_xml_report(_report_file_contents(report_file))
    assert raised_error.value.num_violations == num_violations


@patch('os.remove')
def test_run_codenarc(remove_mock):
    """Test that run_codenarc exits without errors if CodeNarc ran successfully."""
    with patch('os.path.exists') as path_exists_mock:
        path_exists_mock.return_value = True
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.return_value = subprocess.CompletedProcess(
                args='',
                returncode=0,
                stdout=MOCK_CODENARC_SUMMARY,
            )

            output = run_codenarc(
                args=parse_args(args=[
                    '--codenarc-version',
                    '1.0',
                    '--gmetrics-version',
                    '1.0',
                    '--slf4j-version',
                    '1.0',
                ]),
                report_file=_report_file_path('success.xml'),
            )

    assert _report_file_contents('success.xml') == output


def test_run_codenarc_compilation_failure():
    """Test that run_codenarc raises an error if CodeNarc found compilation errors."""
    with patch('subprocess.run') as subprocess_mock:
        subprocess_mock.return_value = subprocess.CompletedProcess(
            args='',
            returncode=0,
            stdout=b'INFO org.codenarc.source.AbstractSourceCode - Compilation'
                   b' failed because of'
                   b' [org.codehaus.groovy.control.CompilationErrorsException] with'
                   b' message: [startup failed:\n'
                   + MOCK_CODENARC_SUMMARY,
        )

        with pytest.raises(ValueError):
            run_codenarc(args=parse_args(args=[]))


def test_run_codenarc_failure_code():
    """Test that run_codenarc raises an error if CodeNarc failed to run."""
    with patch('subprocess.run') as subprocess_mock:
        subprocess_mock.return_value = subprocess.CompletedProcess(
            args='',
            returncode=1,
            stdout=MOCK_CODENARC_SUMMARY,
        )

        with pytest.raises(ValueError):
            run_codenarc(args=parse_args(args=[]))


def test_run_codenarc_missing_jar():
    """Test that run_codenarc raises an error if a JAR file could not be found.

    Calling run_codenarc with no valid version arguments should result in no files found,
    which should cause _build_classpath to raise.
    """
    with pytest.raises(ValueError) as exception_info:
        run_codenarc(
            args=parse_args(args=[
                '--codenarc-version',
                '6.6.6',
                '--gmetrics-version',
                '6.6.6',
                '--slf4j-version',
                '6.6.6',
            ]),
            report_file='invalid',
        )
    # Ensure that the exception message contained an invalid JAR version
    assert '6.6.6' in str(exception_info.value)


def test_run_codenarc_no_report_file():
    """Test that run_codenarc raises an error if CodeNarc did not produce a report."""
    with patch('subprocess.run') as subprocess_mock:
        subprocess_mock.return_value = subprocess.CompletedProcess(
            args='',
            returncode=0,
            stdout=MOCK_CODENARC_SUMMARY,
        )

        with pytest.raises(ValueError):
            run_codenarc(args=parse_args(args=[]), report_file='invalid')
