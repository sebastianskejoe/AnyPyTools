# -*- coding: utf-8 -*-
"""
Utilities for working with the AnyBody Console applicaiton.

Created on Fri Oct 19 21:14:59 2012
@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (ascii, bytes, chr, dict, filter, hex, input,  # noqa
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)

import os
import io
import sys
import time
import copy
import types
import ctypes
import shelve
import atexit
import logging
import collections
from subprocess import Popen
from tempfile import NamedTemporaryFile
from threading import Thread, RLock
from queue import Queue

import numpy as np
from future.utils import text_to_native_str
from past.builtins import basestring as string_types

from .tools import (make_hash, AnyPyProcessOutputList, parse_anybodycon_output,
                    getsubdirs, get_anybodycon_path,
                    AnyPyProcessOutput, run_from_ipython, get_ncpu, silentremove)
from .macroutils import AnyMacro, MacroCommand

try:
    from IPython.display import HTML, display
    import ipywidgets
except ImportError:
    ipywidgets = HTML = display = None


logger = logging.getLogger('abt.anypytools')

_thread_lock = RLock()
_KILLED_BY_ANYPYTOOLS = 10
_NO_LICENSES_AVAILABLE = -22


class _SubProcessContainer(object):
    """Class to hold a record of process pids from Popen.

    Properties
    ----------
    stop_all: boolean
        If set to True all process held by the object will be automatically
        killed

    Methods
    -------
    add(pid):
        Add process id to the record of process

    remove(pid):
        Remove process id from the record

    """

    def __init__(self):
        self._pids = set()
        self._stop_all = False

    def add(self, pid):
        with _thread_lock:
            self._pids.add(pid)
        if self.stop_all:
            self._kill_running_processes()

    def remove(self, pid):
        with _thread_lock:
            try:
                self._pids.remove(pid)
            except KeyError:
                pass

    @property
    def stop_all(self):
        return self._stop_all

    @stop_all.setter
    def stop_all(self, value):
        with _thread_lock:
            if value:
                self._stop_all = True
                self._kill_running_processes()
            else:
                self._stop_all = False

    def _kill_running_processes(self):
        """Clean up and shut down any running processes."""
        # Kill any rouge processes that are still running.
        with _thread_lock:
            killed = []
            for pid in self._pids:
                try:
                    os.kill(pid, _KILLED_BY_ANYPYTOOLS)
                    killed.append(str(pid))
                except:
                    pass
            self._pids.clear()


_subprocess_container = _SubProcessContainer()
atexit.register(_subprocess_container._kill_running_processes)


def _display(line, *args, **kwargs):
    if run_from_ipython():
        display(HTML(line))
    else:
        print(line, *args, **kwargs)


def execute_anybodycon(macro, logfile=None, anybodycon_path=None, timeout=3600,
                       keep_macrofile=False, env=None):
    """Launch a single AnyBodyConsole applicaiton.

    This is a low level function to start a AnyBody Console process
    with a given list macros.

    Parameters
    ----------
    macro : list of str
        List of macros strings to pass to the AnyBody Console Application
    logfile : file like object, optional
        An open file like object to write to pipe the output of AnyBody
        into. (Defaults to None, in which case it will use sys.stdout)
    anybodycon_path : str, optional
        Path to the AnyBodyConsole application. Default to None, in which
        case the default installed AnyBody installation will be looked up
        in the Windows registry.
    timeout : int, optional
        Timeout before the process is killed autmotically. Defaults to
        3600 seconds (1 hour).
    keep_macrofile : bool, optional
        Set to True to prevent the temporary macro file from beeing deleted.
        (Defaults to False)
    env: dict
        Environment varaibles which are passed to the started AnyBody console
        application.

    Returns
    -------
    int
        The return code from the AnyBody Console application.

    """
    if logfile is None:
        logfile = sys.stdout

    try:
        macro_filename = os.path.splitext(logfile.name)[0] + '.anymcr'
    except AttributeError:
        macro_filename = 'macrofile.anymcr'

    if anybodycon_path is None:
        anybodycon_path = get_anybodycon_path()

    if macro and macro[-1] != 'exit':
        macro.append('exit')

    if not os.path.isfile(anybodycon_path):
        raise IOError("Can not find anybodycon.exe: " + anybodycon_path)

    with open(macro_filename, 'w+b') as macro_file:
        macro_file.write('\n'.join(macro).encode('UTF-8'))
        macro_file.flush()
    anybodycmd = [os.path.realpath(anybodycon_path),
                  '--macro=', macro_file.name, '/ni']
    if sys.platform.startswith("win"):
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]
        SEM_NOGPFAULTERRORBOX = 0x0002  # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX)
        subprocess_flags = 0x8000000  # win32con.CREATE_NO_WINDOW?
    else:
        subprocess_flags = 0
    # Check global module flag to avoid starting processes after
    # the user cancelled the processes
    timeout_time = time.clock() + timeout
    proc = Popen(anybodycmd,
                 stdout=logfile,
                 stderr=logfile,
                 creationflags=subprocess_flags,
                 env=env)
    _subprocess_container.add(proc.pid)
    while proc.poll() is None:
        if time.clock() > timeout_time:
            proc.terminate()
            proc.communicate()
            try:
                logfile.seek(0, os.SEEK_END)
            except io.UnsupportedOperation:
                pass
            logfile.write(
                '\nERROR: AnyPyTools : Timeout after {:d} sec.'.format(int(timeout)))
            proc.returncode = 0
            break
        time.sleep(0.05)
    _subprocess_container.remove(proc.pid)
    retcode = ctypes.c_int32(proc.returncode).value
    if retcode == _KILLED_BY_ANYPYTOOLS:
        logfile.write('\nAnybodycon.exe was interrupted by AnyPyTools')
    elif retcode == _NO_LICENSES_AVAILABLE:
        logfile.write('\nERROR: anybodycon.exe existed unexpectedly. '
                      'Return code: '
                      + str(_NO_LICENSES_AVAILABLE)
                      + ' : No license available.')
    elif retcode:
        logfile.write('\nERROR: AnyPyTools : anybodycon.exe exited unexpectedly.'
                      ' Return code: ' + str(retcode))
    if not keep_macrofile:
        silentremove(macro_file.name)
    return retcode


class _Task(object):
    """Class for storing processing jobs.

    Attributes:
        folder: directory in which the macro is executed
        macro: list of macro commands to execute
        number: id number of the task
        name: name of the task, which is used for printing status informations

    """

    def __init__(self, folder=None, macro=None,
                 taskname=None, number=1):
        """Init the Task class with the class attributes."""
        self.folder = folder
        if not folder:
            self.folder = os.getcwd()
        if macro is not None:
            self.macro = macro
        else:
            self.macro = []
        self.output = AnyPyProcessOutput()
        self.number = number
        self.logfile = ""
        self.processtime = 0
        self.name = taskname
        if not taskname:
            head, folder = os.path.split(folder)
            parentfolder = os.path.basename(head)
            self.name = parentfolder + '/' + folder

    @property
    def has_error(self):
        return 'ERROR' in self.output

    def add_error(self, error_msg):
        try:
            self.output['ERROR'].append(error_msg)
        except KeyError:
            self.output['ERROR'] = [error_msg]

    def get_output(self, include_task_info=True):
        out = self.output
        if include_task_info:
            out['task_macro_hash'] = make_hash(self.macro)
            out['task_id'] = self.number
            out['task_work_dir'] = self.folder
            out['task_name'] = self.name
            out['task_processtime'] = self.processtime
            out['task_macro'] = self.macro
            out['task_logfile'] = self.logfile
        return out

    @classmethod
    def from_output_data(cls, task_output):
        if not cls.is_valid(task_output):
            raise ValueError('Output can only be reprocessed, if "Task info"'
                             'is included in the output.')
        task = cls(folder=task_output['task_work_dir'],
                   macro=task_output['task_macro'],
                   taskname=task_output['task_name'],
                   number=task_output['task_id'])
        task.processtime = task_output['task_processtime']
        task.output = task_output
        return task

    @classmethod
    def from_output_list(cls, outputlist):
        for elem in outputlist:
            yield cls.from_output_data(elem)

    @classmethod
    def from_macrofolderlist(cls, macrolist, folderlist):
        if not macrolist:
            raise StopIteration
        macrofolderlist = ((m, f) for f in folderlist for m in macrolist)
        for i, (macro, folder) in enumerate(macrofolderlist):
            yield cls(folder, macro, number=i)

    @staticmethod
    def is_valid(output_elem):
        keys = ('task_macro_hash', 'task_id', 'task_work_dir', 'task_name',
                'task_processtime', 'task_macro', 'task_logfile')
        return all(k in output_elem for k in keys)


class _Summery(object):
    """Class to display the summery of task."""

    def __init__(self, have_ipython=False, silent=False):
        self._silent = silent
        if have_ipython and ipywidgets and not self._silent:
            self.ipywidget = ipywidgets.HTML()
            self.ipywidget.initialized = False
        else:
            self.ipywidget = None

    def task_summery(self, task):
        if self.ipywidget:
            if task.has_error:
                self._display(self.format_summery(task))

    def _display(self, s):
        if self._silent:
            return
        if self.ipywidget is not None:
            if not self.ipywidget.initialized:
                display(self.ipywidget)
                self.ipywidget.initialized = True
            self.ipywidget.value += s + '<br>'
        else:
            print(s)

    def format_summery(self, task):
        entry = ''
        if task.has_error:
            entry += 'Failed :'
        elif task.processtime == 0:
            entry += 'Not completed :'
        else:
            entry += 'Completed :'
        entry += '{1!s} : {2:5.0f} sec : {0} : '.format(task.name,
                                                        task.number,
                                                        task.processtime)
        if task.logfile:
            if run_from_ipython():
                tmpl = '<a href="file:///{0}" target="_blank">{1}</a>'
                entry += tmpl.format(task.logfile,
                                     os.path.basename(task.logfile))
            else:
                entry += '{0}'.format(os.path.basename(task.logfile))
        return entry

    def final_summery(self, total_process_time, tasklist):
        unfinished_tasks = [t for t in tasklist if t.processtime <= 0]
        failed_tasks = [t for t in tasklist
                        if t.has_error and t.processtime > 0]
        if len(failed_tasks):
            self._display('Tasks with errors: {:d}'.format(len(failed_tasks)))
            if self.ipywidget is None:
                self._display('\n'.join([self.format_summery(t)
                                         for t in failed_tasks]))
        if len(unfinished_tasks):
            self._display('Tasks that did not complete: '
                          '{:d}'.format(len(unfinished_tasks)))
        self._display('Total time: {:.1f} seconds'.format(total_process_time))


class AnyPyProcess(object):
    """
    Class for configuring batch process jobs of AnyBody models.

    This is the main interface to control the AnyBody console application from
    python. The class stores all the configuration about how AnyBody is run.
    It has one important method `start_macro` which launches the AnyBody with
    a given anyscript macro.

    Parameters
    ----------
    num_processes : int, optional
        Number of anybody models to start in parallel.
        This defaults to the number of logical CPU cores in the computer.
    anybodycon_path : str, optional
        Overwrite the default anybodycon.exe file to
        use in batch processing. Defaults to what is found in the windows
        registry.
    timeout : int, optional
        Maximum time (i seconds) a model can run until it is terminated.
        Defaults to 3600 sec (1 hour).
    silent : bool, optional
        Set to True to suppress any output such as progress bar and error
        messages. (Defaults to False).
    ignore_errors : list of str, optional
        List of AnyBody Errors substrings to ignore when running the models.
        (Defaults to None)
    warnings_to_include : list of str, optional
        List of strings that are matched to warnings in the model
        output. If a warning with that string is found the warning
        is returned in the output. (Defaults to None)
    return_task_info : bool, optional
        Return the task status information when running macros. Defaults to False.
    keep_logfiles : bool, optional
        If True logfile will never be removed. Even if a simulations successeds
        without error. (Defautls to False)
    logfile_prefix : str, option
        String which will be prefixed to the generated log files. This can be used
        to assign a more meaningfull name to a batch of logfiles.
        (Defaults to None)
    python_env : pathlike, optional
        Path to a python environment/installation that the AnyBody Modeling System
        should use for Python Hooks. This will added the ``PYTHONHOME`` environment variable and
        prepended to the ``PATH`` before starting the AnyBody Console application.
        (Defaults to None, which will use the default Python installation on the computer.)


    Returns
    -------
    AnyPyProcess
        An instance of the AnyPyProcess object for running batch processing,
        parameter studies and pertubation jobs.

    Example
    -------
    The following example shows how to instantiate a AnyPyProcess object.

    >>> app = AnyPyProcess(num_processes=8, return_task_info=True)

    The `app` object has methods for launching macros, saving results etc.

    >>> macro = ['load "MyModel.any"', 'operation Main.MyStudy.Kinematics', 'run']
    >>> app.start_macro(macro)

    """

    def __init__(self,
                 num_processes=get_ncpu(),
                 anybodycon_path=None,
                 timeout=3600,
                 silent=False,
                 ignore_errors=None,
                 warnings_to_include=None,
                 return_task_info=False,
                 keep_logfiles=False,
                 logfile_prefix=None,
                 python_env=None):
        if not isinstance(ignore_errors, (list, type(None))):
            raise ValueError('ignore_errors must be a list of strings')

        if not isinstance(warnings_to_include, (list, type(None))):
            raise ValueError('warnings_to_include must be a list of strings')

        if anybodycon_path is None:
            self.anybodycon_path = get_anybodycon_path()
        elif os.path.exists(anybodycon_path):
            self.anybodycon_path = anybodycon_path
        else:
            raise IOError("Can't find " + anybodycon_path)
        self.num_processes = num_processes
        self.silent = silent
        self.timeout = timeout
        self.counter = 0
        self.return_task_info = return_task_info
        self.ignore_errors = ignore_errors
        self.warnings_to_include = warnings_to_include
        self.keep_logfiles = keep_logfiles
        if logfile_prefix is not None:
            self.logfile_prefix = logfile_prefix + '_'
        else:
            self.logfile_prefix = logfile_prefix
        self.cached_arg_hash = None
        self.cached_tasklist = None
        if python_env is not None:
            if not os.path.isdir(python_env):
                raise IOError('Python environment does not exist:' + python_env)
            env = dict(os.environ)
            env['PYTHONHOME'] = python_env
            env['PATH'] = env['PYTHONHOME'] + ';' + env['PATH']
            self.env = env
        else:
            self.env = None
        logging.debug('\nAnyPyProcess initialized')

    def save_results(self, filename, append=False):
        """Save resently processed results.

        Save results for later reloading or to continue processing unfished
        results at a later time.

        Parameters
        ----------
        filename : str
            filename of the file where processing was stored.
        append : bool
            If true append data to what ever is already saved. This allows
            for saving data in batches.

        Returns
        -------
        None

        Examples
        --------
        >>> macro = ['load "model1.any"', 'operation Main.RunApplication', 'run']
        >>> app.start_macro(macro)
        >>> app.save_results('saved_data.db')

        """
        if self.cached_tasklist:
            savekey = text_to_native_str('processed_tasks')
            db = shelve.open(text_to_native_str(filename), writeback=True)
            if not append or savekey not in db:
                db[savekey] = self.cached_tasklist
            else:
                db[savekey].extend(self.cached_tasklist)
            db.close()
        else:
            raise ValueError('Noting to save')

    def save_to_hdf5(self, filename, batch_name=None):
        """Save cached results to hdf5 file.

        Parameters
        ----------
        filename : str
            filename where data should be stored

        batch_name : str
            Name of the group in the HDF5 file to
            save the data within. If not specified
            the group hash value of the macro will
            be used.

        Returns
        -------
            None

        """
        import h5py

        if not self.cached_tasklist:
            raise ValueError('No data available for saving')

        if batch_name is None:
            batch_name = str(self.cached_arg_hash)

        filename = text_to_native_str(filename)
        batch_name = text_to_native_str(batch_name)

        any_output = AnyPyProcessOutputList([
            task.get_output()
            for task in self.cached_tasklist
        ])
        task_names = [
            elem['task_name']
            for elem in any_output
        ]
        unique_names = len(task_names) == len(set(task_names))
        with h5py.File(filename, "w") as h5file:
            h5_batch_group = h5file.create_group(batch_name)
            for run in any_output:
                task_name = run['task_name'] if unique_names else str(
                    run['task_id'])
                task_name = task_name.replace('/', '|')
                h5_task_group = h5_batch_group.create_group(task_name)
                for k, v in run.items():
                    if not isinstance(v, np.ndarray):
                        if isinstance(v, list):
                            h5_task_group.attrs[text_to_native_str(k)] = text_to_native_str(str(v))
                        else:
                            h5_task_group.attrs[text_to_native_str(k)] = v
                    elif isinstance(v, np.ndarray):
                        h5_task_group.create_dataset(text_to_native_str(k), data=v)

    def load_results(self, filename):
        """Load previously saved results.

        Besides reloading results the function can be used to continue
        a partial finished processing process.

        Parameters
        ----------
        filename : str
            filename of the file where processing was stored.

        Returns
        -------
        list
            A list with the output from each macro executed. This maybe empty
            the macros did not output any data.

        Examples
        --------
        Results are easily reloaded:

        >>> app = AnyPyProcess()
        >>> results = app.load_results('saved_results.db')

        Continue processing unfinished batches:

        >>> app.load_results('unfinished_results.db')
        >>> results = app.start_macro() # rerun unfinished

        """
        loadkey = text_to_native_str('processed_tasks')
        db = shelve.open(text_to_native_str(filename))
        loaded_data = db[loadkey]
        db.close()
        # Hack to help Enrico convert data to the new structured
        if not isinstance(loaded_data[0].output, AnyPyProcessOutput):
            for task in loaded_data:
                task.output = AnyPyProcessOutput(task.output)
        self.cached_tasklist = loaded_data
        results = [task.get_output(True) for task in loaded_data]
        return AnyPyProcessOutputList(results)

    def start_macro(self, macrolist=None, folderlist=None, search_subdirs=None,
                    **kwargs):
        """Start a batch processing job.

        Runs a list of AnyBody Macro commands in
        the current directory, or in the folders specified by `folderlist`. If
        `search_subdirs` is a regular expression the folderlist will be expanded
        to include all subdirectories that match the regular expression

        Parameters
        ----------
        macrolist : list of macrocommands, optional
            List of anyscript macro commands. This may also be obmitted in
            which case the previous macros will be re-run.
        folderlist : list of str, optional
            List of folders in which to excute the macro commands. If `None` the
            current working directory is used. This may also be a list of
            tuples to specify a name to appear in the output
        search_subdirs : str, optional
            Regular expression used to extend the folderlist with all the
            subdirectories that match the regular expression.
            Defaults to None: No subdirectories are included.

        Returns
        -------
        list
            A list with the output from each macro executed. This maybe empty
            the macros did not output any data.


        Examples
        --------
        >>> macro = [['load "model1.any"', 'operation Main.RunApplication', 'run'],
                     ['load "model2.any"', 'operation Main.RunApplication', 'run'],
                     ['load "model3.any"', 'operation Main.RunApplication', 'run']]
        >>> folderlist = [('path1/', 'name1'), ('path2/', 'name2')]
        >>> app.start_macro(macro, folderlist, search_subdirs = "*.main.any")

        """
        # Handle different input types
        if isinstance(macrolist, types.GeneratorType):
            macrolist = list(macrolist)
        if isinstance(macrolist, AnyMacro):
            macrolist = macrolist.create_macros()
        elif isinstance(macrolist, list) and len(macrolist):
            if isinstance(macrolist[0], string_types):
                macrolist = [macrolist]
            if isinstance(macrolist[0], MacroCommand):
                macrolist = [macrolist]
            if isinstance(macrolist[0], list) and len(macrolist[0]):
                if isinstance(macrolist[0][0], MacroCommand):
                    macrolist = [[mc.get_macro(index=0) for mc in elem]
                                 for elem in macrolist]
        elif isinstance(macrolist, string_types):
            if macrolist.startswith('[') and macrolist.endswith(']'):
                macrolist = macrolist.strip('[').rstrip(']')
                macrolist = [macrolist.split(', ')]
            else:
                macrolist = [[macrolist]]
        elif isinstance(macrolist, (type(None), AnyPyProcessOutputList)):
            pass
        else:
            raise ValueError('Wrong input argument for macrolist')
        # Check folderlist input argument
        if not folderlist:
            folderlist = [os.getcwd()]
        if not isinstance(folderlist, list):
            raise TypeError('folderlist must be a list of folders')
        # Extend the folderlist if search_subdir is given
        if (isinstance(search_subdirs, string_types) and
                isinstance(folderlist[0], string_types)):
            folderlist = sum([getsubdirs(d, search_subdirs)
                              for d in folderlist], [])
        # Check the input arguments and generate the tasklist
        if macrolist is None:
            if self.cached_tasklist:
                tasklist = self.cached_tasklist
            else:
                raise ValueError('macrolist argument can only be ommitted if '
                                 'the AnyPyProcess object has cached output '
                                 'to process')
        elif isinstance(macrolist[0], collections.Mapping):
            tasklist = list(_Task.from_output_list(macrolist))
        elif isinstance(macrolist[0], list):
            arg_hash = make_hash([macrolist, folderlist, search_subdirs])
            if self.cached_tasklist and self.cached_arg_hash == arg_hash:
                tasklist = self.cached_tasklist
            else:
                self.cached_arg_hash = arg_hash
                tasklist = list(_Task.from_macrofolderlist(macrolist,
                                                           folderlist))
        else:
            raise ValueError('Nothing to process for ' + str(macrolist))

        self.summery = _Summery(have_ipython=run_from_ipython(),
                                silent=self.silent)

        if self.logfile_prefix is None:
            self.logfile_prefix = str(self.cached_arg_hash)[:4] + '_'

        # Start the scheduler
        process_time = self._schedule_processes(tasklist, self._worker)
        self.cleanup_logfiles(tasklist)
        # Cache the processed tasklist for restarting later
        self.cached_tasklist = tasklist
        self.summery.final_summery(process_time, tasklist)
        task_output = [task.get_output(include_task_info=self.return_task_info)
                       for task in tasklist]
        return AnyPyProcessOutputList(task_output)

    def _worker(self, task, task_queue):
        """Handle processing of the tasks."""
        with _thread_lock:
            task.process_number = self.counter
            self.counter += 1
        if task.output:
            if not task.has_error and task.processtime > 0:
                if not os.path.isfile(task.logfile):
                    task.logfile = ""
                task_queue.put(task)
                return
        try:
            if not os.path.exists(task.folder):
                task.add_error('Could not find folder: {}'.format(task.folder))
                task.logfile = ""
            else:
                tmp_kwargs = dict(mode='a+', prefix=self.logfile_prefix,
                                  suffix='.log', dir=task.folder, delete=False)
                with NamedTemporaryFile(**tmp_kwargs) as logfile:
                    logfile.write('########### MACRO #############\n')
                    logfile.write("\n".join(task.macro))
                    logfile.write('\n\n######### OUTPUT LOG ##########')
                    logfile.flush()
                    task.logfile = logfile.name
                    starttime = time.clock()
                    exe_args = dict(macro=task.macro,
                                    logfile=logfile,
                                    anybodycon_path=self.anybodycon_path,
                                    timeout=self.timeout,
                                    keep_macrofile=self.keep_logfiles,
                                    env=self.env)
                    try:
                        retcode = execute_anybodycon(**exe_args)
                    finally:
                        endtime = time.clock()
                        logfile.seek(0)
                        task.processtime = endtime - starttime
                    if retcode in (_KILLED_BY_ANYPYTOOLS, _NO_LICENSES_AVAILABLE):
                        task.processtime = 0
                        task.add_error('Error: Non zero return code: {}'.format(retcode))
                        return
                    task.output = parse_anybodycon_output(
                        logfile.read(),
                        self.ignore_errors,
                        self.warnings_to_include)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            task.add_error(str(exc_type) + '\n' + str(fname) +
                           '\n' + str(exc_tb.tb_lineno))
            logger.debug(str(e))
        finally:
            if not self.keep_logfiles and not task.has_error:
                try:
                    silentremove(logfile.name)
                    task.logfile = ""
                except OSError as e:
                    pass  # Ignore if AnyBody has not released the log file.
            task_queue.put(task)

    def _schedule_processes(self, tasklist, _worker):
        # Reset the global flag that allows
        global _stop_all_processes
        _subprocess_container.stop_all = False
        # Make a shallow copy of the task list,
        # so we don't mess with the callers list.
        tasklist = copy.copy(tasklist)
        number_tasks = len(tasklist)
        if number_tasks == 0:
            totaltime = 0
            return totaltime
        use_threading = (number_tasks > 1 and self.num_processes > 1)
        starttime = time.clock()
        task_queue = Queue()
        pbar = _ProgressBar(number_tasks, self.silent)
        pbar.animate(0)
        processed_tasks = []
        n_errors = 0
        threads = []
        try:
            # run while there is still threads, tasks or stuff in the queue
            # to process
            while threads or tasklist or task_queue.qsize():
                # if we aren't using all the processors AND there is still
                # data left to compute, then spawn another thread
                if (len(threads) < self.num_processes) and tasklist:
                    if use_threading:
                        t = Thread(target=_worker,
                                   args=tuple([tasklist.pop(0), task_queue]))
                        t.daemon = True
                        t.start()
                        threads.append(t)
                    else:
                        _worker(tasklist.pop(0), task_queue)
                else:
                    # In the case that we have the maximum number
                    # of running threads or we run out tasks.
                    # Check if any of them are done
                    for thread in threads:
                        if not thread.isAlive():
                            threads.remove(thread)
                while task_queue.qsize():
                    task = task_queue.get()
                    if task.has_error:
                        n_errors += 1
                    self.summery.task_summery(task)
                    processed_tasks.append(task)
                    pbar.animate(len(processed_tasks), n_errors)

                time.sleep(0.01)
        except KeyboardInterrupt:
            _display('Processing interrupted')
            _subprocess_container.stop_all = True
            # Add a small delay here. It allows the user to press ctrl-c twice
            # to escape this try-catch. This is usefull when if the code is
            # run in an outer loop which we want to excape as well.
            time.sleep(1)
        totaltime = time.clock() - starttime
        return totaltime

    def cleanup_logfiles(self, tasklist):
        for task in tasklist:
            try:
                if not self.keep_logfiles and not task.has_error:
                    if task.logfile:
                        silentremove(task.logfile)
                        task.logfile = ""
                if task.processtime <= 0 and task.logfile:
                    silentremove(task.logfile)
                    task.logfile = ""
            except OSError as e:
                logger.debug('Could not remove '
                             '{} {}'.format(task.logfile, str(e)))
            if not self.keep_logfiles:
                try:
                    macrofile = task.logfile.replace('.log', '.anymcr')
                    silentremove(macrofile)
                except OSError as e:
                    logger.debug('Could not removing '
                                 '{} {}'.format(macrofile, str(e)))


class _ProgressBar:
    def __init__(self, iterations, silent=False):
        self.silent = silent
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 40
        if run_from_ipython() and not self.silent:
            self.bar_widget = ipywidgets.IntProgress(
                min=0, max=iterations, value=0, bar_style='')
            self.bar_description = ipywidgets.Label('')
            box = ipywidgets.HBox([self.bar_description, self.bar_widget])
            box.layout.align_items = 'center'
            display(box)

    def animate(self, val, failed=0):
        if self.silent:
            return
        if run_from_ipython():
            self._widget_animate(val, failed)
        else:
            self._ascii_animate(val, failed)

    def _widget_animate(self, val, failed):
        self.bar_widget.value = val
        self.bar_description.value = '%d of %s' % (val, self.iterations)
        if failed > 0:
            self.bar_widget.bar_style = 'danger'
        elif val == self.iterations:
            self.bar_widget.bar_style = 'success'

    def _ascii_animate(self, val, failed):
        self.__update_amount((val / float(self.iterations)) * 100.0)
        self.prog_bar += '  %d of %s complete' % (val, self.iterations)
        if failed == 1:
            self.prog_bar += ' ({0} Error)'.format(failed)
        elif failed > 1:
            self.prog_bar += ' ({0} Errors)'.format(failed)
        print('\r', end="")
        print(self.prog_bar, end="")
        sys.stdout.flush()

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[{}{}]'.format(
            self.fill_char * num_hashes,
            ' ' * (all_full - num_hashes)
        )
        pct_place = int(len(self.prog_bar) / 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done

        self.prog_bar = self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])
