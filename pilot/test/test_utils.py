#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Authors:
# - Paul Nilsson, paul.nilsson@cern.ch

import unittest

from pilot.util.workernode import collect_workernode_info, get_disk_space_for_dispatcher


class TestUtils(unittest.TestCase):
    """
    Unit tests for utils functions.
    """

    def test_collect_workernode_info(self):
        """
        Make sure that collect_workernode_info() returns the proper types (float, float).

        :return: (assertion)
        """

        mem, cpu = collect_workernode_info()

        self.assertEqual(type(mem), float)
        self.assertEqual(type(cpu), float)

        self.assertNotEqual(mem, 0.0)
        self.assertNotEqual(cpu, 0.0)

    def test_get_disk_space_for_dispatcher(self):
        """
        Verify that get_disk_space_for_dispatcher() returns the proper type (int).

        :return: (assertion)
        """

        queuedata = {'maxwdir': 123456789}
        diskspace = get_disk_space_for_dispatcher(queuedata)

        self.assertEqual(type(diskspace), int)