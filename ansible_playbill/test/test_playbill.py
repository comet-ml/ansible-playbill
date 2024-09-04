# Description: Test cases for the playbill module
# pylint: disable-all
import pytest
import os
import sys
import threading
import time

from .. import AnsibleRunner, PlaybookConfig


def test_ansible_runner():
    runner = AnsibleRunner(
        playbook_root=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'ansible',
        ),
        global_vars={
            "sixteen": "THIS IS SIXTEEN",
        },
        playbooks=[
            PlaybookConfig(
                "play.test.yml",
                extra_vars={
                    "thirtytwo": "THIS IS THIRTYTWO",
                },
            ),
        ],
        debug=False,
        ansible_bin_path=os.path.join(sys.prefix, 'bin'),
    )

    default_event_handler = runner.get_default_event_handler()

    def event_handler(event) -> bool:
        print("handling event!")
        default_event_handler(event)
        return True
    runner.event_handler = event_handler

    failure_sentinel = threading.Event()
    ex = None

    def run_runner():
        global ex
        try:
            runner.run_all()
        except Exception as e:
            failure_sentinel.set()
            ex = e

    thread = threading.Thread(target=run_runner)
    thread.start()
    time.sleep(1)
    for e in runner.events:
        if e['stdout'].startswith("TASK"):
            print(e)
    thread.join()
    if failure_sentinel.is_set():
        pytest.fail(str(ex))

    expected_tasks_processed = 29
    print(
        f"Tasks Processed: {runner.tasks_processed}/{expected_tasks_processed}"
    )
    assert runner.tasks_processed == expected_tasks_processed
