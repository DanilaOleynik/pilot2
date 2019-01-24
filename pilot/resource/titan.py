#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Authors:
# - Paul Nilsson, paul.nilsson@cern.ch, 2018
# - Danila Oleynik danila.oleynik@cern.ch, 2018

import logging
import os, stat
import shutil
import sys
import time
import pipes

#from jobdescription import JobDescription
from pilot.info.jobdata import JobData
from pilot.common.exception import FileHandlingFailure
from pilot.util.config import config
from pilot.util.constants import PILOT_PRE_STAGEIN, PILOT_POST_STAGEIN
from pilot.util.disk import disk_usage
from pilot.util.filehandling import read_json, write_json, remove
from pilot.util.mpi import get_ranks_info
from pilot.util.timing import add_to_pilot_timing

logger = logging.getLogger(__name__)


def get_job(harvesterpath):
    """
    Return job description in dictonary and MPI rank (if aplicable)
    :return: job - dictonary with job description, rank
    """
    rank = 0
    job = None
    logger.info("Going to read job defenition from file")

    pandaids_list_filename = os.path.join(harvesterpath, config.Harvester.jobs_list_file)
    if not os.path.isfile(pandaids_list_filename):
        logger.info("File with PanDA IDs is missed. Nothing to execute.")
        return job, rank
    harvesterpath = os.path.abspath(harvesterpath)
    rank, max_ranks = get_ranks_info()
    pandaids = read_json(pandaids_list_filename)
    logger.info('Got {0} job ids'.format(len(pandaids)))
    pandaid = pandaids[rank]
    job_workdir = os.path.join(harvesterpath, str(pandaid))

    logger.info('Rank: {2} with job {0} will have work directory {1}'.format(pandaid, job_workdir, rank))

    job_def_filename = os.path.join(job_workdir, config.Harvester.pandajob_file)
    jobs_dict = read_json(job_def_filename)
    job_dict = jobs_dict[str(pandaid)]
    job = JobData(job_dict)

    return job, rank


def get_setup(job=None):
    """
    Return the resource specific setup.

    :param job: optional job object.
    :return: setup commands (list).
    """

    setup_commands = ['source /ccs/proj/csc108/athena_grid_env/setup.sh',
                      'source $MODULESHOME/init/bash',
                      'tmp_dirname=/tmp/scratch',
                      'tmp_dirname+="/tmp"',
                      'export TEMP=$tmp_dirname',
                      'export TMPDIR=$TEMP',
                      'export TMP=$TEMP',
                      'export LD_LIBRARY_PATH=/ccs/proj/csc108/AtlasReleases/ldpatch:$LD_LIBRARY_PATH',
                      'export ATHENA_PROC_NUMBER=16',
                      'export G4ATLAS_SKIPFILEPEEK=1',
                      'export PANDA_RESOURCE=\"ORNL_Titan_MCORE\"',
                      'export ROOT_TTREECACHE_SIZE=1',
                      'export RUCIO_APPID=\"simul\"',
                      'export RUCIO_ACCOUNT=\"pilot\"',
                      'export CORAL_DBLOOKUP_PATH=/ccs/proj/csc108/AtlasReleases/21.0.15/nfs_db_files',
                      'export CORAL_AUTH_PATH=$SW_INSTALL_AREA/DBRelease/current/XMLConfig',
                      'export DATAPATH=$SW_INSTALL_AREA/DBRelease/current:$DATAPATH',
                      'unset FRONTIER_SERVER',
                      ' ']

    return setup_commands


def set_job_workdir(job, path):
    """
    Point pilot to job working directory (job id)

    :param job: job object
    :param path: local path to harvester acceess point
    :return: job working directory
    """
    work_dir = os.path.join(path, str(job.jobid))
    os.chdir(work_dir)
    cleanup_pathes()

    return work_dir


