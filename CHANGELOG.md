# ChangeLog
All notable changes to moddy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2018-12-19
### Changed
- iaViewer 0.4: Improved responsitivity: Handles now huge drawings by using deferred drawing. Support assertion failures.

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

