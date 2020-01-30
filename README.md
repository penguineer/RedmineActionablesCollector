# Redmine Actionables

An item is actionable when its action can be executed without further
prerequesites. A Redmine ticket is classified as actionable, when the
following apply:
* it is assigned to >>me<<
* it has started (past start date)
* it is not preceeded by other items
* has no open children
* its parent project is not closed

An actionable item can still be blocked, i.e. it may have open actions, but cannot be completed.
