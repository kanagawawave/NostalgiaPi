import os
import logging
from tracker import PlayedTracker
from models import Config
from datetime import datetime
import mpv

class PlaylistManager:
    """
    Wraps MPV player, tracks (file and category) so we can mark
    played items via MPV's end-file event.
    """
    def __init__(self, config: Config, tracker: PlayedTracker):
        logging.debug("Init PlaylistManager")
        self.config = config            # store config so we can use it later
        self.tracker = tracker          # store tracker
        logging.debug("Create MPV instance")
        mpv_opts = config.system.mpv_options or {}
        logging.debug(f"MPV options from config: {mpv_opts}")
        self.instance = mpv.MPV(**mpv_opts)

        # Playlist to track files and categories
        self.playlist = []
        self.current_index = 0

        # map file path to category
        self.category_by_path: dict[str, str] = {}

        # attach end event
        logging.debug("Setup MPV Event for end-file")
        @self.instance.event_callback('end-file')
        def on_end_file(event):
            self.on_media_end(event)

    def on_media_end(self, event):

        logging.debug("Begin on_media_end")
        
        if self.current_index >= len(self.playlist):
            return
        
        path = self.playlist[self.current_index]
        logging.debug(f"path is: {path}")
        
        category = self.category_by_path.get(path)
        logging.debug(f"category is: {category}")

        # Normalize path
        path = os.path.normpath(path)
        logging.debug(f"path is {path}")

        # Determine active schedule at the current time
        now = datetime.now()
        logging.debug(f"datetime now is: {now}")
        active_schedule = self.config.get_active_schedule_at(now)
        logging.debug(f"active schedule retrieved")
        if active_schedule:
            logging.debug(f"Get schedule name")
            schedule_name = next((n for n, s in self.config.schedules.items() if s is active_schedule),"global")
            logging.debug(f"schedule name is {schedule_name}")
        else:
            logging.debug(f"no active schedule! set to 'global'")
            schedule_name = "global"

        if category:
            logging.debug(f"Finished: {path} ({category}),  marking played under schedule '{schedule_name}'")
            self.tracker.mark_played(schedule_name, path, category)
        else:
            logging.debug(f"Finished: {path} (unknown category)")
        
        # Move to next item
        self.current_index += 1
        if self.current_index < len(self.playlist):
            next_file = self.playlist[self.current_index]
            self.instance.play(next_file)

    def add_to_playlist(self, file_path: str, category: str):
        logging.debug(f"Begin add_to_playlist")
        self.playlist.append(file_path)
        self.category_by_path[file_path] = category
        logging.debug(f"{file_path} ({category}) added to playlist, total items: {len(self.playlist)}")

    def start_playback(self):
        logging.debug(f"Begin start_playback")
        if len(self.playlist) == 0:
            logging.debug("Playlist empty! returning")
            return
        self.current_index = 0
        self.instance.play(self.playlist[0])
        logging.debug("Playback started")

    def stop_playback(self):
        logging.debug(f"Begin stop_playback")
        self.instance.stop()
        logging.debug("Playback stopped")

    # def set_fullscreen(self, enable: bool):
    #     logging.debug(f"Begin set_fullscreen")
    #     self.instance.fullscreen = enable
    #     logging.debug(f"Fullscreen set to {enable}")