# -*- coding: utf-8 -*-
#
# Copyright 2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.

import os
import hashlib
import shutil

PREFIX = "file://"


def get_hashed_filename(filename):
    return hashlib.sha1(filename.encode()).hexdigest()


for filename in os.listdir("."):
    if filename.endswith(".jpeg"):
        abspath = PREFIX + '/tmp/' + filename
        hashed_filename = get_hashed_filename(abspath)
        hashed_filename += '.jpeg'
        shutil.copyfile(filename, hashed_filename)
