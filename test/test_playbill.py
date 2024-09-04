# Description: Test cases for the playbill module
# pylint: disable-all
import os
import sys
import threading

from ansible_playbill import AnsibleRunner, PlaybookConfig


def test_ansible_runner():
    default_event_handler = AnsibleRunner.get_default_event_handler()

    def event_handler(event) -> bool:
        print("handling event!")
        default_event_handler(event)
        return True

    runner = AnsibleRunner(
        playbook_root=os.path.join(os.path.abspath(__file__), 'ansible'),
        global_vars={
            "sixteen": "THIS IS SIXTEEN",
        },
        playbooks=[
            PlaybookConfig(
                playbook="play.test.yml",
                vars={
                    "thirtytwo": "THIS IS THIRTYTWO",
                },
            ),
        ],
        debug=False,
        log_prefix="/tmp",
        ansible_bin_path=str(sys.path[0]),
        event_handler=event_handler,
    )
    thread = threading.Thread(target=runner.run_all)
    thread.start()
    for e in runner.get_events():
        print(e)
    thread.join()
