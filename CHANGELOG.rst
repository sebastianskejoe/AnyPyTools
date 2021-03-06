=====================
AnyPyTools Change Log
=====================

.. current developments

**New:**

**Changed:**

**Fixed:**

**Removed:**

v0.10.10
=============

** fixed: ** 

-  Fix crash when ``--define`` option was not provided.



v0.10.9
=============

** New: ** 

-  Add option to the pytest plugin, to set the define statements with an argument to pytest.


v0.10.8
=============

** Fixed: ** 

- Wrong error report when AnyBody exists abnormally during batch processing.



v0.10.7
=============

** Changed: ** 

- Always append 'exit' command to all macros. Seems to solve problem with AMS not shutting down correctly.

- Only enable pytest plugin on Windows platform


v0.10.6
=============

** Fixed: ** 

- Bug where no AMS license was not detected as a failed macro.


v0.10.5
=============

** Fixed: ** 

- Crash when the starting pytest plug-in when no AnyBody licenses are available

**New:**

- Pytest plugin support for the ``ANYBODY_PATH_AMMR`` path statement which will be
  used in the AMS 7.1



v0.10.4
=============

** Changed: ** 

- The pytest plugin can now get the BM configurations directly from the 
  AMMR if they are availble. The will be for AMMR 2. This will eliminate
  the problem of keeping AnyPyTools in sync with the AMMR.


v0.10.3
=============

** New: ** 

- Update pytest plugin to support AMMR 2.0 Parameters. AMMR 1 parameters 
  are still supported using ``--ammr-version`` argument to pytest.


v0.10.2
=============

**New:**

- Support new BodyModel statements, which starts and end with a underscore. 


**Changed:**

 - Improved exception handling when trying to access data which 
   is not avaible in the output.

- Detect if AnyBodyCon exited from a license problem and report
  that in the log files.

- Refactor ``_execute_anybodycon()`` into a public function.

**Removed:**
 
 - Remove the deprecated ``disp`` argument to the ``AnyPyProcess`` class. 


v0.10.1
=============

**Changed:**

- Updates and fixes to the documentation website.
- Added flake8 testing on Travis CI
- Fix crash using pytest on systems where git is not installed.


v0.10.0
=============

**Merged pull requests:**

-  Fix PEP8 issues and remaining pytest issues
   `#21 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/21>`__
   (`melund <https://github.com/melund>`__)
-  Update Documentaion and tutorials
   `#20 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/20>`__
   (`melund <https://github.com/melund>`__)
-  Add SaveData MacroCommand for saving hdf5 files
   `#19 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/19>`__
   (`melund <https://github.com/melund>`__)
-  Fix Crash on Python 2.7 when using h5py_wrapper
   `#18 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/18>`__
   (`melund <https://github.com/melund>`__)
-  Setup Travis-CI for building documentation for publishing on github.io
   `#13 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/13>`__
   (`melund <https://github.com/melund>`__)
-  Refactor the library for the new library documention.
   `#12 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/12>`__
   (`melund <https://github.com/melund>`__)
-  Added ``AnyPyProcessOutputList.tolist()`` converting results to native Python 
   `#11 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/11>`__
   (`KasperPRasmussen <https://github.com/KasperPRasmussen>`__)


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.7...master)

v0.9.7
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.6...0.9.7)

v0.9.6
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.5...0.9.6)


v0.9.5
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.4...0.9.5)


v0.9.4
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.3...0.9.4)

v0.9.3
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.2...0.9.3)

v0.9.2
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.1...0.9.2)

v0.9.1
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.0...0.9.1)

v0.9.0
=============



[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.3...0.9.0)


v0.8.3
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.2...0.8.3)


v0.8.2
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.1...0.8.2)

v0.8.1
=============



[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.0...0.8.1)

v0.8.0
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.7.9...0.8.0)

<v0.8
=============
The before times... See GitHub for a full 
[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.1...0.8.0)