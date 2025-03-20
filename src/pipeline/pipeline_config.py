import configparser
import logging
import math


class PipelineConfig:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def configure_streammux(self, streammux, num_sources: int):
        streammux.set_property('width', self.config['pipeline']['streammux']['width'])
        streammux.set_property('height', self.config['pipeline']['streammux']['height'])
        streammux.set_property('batch-size', num_sources)
        streammux.set_property('batched-push-timeout', self.config['pipeline']['streammux']['batch-timeout'])
        streammux.set_property('live-source', 1)
        streammux.set_property('enable-padding', 0)
        streammux.set_property('nvbuf-memory-type', 0)

    def configure_pgie(self, pgie, num_sources: int):
        pgie.set_property('config-file-path', self.config['pipeline']['pgie']['config-file'])

    def configure_tracker(self, tracker):
        config = configparser.ConfigParser()
        config.read(self.config['pipeline']['tracker']['config-file'])

        for key in config['tracker']:
            if key == 'tracker-width':
                tracker.set_property('tracker-width', config.getint('tracker', key))
            elif key == 'tracker-height':
                tracker.set_property('tracker-height', config.getint('tracker', key))
            elif key == 'gpu-id':
                tracker.set_property('gpu_id', config.getint('tracker', key))
            elif key == 'll-lib-file':
                tracker.set_property('ll-lib-file', config.get('tracker', key))
            elif key == 'll-config-file':
                tracker.set_property('ll-config-file', config.get('tracker', key))

    def configure_analytics(self, analytics):
        analytics.set_property("config-file", self.config['pipeline']['nvdsanalytics']['config-file'])

    def configure_tiler(self, tiler, num_sources: int):
        tiler_rows = int(math.sqrt(num_sources))
        tiler_columns = int(math.ceil((1.0 * num_sources) / tiler_rows))
        tiler.set_property("rows", tiler_rows)
        tiler.set_property("columns", tiler_columns)
        tiler.set_property('width', self.config['pipeline']['tiler']['width'])
        tiler.set_property('height', self.config['pipeline']['tiler']['height'])
        tiler.set_property('gpu-id', 0)
        tiler.set_property('nvbuf-memory-type', 0)

    def configure_sink(self, sink):
        sink.set_property('sync', 0)
        sink.set_property('gpu-id', 0)

    def configure_osd(self, nvosd):
        nvosd.set_property('process-mode', 0)
        nvosd.set_property('display-text', 1)
