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
import numpy
from PIL import Image

IMG_DIR = os.path.join(os.path.sep, 'tmp')
IMG_FILE_NAME = "random_image_{number}.jpeg"

for n in range(1000):
    a = numpy.random.rand(1000, 1000, 3) * 255
    img_name = IMG_FILE_NAME.format(number=n)
    img_path = os.path.join(IMG_DIR, img_name)
    im_out = Image.fromarray(a.astype('uint8')).convert('RGB')
    im_out.save(img_path)
