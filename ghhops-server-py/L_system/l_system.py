import rhino3dm
import math

def unitize_vector(vector):
    length = math.sqrt(vector.X**2 + vector.Y**2 + vector.Z**2)
    
    if length == 0:
        raise ValueError("向量的长度为零，不能归一化")
    return rhino3dm.Vector3d(vector.X / length, vector.Y / length, vector.Z / length)

def rotate_vector(vector, angle, axis):
    """
    使用旋转矩阵旋转向量
    :param vector: Vector3d 对象
    :param angle: 旋转角度（弧度）
    :param axis: 绕该轴旋转
    :return: 旋转后的向量
    """
    axis = unitize_vector(axis)
    cos_theta = math.cos(angle)
    sin_theta = math.sin(angle)
    one_minus_cos = 1.0 - cos_theta

    x, y, z = axis.X, axis.Y, axis.Z

    # 3x3 旋转矩阵
    rotation_matrix = [
        [cos_theta + x*x*one_minus_cos, x*y*one_minus_cos - z*sin_theta, x*z*one_minus_cos + y*sin_theta],
        [y*x*one_minus_cos + z*sin_theta, cos_theta + y*y*one_minus_cos, y*z*one_minus_cos - x*sin_theta],
        [z*x*one_minus_cos - y*sin_theta, z*y*one_minus_cos + x*sin_theta, cos_theta + z*z*one_minus_cos]
    ]

    new_x = rotation_matrix[0][0]*vector.X + rotation_matrix[0][1]*vector.Y + rotation_matrix[0][2]*vector.Z
    new_y = rotation_matrix[1][0]*vector.X + rotation_matrix[1][1]*vector.Y + rotation_matrix[1][2]*vector.Z
    new_z = rotation_matrix[2][0]*vector.X + rotation_matrix[2][1]*vector.Y + rotation_matrix[2][2]*vector.Z

    return rhino3dm.Vector3d(new_x, new_y, new_z)

def cross_product(v1, v2):
    """
    计算两个三维向量的叉积
    :param v1: Vector3d 对象
    :param v2: Vector3d 对象
    :return: 叉积后的 Vector3d 对象
    """
    cross_x = v1.Y * v2.Z - v1.Z * v2.Y
    cross_y = v1.Z * v2.X - v1.X * v2.Z
    cross_z = v1.X * v2.Y - v1.Y * v2.X
    return rhino3dm.Vector3d(cross_x, cross_y, cross_z)

def l_system(axiom, rules, iterations):
    current_string = axiom
    for _ in range(int(iterations)):
        next_string = ''.join([rules[char] if char in rules else char for char in current_string])
        current_string = next_string
    return current_string

def lsystem_to_paths(lstring, angle, step_length):
    stack = []
    position = rhino3dm.Point3d(0, 0, 0)
    heading = rhino3dm.Vector3d(0, 1, 0)  # 初始方向
    points = [position]
    
    for char in lstring:
        if char == 'F':
            new_position = rhino3dm.Point3d(position.X + heading.X * step_length, 
                                            position.Y + heading.Y * step_length, 
                                            position.Z + heading.Z * step_length)
            points.append(new_position)
            position = new_position
        elif char == '+':
            heading = rotate_vector(heading,angle * math.pi / 180, rhino3dm.Vector3d(0,0,1)) #顺时针旋转
        elif char == '-':
            heading = rotate_vector(heading, -angle * math.pi / 180, rhino3dm.Vector3d(0,0,1)) #逆时针旋转
        elif char == '[':
            stack.append((position, heading))
        elif char == ']':
            position, heading = stack.pop()
            points.append(position)  # 确保路径连续
    return points

def points_to_mesh(points):
    mesh = rhino3dm.Mesh()
    for i, pt in enumerate(points):
        mesh.Vertices.Add(pt.X, pt.Y, pt.Z)
        if i > 0 and i < len(points) -1:
            mesh.Faces.AddFace(i - 1, i, (i + 1) % len(points))
    return mesh

def l_system_3d(axiom, rules, iterations, angle, distance):
    """
    基于 L-system 生成三维几何体
    :param axiom: 初始符号串
    :param rules: 替换规则
    :param iterations: 迭代次数
    :param angle: 旋转角度（单位为弧度）
    :param distance: 每次前进的距离
    :return: 顶点列表
    """
    stack = []
    current_position = rhino3dm.Point3d(0, 0, 0)
    current_direction = rhino3dm.Vector3d(1, 0, 0)  # 初始方向向量
    current_up = rhino3dm.Vector3d(0, 0, 1)         # Z 轴方向（用来确定3D空间中的旋转）
    
    points = [current_position]  # 用来存储生成的点

    # 迭代生成规则
    result = axiom
    for _ in range(int(iterations)):
        result = "".join([rules.get(c, c) for c in result])

    # 遍历生成后的 L-system 字符串
    for char in result:
        if char == 'F':
            # 前进并绘制线段
            new_position = rhino3dm.Point3d(
                current_position.X + current_direction.X * distance,
                current_position.Y + current_direction.Y * distance,
                current_position.Z + current_direction.Z * distance
            )
            points.append(new_position)
            current_position = new_position
        elif char == '+':
            # 绕当前up方向顺时针旋转
            current_direction = rotate_vector(current_direction, angle, current_up)
        elif char == '-':
            # 绕当前up方向逆时针旋转
            current_direction = rotate_vector(current_direction, -angle, current_up)
        elif char == '&':
            # 向下旋转 around X-axis
            axis_x = cross_product(current_direction, current_up)
            current_direction = rotate_vector(current_direction, angle, axis_x)
        elif char == '^':
            # 向上旋转 around X-axis
            axis_x = cross_product(current_direction, current_up)
            current_direction = rotate_vector(current_direction, -angle, axis_x)
        elif char == '[':
            # 保存当前状态
            stack.append((current_position, current_direction))
        elif char == ']':
            # 恢复保存的状态
            current_position, current_direction = stack.pop()
    return points