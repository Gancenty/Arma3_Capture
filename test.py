import open3d as o3d
import numpy as np
import time

# 创建随机点云生成函数
def generate_random_point_cloud(num_points=1000):
    """生成随机点云"""
    points = np.random.rand(num_points, 3)  # 在 [0, 1) 范围内生成随机点
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(points)
    return point_cloud

# 初始化可视化窗口
vis = o3d.visualization.Visualizer()
vis.create_window(window_name="实时随机点云", width=800, height=600)

# 创建初始点云并添加到可视化窗口
initial_pcd = generate_random_point_cloud()
vis.add_geometry(initial_pcd)

try:
    while True:
        # 随机更新点云数据
        new_pcd = generate_random_point_cloud()
        initial_pcd.points = new_pcd.points
        
        # 更新点云数据并刷新窗口
        vis.update_geometry(initial_pcd)
        vis.poll_events()
        vis.update_renderer()
        
        # 控制刷新频率
        time.sleep(0.1)  # 每 0.1 秒刷新一次
except KeyboardInterrupt:
    print("实时渲染已停止。")
finally:
    vis.destroy_window()
