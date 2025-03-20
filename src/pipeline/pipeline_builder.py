import gi
import logging
from typing import List

gi.require_version('Gst', '1.0')
from gi.repository import Gst

from ..alerts.alarm_client import AlarmClient
from ..pipeline.source_bin import SourceBin
from ..pipeline.element_factory import ElementFactory
from ..pipeline.pipeline_config import PipelineConfig
from ..analytics.analytics_probe import AnalyticsProbe
from ..utils.exceptions import PipelineError

class PipelineBuilder:
    def __init__(self, config: dict, event_loop):
        self.config = PipelineConfig(config)
        self.element_factory = ElementFactory()

        alarm_uri = config['pipeline']['alarm']['uri']
        self.alarm_client = AlarmClient(alarm_uri)
        self.analytics_probe = AnalyticsProbe(self.alarm_client, event_loop)
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_pipeline(self, uris: List[str]) -> Gst.Pipeline:
        pipeline = Gst.Pipeline.new("logiscanre-analytics-pipeline")
        if not pipeline:
            raise PipelineError("Unable to create Pipeline")

        streammux = self.element_factory.create_element('nvstreammux', 'Stream-muxer')
        pipeline.add(streammux)
        for i, uri in enumerate(uris):
            source_bin = SourceBin(i, uri).create()
            if not source_bin:
                raise PipelineError(f"Unable to create source bin for {uri}")
            pipeline.add(source_bin)
            sinkpad = streammux.request_pad_simple(f"sink_{i}")
            if not sinkpad:
                raise PipelineError(f"Unable to get sink pad from streammux for source {i}")
            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                raise PipelineError(f"Unable to get src pad from source bin for source {i}")
            srcpad.link(sinkpad)

        queues = [self.element_factory.create_element("queue", f"queue{i + 1}") for i in range(7)]
        self._add_elements_to_pipeline(pipeline, queues)

        elements = self._create_elements()
        self._configure_elements(streammux, elements, len(uris))
        self._add_elements_to_pipeline(pipeline, elements)
        self._link_elements(streammux, queues, elements)

        nvanalytics_src_pad = elements[2].get_static_pad("src")
        if not nvanalytics_src_pad:
            raise PipelineError("Unable to get src pad from nvanalytics")
        else:
            nvanalytics_src_pad.add_probe(Gst.PadProbeType.BUFFER,
                                          self.analytics_probe.nvanalytics_src_pad_buffer_probe, 0)

        return pipeline

    def _create_elements(self) -> List[Gst.Element]:
        return [
            self.element_factory.create_element('nvinfer', 'primary-inference'),
            self.element_factory.create_element('nvtracker', 'tracker'),
            self.element_factory.create_element('nvdsanalytics', 'analytics'),
            self.element_factory.create_element('nvmultistreamtiler', 'nvtiler'),
            self.element_factory.create_element('nvvideoconvert', 'convertor'),
            self.element_factory.create_element('nvdsosd', 'onscreendisplay'),
            self.element_factory.create_element('nveglglessink', 'nvvideo-renderer')
        ]

    def _add_elements_to_pipeline(self, pipeline: Gst.Pipeline, elements: List[Gst.Element]):
        for element in elements:
            pipeline.add(element)

    def _link_elements(self, streammux: Gst.Element, queues: List[Gst.Element], elements: List[Gst.Element]):
        try:
            streammux.link(queues[0])
            queues[0].link(elements[0])
            elements[0].link(queues[1])
            queues[1].link(elements[1])
            elements[1].link(queues[2])
            queues[2].link(elements[2])
            elements[2].link(queues[3])
            queues[3].link(elements[3])
            elements[3].link(queues[4])
            queues[4].link(elements[4])
            elements[4].link(queues[5])
            queues[5].link(elements[5])
            elements[5].link(queues[6])
            queues[6].link(elements[6])
        except Exception as e:
            raise PipelineError(f"Failed to link elements: {e}")

    def _configure_elements(self, streammux: Gst.Element, elements: List[Gst.Element], num_sources: int):
        pgie, nvtracker, nvdsanalytics, nvtiler, nvvidconv, nvosd, sink = elements

        self.config.configure_streammux(streammux, num_sources)
        self.config.configure_pgie(pgie, num_sources)
        self.config.configure_tracker(nvtracker)
        self.config.configure_analytics(nvdsanalytics)
        self.config.configure_tiler(nvtiler, num_sources)
        self.config.configure_sink(sink)
        self.config.configure_osd(nvosd)