import numpy as np
from pyod.models.iforest import IForest
from pyod.models.knn import KNN
import matplotlib.pyplot as plt
from sklearn import tree
import math

file = open("frames.csv")
frames = file.read()
file.close()
frames = [np.array([float(col) for col in row.split(",") if len(col) > 0]) for row in frames.strip().split("\n")]
frames = [frame for frame in frames if frame[2] < 20000]
x = np.array(frames)
forest = IForest(max_samples=len(x))
forest.fit(x)
print(forest.feature_importances_)
outliers = forest.predict(x)

knn = KNN(method="median") # default is k=5 neighbors
knn.fit(x)
knnOutliers = knn.predict(x)

# # Latitude vs Longitude KNN
# plt.figure()
# plt.scatter(x[:, 1], x[:, 0],  c=knnOutliers, cmap='coolwarm', s=50)
# plt.title("Latitude vs Longitude KNN")
# plt.xlabel("Longitude")
# plt.ylabel("Latitude")
# plt.show()

# # Altitude vs Climb Gradient KNN
# plt.figure()
# plt.scatter(x[:, 3], x[:, 2],  c=knnOutliers, cmap='coolwarm', s=50)
# plt.title("Latitude vs Longitude KNN")
# plt.xlabel("Longitude")
# plt.ylabel("Latitude")
# plt.show()

# # Latitude vs Longitude IForest
# plt.figure()
# plt.scatter(x[:, 1], x[:, 0],  c=outliers, cmap='coolwarm', s=50)
# plt.title("Latitude vs Longitude IForest")
# plt.xlabel("Longitude")
# plt.ylabel("Latitude")
# plt.show()

# # Altitude vs Climb Gradient IForest
# plt.figure()
# plt.scatter(x[:, 3], x[:, 2], c=outliers, cmap='coolwarm', s=50)
# plt.title("Altitude vs Climb Gradient IForest")
# plt.xlabel("Climb Gradient")
# plt.ylabel("Altitude")
# plt.show()

fig, axs = plt.subplots(2, 2, figsize=(12, 10))

# Latitude vs Longitude KNN
axs[0, 0].scatter(x[:, 1], x[:, 0], c=knnOutliers, cmap='coolwarm', s=50)
axs[0, 0].set_title("Latitude vs Longitude KNN")
axs[0, 0].set_xlabel("Longitude")
axs[0, 0].set_ylabel("Latitude")

# Altitude vs Climb Gradient KNN
axs[0, 1].scatter(x[:, 3], x[:, 2], c=knnOutliers, cmap='coolwarm', s=50)
axs[0, 1].set_title("Altitude vs Climb Gradient KNN")
axs[0, 1].set_xlabel("Climb Gradient")
axs[0, 1].set_ylabel("Altitude")

# Latitude vs Longitude IForest
axs[1, 0].scatter(x[:, 1], x[:, 0], c=outliers, cmap='coolwarm', s=50)
axs[1, 0].set_title("Latitude vs Longitude IForest")
axs[1, 0].set_xlabel("Longitude")
axs[1, 0].set_ylabel("Latitude")

# Altitude vs Climb Gradient IForest
axs[1, 1].scatter(x[:, 3], x[:, 2], c=outliers, cmap='coolwarm', s=50)
axs[1, 1].set_title("Altitude vs Climb Gradient IForest")
axs[1, 1].set_xlabel("Climb Gradient")
axs[1, 1].set_ylabel("Altitude")

plt.tight_layout()
plt.show()

print("IForest Outlier Predictions:")
classifier = tree.DecisionTreeClassifier(max_depth=4)
classifier.fit(x, outliers)
tree.plot_tree(classifier)
print(tree.export_text(classifier, class_names=["normal", "anomaly"], feature_names=["latitude", "longitude", "altitude", "climb gradient"]))

print("KNN Outlier Predictions:")
print("KNN Decision Scores:")
print(knn.decision_scores_)
print("Threshold value:")
print(knn.threshold_)