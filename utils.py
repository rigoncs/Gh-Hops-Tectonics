import cv2
import rhino3dm

def get_mesh_by_grey_map(height_factor: float):
    image = cv2.imread('imgs/grey_test.png', cv2.IMREAD_GRAYSCALE)
    # resized_image = cv2.resize(image, (image.shape[1] * scale_factor, image.shape[0] * scale_factor), interpolation=cv2.INTER_CUBIC)
    height, width = image.shape
    print(height)
    mesh = rhino3dm.Mesh()

    for y in range(height):
        for x in range(width):
            z = image[y, x] *height_factor  # z为对应像素的灰度值 0-255之间，缩放用作高度
            mesh.Vertices.Add(x, y, z)

    for y in range(height - 1):
        for x in range(width - 1):
            v0 = y * width + x
            v1 = v0 + 1
            v2 = (y + 1) * width + x
            v3 = v2 + 1
            
            mesh.Faces.AddFace(v0, v1, v3)
            mesh.Faces.AddFace(v0, v3, v2)
    return mesh