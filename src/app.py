import os
import sys
import signal
import logging
from pathlib import Path

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logging
from .pipeline.pipeline_builder import PipelineBuilder
from .utils.exceptions import PipelineError


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


class LogiScanRLCApp:
    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_path = Path('/home/developer/Workspace/logiscan_rlc/config/pipeline_config.yaml')
        self.pipeline = None
        self.loop = None

    def run(self):
        try:
            config = ConfigLoader.load(self.config_path)
            Gst.init(None)

            pipeline_builder = PipelineBuilder(config)
            self.pipeline = pipeline_builder.build_pipeline(config['pipeline']['sources'])

            self.loop = GLib.MainLoop()
            self.start_pipeline()
            self.loop.run()
        except Exception as e:
            self.logger.exception(f"Unexpected error: {e}")
            return 1
        return 0

    def start_pipeline(self):
        if not self.pipeline:
            raise PipelineError("Pipeline not initialized")

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_call)

        self.logger.info("Starting pipeline...")
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.logger.info("Stopping pipeline...")
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if self.loop and self.loop.is_running():
            self.loop.quit()

    def _bus_call(self, bus: Gst.Bus, message: Gst.Message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.logger.info("End-of-stream")
            self.stop()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            self.logger.warning(f"Warning: {err}: {debug}")
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Error: {err}: {debug}")
            self.stop()
        return True


def signal_handler(signum, frame):
    print(f"Received signal {signum}. Shutting down...")
    if app:
        app.stop()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app = LogiScanRLCApp()
    exit_code = app.run()
    sys.exit(exit_code)
