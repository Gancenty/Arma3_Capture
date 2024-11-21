import os
import zmq
import json
import time
import random
import pickle
import logging
import threading
import numpy as np
import open3d as o3d
from vispy import app, visuals, scene


class Arma3_PointsCloud:
    def __init__(
        self,
        uav_name,
        store_path="./PointsCloud",
        color_file_path="./color_dict.json",
        object_file_path="./object_list.pkl",
    ):
        self.received_cnt = 0
        self.uav_name = uav_name
        self.zmq_sub_port = 7777
        self.zmq_pub_port = 7778
        self.communication_port = 7779

        self.is_finnished = False
        self.data_lock = threading.Lock()
        self.store_path = store_path
        self.color_file_path = color_file_path
        self.object_file_path = object_file_path
        self.color_dict = None
        self.object_list = None

        self.load_object_list()
        self.load_color_dict()
        self.init_zmq()
        self.setup_logger()
        self.init_open3d()
        self.start_thread()

    def load_color_dict(self):
        if os.path.exists(self.color_file_path):
            with open(self.color_file_path, "r") as file:
                color_dict = json.load(file)
                color_dict = {int(k): v for k, v in color_dict.items()}
                self.color_dict = color_dict
        else:
            self.color_dict = {}
            self.save_color_dict()
        print(f"load color dict len: {len(self.color_dict)}")

    def save_color_dict(self):
        color_dict_str_keys = {str(k): v for k, v in self.color_dict.items()}
        with open(self.color_file_path, "w") as file:
            json.dump(color_dict_str_keys, file, sort_keys=True, indent=4)

    def get_unique_color(self, index):
        if index not in self.color_dict:
            while True:
                color = [random.randint(0, 255) for _ in range(3)]
                if color not in self.color_dict.values():
                    self.color_dict[index] = color
                    break
        return self.color_dict[index]

    def load_object_list(self):
        if os.path.exists(self.object_file_path):
            with open(self.object_file_path, "rb") as file:
                self.object_list = pickle.load(file)
        else:
            self.object_list = []
            self.save_object_list()
        print(f"load object list len: {len(self.object_list)}")

    def save_object_list(self):
        with open(self.object_file_path, "wb") as file:
            pickle.dump(self.object_list, file)

    def setup_logger(self, log_file="app.log", log_level=logging.INFO):
        logger = logging.getLogger("Logger")
        logger.setLevel(log_level)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        self.logger = logger

    def init_zmq(self):
        sub_context = zmq.Context()
        self.pcl_sub_socket = sub_context.socket(zmq.SUB)
        self.pcl_sub_socket.connect(f"tcp://localhost:{self.zmq_sub_port}")
        self.pcl_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        pub_context = zmq.Context()
        self.pcl_pub_socket = pub_context.socket(zmq.PUB)
        self.pcl_pub_socket.bind(f"tcp://127.0.0.1:{self.zmq_pub_port}")

        com_context = zmq.Context()
        self.com_socket = com_context.socket(zmq.SUB)
        self.com_socket.connect(f"tcp://localhost:{self.communication_port}")
        self.com_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def init_open3d(self):
        self.point_cloud = o3d.geometry.PointCloud()

    def start_thread(self):
        time.sleep(1)
        self.threads = []
        self.threads.append(threading.Thread(target=self.parse_pointcloud, daemon=True))
        self.threads.append(threading.Thread(target=self.communication, daemon=True))
        # self.threads.append(threading.Thread(target=self.vis_update, daemon=True))
        for thread in self.threads:
            thread.start()

    def parse_pointcloud(self):
        while True:
            try:
                while True:
                    self.latest_msg = self.pcl_sub_socket.recv()

                    rec_data = np.frombuffer(self.latest_msg, dtype=np.float32)
                    rec_data = rec_data.reshape(-1, 4)
                    points = rec_data[:, :3]
                    colors_class = rec_data[:, 3].astype(int)

                    if points.shape[0] == 0:
                        print("no points cloud")
                        continue

                    colors = np.array(
                        [
                            np.array(self.get_unique_color(class_id), dtype=np.float32)
                            / 255.0
                            for class_id in colors_class
                        ]
                    )
                    with self.data_lock:
                        self.point_cloud.points = o3d.utility.Vector3dVector(points)
                        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)
                        if self.received_cnt == points.shape[0]:
                            o3d.io.write_point_cloud(
                                f"{time.time()}.ply", self.point_cloud
                            )
                            self.is_finnished = True
                            self.pcl_pub_socket.send_string(str([0, 0]))
                            print("Rec:%d" % (points.shape[0]))
                            # self.point_cloud = generate_random_point_cloud()
            except zmq.Again:
                time.sleep(0.01)

    def communication(self):
        while True:
            try:
                while True:
                    data = self.com_socket.recv_string(zmq.NOBLOCK)
                    if data[0] == "Y":
                        with self.data_lock:
                            print("Truth:%s" % (data[1:]))
                            self.received_cnt = eval(data[1:])
                    if data[0] == "I":
                        self.object_list = eval(data[1:])
                        print(
                            "Color_Len:%d,Object_Len:%d"
                            % (len(self.color_dict), len(self.object_list))
                        )
            except zmq.Again:
                pass


