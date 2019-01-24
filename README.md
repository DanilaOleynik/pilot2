# PanDA Pilot 2

## Contributions

1. Check the ``TODO.md`` and ``STYLEGUIDE.md`` files.

2. Fork the ``PanDAWMS/pilot2`` repository into your private account as ``origin``. Clone it and set the ``PanDAWMS/pilot2`` repository as ``upstream``.

3. Make new code contributions only to a new branch in your repository, push to ``origin`` and make a pull request into ``upstream``. Depending on the type of contribution this should go against either ``upstream/master``, ``upstream/next`` or ``upstream/hotfix``.

## Verifying code correctness

Do not submit code that does not conform to the project standards. We use PEP8 and Flake verification, with everything enabled at a maximum line length of 160 characters and McCabe complexity 12:

    flake8 pilot.py pilot/

For Python 2.6 you need to install ``flake8<3.0.0``, which can miss a few things. Check the output of TravisCI to verify if you have to use this old version.

## Running the pilot

The pilot is a dependency-less Python application and relies on ``/usr/bin/env python``. The minimum pilot can be called like:

    ./pilot.py -q <PANDA_QUEUE> -r <PANDA_RESOURCE> -s <PANDA_SITE>

where ``QUEUE_NAME`` correspond to the ATLAS PandaQueue as defined in AGIS etc. This will launch the default ``generic`` workflow.

## Running the testcases

The test cases are implemented as standard Python unittests under directory ``pilot/test/``. They can be discovered and executed automatically:

    unit2 -v

## Building and viewing docs

1. Install ``sphinx`` into your environment by ``pip`` or other means with all the necessary requirements.

2. Navigate into ``./doc`` in your fork and run ``make html``.

3. Open ``_build/html/index.html`` with your browser.

### Automate documentation to your module

Add the following lines somewhere in the documentation:

    .. automodule:: your.module
        :members:

For more info, visit http://sphinx-doc.org

### Syncing your GitHub repository

Before making a pull request, make sure that you are synced to the latest version.

1. git clone https://github.com/USERNAME/pilot2.git
2. cd pilot2
3. git checkout next
4. git remote -v
5. git remote add upstream https://github.com/PanDAWMS/pilot2.git
6. git fetch upstream
7. git merge upstream/next

# HPC workflow in Pilot2 

HPC workflow is a special mode of Pilot2 when the application works without a remote connection to PanDA server or other 
remote facilities. All intercommunication in this case managed by Harvester application. Also, in this mode Pilot2 acts 
like simple MPI application, which performs execution of multiple jobs on computing nodes of HPC. 

### How to launch HPC workflow

To launch HPC workflow in Pilot2 commandline parameter '-w generic_hpc' should be specified. 

### HPC PlugIns

Different HPC may require special treatments for preparation of launching of payload. To cover this, implementations were 
placed into HPC specific plugin.
The particular plugin should be specified through the command line parameter: '--hpc-resource'

### Mandatory functions in HPC Plugin

get_job(communication_point) - retrieve job description and fill Job object (usually from json file)

set_job_workdir(job, communication_point) - set job/pilot working directory

get_setup() return list of setup commands, which may be required by infrastructure

set_scratch_workdir() - setup working directory on transient high-speed storage (RAM disk, local SSD etc)

command_fix() - adapt some payload parameters for execution on particular infrastructure

process_jobreport() - shrink job report file and copy to working directory from scratch if needed

postprocess_workdir() - some post processing of working directory (if needed)