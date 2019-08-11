# -*- coding: utf-8 -*-
#
# Copyright 2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.

import sqlite3
import shutil
import subprocess
import signal
import sys
import time
import os
import logging
import random

HOME_DIR = os.path.expanduser('~')
YARELY_PROJ_DIR = os.path.join(HOME_DIR, "proj")
YARELY_LOG_DIR = os.path.join(YARELY_PROJ_DIR, "yarely-local", "logs")
YARELY_CDS_PATH = os.path.join(
    YARELY_PROJ_DIR, "yarely-local", "config", "benchmark.xml"
)
BENCHMAKR_LOG_PATH = os.path.join(YARELY_LOG_DIR, "yarely_core_scheduling_manager.py.log")  # FIXME
BENCHMARK_INTERVALS = list(range(1, 501, 1))
DEFAULT_ITERATIONS = 30

IMAGES_PATH = os.path.join(os.path.sep, "tmp")

CDS_XML_HEADER = '<?xml version="1.0"?>'
CDS_ROOT = (
    '<content-set name="random files" type="inline">{inline}</content-set>'
)
CDS_CHILD = (
    '<content-set name="random_image_{number}" type="inline">'
    '<content-item content-type="image/jpeg">'
    '<requires-file>'
    '<hashes/>'
    '<sources>'
    '<uri>'
    'file://{path}/random_image_{number}.jpeg'
    '</uri>'
    '</sources>'
    '</requires-file>'
    '</content-item>'
    '</content-set>'
)
CDS_PATH = "cds_random_images_{}.xml"

# SQLite commands
CREATE_CONTEXT_TABLE = (
    "CREATE TABLE IF NOT EXISTS {table} ("
    "context_id INTEGER PRIMARY KEY, created DATETIME DEFAULT "
    "CURRENT_TIMESTAMP, context_type TEXT, content_item_xml TEXT)"
)
INSERT_CONTEXT_RECORD = (
    "INSERT INTO {table} (context_type, content_item_xml) "
    "VALUES ('{context_type}', '{content_item_xml}')"
)
CONTEXT_TYPE_PAGEVIEW = 'pageview'
CONTEXT_STORE_PATH = '/tmp/yarely_context_store.sqlite'
CONTEXT_TABLE_NAME = 'context_store'

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger_handlers = {
    # handler: format string
    logging.StreamHandler(sys.stdout): '%(levelname)s - %(message)s',
}

for logger_handler, format_str in logger_handlers.items():
    logger_handler.setLevel(logging.INFO)
    logger_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(logger_handler)


def generate_context_store(num_of_items):
    os.remove(CONTEXT_STORE_PATH)

    open(CONTEXT_STORE_PATH, 'a').close()
    db_connection = sqlite3.connect(CONTEXT_STORE_PATH)

    with db_connection:
        db_connection.executescript(CREATE_CONTEXT_TABLE.format(
            table=CONTEXT_TABLE_NAME
        ))

    db_cursor = db_connection.cursor()

    items = list()
    for i in range(num_of_items):
        tmp = CDS_CHILD.format(number=i, path=IMAGES_PATH)
        items.append(tmp)

    with db_connection:
        for i in range(1001):
            tmp = random.choice(items)
            sql = INSERT_CONTEXT_RECORD.format(
                context_type=CONTEXT_TYPE_PAGEVIEW,
                content_item_xml=tmp,
                table=CONTEXT_TABLE_NAME
            )
            db_cursor.execute(sql)

    db_cursor.close()
    db_connection.close()


def copy_benchmark_log(num_of_items):
    """ Copy the benchmark log and rename it. """
    dest = BENCHMAKR_LOG_PATH + ".{}".format(num_of_items)
    shutil.copyfile(BENCHMAKR_LOG_PATH, dest)


def empty_benchmark():
    """ Delete the content of benchmark.log. """
    with open(BENCHMAKR_LOG_PATH, 'w'):
        pass


def generate_cds(number_of_elements):
    content_sets = ''

    for i in range(number_of_elements):
        tmp = CDS_CHILD.format(number=i, path=IMAGES_PATH)
        content_sets += tmp

    xml_output = CDS_XML_HEADER + '\n'
    xml_output += CDS_ROOT.format(inline=content_sets)
    return xml_output


def get_current_iteration():
    """ Get the current iteration from benchmark log and return it. """

    # Check if the file exists first. If not we assume that we have just
    # started Yarely and the benchmark log wasn't created yet.
    if not os.path.isfile(BENCHMAKR_LOG_PATH):
        return 0

    with open(BENCHMAKR_LOG_PATH, 'r') as f:
        reversed_file = reversed(f.readlines())

    for entry in reversed_file:
        if "start_iteration" not in entry:
            continue

        # Return the first occurence and typecast it to integer.
        return int(entry.split()[4])

    return 0


def kill_processes_by_name(process_name):
    """ Kill all processes that contain process_name """

    cmd = "pgrep -u yarely -f {}".format(process_name)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    print(p.pid)

    out, err = p.communicate()
    # Get our list of processes. We don't want empty lines in it.
    out = out.decode('utf-8')
    processes = [n.split() for n in out.split('\n') if n]

    # Kill all processes now
    for process in processes:
        # The PID is always at the very beginning. This one we will kill.
        logger.info("Trying to kill {}".format(process))
        pid = int(process[0])

        # Make sure we don't kill subprocess.
        if pid == p.pid:
            logger.info("Ignoring PID {}.".format(pid))
            continue

        if pid == os.getpid():
            logger.info("Ignoring our own PID {}.".format(os.getpid()))
            continue

        # If we get OSError, then the process was probably killed already.
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as err:
            logger.error(err)
            continue


def main():

    # Make sure there is no Yarely running
    kill_processes_by_name('python3')

    for num_of_items in BENCHMARK_INTERVALS:
        logger.info("Doing {} items now.".format(num_of_items))

        # Empty the benchmark log
        empty_benchmark()

        # Get the CDS as string with the number of items
        cds_string = generate_cds(num_of_items)

        # And write it to the XML
        write_cds(cds_string)

        # Generate context store
        generate_context_store(num_of_items)

        # Start Yarely and run until we have all iterations. This will block
        # here.
        run_until(DEFAULT_ITERATIONS)

        # Copy the log as soon as we're done.
        copy_benchmark_log(num_of_items)


def run_until(iterations):
    """ Run until we have our number of iterations. """

    logger.info("Run Yarely until {} iterations.".format(iterations))

    start_yarely()

    # Wait until we have enough iterations.
    while get_current_iteration() <= iterations:
        time.sleep(2)
        pass

    logger.info("Stopping at iteration {}".format(get_current_iteration()))
    kill_processes_by_name('yarely')


def start_yarely():
    # We won't start the display controller as we don't have one anyway

    start_script = os.path.join(
        YARELY_PROJ_DIR, "start_yarely_for_benchmark.sh &"
    )
    FNULL = open(os.devnull, 'w')
    p = subprocess.Popen(
        start_script, shell=True, stderr=subprocess.STDOUT, stdout=FNULL
    )
    logger.info("Started Yarely: {}".format(p))


def write_cds(cds_string):
    """ Write cds_string to the default CDS benchmark path. """

    logger.info("Writing new CDS XML.")

    with open(YARELY_CDS_PATH, "w+") as f:
        f.write(cds_string)


if __name__ == '__main__':
    main()
