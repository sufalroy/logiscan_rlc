import cv2
import yaml
from screeninfo import get_monitors


class RegionDrawer:
    def __init__(self, config_width, config_height):
        self.drawing = False
        self.points = []
        self.config_width = config_width
        self.config_height = config_height

    def draw_polygon(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))
            cv2.circle(param, (x, y), 3, (0, 255, 0), -1)
            if len(self.points) > 1:
                cv2.line(param, self.points[-2], self.points[-1], (0, 255, 0), 2)
            cv2.imshow('Frame', param)

    def scale_polygon(self, frame_width, frame_height):
        scaled_points = []
        for x, y in self.points:
            x_scaled = int(x * self.config_width / frame_width)
            y_scaled = int(y * self.config_height / frame_height)
            scaled_points.append((x_scaled, y_scaled))
        return scaled_points

    def write_roi_rf_format(self, scaled_polygon):
        roi_rf = ';'.join([f"{x};{y}" for x, y in scaled_polygon])
        return roi_rf

    def capture_frame(self, video_source):
        cap = cv2.VideoCapture(video_source)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("Failed to capture frame from video source")
        return frame

    def resize_frame(self, frame):
        screen_width, screen_height = self.get_screen_size()
        frame_height, frame_width = frame.shape[:2]

        scale_width = screen_width / frame_width
        scale_height = screen_height / frame_height
        scale = min(scale_width, scale_height)

        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        resized_frame = cv2.resize(frame, (new_width, new_height))

        return resized_frame

    def get_screen_size(self):
        monitor = get_monitors()[0]
        return monitor.width, monitor.height

    def process_frame(self, frame):
        frame = self.resize_frame(frame)
        cv2.namedWindow('Frame', cv2.WINDOW_NORMAL)
        cv2.setMouseCallback('Frame', self.draw_polygon, frame)

        while True:
            cv2.imshow('Frame', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                if len(self.points) > 2:
                    cv2.line(frame, self.points[-1], self.points[0], (0, 255, 0), 2)
                    cv2.imshow('Frame', frame)
                break
            elif key == 27:
                break

        cv2.destroyAllWindows()

        if self.points:
            frame_height, frame_width = frame.shape[:2]
            scaled_polygon = self.scale_polygon(frame_width, frame_height)
            roi_rf = self.write_roi_rf_format(scaled_polygon)
            print(f"roi-RF: {roi_rf}")

            for i in range(len(scaled_polygon)):
                cv2.line(frame, scaled_polygon[i], scaled_polygon[(i + 1) % len(scaled_polygon)], (0, 255, 0), 2)
            cv2.imshow('Frame with ROI', frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


if __name__ == "__main__":
    config_path = "/home/developer/Workspace/logiscan_rlc/config/pipeline_config.yaml"
    config = load_config(config_path)

    config_width = config['pipeline']['streammux']['width']
    config_height = config['pipeline']['streammux']['height']
    source_uri = config['pipeline']['sources'][0]

    region_drawer = RegionDrawer(config_width, config_height)
    frame = region_drawer.capture_frame(source_uri)
    region_drawer.process_frame(frame)
