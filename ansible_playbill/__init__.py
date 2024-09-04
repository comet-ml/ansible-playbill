# pylint: disable-all
"""ansible_playbill"""
# -*- coding: utf-8 -*-

import threading
import time
import os
import sys

from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional, Callable, Iterable

import ansible_runner
import yaml

# We first define a type variable YAMLTypes so that we can use it recursively
# in the definition of the Union below. We then define the Union of all the
# types that can be used in YAML.
YAMLTypes = Union[
    str, int, float, bool, None, Dict[str, "YAMLTypes"], List["YAMLTypes"]
]


class AnsibleRunnerException(Exception):
    """AnsibleRunnerException."""


@dataclass
class PlaybookConfig:
    """PlaybookConfig."""

    playbook_paths: Union[str, List[str]]
    extra_var_files: List[str] = field(default_factory=list)
    extra_vars: Dict[str, YAMLTypes] = field(default_factory=dict)


class AnsibleRunner:
    """AnsibleRunner."""

    __runner_lock = threading.Lock()

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        playbook_root: str = "",
        global_vars_files: List[str] = [],
        global_vars: Dict[str, YAMLTypes] = {},
        playbooks: List[PlaybookConfig] = [],
        debug: bool = False,
        log_prefix: str = "/tmp",
        ansible_bin_path: Optional[str] = os.path.join(sys.prefix, 'bin'),
        event_handler: Optional[Callable[[dict], bool]] = None,
    ):
        """Constructor.

        Args:
            self:
            playbook_root (str): playbook_root
            global_vars_files (List[str]): global_vars_files
            global_vars (Dict[str, YAMLTypes]): global_vars
            playbooks (List[PlaybookConfig]): playbooks
            debug (bool): debug
            log_prefix (str): log_prefix
            ansible_bin_path (Optional[str]): ansible_bin_path
            event_handler (Optional[Callable[[dict], bool]]): event_handler
        """
        self.playbook_root = playbook_root
        self.global_vars_files = global_vars_files
        self.global_vars = global_vars
        self.playbooks = playbooks
        self.debug = debug
        self.log_prefix = log_prefix
        self.ansible_bin_path = ansible_bin_path
        self.__events: List[Iterable[dict]] = []
        self.__tasks_processed: int = 0
        if event_handler is None:
            self.event_handler = self.get_default_event_handler()
        else:
            self.event_handler = event_handler

    def _parse_vars_file(self, path: str) -> Dict[str, YAMLTypes]:
        """_parse_vars_file.

        Args:
            self:
            path (str): path

        Returns:
            Dict[str, YAMLTypes]:

        Raises:
            AnsibleRunnerException: If unable to parse any vars files.
        """
        try:
            with open(path, "r", encoding='utf-8') as file:
                file_vars: Dict[str, YAMLTypes] = yaml.safe_load(file)
                return file_vars
        except FileNotFoundError as ex:
            raise AnsibleRunnerException(f"File not found: {path}") from ex
        except yaml.YAMLError as ex:
            raise AnsibleRunnerException(f"YAML error in file: {path}") from ex

    def _collate_playbook_confg(
        self,
        playbook: PlaybookConfig,
    ) -> PlaybookConfig:
        """_collate_playbook_confg.

        Args:
            self:
            playbook (PlaybookConfig): playbook

        Returns:
            PlaybookConfig:
        """
        extra_vars = {}
        extra_vars.update(self.global_vars)
        extra_vars.update(playbook.extra_vars)
        extra_vars_files = []
        extra_vars_files.extend(self.global_vars_files)
        extra_vars_files.extend(playbook.extra_var_files)
        for path in extra_vars_files:
            extra_vars.update(self._parse_vars_file(path))
        return PlaybookConfig(
            playbook_paths=playbook.playbook_paths,
            extra_vars=extra_vars,
            extra_var_files=[],
        )

    def get_default_event_handler(self) -> Callable[[dict], bool]:
        """get_default_event_handler.

        Args:
            self:

        Returns:
            Callable[[dict], bool]:
        """
        def default_event_handler(event: dict) -> bool:
            if event.get("stdout", "").startswith("TASK"):
                self.__tasks_processed += 1
            return True
        return default_event_handler

    @property
    def events(self) -> Iterable[dict]:
        """events.

        Args:
            self:

        Returns:
            Iterable[dict]:
        """
        while len(self.__events) == 0:
            if not self.__runner_lock.locked():
                raise AnsibleRunnerException(
                    "No events available yet. Run a playbook first."
                )
            continue
        for run_events in self.__events:
            for event in run_events:
                yield event

    @property
    def tasks_processed(self) -> int:
        """tasks_processed.

        Args:
            self:

        Returns:
            int:
        """
        return self.__tasks_processed

    def run(
        self,
        playbook: PlaybookConfig,
        verbosity: int = 0,
        collate_playbook_config: bool = True,
    ) -> None:
        """run.

        Args:
            self:
            playbook (PlaybookConfig): playbook
            verbosity (int): verbosity
            collate_playbook_config (bool): collate_playbook_config

        Returns:
            None:

        Raises:
            AnsibleRunnerException: If unable to run ansible or and ansible
                run fails.
        """
        if self.__runner_lock.locked():
            raise AnsibleRunnerException("Ansible runner is already running")

        with self.__runner_lock:
            if collate_playbook_config:
                playbook = self._collate_playbook_confg(playbook)

            now = time.strftime("%Y%m%d-%H%M%S")
            os.environ[
                "ANSIBLE_LOG_PATH"
            ] = os.path.join(self.log_prefix, f"ansible-runner-{now}.log")

            quiet: bool = False
            if not self.debug:
                quiet = True

            try:
                run_conf = ansible_runner.RunnerConfig(
                    private_data_dir=self.playbook_root,
                    playbook=playbook.playbook_paths,
                    extravars=playbook.extra_vars,
                    host_pattern="localhost",
                    verbosity=verbosity,
                    quiet=quiet,
                )
                run_conf.prepare()
                # We need to prepend the executable with its absolute path so
                # that ansible-runner can find the bundled ansible executable.
                if self.ansible_bin_path:
                    run_conf.command[0] = f"{self.ansible_bin_path}/{run_conf.command[0]}"  # noqa: E501
                # Reset the environment variables magic that ansible_runner
                # tries to do. We want to use the environment variables as is.
                run_conf.env = os.environ.copy()
                runner = ansible_runner.Runner(
                    config=run_conf,
                    event_handler=self.event_handler,
                )
                self.__events.append(runner.events)
                runner.run()
            except Exception as ex:
                raise AnsibleRunnerException("Failed to run ansible") from ex
            if runner.status != "successful":
                raise AnsibleRunnerException("Ansible playbook fail")

    def run_all(self) -> None:
        """run_all.

        Args:
            self:

        Returns:
            None:
        """
        self.__tasks_processed = 0
        for playbook in self.playbooks:
            # When running multiple playbook runs, we want to collate all
            # the configs prior to performing the runs to fail fast if any
            # of the configs are invalid.
            playbook = self._collate_playbook_confg(playbook)
            self.run(playbook, collate_playbook_config=False)
