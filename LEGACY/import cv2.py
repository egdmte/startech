import cv2
import numpy as np

# Load or generate an RGB image
rgb_img = cv2.imread("input.jpg")

# The one-liner channel swap (RGB -> BGR or BGR -> RGB)
bgr_img = rgb_img[:, :, ::-1]

# Display side-by-side to compare original vs swapped channels
comparison = np.hstack((rgb_img, bgr_img))

cv2.imshow("Original vs BGR Swapped Channel", comparison)
cv2.waitKey(0)
cv2.destroyAllWindows()