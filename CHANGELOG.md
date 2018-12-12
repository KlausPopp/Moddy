# ChangeLog
All notable changes to moddy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