def generate_random_point_cloud(num_points=1000):
    """生成随机点云"""
    points = np.random.rand(num_points, 3)  # 在 [0, 1) 范围内生成随机点
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(points)
    return point_cloud


if __name__ == "__main__":
    points_cloud_store_path = r"./PointsCloud"
    color_file_path = r".\PointsCloud\color_dict.json"
    object_file_path = r".\PointsCloud\object_list.pkl"
    pcl = Arma3_PointsCloud(
        "uav1",
        store_path=points_cloud_store_path,
        color_file_path=color_file_path,
        object_file_path=object_file_path,
    )

    while True:
        time.sleep(5)
    # 创建 VisPy 可视化窗口
    # canvas = scene.SceneCanvas(
    #     keys="interactive", show=True, title="Point Cloud Viewer"
    # )
    # canvas.bgcolor = "white"
    # view = canvas.central_widget.add_view()
    # view.camera = "turntable"  # 支持旋转/缩放操作

    # # 使用点图 (MarkersVisual) 渲染点云
    # scatter = scene.visuals.Markers()
    # view.add(scatter)

    # def update(event):
    #     """实时更新点云数据"""
    #     with pcl.data_lock:
    #         if pcl.is_finnished:
    #             pcl.is_finnished = False
    #             pc_array = np.asarray(pcl.point_cloud.points)
    #             scatter.set_data(
    #                 pc_array,
    #                 face_color=(0, 0, 0, 0.5),
    #                 edge_color=None,
    #                 size=10,
    #             )
    #             view.camera.azimuth = 1
    #             view.camera.center = pc_array[0]
    #             canvas.update()

    # # 定义更新频率
    # timer = app.Timer()
    # timer.connect(update)
    # timer.start(0.016)  # 大约每秒更新 60 次

    # # 运行应用
    # app.run()

    while pcl.is_finnished == False:
        time.sleep(0.001)

    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Real-Time Point Cloud Viewer", width=800, height=600)
    points = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
    vis_pcd = o3d.geometry.PointCloud()
    vis_pcd.points = o3d.utility.Vector3dVector(points)

    initial_pcd = generate_random_point_cloud()
    vis.add_geometry(initial_pcd)

    try:
        while True:
            with pcl.data_lock:
                if pcl.is_finnished:
                    pcl.is_finnished = False
                    # new_pcd = generate_random_point_cloud()
                    initial_pcd.points = pcl.point_cloud.points
            vis.update_geometry(initial_pcd)
            vis.poll_events()
            vis.update_renderer()
            vis.reset_view_point()
            time.sleep(0.01)
    except KeyboardInterrupt:
        vis.destroy_window()
        print("Exiting")