def set_scratch_workdir(job, work_dir, args):
    """
    Copy input files and some db files to RAM disk

    :param job: job object
    :param work_dir: job working directory (permanent FS)
    :param args:  args dictionary to collect timing metrics
    :return: job working directory in scratch
    """

    scratch_path = config.HPC.scratch
    du = disk_usage(scratch_path)
    logger.info("Scratch dir available space: {0} used: {1}".format(du.free, du.used))
    job_scratch_dir = os.path.join(scratch_path, str(job.jobid))
    for inp_file in job.indata:
        inp_file.scratch_path = job_scratch_dir
    logger.debug("Job scratch path: {0}".format(job_scratch_dir))
    # special data, that should be preplaced in RAM disk
    dst_db_path = 'sqlite200/'
    dst_db_filename = 'ALLP200.db'
    dst_db_path_2 = 'geomDB/'
    dst_db_filename_2 = 'geomDB_sqlite'
    tmp_path = 'tmp/'
    src_file = '/ccs/proj/csc108/AtlasReleases/21.0.15/DBRelease/current/sqlite200/ALLP200.db'
    src_file_2 = '/ccs/proj/csc108/AtlasReleases/21.0.15/DBRelease/current/geomDB/geomDB_sqlite'

    if os.path.exists(scratch_path):
        try:
            add_to_pilot_timing(job.jobid, PILOT_PRE_STAGEIN, time.time(), args)
            logger.debug("Prepare 'tmp' dir in scratch ")
            if not os.path.exists(scratch_path + tmp_path):
                os.makedirs(scratch_path + tmp_path)
            logger.debug("Prepare dst and copy sqlite db files")
            t0 = time.time()
            if not os.path.exists(scratch_path + dst_db_path):
                os.makedirs(scratch_path + dst_db_path)
            shutil.copyfile(src_file, scratch_path + dst_db_path + dst_db_filename)
            logger.debug("")
            sql_cp_time = time.time() - t0
            logger.debug("Copy of squlite files took: {0}".format(sql_cp_time))
            logger.debug("Prepare dst and copy geomDB  files")
            t0 = time.time()
            if not os.path.exists(scratch_path + dst_db_path_2):
                os.makedirs(scratch_path + dst_db_path_2)
            shutil.copyfile(src_file_2, scratch_path + dst_db_path_2 + dst_db_filename_2)
            geomdb_cp_time = time.time() - t0
            logger.debug("Copy of geomDB files took: {0}".format(geomdb_cp_time))
            logger.debug("Prepare job scratch dir")
            t0 = time.time()
            if not os.path.exists(job_scratch_dir):
                os.makedirs(job_scratch_dir)
            logger.debug("Copy input file")
            for inp_file in job.indata:
                logger.debug("Copy: {0} to {1}".format(os.path.join(work_dir, inp_file.lfn), inp_file.scratch_path))
                shutil.copyfile(os.path.join(work_dir, inp_file.lfn), os.path.join(inp_file.scratch_path, inp_file.lfn))
            input_cp_time = time.time() - t0
            logger.debug("Copy of input files took: {0}".format(input_cp_time))
        except IOError as e:
            logger.error("I/O error({0}): {1}".format(e.errno, e.strerror))
            logger.error("Copy to scratch failed, execution terminated':  \n %s " % (sys.exc_info()[1]))
            raise FileHandlingFailure("Copy to RAM disk failed")
        finally:
            add_to_pilot_timing(job.jobid, PILOT_POST_STAGEIN, time.time(), args)
    else:
        logger.info('Scratch directory (%s) dose not exist' % scratch_path)
        return work_dir

    os.chdir(job_scratch_dir)
    logger.debug("Current directory: {0}".format(os.getcwd()))
    true_dir = '/ccs/proj/csc108/AtlasReleases/21.0.15/nfs_db_files'
    pseudo_dir = "./poolcond"
    os.symlink(true_dir, pseudo_dir)
    du = disk_usage(scratch_path)
    logger.info("Scratch dir available space for job: {0} used: {1}".format(du.free, du.used))

    return job_scratch_dir


def process_jobreport(payload_report_file, job_scratch_path, job_communication_point):
    """
    Copy job report file to be aaccesible by Harvester. Shrink job report file
    :param payload_report_file:
    :param job_scratch_path:
    :param job_communication_point:
    """
    src_file = os.path.join(job_scratch_path, payload_report_file)
    dst_file = os.path.join(job_communication_point, payload_report_file)

    try:
        logger.info(
            "Copy of payload report [{0}] to access point: {1}".format(payload_report_file, job_communication_point))
        # shrink jobReport
        job_report = read_json(src_file)
        if 'executor' in job_report:
            for executor in job_report['executor']:
                if 'logfileReport' in executor:
                    executor['logfileReport'] = {}

        write_json(dst_file, job_report)

    except IOError:
        logger.error("Job report copy failed, execution terminated':  \n %s " % (sys.exc_info()[1]))
        raise FileHandlingFailure("Job report copy from RAM failed")


def postprocess_workdir(workdir):
    """
    Postprocesing of working directory. Unlink pathes

    :param workdir: path to directory to be processed
    """
    pseudo_dir = "poolcond"
    try:
        if os.path.exists(pseudo_dir):
            remove(os.path.join(workdir, pseudo_dir))
    except IOError:
        raise FileHandlingFailure("Post processing of working directory failed")


