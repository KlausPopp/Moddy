# ChangeLog
All notable changes to moddy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2019-04-03

### Added
- Allow to specify a part's ports in the constructor
- Sequential programs: Allow to pass the program's function to the vThread/vSimpleProg constructor (target parameter)
- waitForMsg() method for Queuing ports
- Allow to bind multi output ports to one input port
- simulator smartBind() method to bind all ports in a single call

### Changed
- all tutorials to use new comfort functions (smartBind, waitForMsg, creation of ports via constructor)
- Remove timeouts between simulator thread and vThreads, otherwise debugging impossible

## [1.7.1] - 2019-03-24

### Added
- First installation via pip

## [1.7.2] - 2019-03-26

### Fixed
- Threads that are initially preempted lose incoming messages on ports

## [1.7.1] - 2019-03-24

### Added
- First installation via pip

## [1.7.0] - 2019-03-21

### Added
- Installation via pip 

### Changed
- Documentation changed from .docx/pdf to Sphinx
- Internal directory structure: seqDiagInteractiveViewer now below moddy/

## [1.6.1] - 2019-01-16

### Added
- iaViewer 0.8: search function 

## [1.6.0] - 2019-01-06

### Changed
- iaViewer 0.7: Fix time marker handling. Markers toggle their appearance with every click. Time delta now displayed in headline.

- Simulator speed improved by approx factor 4..5: Replaced msg-passing deepcopy by pickle. Use specialized queues and heaps, replaced slow exec() calls.

### Added
- waitUntil() API for vThreads
- Allow vThread wait() API to wait for IOPorts (not only input ports) 

## [1.5.1] - 2018-12-21
### Changed
- vThread communication timeout increased to 20s (was 2s, too short for heavily loaded systems)
- vThread: Corrected term "queing" -> "queuing" in port names and method names. The old miss-spelled name is still supported in queue names (not method names)

### Added
- iaViewer 0.6: Support time markers.
- support for model assertions: models can call assertionFailed(). Simulator by default stops on assertionFailure. Use 
- Update User Manual 

## [1.5.0] - 2018-12-19
### Changed
- iaViewer 0.5: Improved responsitivity: Handles now huge drawings by using deferred drawing. Support assertion failures. Fixed vScroll bug.

### Added
- support for model assertions: models can call assertionFailed(). Simulator by default stops on assertionFailure. Use sim.run(stopOnAssertionFailure=False) to override this. Simulator displays a list of all assertion failures at end of simulation  
- Support remote controllable vThreads: Create a vThread with remoteController=True and the vThread will have then a moddy port "threadControlPort" which expects "start" or "kill" messages. Unlike normal vThreads, remoteControlled threads do not start automatically, but are waiting for "start" command. If a thread is terminated, all pending timers are stopped, all receive queues are cleared and no messages can be received while terminated. 
- New tutorial: 6_vthreadRemoteControlled.py to demonstrate remote controllable vThreads and model assertions 
- Allow vThreads to exit their main loop: in that case, the thread is dead (a remoteControlled thread may be restarted)
- simPart.time() as a shortcut for models (models can call self.time() instead of self._sim.time())  
- support sim.run(maxEvents=None) for infinite number of events.
- commonly used status box appearance colors bcXXX, e.g. bcWhiteOnRed (see moddy/__init__.py)

### Fixed
- simulator's incorrect stop time handling. Sometimes, last event has not been processed
- simulator now terminates correctly (without a timeout) when a model thread throws an exception 


## [1.4.2] - 2018-12-12
### Changed
- iaViewer 0.3: Improved responsitivity: Removed limitation where labels are no more placed when more than 100 labels visible. Only a few Labels are now placed in each animationframe.

## [1.4.1] - 2018-11-20
### Fixed
- iaViewer 0.2: Watched variables were not shown if the part containing variable was not shown
- Exception if output files were in current directory (and not in a subdirectory)

## [1.4.0] - 2018-11-19
### Added 
- iaViewer 0.2: Part boxes can now be moved (dragged) on
- For all output files, create intermediate missing directories to output files

### Fixed
- Sequence Diagram Interactive Viewer: Hangups while time zooming
- Sequence Diagram Interactive Viewer: improved performance
- Model structure graph generation was broken for ports with vtIOPorts (double connections were shown)
 

## [1.3.99] - 2018-11-12
### Added
- Alpha version 0.1 of sequence diagram interactive Viewer
- Support messages to self (not shown in static SD)
- Support ioPort loopBind()

## [1.3.0] - 2017-08-30
### Added
- Variable watching support
- Lost Messages support
- Target Trace Import feature

## [1.2.0] - 2017-03-26

