import time
import asyncio
from gi.repository import Gst
import pyds

class AnalyticsProbe:
    def __init__(self, alarm_client, event_loop, threshold_count=4, check_interval_seconds=30):
        self.alarm_client = alarm_client
        self.event_loop = event_loop
        self.threshold_count = threshold_count
        self.check_interval_seconds = check_interval_seconds
        self.last_check_time = time.time()

    def nvanalytics_src_pad_buffer_probe(self, pad, info, u_data):
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval_seconds:
            gst_buffer = info.get_buffer()
            if not gst_buffer:
                return Gst.PadProbeReturn.OK
            batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
            l_frame = batch_meta.frame_meta_list
            should_trigger = False
            while l_frame:
                try:
                    frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
                except StopIteration:
                    break
                object_count = 0
                l_obj = frame_meta.obj_meta_list
                while l_obj:
                    try:
                        obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                    except StopIteration:
                        break
                    l_user_meta = obj_meta.obj_user_meta_list
                    while l_user_meta:
                        try:
                            user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)
                            if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):
                                user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)
                                if user_meta_data.roiStatus:
                                    object_count += 1
                        except StopIteration:
                            break
                        l_user_meta = l_user_meta.next
                    l_obj = l_obj.next
                if object_count < self.threshold_count:
                    should_trigger = True
                l_frame = l_frame.next
            if should_trigger:
                asyncio.run_coroutine_threadsafe(self.alarm_client.trigger_alarm(), self.event_loop)
            self.last_check_time = current_time
        return Gst.PadProbeReturn.OK