def command_fix(command, job_scratch_dir=""):
    """
    Modifing of payload parameters, to be executed on Titan on RAM disk. Cleanup of some

    :param command:
    :param job_scratch_dir:
    :return:
    """

    subs_a = command.split()
    for i in range(len(subs_a)):
        if i > 0:
            if subs_a[i].startswith("--inputEVNTFile"):
                filename = subs_a[i].split("=")[1]
                subs_a[i] = subs_a[i].replace(filename, os.path.join(job_scratch_dir, filename))

    fixed_command = ' '.join(subs_a)
    fixed_command = fixed_command.strip()
    fixed_command = fixed_command.replace('--DBRelease="all:current"', '')  # avoid Frontier reading
    fixed_command = fixed_command.replace('--DBRelease=all:current', '')

    return fixed_command


def cleanup_pathes(pathprefix="/lustre/"):
    """"
    Cleanup of PATH, LD_PATH etc from entities, which points to shared file system required to reduce IO from traversing
    of python libraries
    """
    path = os.environ['PATH'].split(':')
    for p in path[:]:
        if p.startswith("/lustre/"):
            path.remove(p)
    ppath = os.environ['PYTHONPATH'].split(':')
    for p in ppath[:]:
        if p.startswith("/lustre/"):
            ppath.remove(p)
    ldpath = os.environ['LD_LIBRARY_PATH'].split(':')
    for p in ldpath[:]:
        if p.startswith("/lustre/"):
            ldpath.remove(p)

    os.environ['PATH'] = ':'.join(path)
    os.putenv('PATH', ':'.join(path))
    os.environ['PYTHONPATH'] = ':'.join(ppath)
    os.putenv('PYTHONPATH', ':'.join(ppath))
    os.environ['LD_LIBRARY_PATH'] = ':'.join(ldpath)
    os.putenv('LD_LIBRARY_PATH', ':'.join(ldpath))

    return 0


def get_container_wrap(job, img_path, job_scratch_dir = ""):
    """
    Prepare the command wrapped in singularity container
    :param job:
    :return:
    """
    script_file = os.path.join(job_scratch_dir, 'run_payload.sh')
    setup_cmd = ['#!/bin/bash',
                 'pwd',
                 'export SW_INSTALL_AREA=/atlas_releases/AtlasOffline_21.0.15_x86_64-slc6-gcc49-opt',
                 'source $SW_INSTALL_AREA/AtlasSetup/scripts/asetup.sh 21.0.15 --releasesarea=$SW_INSTALL_AREA --cmakearea=$SW_INSTALL_AREA/sw/lcg/contrib/CMake --gcclocation=$SW_INSTALL_AREA/sw/lcg/releases/gcc/4.9.3/x86_64-slc6',
                 'export CORAL_DBLOOKUP_PATH=$SW_INSTALL_AREA/DBRelease/current/XMLConfig',
                 'export CORAL_AUTH_PATH=$SW_INSTALL_AREA/DBRelease/current/XMLConfig',
                 'export DATAPATH=$SW_INSTALL_AREA/DBRelease/current:$DATAPATH',
                 'export ATHENA_PROC_NUMBER=16',
                 'export G4ATLAS_SKIPFILEPEEK=1']

    #setup_str = ";".join(setup_cmd)

    cmd = " ".join([job.transformation, command_fix(job.jobparams, job_scratch_dir)])
    #cmd = setup_str + ";" + cmd
    container_run = "singularity --verbose exec {0} /bin/bash -c ".format(img_path)

    script_body = "\n".join(setup_cmd)
    script_body = script_body + "\n" + cmd
    logger.debug("Script:\n{0}".format(script_body))

    with open(script_file, 'w') as sf:
        sf.write(script_body)
    #cmd = container_run + pipes.quote(cmd)
    os.chmod(script_file, 0o777)
    cmd = container_run + script_file

    return cmd


def get_payload_command(job, job_scratch_dir=""):
    """
    Return command string to launch

    :param job:
    :return command_str:
    """
    command_str = ""
    img_path = is_container()
    if img_path:
        command_str = get_container_wrap(job, img_path, job_scratch_dir)
    else:
        setup_str = "; ".join(get_setup())
        command_str = " ".join([job.transformation, job.jobparams])
        command_str = command_fix(command_str, job_scratch_dir)
        command_str = setup_str + command_str

    logger.debug("Payload command:\n{0}\n".format(command_str))
    return command_str


def is_container():

    container_path = ""
    try:
        container_path = config.HPC.container
    except:
        pass

    return container_path
