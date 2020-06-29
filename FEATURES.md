# Feature Proposals
### Global download queue concurrency
Currently the queue concurrency only affects albums and playlists. This feature proposes to make it affect single tracks as well. But this needs restructuring the entire queue structure or find a clever way of managing it otherwise.

### Add option to pause all downloads
This is another feature reqeust that needs the entire queue structure redesigned, maybe when "Global download queue concurrency" is added this will be easied to add as well.

### Check if the drive is full
Needs more info. Exceptions not known for all OSs to implement this.

### In app proxy support
Need help on how to implement this using flask and flask-socketio.

### Add search history
Maybe custom code to add it, or maybe just the autocomplete HTML5 thing.

### More options to save the cover files
Add option to select what format the cover gets saved where.
- Separate the png option for Local and Embedded artwork
- Maybe force JPG for Embedded and add option only for Local
- Local option save jpg, png or both

# Approved Features
### Custom HTML right click menu
Currently pywebview disabled rightclicking on their webviews so an HTML custom menu needs to be developed to fix this issue.<br>
This menu should contain:
- Copy & Paste functionality
- Copy release link (on release elemets)
- Add/Remove from favorites
- Move the download formats from the popup to the context menu

### App localization
Still need to find a working setup, possible solutions:
- Translations all in the frontend using js (usefull to have the UI ready to use in other ports of the app)
- Translating the static strings on the server and the dynamic strings in the js (can be challenging finding a standard scheme that works on the backend and the frontend)

# Not Approved Features
### Stream the track instead of just playing the preview
This app is not an alternative client for deezer. It's a music downloader.

### Download larger cover arts than 1800x1800
I know some releases have larger cover arts, but not all of them have it.
The coverart size is capped at 1800 as we know that almost all cover arts are available at that size.
