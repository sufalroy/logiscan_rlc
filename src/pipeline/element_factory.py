import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst
from ..utils.exceptions import PipelineError


class ElementFactory:
    @staticmethod
    def create_element(factory_name: str, name: str) -> Gst.Element:
        element = Gst.ElementFactory.make(factory_name, name)
        if not element:
            raise PipelineError(f"Unable to create element {name}")
        return element
