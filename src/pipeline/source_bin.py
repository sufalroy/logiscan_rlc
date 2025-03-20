import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst
from ..utils.exceptions import PipelineError


class SourceBin:
    def __init__(self, index: int, uri: str):
        self.index = index
        self.uri = uri

    def create(self) -> Gst.Bin:
        bin_name = f"source-bin-{self.index:02d}"
        nbin = Gst.Bin.new(bin_name)
        if not nbin:
            raise PipelineError(f"Unable to create bin {bin_name}")

        uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
        if not uri_decode_bin:
            raise PipelineError(f"Unable to create uridecodebin for {self.uri}")
        uri_decode_bin.set_property("uri", self.uri)
        uri_decode_bin.connect("pad-added", self._cb_newpad, nbin)
        uri_decode_bin.connect("child-added", self._decodebin_child_added, nbin)

        Gst.Bin.add(nbin, uri_decode_bin)
        bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
        if not bin_pad:
            raise PipelineError("Failed to add ghost pad in source bin")
        return nbin

    def _cb_newpad(self, decodebin, decoder_src_pad, data):
        caps = decoder_src_pad.get_current_caps()
        gststruct = caps.get_structure(0)
        gstname = gststruct.get_name()
        source_bin = data
        features = caps.get_features(0)
        if gstname.find("video") != -1:
            if features.contains("memory:NVMM"):
                bin_ghost_pad = source_bin.get_static_pad("src")
                if not bin_ghost_pad.set_target(decoder_src_pad):
                    raise PipelineError("Failed to link decoder src pad to source bin ghost pad")
            else:
                raise PipelineError("Decodebin did not pick nvidia decoder plugin")

    def _decodebin_child_added(self, child_proxy, Object, name, user_data):
        if name.find("decodebin") != -1:
            Object.connect("child-added", self._decodebin_child_added, user_data)
