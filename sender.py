import zmq
import numpy as np
import time

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://127.0.0.1:5555")

while True:
    # 生成随机点云数据
    point_cloud = np.random.rand(1000, 3).astype(np.float32)  # 1000 个随机点

    # 发送数据
    socket.send(point_cloud.tobytes())

    time.sleep(0.05)  # 每 50 毫秒发送一次
